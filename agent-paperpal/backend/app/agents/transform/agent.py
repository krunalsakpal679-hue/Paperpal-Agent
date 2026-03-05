# backend/app/agents/transform/agent.py
"""
Stage 4 — TransformAgent.

Applies JRO formatting rules to the annotated IR, producing a
transformed IR and a detailed change log of every modification.

Input:  annotated_ir (IRSchema) + jro (JROSchema)
Output: transformed_ir (IRSchema) + change_log (list[ChangeEntry])
"""

import logging

from app.schemas.job_state import AgentError, ChangeEntry, JobState, JobStatus

logger = logging.getLogger(__name__)

AGENT_NAME = "TransformAgent"


async def run_transform(state: JobState) -> JobState:
    """
    Orchestrator-facing entry point for the transformation stage.

    Iterates through annotated IR elements and applies JRO rules:
    - Font changes (family, size, spacing)
    - Heading formatting (bold, italic, numbering, case)
    - Citation style conversion
    - Reference list reformatting
    - Margin and layout adjustments

    Args:
        state: Pipeline state with annotated_ir and jro populated.

    Returns:
        Updated state with transformed_ir and change_log populated.
    """
    logger.info("[%s] Starting transformation for job %s", AGENT_NAME, state.job_id)
    state.status = JobStatus.TRANSFORMING
    state.progress_pct = 65.0

    try:
        if state.annotated_ir is None:
            raise ValueError("annotated_ir is None — parse stage may have failed")
        if state.jro is None:
            raise ValueError("jro is None — rule interpretation stage may have failed")

        # TODO: Implement rule application logic
        # For each element in annotated_ir:
        #   1. Look up applicable JRO rules
        #   2. Compute diff between current and target formatting
        #   3. Apply changes and record in change_log

        state.transformed_ir = state.annotated_ir.model_copy(deep=True)
        state.change_log = [
            ChangeEntry(
                element_id="placeholder",
                field="font_size_pt",
                old_value="11.0",
                new_value="12.0",
                rule_source="jro.body_font.size_pt",
            )
        ]
        state.progress_pct = 80.0
        logger.info("[%s] Transformation completed for job %s", AGENT_NAME, state.job_id)

    except Exception as exc:
        error = AgentError(
            agent=AGENT_NAME,
            error_type=type(exc).__name__,
            message=str(exc),
            recoverable=False,
        )
        state.errors.append(error)
        state.status = JobStatus.FAILED
        logger.exception("[%s] Transform failed for job %s", AGENT_NAME, state.job_id)

    return state
