# backend/app/api/v1/router.py
"""
API v1 router — aggregates all v1 endpoint routers.

All endpoints are prefixed with /api/v1 (set in main.py).
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, jobs, results, styles
from app.api.websocket import router as ws_router

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
api_v1_router.include_router(
    results.router,
    prefix="/jobs",
    tags=["Results"],
)
api_v1_router.include_router(
    styles.router,
    prefix="/styles",
    tags=["Styles"],
)
api_v1_router.include_router(
    ws_router,
    tags=["WebSockets"],
)
