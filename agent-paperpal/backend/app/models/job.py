# backend/app/models/job.py
"""
Job ORM model.

Represents a manuscript formatting job submitted by a user.
Tracks pipeline status, progress, and output artifacts.
"""

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class JobStatus(str, enum.Enum):
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


class Job(Base):
    """Manuscript formatting job."""

    __tablename__ = "jobs"

    # ── Ownership ───────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Job metadata ────────────────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    target_journal: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )
    progress_pct: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # ── S3 references ───────────────────────────────────────────────────────
    input_s3_key: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    output_s3_urls: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # ── Pipeline artifacts (stored as JSON) ─────────────────────────────────
    change_log: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    compliance_report: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    errors: Mapped[list | None] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )

    # ── Error details ───────────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ── Relationships ───────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="jobs",
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, status={self.status}, journal={self.target_journal})>"
