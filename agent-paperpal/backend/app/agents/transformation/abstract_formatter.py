# backend/app/agents/transformation/abstract_formatter.py
"""
AbstractFormatter: Performs word count checks and enforces structural labels.
"""

import logging
from typing import List

from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ChangeEntry
from app.schemas.ir import IRSchema, IRElement, ElementType, TextRun
from .transformer_base import BaseTransformer

logger = logging.getLogger(__name__)

class AbstractFormatter(BaseTransformer):
    """
    Validates and formats the abstract section.
    """

    def transform(self, ir: IRSchema) -> IRSchema:
        """Apply abstract formatting and validation."""
        abstract_rules = self.jro.abstract_rules
        if not abstract_rules:
            logger.info("No abstract rules provided. Skipping.")
            return ir

        # Find abstract paragraph(s)
        abstract_paras = [p for p in ir.elements if p.element_type == ElementType.ABSTRACT]
        if not abstract_paras:
            logger.debug("No abstract found in IR.")
            return ir

        for para in abstract_paras:
            # 1. Word Count Check
            word_count = len(para.raw_text.split())
            if abstract_rules.max_words and word_count > abstract_rules.max_words:
                issue = {
                    "rule": "abstract_word_count",
                    "severity": "warning",
                    "message": f"Abstract word count ({word_count}) exceeds journal limit ({abstract_rules.max_words}).",
                    "element_id": para.element_id
                }
                # Initialize issues list in meta if not present
                if "validation_issues" not in ir.metadata:
                    ir.metadata["validation_issues"] = []
                ir.metadata["validation_issues"].append(issue)

            # 2. Structured Sections
            if abstract_rules.structured and abstract_rules.required_sections:
                # Check if it covers common labels
                has_structure = any(para.raw_text.strip().startswith(tuple(abstract_rules.required_sections)))
                if not has_structure:
                    # Prepend each required section label as a prompt/placeholder if empty,
                    # but here we just prepend the first one if it's a single block or 
                    # join them if we want to force structure.
                    # Per prompt: "prepend each section label (Background:, etc.)"
                    old_text = para.raw_text
                    prefix = " ".join([f"{s}:" for s in abstract_rules.required_sections])
                    new_text = f"{prefix} {old_text}"
                    
                    self.record_change(
                        para.element_id, 
                        "abstract", 
                        old_text, 
                        new_text, 
                        "jro.abstract_rules: structured=True"
                    )
                    para.raw_text = new_text
                    para.content = [TextRun(text=new_text)]

        return ir

    def format(self, ir: IRSchema) -> IRSchema:
        return self.transform(ir)
