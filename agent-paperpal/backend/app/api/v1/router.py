# backend/app/api/v1/router.py
"""
API v1 router — aggregates all v1 endpoint routers.

All endpoints are prefixed with /api/v1 (set in main.py).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, jobs

api_v1_router = APIRouter()

api_v1_router.include_router(
    health.router,
    tags=["Health"],
)
api_v1_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["Jobs"],
)
