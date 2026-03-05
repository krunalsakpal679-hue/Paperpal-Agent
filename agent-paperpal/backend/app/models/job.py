# backend/app/models/job.py
"""
Job ORM model.

Stores formatting job metadata and tracking information.
"""

from enum import Enum
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class JobStatus(str, Enum):
    """Execution status of a formatting job."""
    queued = "queued"
    ingesting = "ingesting"
    parsing = "parsing"
    interpreting = "interpreting"
    transforming = "transforming"
    validating = "validating"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


class Job(Base):
    """Formatting Job."""
    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.queued, nullable=False, index=True)
    
    source_format: Mapped[str] = mapped_column(String(10), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    
    raw_s3_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    output_s3_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    latex_s3_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    journal_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    style_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_changes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="jobs")
