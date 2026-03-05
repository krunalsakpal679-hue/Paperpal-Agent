# backend/app/services/job_service.py
"""
Job service for interaction with database and managing job state.
"""

import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate
from app.schemas.result import ResultResponse
from app.models.user import User


class JobService:
    async def create_job(self, db: AsyncSession, user_id: uuid.UUID, create_schema: JobCreate, s3_key: str, filename: str) -> Job:
        """Create a new job in the database."""
        job = Job(
            user_id=user_id,
            source_format=filename.split(".")[-1],
            original_filename=filename,
            raw_s3_key=s3_key,
            journal_identifier=create_schema.journal_identifier,
            style_name=create_schema.style_name,
            status=JobStatus.queued,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def get_job(self, db: AsyncSession, job_id: uuid.UUID) -> Job | None:
        """Retrieve a specific job."""
        stmt = select(Job).where(Job.id == job_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, db: AsyncSession, job_id: uuid.UUID, status: JobStatus, progress_pct: float) -> None:
        """Update job status and progression."""
        job = await self.get_job(db, job_id)
        if job:
            job.status = status
            job.progress_pct = progress_pct
            await db.commit()

    async def save_result(self, db: AsyncSession, job_id: uuid.UUID, result_dict: dict[str, Any]) -> None:
        """Save results/output data to a job upon completion."""
        job = await self.get_job(db, job_id)
        if job:
            job.compliance_score = result_dict.get("compliance_score")
            job.total_changes = result_dict.get("total_changes")
            job.output_s3_key = result_dict.get("output_s3_key")
            job.latex_s3_key = result_dict.get("latex_s3_key")
            job.status = JobStatus.completed
            job.progress_pct = 100.0
            from datetime import datetime
            job.completed_at = datetime.utcnow()
            await db.commit()

    async def get_result(self, db: AsyncSession, job_id: uuid.UUID) -> ResultResponse | None:
        """Fetch job result."""
        job = await self.get_job(db, job_id)
        if not job or job.status != JobStatus.completed:
            return None
            
        # Dummy structure for now until S3 URL resolvers are wired
        return ResultResponse(
            job_id=str(job.id),
            docx_url=job.output_s3_key,
            latex_url=job.latex_s3_key,
            compliance_score=job.compliance_score,
            total_changes=job.total_changes,
        )


# Singleton
job_service = JobService()
