# backend/app/celery_app.py
"""
Celery application configuration for Agent Paperpal.

Used by the celery_worker service to process long-running
manuscript formatting jobs asynchronously.
"""

from celery import Celery

from app.config import settings

celery = Celery(
    "paperpal",
    broker=settings.CELERY_BROKER_URL,
    backend=str(settings.REDIS_URL),
    include=[
        "app.tasks.formatting",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)
