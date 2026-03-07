# backend/app/agents/interpretation/agent.py
"""
RuleInterpretAgent: Orchestrates the journal rule interpretation stage.
Checks cache, performs CSL lookup, scrapes journal guidelines, and uses LLM for extraction.
"""

import logging
import hashlib
import asyncio
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
        await cache_service.publish_progress(state.job_id, {
            "agent": "interpreting",
            "status": "processing",
            "progress": 45,
            "message": f"Fetching and interpreting formatting guidelines for {journal_id}..."
        })

        try:
            cache_key = hashlib.sha256(journal_id.encode()).hexdigest()
            cached_jro = await cache_service.get_jro(cache_key)
            if cached_jro:
                logger.info("[%s] Cache hit for %s", "RuleInterpretAgent", journal_id)
                state.jro = cached_jro
                state.progress_pct = 60.0
                await cache_service.publish_progress(state.job_id, {
                    "agent": "interpreting", 
                    "status": "processing", 
                    "progress": 60,
                    "message": f"Retrieved journal rules from cache for {journal_id}"
                })
                return state

            # ── 2. Concurrent Lookup & Scrape ──────────────────────────────────
            csl_task = self.csl_loader.lookup(journal_id)
            scrape_task = (
                self.scraper.scrape(style_guide_url) 
                if style_guide_url else asyncio.sleep(0, result=("", False))
            )

            try:
                # Add overall timeout (45s) to prevent hanging Stage 3 indefinitely
                csl_xml, (raw_scrape_text, wall_detected) = await asyncio.wait_for(
                    asyncio.gather(csl_task, scrape_task),
                    timeout=45.0
                )
            except asyncio.TimeoutError:
                logger.error("[%s] TIMEOUT: Scrape/Lookup took too long for %s. Continuing with defaults.", "RuleInterpretAgent", journal_id)
                csl_xml, (raw_scrape_text, wall_detected) = None, ("", False)
            
            llm_jro = None
            if raw_scrape_text and not wall_detected:
                # Truncate to 20k chars to stay within Gemini flash optimal speed and handle large guideline pages
                scrape_text_str = str(raw_scrape_text)
                targeted_text = scrape_text_str[:20000]
                logger.info("[%s] SCRAPE SUCCESS. Extracted %d chars (using first 20k). Starting LLM...", "RuleInterpretAgent", len(scrape_text_str))
                llm_jro = await self.llm_extractor.extract(targeted_text, journal_id)
            elif wall_detected:
                logger.warning("[%s] Login wall detected for URL %s. Skipping LLM extraction.", 
                               "RuleInterpretAgent", style_guide_url)

            jro = self.merger.merge(csl_xml, llm_jro, journal_id)
            await cache_service.set_jro(cache_key, jro)

            state.jro = jro
            state.progress_pct = 60.0
            
            await cache_service.publish_progress(state.job_id, {
                "agent": "interpreting", 
                "status": "processing", 
                "progress": 60,
                "message": f"Successfully interpreted formatting rules for {journal_id}"
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
