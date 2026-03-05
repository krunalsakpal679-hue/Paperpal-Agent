# backend/app/schemas/validation_schema.py
"""
Validation and Job State Schemas.

Models for reporting changes, errors, compliance, and the global LangGraph JobState.
"""

from typing import Literal, TypedDict
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from app.models.job import JobStatus
from app.schemas.ir_schema import IRSchema
from app.schemas.jro_schema import JROSchema


class ValidationIssue(BaseModel):
    issue_id: str
    severity: Literal["error", "warning", "info"]
    element_id: str | None = None
    description: str
    rule_ref: str | None = None
    suggestion: str | None = None


class ValidationReport(BaseModel):
    overall_score: float = Field(0.0, ge=0.0, le=100.0)
    category_scores: dict[str, float] = {}
    issues: list[ValidationIssue] = []
    citation_coverage: float = Field(default=0.0)
    reference_coverage: float = Field(default=0.0)
    total_issues: int = 0


class ChangeEntry(BaseModel):
    entry_id: str
    element_id: str | None = None
    element_type: str
    before: str | None = None
    after: str | None = None
    rule_ref: str | None = None
    transformer: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentError(BaseModel):
    agent_name: str
    error_type: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JobState(TypedDict):
    """Global state object passed through the LangGraph agents."""
    job_id: str
    raw_ir: IRSchema | None
    annotated_ir: IRSchema | None
    jro: JROSchema | None
    transformed_ir: IRSchema | None
    change_log: list[ChangeEntry]
    compliance_report: ValidationReport | None
    output_s3_urls: dict[str, str]
    status: JobStatus
    errors: list[AgentError]
    progress_pct: float
