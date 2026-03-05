# backend/app/schemas/jro_schema.py
"""
Journal Rule Object (JRO) Pydantic Schemas.

Models for representing parsed journal formatting requirements.
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class LevelStyle(BaseModel):
    font_size: int | None = None
    is_bold: bool | None = None
    is_italic: bool | None = None
    alignment: str | None = None


class HeadingRules(BaseModel):
    numbering_scheme: str | None = None
    capitalization: str | None = None
    levels: dict[int, LevelStyle] = {}


class AbstractRules(BaseModel):
    max_words: int | None = None
    min_words: int | None = None
    structured: bool | None = None
    required_sections: list[str] = []


class LayoutRules(BaseModel):
    font_name: str | None = None
    font_size: int | None = None
    line_spacing: float | None = None
    margins: dict[str, float] = {}  # e.g., {"top": 1.0, "bottom": 1.0}
    columns: int | None = 1


class FigureRules(BaseModel):
    caption_position: Literal["top", "bottom", "any"] = "bottom"
    caption_prefix: str | None = "Figure"
    numbering_format: str | None = "arabic"


class TableRules(BaseModel):
    caption_position: Literal["top", "bottom", "any"] = "top"
    caption_prefix: str | None = "Table"
    border_style: str | None = "simple"


class SectionRequirements(BaseModel):
    required: list[str] = []
    optional: list[str] = []


class JROSchema(BaseModel):
    """Journal Rule Object definition."""
    model_config = ConfigDict(from_attributes=True)

    journal_name: str
    issn: str | None = None
    citation_style: str | None = None
    csl_xml: str | None = None
    heading_rules: HeadingRules
    abstract_rules: AbstractRules
    layout_rules: LayoutRules
    figure_rules: FigureRules
    table_rules: TableRules
    section_requirements: SectionRequirements
    statistical_notation: str | None = None
    extraction_source: str
    extraction_confidence: float
