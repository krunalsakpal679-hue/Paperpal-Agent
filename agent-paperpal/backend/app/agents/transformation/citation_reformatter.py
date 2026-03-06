# backend/app/agents/transformation/citation_reformatter.py
"""
CitationReformatter: Reformats in-text citations using citeproc-py based on JRO CSL.
"""

import logging
from typing import List, Dict, Any
import io

from citeproc import CitationStylesStyle, CitationStylesBibliography, Citation, CitationItem, formatter
from citeproc.source.json import CiteProcJSON

from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ChangeEntry
from app.schemas.ir import IRSchema, IRElement, ElementType
from .transformer_base import BaseTransformer

logger = logging.getLogger(__name__)

class CitationReformatter(BaseTransformer):
    """
    Transforms in-text citations to match the target journal's CSL style.
    """

    def __init__(self, jro: JROSchema, change_log: List[ChangeEntry]):
        super().__init__(jro, change_log)
        self.style = None
        if self.jro.csl_xml:
            try:
                # citeproc-py can take a file-like object or a path
                csl_file = io.StringIO(self.jro.csl_xml)
                self.style = CitationStylesStyle(csl_file, validate=False)
            except Exception as e:
                logger.error("Failed to load CSL style: %s", e)
        else:
            logger.warning("No CSL XML provided in JRO.")

    def _to_citeproc_json(self, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert internal reference objects to CiteProc JSON format."""
        cp_refs = []
        for ref in references:
            item = {
                "id": ref.get("id"),
                "type": "article-journal", # Defaulting to journal article
                "title": ref.get("title", ""),
                "container-title": ref.get("journal", ""),
                "volume": ref.get("volume", ""),
                "issue": ref.get("issue", ""),
                "page": ref.get("pages", ""),
                "DOI": ref.get("doi", ""),
                "URL": ref.get("url", ""),
            }
            
            # Authors
            authors = ref.get("authors", [])
            cp_authors = []
            for author in authors:
                # Basic split for name if it's a single string
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
            
            # Year
            year = ref.get("year")
            if year:
                item["issued"] = {"date-parts": [[int(year)]]} if str(year).isdigit() else {"raw": year}
            
            cp_refs.append(item)
        return cp_refs

    def transform(self, ir: IRSchema) -> IRSchema:
        """Apply citation reformatting to the IR."""
        if not self.style:
            logger.warning("No CSL style available for citation reformatting.")
            return ir

        references_data = ir.metadata.get("references_parsed", [])
        if not references_data:
            logger.warning("No parsed references found in IR metadata.")
            return ir

        try:
            bib_source = CiteProcJSON(self._to_citeproc_json(references_data))
            bibliography = CitationStylesBibliography(self.style, bib_source, formatter.plain)
            
            # Map elements for easy access
            citations_parsed = ir.metadata.get("citations_parsed", [])
            
            for element in ir.elements:
                if element.element_type == ElementType.PARAGRAPH:
                    # Find citations linked to this paragraph id
                    # Assuming CitationObject has a reference to the element_id or we match by index
                    # In this IR structure, citations are often embedded in raw_text
                    
                    original_text = element.raw_text
                    updated_text = original_text
                    
                    # Look for citations in this paragraph
                    # The DocParseAgent should have provided a mapping
                    paragraph_cits = [c for c in citations_parsed if c.get("paragraph_id") == element.element_id]
                    
                    for cit_obj in paragraph_cits:
                        cit_id = cit_obj.get("id")
                        ref_ids = cit_obj.get("ref_ids", []) # List of reference IDs this citation points to
                        
                        if not ref_ids:
                            continue
                            
                        # Build citeproc citation
                        items = [CitationItem(rid) for rid in ref_ids if rid in bib_source]
                        if not items:
                            continue
                            
                        citation = Citation(items)
                        
                        try:
                            # Registration is required for some styles
                            bibliography.register(citation)
                            new_cit_text = bibliography.cite(citation, logger.warning)
                            
                            # Replace in text
                            # We need to be careful with repeated raw_text
                            find_text = cit_obj.get("raw_text")
                            if find_text and find_text in updated_text:
                                updated_text = updated_text.replace(find_text, new_cit_text, 1)
                                self.record_change(
                                    element.element_id, 
                                    "citation", 
                                    find_text, 
                                    new_cit_text, 
                                    f"{self.jro.citation_style} in-text citation format"
                                )
                        except Exception as e:
                            logger.error("Error formatting citation %s: %s", cit_id, e)
                    
                    element.raw_text = updated_text
                    # Also update content runs if necessary (simplified for now as raw_text update)
                    if element.content:
                        # For now, just update the first run or clear and add one
                        from app.schemas.ir import TextRun
                        element.content = [TextRun(text=updated_text)]
                            
        except Exception as e:
            logger.exception("Citation reformatting failed: %s", e)
            
        return ir

    def reformat_all(self, ir: IRSchema) -> IRSchema:
        return self.transform(ir)
