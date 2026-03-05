# backend/app/services/renderer.py
"""
RendererService — Converts transformed IR to output formats.

Takes the final transformed_ir and generates:
1. A formatted .docx file using python-docx
2. A LaTeX source file
3. Uploads both to S3 and returns signed URLs

This is NOT an agent node — it runs after Stage 5 (ValidationAgent).
"""

import logging
from io import BytesIO

from app.schemas.ir import IRSchema
from app.schemas.jro import JROSchema

logger = logging.getLogger(__name__)


class RendererService:
    """Renders transformed IR into .docx and LaTeX output formats."""

    def __init__(self, s3_client=None) -> None:
        """
        Initialise the renderer.

        Args:
            s3_client: Optional boto3/aioboto3 S3 client for uploads.
        """
        self._s3_client = s3_client

    async def render_docx(
        self,
        ir: IRSchema,
        jro: JROSchema,
    ) -> BytesIO:
        """
        Convert IR to a formatted .docx file.

        Args:
            ir: The transformed intermediate representation.
            jro: Journal rules to apply for formatting.

        Returns:
            BytesIO buffer containing the .docx file.
        """
        logger.info("Rendering .docx for '%s'", ir.document_title)

        # TODO: Implement using python-docx
        # 1. Create Document()
        # 2. Set page margins from jro.margins
        # 3. Set default font from jro.body_font
        # 4. Iterate elements, apply formatting based on element_type
        # 5. Handle citations, references, figures, tables

        buffer = BytesIO()
        # Placeholder: write empty docx
        buffer.write(b"PK")  # .docx is a ZIP archive
        buffer.seek(0)
        return buffer

    async def render_latex(
        self,
        ir: IRSchema,
        jro: JROSchema,
    ) -> str:
        """
        Convert IR to LaTeX source.

        Args:
            ir: The transformed intermediate representation.
            jro: Journal rules for formatting commands.

        Returns:
            LaTeX source as a string.
        """
        logger.info("Rendering LaTeX for '%s'", ir.document_title)

        # TODO: Implement LaTeX generation
        # 1. Build preamble from jro (documentclass, packages, margins)
        # 2. Iterate elements, convert to LaTeX commands
        # 3. Handle bibliography style from jro.references

        latex = (
            f"\\documentclass{{article}}\n"
            f"\\title{{{ir.document_title}}}\n"
            f"\\begin{{document}}\n"
            f"\\maketitle\n"
            f"% Content placeholder\n"
            f"\\end{{document}}\n"
        )
        return latex

    async def upload_to_s3(
        self,
        job_id: str,
        docx_buffer: BytesIO,
        latex_content: str,
        bucket: str,
    ) -> dict[str, str]:
        """
        Upload rendered files to S3 and return signed URLs.

        Args:
            job_id: Job UUID for organizing S3 keys.
            docx_buffer: The rendered .docx file.
            latex_content: The rendered LaTeX source.
            bucket: Target S3 bucket name.

        Returns:
            Dictionary mapping format names to signed S3 URLs.
        """
        logger.info("Uploading outputs for job %s to S3 bucket '%s'", job_id, bucket)

        # TODO: Implement S3 upload with aioboto3
        # 1. Upload docx_buffer to s3://bucket/outputs/{job_id}/manuscript.docx
        # 2. Upload latex_content to s3://bucket/outputs/{job_id}/manuscript.tex
        # 3. Generate presigned URLs for both

        return {
            "docx": f"https://{bucket}.s3.amazonaws.com/outputs/{job_id}/manuscript.docx",
            "latex": f"https://{bucket}.s3.amazonaws.com/outputs/{job_id}/manuscript.tex",
        }
