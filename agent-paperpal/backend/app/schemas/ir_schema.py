# backend/app/schemas/ir_schema.py
"""
Intermediate Representation (IR) Schemas.

The CANONICAL schema for parsed document structures used by all LangGraph agents.
"""

from typing import Literal
from pydantic import BaseModel, Field


class Author(BaseModel):
    name: str | None = None
    affiliation: str | None = None
    email: str | None = None


class Paragraph(BaseModel):
    id: str
    raw_text: str
    element_type: Literal["heading", "paragraph", "list_item", "quote", "unknown"] = "unknown"
    heading_level: int | None = None
    confidence: float | None = Field(default=1.0, ge=0.0, le=1.0)
    style_name: str | None = None
    font_size: int | None = None
    is_bold: bool | None = None
    is_italic: bool | None = None


class RawCitation(BaseModel):
    id: str
    raw_text: str
    position_in_paragraph: int | None = None


class RawReference(BaseModel):
    id: str
    raw_text: str
    position_in_list: int | None = None


class CitationObject(BaseModel):
    id: str
    authors: list[str] = []
    year: str | None = None
    pages: str | None = None
    raw_text: str | None = None
    style_hint: str | None = None


class ReferenceObject(BaseModel):
    id: str
    authors: list[str] = []
    year: str | None = None
    title: str | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    raw_text: str | None = None


class IRTable(BaseModel):
    id: str
    caption: str | None = None
    rows: list[list[str]] = []
    position: int | None = None


class IRFigure(BaseModel):
    id: str
    caption: str | None = None
    s3_key: str | None = None
    alt_text: str | None = None
    position: int | None = None


class Footnote(BaseModel):
    id: str
    anchor_paragraph_id: str | None = None
    text: str


class DocMetadata(BaseModel):
    word_count: int | None = None
    page_count: int | None = None
    language: str | None = None
    detected_heading_count: int | None = None


class IRSchema(BaseModel):
    """The canonical internal representation of a manuscript."""
    job_id: str
    source_format: str
    title: str | None = None
    authors: list[Author] = []
    sections: list[str] = []
    paragraphs: list[Paragraph] = []
    citations_raw: list[RawCitation] = []
    references_raw: list[RawReference] = []
    citations_parsed: list[CitationObject] = []
    references_parsed: list[ReferenceObject] = []
    tables: list[IRTable] = []
    figures: list[IRFigure] = []
    footnotes: list[Footnote] = []
    metadata: DocMetadata | None = None
    detected_style: str | None = None
    style_confidence: float | None = None
