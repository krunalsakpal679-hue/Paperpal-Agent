# backend/tests/test_health.py
"""Tests for the health check endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(async_client):
    """GET /api/v1/health should return status: ok."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data
    assert "database" in data
    assert "redis" in data
