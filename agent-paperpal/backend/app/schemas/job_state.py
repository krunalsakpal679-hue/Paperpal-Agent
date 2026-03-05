# backend/app/schemas/job_state.py
"""
JobState schema — the shared state object for the LangGraph pipeline.

This is the central data contract that flows through all 5 agent stages.
Field names in this file are IMMUTABLE per project convention.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.ir import IRSchema
from app.schemas.jro import JROSchema


class JobStatus(str, Enum):
    """Pipeline job status enumeration."""

    PENDING = "pending"
    INGESTING = "ingesting"
    PARSING = "parsing"
    INTERPRETING = "interpreting"
    TRANSFORMING = "transforming"
    VALIDATING = "validating"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentError(BaseModel):
    """Structured error from any pipeline agent."""

    agent: str = Field(..., description="Agent name that raised the error")
    error_type: str = Field(..., description="Exception class name")
    message: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    recoverable: bool = Field(default=False)


class ChangeEntry(BaseModel):
    """A single formatting change made by the TransformAgent."""

    element_id: str = Field(..., description="ID of the modified IR element")
    field: str = Field(..., description="Field that was changed (e.g. 'font_size_pt')")
    old_value: str = Field(..., description="Previous value")
    new_value: str = Field(..., description="New value after transformation")
    rule_source: str = Field(default="", description="JRO rule that triggered this change")


class ComplianceItem(BaseModel):
    """A single compliance check result."""

    rule: str = Field(..., description="Rule being checked")
    passed: bool = Field(..., description="Whether the check passed")
    message: str = Field(default="", description="Details about the check result")
    severity: str = Field(default="info", description="info | warning | error")


class ValidationReport(BaseModel):
    """Output of the ValidationAgent — full compliance report."""

    total_checks: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    warnings: int = Field(default=0)
    items: list[ComplianceItem] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)


class JobState(BaseModel):
    """
    LangGraph shared state — flows through all pipeline stages.

    ⚠️  NEVER change these field names — they are project-wide contracts.
    """

    job_id: str = Field(..., description="UUID4 job identifier")
    raw_ir: IRSchema | None = Field(default=None)
    annotated_ir: IRSchema | None = Field(default=None)
    jro: JROSchema | None = Field(default=None)
    transformed_ir: IRSchema | None = Field(default=None)
    change_log: list[ChangeEntry] = Field(default_factory=list)
    compliance_report: ValidationReport | None = Field(default=None)
    output_s3_urls: dict[str, str] = Field(default_factory=dict)
    status: JobStatus = Field(default=JobStatus.PENDING)
    errors: list[AgentError] = Field(default_factory=list)
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
