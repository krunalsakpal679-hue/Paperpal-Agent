# backend/app/agents/interpretation/tests/test_interpretation.py
"""
Unit tests for Stage 3 — Rule Interpretation Agent.
Tests CSL lookup, LLM mocking, and orchestrator logic.
"""

import pytest
import json
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.interpretation.agent import RuleInterpretAgent
from app.agents.interpretation.csl_loader import CSLLoader
from app.agents.interpretation.llm_extractor import LLMRuleExtractor
from app.schemas.job_state import JobState, JobStatus
from app.schemas.jro_schema import JROSchema

@pytest.fixture
def mock_jro_data():
    return {
        "journal_name": "Test Journal",
        "issn": None,
        "citation_style": "apa",
        "csl_xml": None,
        "heading_rules": {"numbering_scheme": "none", "capitalization": "title", "levels": {}},
        "abstract_rules": {"max_words": 250, "min_words": None, "structured": False, "required_sections": []},
        "layout_rules": {"font_name": "Times New Roman", "font_size": 12, "line_spacing": 2.0, "margins": {}, "columns": 1},
        "figure_rules": {"caption_position": "bottom", "caption_prefix": "Figure", "numbering_format": "arabic"},
        "table_rules": {"caption_position": "top", "caption_prefix": "Table", "border_style": "simple"},
        "section_requirements": {"required": [], "optional": []},
        "statistical_notation": None,
        "extraction_source": "llm",
        "extraction_confidence": 0.9
    }

@pytest.mark.asyncio
async def test_csl_loader_lookup_not_found():
    """Test CSLLoader returns None for nonexistent journal."""
    with patch("app.agents.interpretation.csl_loader.CSLLoader.ensure_data", new_callable=AsyncMock):
        loader = CSLLoader()
        loader.name_index = {} # Empty index
        res = await loader.lookup("Nonexistent Journal XYZ")
        assert res is None

@pytest.mark.asyncio
async def test_llm_extractor_mock_api(mock_jro_data):
    """Test LLMRuleExtractor with mocked Anthropic API."""
    extractor = LLMRuleExtractor()
    
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=f"```json\n{json.dumps(mock_jro_data)}\n```")]
    
    with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_message
        
        jro = await extractor.extract("dummy text", "Test Journal")
        assert jro.journal_name == "Test Journal"
        assert jro.extraction_confidence == 0.9

@pytest.mark.asyncio
async def test_agent_cache_hit(mock_jro_data):
    """Test RuleInterpretAgent skips extraction on cache hit."""
    state = JobState(job_id="test_job", metadata={"journal_identifier": "APA 7th"})
    cached_jro = JROSchema.model_validate(mock_jro_data)
    
    agent = RuleInterpretAgent()
    
    with patch("app.services.cache_service.cache_service.get_jro", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = cached_jro
        
        updated_state = await agent.run(state)
        
        assert updated_state.jro.journal_name == "Test Journal"
        assert updated_state.progress_pct == 60.0

@pytest.mark.asyncio
async def test_full_orchestration_flow(mock_jro_data):
    """Test complete flow from CSL lookup to merge (no scraping)."""
    state = JobState(job_id="test_job_full", metadata={"journal_identifier": "Nature"})
    
    agent = RuleInterpretAgent()
    
    with patch("app.services.cache_service.cache_service.get_jro", new_callable=AsyncMock) as mock_cache_get, \
         patch("app.services.cache_service.cache_service.set_jro", new_callable=AsyncMock) as mock_cache_set, \
         patch("app.agents.interpretation.csl_loader.CSLLoader.lookup", new_callable=AsyncMock) as mock_csl_lookup:
        
        mock_cache_get.return_value = None
        mock_csl_lookup.return_value = "<csl>title: Nature</csl>"
        mock_cache_set.return_value = True
        
        updated_state = await agent.run(state)
        
        assert updated_state.jro is not None
        assert updated_state.jro.extraction_source == "csl"
