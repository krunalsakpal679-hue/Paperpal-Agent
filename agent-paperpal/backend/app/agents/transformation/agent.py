# backend/app/agents/transformation/agent.py
"""
TransformAgent: Orchestrates the transformation stage of the document pipeline.
Applies various formatting transformers in sequence to produce a publication-ready IR.
"""

import logging
import copy
from datetime import datetime
from typing import List

from app.schemas.job_state import JobState, JobStatus, AgentError, ChangeEntry
from app.services.cache_service import cache_service

from .citation_reformatter import CitationReformatter
from .reference_builder import ReferenceListBuilder
from .heading_formatter import HeadingFormatter
from .abstract_formatter import AbstractFormatter
from .layout_adjuster import LayoutAdjuster
from .figure_table_formatter import FigureTableFormatter

logger = logging.getLogger(__name__)

class TransformAgent:
    """
    Orchestrates the conversion of an annotated IR into a transformed IR
    based on the Journal Rule Object (JRO).
    """

    async def run(self, state: JobState) -> JobState:
        """
        Execute the transformation pipeline stage.
        """
        if not state.annotated_ir or not state.jro:
            logger.error("[%s] annotated_ir or jro missing from JobState.", "TransformAgent")
            state.errors.append(AgentError(
                agent="TransformAgent",
                error_type="ValueError",
                message="Transformation requires both annotated_ir and jro to be populated.",
                recoverable=False
            ))
            state.status = JobStatus.FAILED
            return state

        logger.info("[%s] Starting transformation for job: %s", "TransformAgent", state.job_id)
        state.status = JobStatus.TRANSFORMING
        state.progress_pct = 65.0

        try:
            # 1. Initialize transformation state
            # Ensure we don't mutate state.annotated_ir directly
            ir = state.annotated_ir.model_copy(deep=True)
            jro = state.jro
            change_log: List[ChangeEntry] = []

            # 2. Run sequential transformers
            # The order matters for consistency
            CitationReformatter(jro, change_log).reformat_all(ir)
            ReferenceListBuilder(jro, change_log).rebuild(ir)
            HeadingFormatter(jro, change_log).format_all(ir)
            AbstractFormatter(jro, change_log).format(ir)
            LayoutAdjuster(jro, change_log).adjust(ir)
            FigureTableFormatter(jro, change_log).format_all(ir)

            # 3. Finalize state
            state.transformed_ir = ir
            state.change_log = change_log
            state.progress_pct = 80.0
            
            # 4. Publish progress
            await cache_service.publish_progress(state.job_id, {
                "agent": "transformation",
                "status": "processing",
                "progress": 80,
                "message": f"Transformation complete: {len(change_log)} stylistic changes applied."
            })
            
            logger.info(
                "[%s] Transformation completed for %s — changes applied: %d", 
                "TransformAgent", state.job_id, len(change_log)
            )

        except Exception as e:
            logger.exception("[%s] Unexpected error during transformation: %s", "TransformAgent", e)
            state.errors.append(AgentError(
                agent="TransformAgent",
                error_type=type(e).__name__,
                message=str(e),
                recoverable=True
            ))
            state.status = JobStatus.FAILED

        return state

async def run_stage4(state: JobState) -> JobState:
    """LangGraph node helper for Stage 4."""
    agent = TransformAgent()
    return await agent.run(state)
