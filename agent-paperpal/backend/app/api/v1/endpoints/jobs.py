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
    status_code=201,
    summary="Submit a new formatting job",
)
async def create_job(
    file: UploadFile = File(..., description="Manuscript file (.docx, .pdf, or .txt)"),
    target_journal: str = Form(..., description="Target journal name"),
    db: AsyncSession = Depends(get_db),
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

    # TODO: Upload file to S3
    s3_key = f"uploads/{job_id}/{file.filename}"

    # Create job record
    job = Job(
        id=uuid.UUID(job_id),
        user_id=uuid.uuid4(),  # TODO: Get from authenticated user
        filename=file.filename or "unnamed",
        target_journal=target_journal,
        input_s3_key=s3_key,
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.flush()

    # TODO: Dispatch Celery task
    # from app.tasks.formatting import format_manuscript_task
    # format_manuscript_task.delay(job_id)

    logger.info("Created job %s for journal '%s'", job_id, target_journal)

    return JobCreateResponse(
        job_id=job_id,
        status="pending",
        message=f"Job created. Formatting for '{target_journal}' will begin shortly.",
    )


@router.get(
    "/",
    response_model=list[JobListItem],
    summary="List user's formatting jobs",
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
) -> list[JobListItem]:
    """List all formatting jobs for the authenticated user."""
    from sqlalchemy import select

    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(50)
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
) -> dict[str, str]:
    """Cancel a formatting job that is currently in progress."""
    from sqlalchemy import select

    result = await db.execute(
        select(Job).where(Job.id == uuid.UUID(job_id))
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status.value}'",
        )

    job.status = JobStatus.CANCELLED
    await db.flush()

    logger.info("Cancelled job %s", job_id)
    return {"job_id": job_id, "status": "cancelled"}
