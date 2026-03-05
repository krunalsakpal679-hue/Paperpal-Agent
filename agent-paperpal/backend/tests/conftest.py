# backend/tests/conftest.py
"""
Pytest configuration and shared fixtures for backend tests.

Provides async database sessions, test client, and sample data factories.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP test client for the FastAPI app.

    Uses httpx ASGITransport to call the app directly without a server.
    """
    # Import here to avoid triggering settings validation in test env
    import os

    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-16-chars")
    os.environ.setdefault("ENVIRONMENT", "development")

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_job_data() -> dict:
    """Return sample job creation data for tests."""
    return {
        "target_journal": "Nature Communications",
        "filename": "test_manuscript.docx",
    }
