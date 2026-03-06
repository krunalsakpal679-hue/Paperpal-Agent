# backend/app/agents/transformation/reference_builder.py
"""
ReferenceListBuilder: Rebuilds the reference list according to the target style JRO.
"""

import logging
from typing import List, Dict, Any, Optional
import io

from citeproc import CitationStylesStyle, CitationStylesBibliography, Citation, CitationItem, formatter
from citeproc.source.json import CiteProcJSON

from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ChangeEntry
from app.schemas.ir import IRSchema, IRElement, ElementType, TextRun
from .transformer_base import BaseTransformer

logger = logging.getLogger(__name__)

class ReferenceListBuilder(BaseTransformer):
    """
    Rebuilds the reference section using citeproc-py based on JRO CSL.
    """

    def __init__(self, jro: JROSchema, change_log: List[ChangeEntry]):
        super().__init__(jro, change_log)
        self.style = None
        if self.jro.csl_xml:
            try:
                csl_file = io.StringIO(self.jro.csl_xml)
                self.style = CitationStylesStyle(csl_file, validate=False)
            except Exception as e:
                logger.error("Failed to load CSL style: %s", e)

    def _to_citeproc_json(self, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Same logic as CitationReformatter for reference formatting."""
        cp_refs = []
        for ref in references:
            item = {
                "id": ref.get("id"),
                "type": "article-journal", 
                "title": ref.get("title", ""),
                "container-title": ref.get("journal", ""),
                "volume": ref.get("volume", ""),
                "issue": ref.get("issue", ""),
                "page": ref.get("pages", ""),
                "DOI": ref.get("doi", ""),
                "URL": ref.get("url", ""),
            }
            authors = ref.get("authors", [])
            item["author"] = [{"family": a.split(",")[-1].strip(), "given": a.split(",")[0].strip()} for a in authors] if "," in str(authors) else [{"family": a, "given": ""} for a in authors]
            
            cp_authors = []
            for author in authors:
                parts = author.split(",")
                if len(parts) == 2:
                    cp_authors.append({"family": parts[0].strip(), "given": parts[1].strip()})
                else:
                    parts = author.split()
                    if len(parts) > 1:
                        cp_authors.append({"family": parts[-1], "given": " ".join(parts[:-1])})
                    else:
                        cp_authors.append({"family": author, "given": ""})
            item["author"] = cp_authors
            
            year = ref.get("year")
            if year:
                item["issued"] = {"date-parts": [[int(year)]]} if str(year).isdigit() else {"raw": year}
            cp_refs.append(item)
        return cp_refs

    def transform(self, ir: IRSchema) -> IRSchema:
        """Apply reference rebuilding to the IR."""
        if not self.style:
            logger.warning("No CSL style available for reference rebuilding.")
            return ir

        references_parsed = ir.metadata.get("references_parsed", [])
        if not references_parsed:
            logger.warning("No parsed references found in IR metadata.")
            return ir

        references_raw_elements = [el for el in ir.elements if el.element_type == ElementType.REFERENCE]
        if not references_raw_elements:
            logger.warning("No reference elements found in IR.")
            return ir

        try:
            bib_source = CiteProcJSON(self._to_citeproc_json(references_parsed))
            bibliography = CitationStylesBibliography(self.style, bib_source, formatter.plain)
            
            # Register all references for the bibliography
            # Need valid ids to avoid KeyError
            for item in references_parsed:
                ref_id = item.get("id")
                if ref_id in bib_source:
                    # Registry is typically through citation items or explicit
                    pass
            
            # In citeproc-py, we usually register citations first, 
            # then call bibliography() to get formatted entries.
            # If we want a full bibliography regardless of citations, 
            # we need to register all keys.
            for ref_id in bib_source:
                citation = Citation([CitationItem(ref_id)])
                bibliography.register(citation)
            
            # bibliography.bibliography() returns an ordered list of formatted entries
            entries = bibliography.bibliography()
            
            # Sort as per JRO if style doesn't handle it (though CSL styles usually do)
            # The bib entries are typically ordered by how they are registered (if numeric) 
            # or by name (if author-year).
            
            # Match each original reference element with its new formatted text
            # This is tricky because indices might have changed due to sorting.
            # For simplicity, we'll replace the first N reference elements with 
            # the formatted entries or replace the whole section.
            
            for i, entry in enumerate(entries):
                if i < len(references_raw_elements):
                    old_text = references_raw_elements[i].raw_text
                    new_text = str(entry).strip()
                    
                    references_raw_elements[i].raw_text = new_text
                    references_raw_elements[i].content = [TextRun(text=new_text)]
                    
                    self.record_change(
                        references_raw_elements[i].element_id, 
                        "reference", 
                        old_text, 
                        new_text, 
                        f"{self.jro.citation_style} reference list format"
                    )
                    
        except Exception as e:
            logger.exception("Reference rebuilding failed: %s", e)
            
        return ir

    def rebuild(self, ir: IRSchema) -> IRSchema:
        return self.transform(ir)
