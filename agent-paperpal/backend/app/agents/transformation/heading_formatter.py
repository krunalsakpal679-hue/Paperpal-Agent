# backend/app/agents/transformation/heading_formatter.py
"""
HeadingFormatter: Applies capitalization and numbering rules to section headings.
"""

import logging
import re
from typing import List

from titlecase import titlecase
from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ChangeEntry
from app.schemas.ir import IRSchema, IRElement, ElementType, TextRun
from .transformer_base import BaseTransformer

logger = logging.getLogger(__name__)

class HeadingFormatter(BaseTransformer):
    """
    Formats section headers based on JRO rules.
    """

    def transform(self, ir: IRSchema) -> IRSchema:
        """Apply heading formatting to the IR."""
        heading_rules = self.jro.heading_rules
        if not heading_rules:
            logger.info("No heading rules provided. Skipping.")
            return ir

        # For numeric numbering, we need to maintain state
        numbering_state = [0, 0, 0, 0, 0, 0] # Levels 1-6

        for element in ir.elements:
            if element.element_type == ElementType.HEADING:
                original_text = element.raw_text
                current_text = original_text
                
                # 1. Clean existing numbering if necessary
                # Match common patterns like "1.", "1.1.", "(a)", "I."
                current_text = re.sub(r"^\s*([0-9A-Za-z\.]+[\.\)]\s*)+", "", current_text).strip()
                
                # 2. Apply Capitalization
                cap_rule = heading_rules.capitalization
                if cap_rule == "title_case":
                    current_text = titlecase(current_text)
                elif cap_rule == "sentence_case":
                    if len(current_text) > 0:
                        current_text = current_text[0].upper() + current_text[1:].lower()
                elif cap_rule == "all_caps":
                    current_text = current_text.upper()
                
                # 3. Apply Numbering Scheme
                num_scheme = heading_rules.numbering_scheme
                if num_scheme == "numeric":
                    level = element.level or 1
                    if level > 0:
                        # Reset child levels
                        for i in range(level, 6):
                            numbering_state[i] = 0
                        # Increment current level
                        numbering_state[level-1] += 1
                        # Create prefix e.g., "1.1"
                        prefix = ".".join(str(n) for n in numbering_state[:level])
                        current_text = f"{prefix} {current_text}"

                # Record change and update
                if original_text != current_text:
                    self.record_change(
                        element.element_id, 
                        "heading", 
                        original_text, 
                        current_text, 
                        f"jro.heading_rules: cap={cap_rule}, num={num_scheme}"
                    )
                    element.raw_text = current_text
                    element.content = [TextRun(text=current_text)]
                    
        return ir

    def format_all(self, ir: IRSchema) -> IRSchema:
        return self.transform(ir)
