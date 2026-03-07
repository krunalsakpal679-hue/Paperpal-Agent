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

async def get_session_factory():
    try:
        return sessionmanager.session_factory
    except RuntimeError:
        sessionmanager.init(str(settings.DATABASE_URL))
        return sessionmanager.session_factory

async def _run_pipeline_async(job_id: str):
    logger.error(f"DEBUG: Starting _run_pipeline_async for {job_id}")
    session_factory = await get_session_factory()
    async with session_factory() as db:
        job = await job_service.get_job(db, uuid.UUID(job_id))
        if not job:
            logger.error(f"DEBUG: Job {job_id} not found in DB")
            return
        logger.error(f"DEBUG: Job found: {job.original_filename}")

        # Prepare initial state
        state = JobState(job_id=job_id, status=StateStatus.INGESTING)
        # Using the raw file key in metadata to be available for the ingestion agent
        state.metadata["raw_s3_key"] = job.raw_s3_key
        state.metadata["source_format"] = job.source_format
        state.metadata["journal_identifier"] = job.journal_identifier

    try:
        # Run standard LangGraph invocation
        # Since we passed a JobState instance, we receive a JobState instance back
        logger.info(f"[%s] Invoking pipeline for job %s", "Worker", job_id)
        final_state: JobState = await pipeline.ainvoke(state)
        
        # Save results back to DB
        async with session_factory() as db:
            if final_state.errors:
                logger.error(f"Pipeline reported errors for job {job_id}: {final_state.errors}")
                # Mark as failed if any error exists
                await job_service.update_status(db, uuid.UUID(job_id), JobStatus.failed, 100.0)
                
                # Update job with the first error message for quick visibility
                job = await job_service.get_job(db, uuid.UUID(job_id))
                if job:
                    job.error_message = final_state.errors[0].message
                    await db.commit()
            else:
                s3_urls = final_state.output_s3_urls
                compliance_score = 0.0
                if final_state.compliance_report:
                    compliance_score = final_state.compliance_report.overall_score
                
                result_dict = {
                    "compliance_score": compliance_score,
                    "total_changes": len(final_state.change_log),
                    "output_s3_key": s3_urls.get("docx_url"),
                    "latex_s3_key": s3_urls.get("latex_url")
                }
                logger.info(f"[%s] Saving results for job %s. Score: %.2f", "Worker", job_id, compliance_score)
                await job_service.save_result(db, uuid.UUID(job_id), result_dict)

                # ── PUBLISH FINAL COMPLETION ──────────────────────────────────
                # This signal tells the frontend that EVERYTHING is done
                from app.services.cache_service import cache_service
                await cache_service.publish_progress(
                    job_id=job_id,
                    event_dict={
                        "status": "completed",
                        "progress": 100,
                        "message": "Manuscript polishing complete! Navigating to results...",
                        "agent": "SYSTEM"
                    }
                )
    except Exception as exc:
        logger.exception("Pipeline crashed for job %s: %s", job_id, exc)
        async with session_factory() as db:
            await job_service.update_status(db, uuid.UUID(job_id), JobStatus.failed, 0.0)
        raise exc


@celery.task(bind=True, max_retries=3, retry_backoff=True)
def run_pipeline_task(self, job_id: str):
    logger.error(f"DEBUG: run_pipeline_task START for {job_id}")
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
