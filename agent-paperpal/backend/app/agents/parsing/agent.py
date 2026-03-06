# backend/app/agents/parsing/agent.py
"""
Stage 2 — DocParseAgent.

Uses NLP (spaCy + rule-based heuristics) to semantically label all elements
in the raw IR from Stage 1 (DocIngestionAgent) and produces an annotated IR
with citations and references parsed.

Pipeline:
  1. Validate raw_ir is present.
  2. StructureDetector  → annotate element types.
  3. CitationParser     → extract in-text citations.
  4. CitationStyleClassifier → detect dominant reference style.
  5. ReferenceParser    → parse reference section into structured objects.
  6. Store results in state.annotated_ir.
  7. Publish progress { agent: 'parsing', pct: 40 } to Redis.
  8. Return updated state.

Input:  JobState with raw_ir populated (from Stage 1).
Output: JobState with annotated_ir populated and status = PARSING.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.agents.parsing.citation_parser import CitationParser
from app.agents.parsing.citation_style_classifier import (
    CitationStyleClassifier,
    CitationStyleEnum,
)
from app.agents.parsing.reference_parser import ReferenceParser
from app.agents.parsing.structure_detector import StructureDetector
from app.schemas.job_state import AgentError, JobState, JobStatus
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

AGENT_NAME = "DocParseAgent"


class DocParseAgent:
    """
    Stage 2 agent — annotates the raw IR with semantic element labels.

    Usage::
        agent = DocParseAgent()
        updated_state = await agent.run(state)
    """

    def __init__(self, use_spacy: bool = True) -> None:
        self._detector = StructureDetector(use_spacy=use_spacy)
        self._citation_parser = CitationParser()
        self._classifier = CitationStyleClassifier()
        self._ref_parser = ReferenceParser()

    async def run(self, state: JobState) -> JobState:
        """
        Execute the parsing stage.

        Args:
            state: Current pipeline state. Must have raw_ir populated.

        Returns:
            Updated JobState with annotated_ir on success, or
            errors appended and status = FAILED on failure.
        """
        logger.info("[%s] Starting parse for job %s", AGENT_NAME, state.job_id)
        state.status = JobStatus.PARSING
        state.progress_pct = 25.0

        try:
            # ── 1. Guard ───────────────────────────────────────────────────────
            if state.raw_ir is None:
                raise ValueError(
                    "state.raw_ir is None — ingestion stage may have failed."
                )

            # ── 2. Deep-copy raw IR to avoid mutating shared state ────────────
            ir = state.raw_ir.model_copy(deep=True)

            # ── 2. Structure detection ─────────────────────────────────────────
            logger.debug("[%s] Running StructureDetector on %d elements",
                         AGENT_NAME, len(ir.elements))
            ir = self._detector.detect(ir)

            # ── 3. Citation extraction ─────────────────────────────────────────
            citations = self._citation_parser.parse_all(ir)
            # Store in IR metadata for downstream agents
            ir.metadata["citations_parsed"] = [c.model_dump() for c in citations]
            logger.debug("[%s] Extracted %d citations", AGENT_NAME, len(citations))

            # ── 4. Citation style classification ──────────────────────────────
            detected_style, style_conf = self._classifier.classify(citations)
            ir.metadata["detected_style"] = detected_style.value
            ir.metadata["style_confidence"] = style_conf
            logger.debug(
                "[%s] Detected style=%s confidence=%.2f",
                AGENT_NAME, detected_style.value, style_conf,
            )

            # ── 5. Reference parsing ───────────────────────────────────────────
            references = await self._ref_parser.parse_all(ir, detected_style)
            ir.metadata["references_parsed"] = [r.model_dump() for r in references]
            logger.debug("[%s] Parsed %d references", AGENT_NAME, len(references))

            # ── 6. Update state ────────────────────────────────────────────────
            state.annotated_ir = ir
            state.progress_pct = 40.0

            # ── 7. Publish progress ────────────────────────────────────────────
            await self._publish_progress(state.job_id)

            logger.info(
                "[%s] Completed for job %s — elements=%d, citations=%d, refs=%d",
                AGENT_NAME, state.job_id,
                len(ir.elements), len(citations), len(references),
            )

        except Exception as exc:
            logger.exception("[%s] Failed for job %s: %s", AGENT_NAME, state.job_id, exc)
            state.errors.append(
                AgentError(
                    agent=AGENT_NAME,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    timestamp=datetime.utcnow(),
                    recoverable=False,
                )
            )
            state.status = JobStatus.FAILED

        return state

    async def _publish_progress(self, job_id: str) -> None:
        """Publish a progress event to the Redis job channel (non-fatal)."""
        try:
            await cache_service.publish_progress(
                job_id=job_id,
                event_dict={
                    "agent": "parsing",
                    "status": "completed",
                    "pct": 40,
                },
            )
        except Exception as pub_exc:
            logger.warning(
                "[%s] Could not publish progress for job %s: %s",
                AGENT_NAME, job_id, pub_exc,
            )


# ── LangGraph-compatible module-level entry point ─────────────────────────────

_agent_instance = DocParseAgent()


async def run_parsing(state: JobState) -> JobState:
    """
    Module-level LangGraph node function.

    Delegates to the singleton DocParseAgent instance, preserving the
    class-based design whilst satisfying LangGraph's plain-async-function
    interface.
    """
    return await _agent_instance.run(state)
