# backend/app/agents/ingestion/agent.py
"""
Stage 1 — DocIngestionAgent.

Reads uploaded manuscripts (.docx, .pdf, .txt) from S3 and converts
them into the raw Intermediate Representation (IR) format.

Input:  job_id + S3 file key
Output: raw_ir (IRSchema)
"""

import logging
from uuid import uuid4

from app.schemas.ir import ElementType, IRElement, IRSchema, TextRun
from app.schemas.job_state import AgentError, JobState, JobStatus

logger = logging.getLogger(__name__)

AGENT_NAME = "DocIngestionAgent"


async def run_ingestion(state: JobState) -> JobState:
    """
    Orchestrator-facing entry point for the ingestion stage.

    Downloads the manuscript from S3, extracts text content,
    and produces a raw IR representation.

    Args:
        state: Current pipeline state with job_id set.

    Returns:
        Updated state with raw_ir populated and status advanced.
    """
    logger.info("[%s] Starting ingestion for job %s", AGENT_NAME, state.job_id)
    state.status = JobStatus.INGESTING
    state.progress_pct = 5.0

    try:
        # TODO: Download file from S3 using job_id
        # TODO: Detect format and invoke appropriate parser
        # For now, create a placeholder IR

        raw_ir = IRSchema(
            document_title="Placeholder — Awaiting Implementation",
            authors=[],
            elements=[
                IRElement(
                    element_id=str(uuid4()),
                    element_type=ElementType.PARAGRAPH,
                    content=[TextRun(text="Document content will be extracted here.")],
                    raw_text="Document content will be extracted here.",
                ),
            ],
            source_format="unknown",
            word_count=0,
        )

        state.raw_ir = raw_ir
        state.progress_pct = 20.0
        logger.info("[%s] Ingestion completed for job %s", AGENT_NAME, state.job_id)

    except Exception as exc:
        error = AgentError(
            agent=AGENT_NAME,
            error_type=type(exc).__name__,
            message=str(exc),
            recoverable=False,
        )
        state.errors.append(error)
        state.status = JobStatus.FAILED
        logger.exception("[%s] Ingestion failed for job %s", AGENT_NAME, state.job_id)

    return state
