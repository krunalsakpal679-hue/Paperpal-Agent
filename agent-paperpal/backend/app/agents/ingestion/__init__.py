# backend/app/agents/ingestion/__init__.py
"""Stage 1 — Document Ingestion Agent."""

from app.agents.ingestion.agent import DocIngestionAgent, run_ingestion

__all__ = ["DocIngestionAgent", "run_ingestion"]
