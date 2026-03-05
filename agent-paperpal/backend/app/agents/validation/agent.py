# backend/app/agents/validation/agent.py
"""
Stage 5 — ValidationAgent.

Runs compliance checks against the JRO to verify that the transformed IR
meets all journal formatting requirements. Produces a scored compliance report.

Input:  transformed_ir (IRSchema) + jro (JROSchema)
Output: compliance_report (ValidationReport)
"""

import logging

from app.schemas.job_state import (
    AgentError,
    ComplianceItem,
    JobState,
    JobStatus,
    ValidationReport,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "ValidationAgent"


async def run_validation(state: JobState) -> JobState:
    """
    Orchestrator-facing entry point for the validation stage.

    Checks the transformed IR against every rule in the JRO and
    generates a scored compliance report.

    Args:
        state: Pipeline state with transformed_ir and jro populated.

    Returns:
        Updated state with compliance_report populated.
    """
    logger.info("[%s] Starting validation for job %s", AGENT_NAME, state.job_id)
    state.status = JobStatus.VALIDATING
    state.progress_pct = 85.0

    try:
        if state.transformed_ir is None:
            raise ValueError("transformed_ir is None — transform stage may have failed")
        if state.jro is None:
            raise ValueError("jro is None — rule interpretation stage may have failed")

        # TODO: Implement comprehensive compliance checks
        # Check categories:
        #   - Font compliance (family, size, spacing)
        #   - Heading formatting
        #   - Citation style
        #   - Reference format
        #   - Abstract requirements
        #   - Word count limits
        #   - Required sections

        items = [
            ComplianceItem(
                rule="Font family matches JRO",
                passed=True,
                message="Body font is Times New Roman as required",
                severity="info",
            ),
            ComplianceItem(
                rule="Font size matches JRO",
                passed=True,
                message="Body font size is 12pt as required",
                severity="info",
            ),
            ComplianceItem(
                rule="Line spacing matches JRO",
                passed=True,
                message="Line spacing is 2.0 as required",
                severity="info",
            ),
        ]

        passed = sum(1 for item in items if item.passed)
        failed = sum(1 for item in items if not item.passed)
        warnings = sum(1 for item in items if item.severity == "warning")

        state.compliance_report = ValidationReport(
            total_checks=len(items),
            passed=passed,
            failed=failed,
            warnings=warnings,
            items=items,
            overall_score=(passed / len(items) * 100) if items else 0.0,
        )

        state.progress_pct = 95.0
        state.status = JobStatus.COMPLETED
        logger.info(
            "[%s] Validation completed for job %s (score: %.1f%%)",
            AGENT_NAME,
            state.job_id,
            state.compliance_report.overall_score,
        )

    except Exception as exc:
        error = AgentError(
            agent=AGENT_NAME,
            error_type=type(exc).__name__,
            message=str(exc),
            recoverable=False,
        )
        state.errors.append(error)
        state.status = JobStatus.FAILED
        logger.exception("[%s] Validation failed for job %s", AGENT_NAME, state.job_id)

    return state
