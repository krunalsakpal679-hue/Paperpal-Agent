# backend/app/agents/transformation/figure_table_formatter.py
"""
FigureTableFormatter: Reformats figure and table captions based on JRO prefixes.
"""

import logging
import re
from typing import List

from app.schemas.jro_schema import JROSchema
from app.schemas.job_state import ChangeEntry
from app.schemas.ir import IRSchema, IRElement, ElementType, TextRun
from .transformer_base import BaseTransformer

logger = logging.getLogger(__name__)

class FigureTableFormatter(BaseTransformer):
    """
    Reformats and synchronizes figure/table captions with JRO requirements.
    """

    def transform(self, ir: IRSchema) -> IRSchema:
        """Apply figure and table reformatting."""
        figure_rules = self.jro.figure_rules
        table_rules = self.jro.table_rules
        
        # 1. Figure Captions
        fig_prefix = figure_rules.caption_prefix if figure_rules else "Figure"
        for element in ir.elements:
            if element.element_type == ElementType.FIGURE_CAPTION:
                original_text = element.raw_text
                # Match "Fig 1", "Figure 1", "Fig. 1" etc.
                match = re.match(r"^(Fig\.?|Figure)\s*([\w]+)[\.:\s]*(.*)$", original_text, re.IGNORECASE)
                if match:
                    # Capture "Fig", numbering, and original caption text
                    num, content = match.group(2), match.group(3)
                    new_text = f"{fig_prefix} {num}. {content.strip()}"
                    
                    if original_text != new_text:
                        self.record_change(
                            element.element_id, 
                            "figure_caption", 
                            original_text, 
                            new_text, 
                            f"jro.figure_rules: {fig_prefix}"
                        )
                        element.raw_text = new_text
                        element.content = [TextRun(text=new_text)]

        # 2. Table Captions
        tbl_prefix = table_rules.caption_prefix if table_rules else "Table"
        for element in ir.elements:
            if element.element_type == ElementType.TABLE_CAPTION:
                original_text = element.raw_text
                # Match "Tab. 1", "Table 1", "Tab 1" etc.
                match = re.match(r"^(Tab\.?|Table)\s*([\w]+)[\.:\s]*(.*)$", original_text, re.IGNORECASE)
                if match:
                    num, content = match.group(2), match.group(3)
                    new_text = f"{tbl_prefix} {num}. {content.strip()}"
                    
                    if original_text != new_text:
                        self.record_change(
                            element.element_id, 
                            "table_caption", 
                            original_text, 
                            new_text, 
                            f"jro.table_rules: {tbl_prefix}"
                        )
                        element.raw_text = new_text
                        element.content = [TextRun(text=new_text)]

        return ir

    def format_all(self, ir: IRSchema) -> IRSchema:
        return self.transform(ir)
