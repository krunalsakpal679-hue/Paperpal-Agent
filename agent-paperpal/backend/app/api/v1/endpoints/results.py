# backend/app/api/v1/endpoints/results.py
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.job import Job, JobStatus
from app.middleware.auth import JWTBearer
from app.schemas.result import ResultResponse, DiffResponse
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class JROPreviewResponse(BaseModel):
    job_id: str | None = None
    jro_data: dict[str, Any] = {}

@router.get(
    "/{job_id}/result",
    response_model=ResultResponse,
    summary="Get job results"
)
async def get_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(JWTBearer())
) -> ResultResponse:
    result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.completed, JobStatus.failed):
        raise HTTPException(status_code=400, detail=f"Job is not completed yet (status: {job.status})")

    response = ResultResponse(
        job_id=job_id,
        docx_url=job.output_s3_key,
        latex_url=job.latex_s3_key,
        compliance_score=job.compliance_score,
        total_changes=job.total_changes,
    )
    return response

@router.get(
    "/{job_id}/diff",
    response_model=DiffResponse,
    summary="Get job modification diff log"
)
async def get_job_diff(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(JWTBearer())
) -> DiffResponse:
    result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # In production, change_log would likely be fetched from job.change_log
    # or an external JSON file downloaded from an S3 URL.
    return DiffResponse(
        job_id=job_id,
        change_log=[],
        total_changes=job.total_changes or 0
    )


@router.get(
    "/{job_id}/jro-preview",
    response_model=JROPreviewResponse,
    summary="Preview Journal Requirements Object"
)
async def get_job_jro(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(JWTBearer())
) -> JROPreviewResponse:
    result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JROPreviewResponse(
        job_id=job_id,
        jro_data={}
    )
