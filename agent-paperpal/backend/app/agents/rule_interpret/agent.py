# backend/app/agents/rule_interpret/agent.py
"""
Stage 3 — RuleInterpretAgent.

Extracts journal-specific formatting rules and produces a structured
Journal Rule Object (JRO). First checks the Redis/DB cache, then
uses Claude LLM to interpret author guidelines if not cached.

Input:  target journal name
Output: jro (JROSchema)
"""

import logging

from app.schemas.jro import (
    AbstractRule,
    CitationRule,
    FontRule,
    HeadingRule,
    JROSchema,
    MarginRule,
    ReferenceRule,
)
from app.schemas.job_state import AgentError, JobState, JobStatus

logger = logging.getLogger(__name__)

AGENT_NAME = "RuleInterpretAgent"


async def run_rule_interpret(state: JobState) -> JobState:
    """
    Orchestrator-facing entry point for the rule interpretation stage.

    Checks cache for existing JRO, otherwise uses Claude to extract
    formatting rules from journal author guidelines.

    Args:
        state: Pipeline state (needs job metadata for target journal).

    Returns:
        Updated state with jro populated.
    """
    logger.info("[%s] Starting rule interpretation for job %s", AGENT_NAME, state.job_id)
    state.status = JobStatus.INTERPRETING
    state.progress_pct = 45.0

    try:
        # TODO: Check Redis cache for existing JRO
        # TODO: Check DB style_cache table
        # TODO: If not cached, use Claude to extract rules from guidelines
        # For now, return a default JRO

        jro = JROSchema(
            journal_name="Example Journal",
            style_guide="apa",
            body_font=FontRule(family="Times New Roman", size_pt=12.0, line_spacing=2.0),
            margins=MarginRule(top=1.0, bottom=1.0, left=1.0, right=1.0),
            headings=[
                HeadingRule(level=1, bold=True, case="title"),
                HeadingRule(level=2, bold=True, italic=True, case="title"),
                HeadingRule(level=3, bold=False, italic=True, case="sentence"),
            ],
            citation=CitationRule(style="author-year", bracket_type="round"),
            references=ReferenceRule(style="apa", hanging_indent=True, doi_required=True),
            abstract=AbstractRule(max_words=250, structured=False),
        )

        state.jro = jro
        state.progress_pct = 60.0
        logger.info("[%s] Rule interpretation completed for job %s", AGENT_NAME, state.job_id)

    except Exception as exc:
        error = AgentError(
            agent=AGENT_NAME,
            error_type=type(exc).__name__,
            message=str(exc),
            recoverable=True,
        )
        state.errors.append(error)
        state.status = JobStatus.FAILED
        logger.exception("[%s] Rule interpretation failed for job %s", AGENT_NAME, state.job_id)

    return state
