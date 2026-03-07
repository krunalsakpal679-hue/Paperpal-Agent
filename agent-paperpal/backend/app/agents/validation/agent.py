# backend/app/agents/validation/agent.py
"""
ValidationAgent: Orchestrates the final compliance validation stage.
Aggregates results from citation, structure, and content checkers.
"""

import logging
from typing import List

from app.schemas.job_state import JobState, JobStatus, ValidationReport, AgentError, ComplianceItem
from app.services.cache_service import cache_service

from .citation_checker import CitationConsistencyChecker
from .structure_checker import StructureChecker
from .content_checker import ContentChecker
from .compliance_scorer import ComplianceScorer

logger = logging.getLogger(__name__)

class ValidationAgent:
    """
    Orchestrates compliance checking and scoring.
    """

    async def run(self, state: JobState) -> JobState:
        """
        Execute the validation pipeline stage.
        """
        if not state.transformed_ir or not state.jro:
            logger.error("[%s] transformed_ir or jro missing from JobState.", "ValidationAgent")
            state.errors.append(AgentError(
                agent="ValidationAgent",
                error_type="ValueError",
                message="Validation requires both transformed_ir and jro to be populated.",
                recoverable=False
            ))
            state.status = JobStatus.FAILED
            return state

        logger.info("[%s] Starting validation for job: %s", "ValidationAgent", state.job_id)
        state.status = JobStatus.VALIDATING
        state.progress_pct = 90.0
        await cache_service.publish_progress(state.job_id, {
            "agent": "validating",
            "status": "processing",
            "progress": 90,
            "message": "Performing final compliance check against journal standards..."
        })

        try:
            issues: List[ComplianceItem] = []
            
            # 1. Check citations
            citation_issues, citation_cov = CitationConsistencyChecker().check(state.transformed_ir)
            issues.extend(citation_issues)
            
            # 2. Check structure
            issues.extend(StructureChecker().check(state.transformed_ir, state.jro))
            
            # 3. Check content
            issues.extend(ContentChecker().check(state.transformed_ir, state.jro))
            
            # 4. Calculate scores
            scores = ComplianceScorer().score(issues, state.transformed_ir)
            
            # 5. Populate ValidationReport
            failed_count = len([i for i in issues if i.severity == "error"])
            warning_count = len([i for i in issues if i.severity == "warning"])
            
            state.compliance_report = ValidationReport(
                overall_score=round(scores["overall"] * 100, 2),
                category_scores={k: round(v * 100, 2) for k, v in scores.items() if k != "overall"},
                issues=issues,
                citation_coverage=citation_cov,
                total_issues=len(issues),
                total_checks=len(issues) + 10, # Heuristic
                passed=max(0, 10 - failed_count),
                failed=failed_count,
                warnings=warning_count
            )
            
            state.progress_pct = 95.0
            # Removed premature state.status = JobStatus.COMPLETED
            
            # 6. Publish progress
            await cache_service.publish_progress(state.job_id, {
                "agent": "validating",
                "status": "processing",
                "progress": 95,
                "message": f"Final compliance validation complete. Overall score: {state.compliance_report.overall_score}%"
            })
            
            logger.info(
                "[%s] Validation completed for %s — Score: %.2f, Issues: %d", 
                "ValidationAgent", state.job_id, state.compliance_report.overall_score, len(issues)
            )

        except Exception as e:
            logger.exception("[%s] Unexpected error during validation: %s", "ValidationAgent", e)
            state.errors.append(AgentError(
                agent="ValidationAgent",
                error_type=type(e).__name__,
                message=str(e),
                recoverable=True
            ))
            state.status = JobStatus.FAILED

        return state

async def run_stage5(state: JobState) -> JobState:
    """LangGraph node helper for Stage 5."""
    agent = ValidationAgent()
    return await agent.run(state)
