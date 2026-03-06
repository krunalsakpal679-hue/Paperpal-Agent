# backend/app/api/v1/endpoints/jobs.py
"""
Job management API endpoints.

Handles manuscript formatting job CRUD operations:
- Submit a new formatting job (upload file + specify journal)
- List jobs for the authenticated user
- Get job status and results
- Cancel a running job
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.job import Job, JobStatus

from app.middleware.auth import JWTBearer
from app.services.storage_service import storage_service
from app.worker.tasks import run_pipeline_task

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Response Schemas ────────────────────────────────────────────────────────

class JobCreateResponse(BaseModel):
    """Response after creating a new formatting job."""

    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Detailed job status response."""

    job_id: str
    status: str
    progress_pct: float
    filename: str
    target_journal: str
    output_s3_urls: dict | None = None
    compliance_report: dict | None = None
    change_log: list | None = None
    errors: list | None = None
    created_at: str
    updated_at: str


class JobListItem(BaseModel):
    """Summary item for job listing."""

    job_id: str
    filename: str
    target_journal: str
    status: str
    progress_pct: float
    created_at: str


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=JobCreateResponse,
    status_code=202,
    summary="Submit a new formatting job",
)
async def create_job(
    file: UploadFile = File(..., description="Manuscript file (.docx, .pdf, or .txt)"),
    journal_identifier: str = Form(..., description="Target journal name"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(JWTBearer())
) -> JobCreateResponse:
    """
    Submit a manuscript for formatting to a target journal's guidelines.

    The file is uploaded to S3 and a background Celery task is dispatched
    to run the 5-stage agentic pipeline.
    """
    # Validate file size
    if file.size and file.size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Validate file extension
    allowed_extensions = {".docx", ".pdf", ".txt"}
    file_ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    job_id = str(uuid.uuid4())

    # Upload file to S3
    file_bytes = await file.read()
    s3_key = await storage_service.upload_raw(job_id, file.filename, file_bytes)

    # Create job record
    job = Job(
        id=uuid.UUID(job_id),
        user_id=uuid.UUID(user_id) if user_id and user_id != "guest" else uuid.uuid4(),
        original_filename=file.filename or "unnamed",
        source_format=file.filename.split(".")[-1] if file.filename else "txt",
        journal_identifier=journal_identifier,
        raw_s3_key=s3_key,
        status=JobStatus.queued,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch Celery task
    run_pipeline_task.delay(job_id)

    logger.info("Created job %s for journal '%s'", job_id, journal_identifier)

    return JobCreateResponse(
        job_id=job_id,
        status="queued",
        message=f"Job created. Formatting for '{journal_identifier}' will begin shortly.",
    )


@router.get(
    "/",
    response_model=list[JobListItem],
    summary="List user's formatting jobs",
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(JWTBearer())
) -> list[JobListItem]:
    """List all formatting jobs for the authenticated user."""
    from sqlalchemy import select

    result = await db.execute(
        select(Job).where(Job.user_id == (uuid.UUID(user_id) if user_id != "guest" else Job.user_id)).order_by(Job.created_at.desc()).limit(50)
    )
    jobs = result.scalars().all()

    return [
        JobListItem(
            job_id=str(job.id),
            filename=job.filename,
            target_journal=job.target_journal,
            status=job.status.value,
            progress_pct=job.progress_pct,
            created_at=job.created_at.isoformat(),
        )
        for job in jobs
    ]


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and results",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(JWTBearer())
) -> JobStatusResponse:
    """Get detailed status and results of a specific formatting job."""
    from sqlalchemy import select

    result = await db.execute(
        select(Job).where(Job.id == uuid.UUID(job_id))
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status.value,
        progress_pct=job.progress_pct,
        filename=job.filename,
        target_journal=job.target_journal,
        output_s3_urls=job.output_s3_urls,
        compliance_report=job.compliance_report,
        change_log=job.change_log,
        errors=job.errors,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.post(
    "/{job_id}/cancel",
    summary="Cancel a running job",
)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(JWTBearer())
) -> dict[str, str]:
    """Cancel a formatting job that is currently in progress."""
    from sqlalchemy import select

    result = await db.execute(
        select(Job).where(Job.id == uuid.UUID(job_id))
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.completed, JobStatus.failed):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status.value}'",
        )

    job.status = JobStatus.failed
    await db.flush()

    logger.info("Cancelled job %s", job_id)
    return {"job_id": job_id, "status": "cancelled"}
