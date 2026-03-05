# backend/app/agents/parse/agent.py
"""
Stage 2 — DocParseAgent.

Uses NLP (spaCy + LLM) to semantically label all elements in the raw IR.
Classifies paragraphs as headings, citations, figure captions, etc.

Input:  raw_ir (IRSchema)
Output: annotated_ir (IRSchema with element_type labels)
"""

import logging

from app.schemas.job_state import AgentError, JobState, JobStatus

logger = logging.getLogger(__name__)

AGENT_NAME = "DocParseAgent"


async def run_parse(state: JobState) -> JobState:
    """
    Orchestrator-facing entry point for the parsing stage.

    Takes the raw IR from Stage 1, runs NLP classification on each element,
    and produces an annotated IR with semantic labels.

    Args:
        state: Pipeline state with raw_ir populated.

    Returns:
        Updated state with annotated_ir populated.
    """
    logger.info("[%s] Starting parse for job %s", AGENT_NAME, state.job_id)
    state.status = JobStatus.PARSING
    state.progress_pct = 25.0

    try:
        if state.raw_ir is None:
            raise ValueError("raw_ir is None — ingestion stage may have failed")

        # TODO: Run spaCy NLP pipeline on each element
        # TODO: Use LLM for ambiguous element classification
        # For now, pass through raw_ir as annotated_ir

        state.annotated_ir = state.raw_ir.model_copy(deep=True)
        state.progress_pct = 40.0
        logger.info("[%s] Parse completed for job %s", AGENT_NAME, state.job_id)

    except Exception as exc:
        error = AgentError(
            agent=AGENT_NAME,
            error_type=type(exc).__name__,
            message=str(exc),
            recoverable=False,
        )
        state.errors.append(error)
        state.status = JobStatus.FAILED
        logger.exception("[%s] Parse failed for job %s", AGENT_NAME, state.job_id)

    return state
