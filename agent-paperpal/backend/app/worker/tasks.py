# backend/app/worker/tasks.py
import asyncio
import logging
from celery import shared_task
from app.celery_app import celery
from app.schemas.job_state import JobState, JobStatus as StateStatus
from app.services.job_service import job_service
from app.agents.orchestrator import pipeline
from app.database import sessionmanager
from app.config import settings
from app.models.job import JobStatus
import uuid

logger = logging.getLogger(__name__)

async def get_session():
    try:
        sessionmanager.session_factory
    except RuntimeError:
        sessionmanager.init(str(settings.DATABASE_URL))
    return sessionmanager.session_factory()

async def _run_pipeline_async(job_id: str):
    session_factory = await get_session()
    async with session_factory() as db:
        job = await job_service.get_job(db, uuid.UUID(job_id))
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # Prepare initial state
        state = JobState(job_id=job_id, status=StateStatus.INGESTING)
        # Using the raw file key in metadata to be available for the ingestion agent
        state.metadata["raw_s3_key"] = job.raw_s3_key
        state.metadata["source_format"] = job.source_format
        state.metadata["journal_identifier"] = job.journal_identifier

    try:
        # Run standard LangGraph invocation
        final_state = await pipeline.ainvoke(state)
        
        # Save results back to DB
        async with session_factory() as db:
            if final_state.get("errors"):
                # if there is an error
                await job_service.update_status(db, uuid.UUID(job_id), JobStatus.failed, 100.0)
            else:
                s3_urls = final_state.get("metadata", {}).get("urls", {})
                result_dict = {
                    "compliance_score": final_state.get("validation_score", 0.0),
                    "total_changes": len(final_state.get("change_log", [])),
                    "output_s3_key": s3_urls.get("docx_url"),
                    "latex_s3_key": s3_urls.get("latex_url")
                }
                await job_service.save_result(db, uuid.UUID(job_id), result_dict)
    except Exception as exc:
        logger.exception("Pipeline failed for job %s: %s", job_id, exc)
        async with session_factory() as db:
            await job_service.update_status(db, uuid.UUID(job_id), JobStatus.failed, 0.0)
        raise exc


@celery.task(bind=True, max_retries=3, retry_backoff=True)
def run_pipeline_task(self, job_id: str):
    logger.info("Starting formatting pipeline for job %s", job_id)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(_run_pipeline_async(job_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
