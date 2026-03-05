# backend/app/schemas/style.py
"""
Style definitions and schemas.
"""

from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict
from app.schemas.jro_schema import HeadingRules, AbstractRules


class StyleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    journal: str
    citation_format: str | None = None


class JROPreviewResponse(BaseModel):
    journal_name: str
    citation_style: str | None = None
    heading_rules: HeadingRules
    abstract_rules: AbstractRules
    extraction_confidence: float
    extraction_source: str
