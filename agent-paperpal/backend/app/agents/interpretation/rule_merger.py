# backend/app/agents/interpretation/rule_merger.py
"""
RuleMerger: Combines CSL metadata and LLM-extracted rules into a final JRO.
Ensures consistency and fills gaps with structural defaults.
"""

import logging
import re
from typing import Optional
from app.schemas.jro_schema import (
    JROSchema, HeadingRules, AbstractRules, LayoutRules, 
    FigureRules, TableRules, SectionRequirements
)

logger = logging.getLogger(__name__)

class RuleMerger:
    """
    Merges different extraction paths.
    Csl data for citation, LLM for structural guidelines.
    """

    def merge(self, csl_xml: Optional[str], llm_jro: Optional[JROSchema], style_name: str) -> JROSchema:
        """
        Combine CSL XML and LLM-extracted rules.
        Precedence: LLM for structural rules, CSL for citation string.
        """
        default_jro = self._create_apa_default(style_name)
        
        if not csl_xml and not llm_jro:
            return default_jro

        merged = llm_jro or default_jro
        merged.journal_name = style_name
        
        if csl_xml:
            merged.csl_xml = csl_xml
            if not merged.citation_style:
                title_match = re.search(r'<title>(.*?)</title>', csl_xml)
                if title_match:
                    merged.citation_style = title_match.group(1).lower()

        if csl_xml and llm_jro and llm_jro.extraction_source != "llm_partial":
            merged.extraction_source = "hybrid"
            merged.extraction_confidence = (1.0 + llm_jro.extraction_confidence) / 2.0
        elif csl_xml:
            merged.extraction_source = "csl"
            merged.extraction_confidence = 0.9
        elif llm_jro:
            merged.extraction_source = "llm"
            merged.extraction_confidence = llm_jro.extraction_confidence
            
        return merged

    def _create_apa_default(self, journal_name: str) -> JROSchema:
        """Create a sensible default JRO based on APA 7 requirements."""
        return JROSchema(
            journal_name=journal_name,
            citation_style="apa",
            extraction_source="default_apa",
            extraction_confidence=0.5,
            heading_rules=HeadingRules(
                numbering_scheme="none",
                capitalization="title",
                levels={
                    1: {"is_bold": True, "font_size": 12},
                    2: {"is_bold": True, "is_italic": True, "font_size": 12},
                    3: {"is_bold": False, "is_italic": True, "font_size": 12}
                }
            ),
            abstract_rules=AbstractRules(
                max_words=250,
                structured=False,
                required_sections=[]
            ),
            layout_rules=LayoutRules(
                font_name="Times New Roman",
                font_size=12,
                line_spacing=2.0,
                margins={"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
                columns=1
            ),
            figure_rules=FigureRules(
                caption_position="bottom",
                caption_prefix="Figure",
                numbering_format="arabic"
            ),
            table_rules=TableRules(
                caption_position="top",
                caption_prefix="Table",
                border_style="simple"
            ),
            section_requirements=SectionRequirements(
                required=["Introduction", "Methods", "Results", "Discussion", "References"],
                optional=["Abstract", "Keywords", "Appendix"]
            )
        )
