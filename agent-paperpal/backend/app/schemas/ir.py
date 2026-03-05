# backend/app/schemas/ir.py
"""
Intermediate Representation (IR) schema.

The IR is the canonical internal format that every agent reads and writes.
It represents a structured document with typed elements (title, abstract,
headings, paragraphs, citations, tables, figures, etc.).
"""

from enum import Enum

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    """Types of document elements in the IR."""

    TITLE = "title"
    ABSTRACT = "abstract"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CITATION = "citation"
    REFERENCE = "reference"
    TABLE = "table"
    FIGURE = "figure"
    FIGURE_CAPTION = "figure_caption"
    TABLE_CAPTION = "table_caption"
    LIST_ITEM = "list_item"
    EQUATION = "equation"
    FOOTNOTE = "footnote"
    ACKNOWLEDGMENT = "acknowledgment"
    APPENDIX = "appendix"
    AUTHOR = "author"
    AFFILIATION = "affiliation"
    KEYWORD = "keyword"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class TextRun(BaseModel):
    """A contiguous run of text with uniform formatting."""

    text: str = Field(..., description="The text content")
    bold: bool = Field(default=False)
    italic: bool = Field(default=False)
    underline: bool = Field(default=False)
    superscript: bool = Field(default=False)
    subscript: bool = Field(default=False)
    font_name: str | None = Field(default=None)
    font_size_pt: float | None = Field(default=None)


class IRElement(BaseModel):
    """A single structural element in the document IR."""

    element_id: str = Field(..., description="Unique element identifier")
    element_type: ElementType = Field(..., description="Semantic type of this element")
    content: list[TextRun] = Field(default_factory=list, description="Text runs in this element")
    raw_text: str = Field(default="", description="Plain text content (all runs concatenated)")
    level: int = Field(default=0, description="Heading level (1-6) or nesting depth")
    metadata: dict = Field(default_factory=dict, description="Extra metadata (e.g. citation key)")
    children: list["IRElement"] = Field(default_factory=list, description="Nested sub-elements")


class IRSchema(BaseModel):
    """
    Complete Intermediate Representation of a manuscript.

    This is the shared data contract that flows through all pipeline stages.
    """

    document_title: str = Field(default="", description="Document title")
    authors: list[str] = Field(default_factory=list, description="Author names")
    elements: list[IRElement] = Field(default_factory=list, description="Ordered document elements")
    metadata: dict = Field(default_factory=dict, description="Document-level metadata")
    source_format: str = Field(default="unknown", description="Original file format (docx/pdf/txt)")
    word_count: int = Field(default=0, description="Approximate word count")
