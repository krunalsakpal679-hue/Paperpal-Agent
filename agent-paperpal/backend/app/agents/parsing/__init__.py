# backend/app/agents/parsing/__init__.py
"""
Stage 2 — DocParseAgent package.

Exports the LangGraph-compatible entry-point and the agent class.
"""

from app.agents.parsing.agent import DocParseAgent, run_parsing

__all__ = ["DocParseAgent", "run_parsing"]
