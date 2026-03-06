# backend/app/main.py
"""
FastAPI application factory for Agent Paperpal.

Responsibilities:
- CORS middleware configuration
- Lifespan context manager for startup/shutdown (DB + Redis connections)
- Global exception handler
- API router mounting
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.config import settings
from app.database import engine, sessionmanager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle.

    On startup: initialise database connection pool and Redis client.
    On shutdown: dispose of all connections gracefully.
    """
    logger.info("🚀 Agent Paperpal starting up (env=%s)", settings.ENVIRONMENT)

    # Initialise async DB engine
    sessionmanager.init(str(settings.DATABASE_URL))
    logger.info("✅ Database connection pool established")

    # Initialise Redis
    try:
        import redis.asyncio as aioredis

        app.state.redis = aioredis.from_url(
            str(settings.REDIS_URL),
            decode_responses=True,
        )
        await app.state.redis.ping()
        logger.info("✅ Redis connection established")
    except Exception as exc:
        logger.warning("⚠️  Redis connection failed: %s", exc)
        app.state.redis = None

    yield

    # ── Shutdown ────────────────────────────────────────────────────────────
    logger.info("🛑 Agent Paperpal shutting down...")
    if hasattr(app.state, "redis") and app.state.redis:
        await app.state.redis.close()
    await sessionmanager.close()
    logger.info("✅ All connections closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Agent Paperpal",
        description=(
            "Agentic AI system that automatically reformats academic research "
            "manuscripts to comply with journal-specific formatting guidelines."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS Middleware ─────────────────────────────────────────────────────
    origins = ["*"] if settings.is_development else [
        "https://paperpal.com",
        "https://app.paperpal.com",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    # ── Global Exception Handler ────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": type(exc).__name__,
            },
        )

    # ── Mount Routers ───────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


# Application instance used by uvicorn
app = create_app()
