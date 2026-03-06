# backend/app/agents/interpretation/agent.py
"""
RuleInterpretAgent: Orchestrates the journal rule interpretation stage.
Checks cache, performs CSL lookup, scrapes journal guidelines, and uses LLM for extraction.
"""

import logging
import hashlib
from typing import Optional

from app.schemas.job_state import JobState, JobStatus, AgentError
from app.schemas.jro_schema import JROSchema
from app.services.cache_service import cache_service

from .csl_loader import CSLLoader
from .scraper import JournalScraper
from .llm_extractor import LLMRuleExtractor
from .rule_merger import RuleMerger

logger = logging.getLogger(__name__)

class RuleInterpretAgent:
    """
    Rule interpretation agent implementation.
    Integrates all sub-modules for end-to-end extraction.
    """

    def __init__(self):
        self.csl_loader = CSLLoader()
        self.scraper = JournalScraper()
        self.llm_extractor = LLMRuleExtractor()
        self.merger = RuleMerger()

    async def run(self, state: JobState) -> JobState:
        """
        Execute the rule interpretation pipeline stage.
        """
        journal_id = state.metadata.get("journal_identifier") or state.metadata.get("style_name")
        style_guide_url = state.metadata.get("style_guide_url")
        
        if not journal_id:
            logger.error("[%s] No journal identifier found in state metadata.", "RuleInterpretAgent")
            state.errors.append(AgentError(
                agent="RuleInterpretAgent",
                error_type="ValueError",
                message="No journal identifier or style name provided for interpretation.",
                recoverable=False
            ))
            state.status = JobStatus.FAILED
            return state

        logger.info("[%s] Interpreting rules for journal: %s", "RuleInterpretAgent", journal_id)
        state.status = JobStatus.INTERPRETING
        state.progress_pct = 45.0

        try:
            cache_key = hashlib.sha256(journal_id.encode()).hexdigest()
            cached_jro = await cache_service.get_jro(cache_key)
            if cached_jro:
                logger.info("[%s] Cache hit for %s", "RuleInterpretAgent", journal_id)
                state.jro = cached_jro
                state.progress_pct = 60.0
                await cache_service.publish_progress(state.job_id, {
                    "agent": "interpretation", "status": "completed", "pct": 60
                })
                return state

            csl_xml = await self.csl_loader.lookup(journal_id)
            
            llm_jro = None
            if style_guide_url:
                text, wall_detected = await self.scraper.scrape(style_guide_url)
                if text and not wall_detected:
                    llm_jro = await self.llm_extractor.extract(text, journal_id)
                elif wall_detected:
                    logger.warning("[%s] Login wall detected for URL %s. Skipping LLM extraction.", 
                                   "RuleInterpretAgent", style_guide_url)

            jro = self.merger.merge(csl_xml, llm_jro, journal_id)
            await cache_service.set_jro(cache_key, jro)

            state.jro = jro
            state.progress_pct = 60.0
            
            await cache_service.publish_progress(state.job_id, {
                "agent": "interpretation", "status": "completed", "pct": 60
            })
            
            logger.info("[%s] Rule interpretation completed for %s", "RuleInterpretAgent", journal_id)

        except Exception as e:
            logger.exception("[%s] Unexpected error in rule interpretation: %s", "RuleInterpretAgent", e)
            state.errors.append(AgentError(
                agent="RuleInterpretAgent",
                error_type=type(e).__name__,
                message=str(e),
                recoverable=True
            ))
            state.status = JobStatus.FAILED

        return state

async def run_stage3(state: JobState) -> JobState:
    """External entry point helper matching the orchestrator interface."""
    agent = RuleInterpretAgent()
    return await agent.run(state)
