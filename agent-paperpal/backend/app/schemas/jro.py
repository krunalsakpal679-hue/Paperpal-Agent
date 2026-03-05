# backend/app/schemas/jro.py
"""
Journal Rule Object (JRO) schema.

Defines the structured representation of a journal's formatting guidelines.
Extracted by the RuleInterpretAgent and consumed by the TransformAgent.
"""

from pydantic import BaseModel, Field


class FontRule(BaseModel):
    """Font formatting rules."""

    family: str = Field(default="Times New Roman")
    size_pt: float = Field(default=12.0)
    line_spacing: float = Field(default=2.0, description="Line spacing multiplier")
    color: str = Field(default="#000000")


class MarginRule(BaseModel):
    """Page margin rules in inches."""

    top: float = Field(default=1.0)
    bottom: float = Field(default=1.0)
    left: float = Field(default=1.0)
    right: float = Field(default=1.0)


class HeadingRule(BaseModel):
    """Rules for heading formatting at a specific level."""

    level: int = Field(..., ge=1, le=6)
    font: FontRule = Field(default_factory=FontRule)
    bold: bool = Field(default=True)
    italic: bool = Field(default=False)
    numbering: bool = Field(default=False, description="Whether headings are numbered")
    case: str = Field(default="title", description="title | upper | sentence | lower")


class CitationRule(BaseModel):
    """In-text citation formatting rules."""

    style: str = Field(default="numeric", description="numeric | author-year | footnote")
    bracket_type: str = Field(default="square", description="square | round | superscript | none")
    separator: str = Field(default=",", description="Separator between multiple citations")
    max_authors_before_et_al: int = Field(default=3)


class ReferenceRule(BaseModel):
    """Reference list formatting rules."""

    style: str = Field(default="vancouver", description="vancouver | apa | mla | ieee | chicago")
    numbering: bool = Field(default=True)
    hanging_indent: bool = Field(default=False)
    doi_required: bool = Field(default=False)
    order: str = Field(default="cited", description="cited | alphabetical")


class AbstractRule(BaseModel):
    """Abstract section rules."""

    max_words: int | None = Field(default=250)
    structured: bool = Field(default=False, description="Does it require sub-headings?")
    required_sections: list[str] = Field(
        default_factory=list,
        description="e.g. ['Background', 'Methods', 'Results', 'Conclusions']",
    )


class FigureTableRule(BaseModel):
    """Rules for figures and tables."""

    caption_position: str = Field(default="below", description="above | below")
    numbering_style: str = Field(default="arabic", description="arabic | roman")
    caption_font: FontRule = Field(default_factory=FontRule)


class JROSchema(BaseModel):
    """
    Journal Rule Object — complete formatting specification for a target journal.

    This is the output of Stage 3 (RuleInterpretAgent) and the primary input
    for Stage 4 (TransformAgent).
    """

    journal_name: str = Field(..., description="Full journal name")
    journal_issn: str | None = Field(default=None, description="ISSN if available")
    style_guide: str = Field(default="custom", description="Base style (apa/mla/vancouver/ieee/chicago)")

    # ── Formatting rules ────────────────────────────────────────────────────
    body_font: FontRule = Field(default_factory=FontRule)
    margins: MarginRule = Field(default_factory=MarginRule)
    headings: list[HeadingRule] = Field(default_factory=list)
    citation: CitationRule = Field(default_factory=CitationRule)
    references: ReferenceRule = Field(default_factory=ReferenceRule)
    abstract: AbstractRule = Field(default_factory=AbstractRule)
    figures: FigureTableRule = Field(default_factory=FigureTableRule)
    tables: FigureTableRule = Field(default_factory=FigureTableRule)

    # ── Structural rules ────────────────────────────────────────────────────
    title_page_required: bool = Field(default=False)
    running_header: bool = Field(default=False)
    page_numbers: bool = Field(default=True)
    word_limit: int | None = Field(default=None)
    required_sections: list[str] = Field(
        default_factory=lambda: ["Introduction", "Methods", "Results", "Discussion"],
    )

    # ── Raw source ──────────────────────────────────────────────────────────
    raw_guidelines: str = Field(
        default="",
        description="Original unprocessed guidelines text",
    )
