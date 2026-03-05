# backend/app/schemas/job.py
"""
Job request and response schemas.
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid
from app.models.job import JobStatus


class JobCreate(BaseModel):
    journal_identifier: str | None = None
    style_name: str | None = None
    force_refresh: bool = False


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    status: JobStatus
    progress_pct: float
    created_at: datetime
    source_format: str


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    progress_pct: float
    current_agent: str | None = None
    error_message: str | None = None
