# backend/app/services/renderer/renderer_service.py
import subprocess
import tempfile
import json
import logging
from io import BytesIO
import os

from docx.document import Document
from app.schemas.job_state import JobState, JobStatus, AgentError
from app.schemas.ir import ElementType
from app.services.storage_service import storage_service

from .style_applicator import StyleApplicator
from .section_renderer import SectionRenderer
from .table_renderer import TableRenderer
from .figure_renderer import FigureRenderer

class RendererService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.style_applicator = StyleApplicator()
        self.section_renderer = SectionRenderer()
        self.table_renderer = TableRenderer()
        self.figure_renderer = FigureRenderer(storage_service)

    async def render(self, state: JobState) -> dict[str, str]:
        """
        Renders the IR into docx, attempts latex, and uploads to S3.
        Returns a map of signed S3 URLs.
        """
        urls = {}
        if not state.transformed_ir or not state.jro:
             self.logger.error("Missing IR or JRO to render.")
             state.errors.append(AgentError(agent="RendererService", error_type="ValueError", message="Missing IR or JRO"))
             state.status = JobStatus.FAILED
             return urls

        job_id = state.job_id
        
        # 1. Build document styles
        doc: Document = self.style_applicator.build_document_styles(state.jro)
        
        # 2. Iterate elements and route to appropriate renderer
        for el in state.transformed_ir.elements:
            if el.element_type == ElementType.TABLE:
                self.table_renderer.render(doc, el, state.jro)
            elif el.element_type == ElementType.FIGURE:
                await self.figure_renderer.render(doc, el, state.jro)
            else:
                self.section_renderer.render(doc, el)

        # 3. Save DOCX to BytesIO
        docx_buf = BytesIO()
        doc.save(docx_buf)
        docx_bytes = docx_buf.getvalue()

        # Upload DOCX
        docx_key = await storage_service.upload_output(job_id, "formatted.docx", docx_bytes)
        urls["docx_url"] = await storage_service.get_signed_url(docx_key)

        # 4. Save and Upload change log JSON
        changelog_dict_list = [change.model_dump() for change in state.change_log]
        json_bytes = json.dumps(changelog_dict_list, indent=2).encode('utf-8')
        json_key = await storage_service.upload_output(job_id, "changes.json", json_bytes)
        urls["change_log_url"] = await storage_service.get_signed_url(json_key)

        # 5. Try LaTeX Conversion via Pandoc
        with tempfile.TemporaryDirectory() as tempdir:
            docs_path = os.path.join(tempdir, "temp.docx")
            tex_path = os.path.join(tempdir, "temp.tex")
            
            with open(docs_path, "wb") as f:
                f.write(docx_bytes)

            try:
                # Provide pandoc executable path. Will fail gracefully if pandoc isn't installed
                result = subprocess.run(["pandoc", docs_path, "-o", tex_path, "--standalone"], capture_output=True, text=True)
                if result.returncode == 0 and os.path.exists(tex_path):
                     with open(tex_path, "rb") as ft:
                         tex_bytes = ft.read()
                     tex_key = await storage_service.upload_output(job_id, "formatted.tex", tex_bytes)
                     urls["latex_url"] = await storage_service.get_signed_url(tex_key)
                else:
                     self.logger.warning("Pandoc failed with code %d. LaTeX skipped. Error: %s", result.returncode, result.stderr)
                     urls["latex_url"] = None
            except FileNotFoundError:
                self.logger.warning("Pandoc missing from system path. LaTeX generation skipped.")
                urls["latex_url"] = None
                
        # 6. Set Job States
        state.output_s3_urls = urls
        
        return urls
