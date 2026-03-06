# backend/app/agents/transformation/layout_adjuster.py
"""
LayoutAdjuster: Sets document-level formatting metadata for the rendering stage.
"""

import logging
from typing import List

from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ChangeEntry
from app.schemas.ir import IRSchema, IRElement
from .transformer_base import BaseTransformer

logger = logging.getLogger(__name__)

class LayoutAdjuster(BaseTransformer):
    """
    Adjusts document layout metadata based on JRO layout_rules.
    """

    def transform(self, ir: IRSchema) -> IRSchema:
        """Apply layout adjustments to the IR metadata."""
        layout_rules = self.jro.layout_rules
        if not layout_rules:
            logger.info("No layout rules provided. Skipping.")
            return ir

        # Map JRO layout fields to IR metadata
        target_map = {
            "target_font": layout_rules.font_name,
            "target_font_size": layout_rules.font_size,
            "target_line_spacing": layout_rules.line_spacing,
            "target_margins": layout_rules.margins,
            "target_columns": layout_rules.columns
        }

        for key, new_val in target_map.items():
            if new_val is not None:
                old_val = ir.metadata.get(key)
                if old_val != new_val:
                    ir.metadata[key] = new_val
                    self.record_change(
                        "document", 
                        key, 
                        str(old_val), 
                        str(new_val), 
                        f"jro.layout_rules: {key}"
                    )
                    
        return ir

    def adjust(self, ir: IRSchema) -> IRSchema:
        return self.transform(ir)
