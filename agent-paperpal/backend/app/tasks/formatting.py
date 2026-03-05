# backend/app/tasks/formatting.py
"""
Celery task for running the full manuscript formatting pipeline.

This task is dispatched when a user submits a formatting job via the API.
It orchestrates the LangGraph pipeline and updates job status in the database.
"""

import logging
from uuid import UUID

from app.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="paperpal.format_manuscript", max_retries=2)
def format_manuscript_task(self, job_id: str) -> dict[str, str]:
    """
    Execute the full formatting pipeline for a given job.

    Args:
        job_id: UUID of the formatting job to process.

    Returns:
        Dictionary with job_id and final status.
    """
    logger.info("Starting formatting pipeline for job %s", job_id)

    try:
        _job_uuid = UUID(job_id)  # Validate UUID format

        # TODO: Invoke LangGraph pipeline here
        # pipeline = create_pipeline()
        # result = pipeline.invoke({"job_id": job_id})

        logger.info("Formatting pipeline completed for job %s", job_id)
        return {"job_id": job_id, "status": "completed"}

    except Exception as exc:
        logger.exception("Pipeline failed for job %s: %s", job_id, exc)
        raise self.retry(exc=exc, countdown=30)
