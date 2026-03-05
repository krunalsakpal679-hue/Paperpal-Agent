# backend/app/api/v1/endpoints/health.py
"""
Health check endpoint.

Used by Docker healthchecks, load balancers, and monitoring systems
to verify the backend service is running and can reach its dependencies.
"""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    environment: str
    database: str
    redis: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Returns health status of the backend and its dependencies.",
)
async def health_check(request: Request) -> HealthResponse:
    """
    Check the health of the application and its dependencies.

    Returns:
        HealthResponse with status of each dependency.
    """
    from app.config import settings

    # Check Redis connectivity
    redis_status = "disconnected"
    if hasattr(request.app.state, "redis") and request.app.state.redis:
        try:
            await request.app.state.redis.ping()
            redis_status = "connected"
        except Exception as exc:
            logger.warning("Redis health check failed: %s", exc)
            redis_status = "error"

    # Check Database connectivity
    db_status = "connected"  # If we got here, DB is reachable
    try:
        from app.database import sessionmanager

        async with sessionmanager.session_factory() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        db_status = "error"

    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
    )
