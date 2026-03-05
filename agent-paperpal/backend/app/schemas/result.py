# backend/app/schemas/result.py
"""
Result and diff schemas for completed jobs.
"""

from typing import Any
from pydantic import BaseModel
from app.schemas.validation_schema import ChangeEntry, ValidationIssue


class ResultResponse(BaseModel):
    job_id: str
    docx_url: str | None = None
    latex_url: str | None = None
    change_log_url: str | None = None
    compliance_score: float | None = None
    total_changes: int | None = None
    category_scores: dict[str, float] = {}
    issues: list[ValidationIssue] = []


class DiffResponse(BaseModel):
    job_id: str
    change_log: list[ChangeEntry] = []
    total_changes: int = 0
