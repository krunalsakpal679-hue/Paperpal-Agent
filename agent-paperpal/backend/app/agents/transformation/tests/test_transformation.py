# backend/app/agents/transformation/tests/test_transformation.py
"""
Unit and integration tests for Stage 4 — TransformAgent.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.schemas.job_state import JobState, JobStatus, ChangeEntry
from app.schemas.jro_schema import (
    JROSchema, HeadingRules, AbstractRules, LayoutRules, 
    FigureRules, TableRules, SectionRequirements
)
from app.schemas.ir import IRSchema, IRElement, ElementType, TextRun

from app.agents.transformation.agent import TransformAgent
from app.agents.transformation.citation_reformatter import CitationReformatter
from app.agents.transformation.heading_formatter import HeadingFormatter
from app.agents.transformation.transformer_base import BaseTransformer

@pytest.fixture
def sample_jro():
    """Create a sample JRO with APA-ish rules."""
    return JROSchema(
        journal_name="Test Journal",
        citation_style="apa",
        csl_xml="""<?xml version="1.0" encoding="utf-8"?>
<style xmlns="http://purl.org/net/xbiblio/csl" class="in-text" version="1.0">
  <info><title>Mock APA</title><id>mock-apa</id></info>
  <citation><layout><group delimiter=", "><names variable="author"><name form="short" and="symbol"/></names><date variable="issued"><date-part name="year"/></date></group></layout></citation>
  <bibliography><layout><names variable="author"><name and="symbol" name-as-sort-order="all" sort-separator=", "/></names><date variable="issued" prefix=" (" suffix=")."><date-part name="year"/></date><text variable="title" prefix=" "/></layout></bibliography>
</style>""",
        heading_rules=HeadingRules(capitalization="title_case", numbering_scheme="numeric", levels={}),
        abstract_rules=AbstractRules(max_words=200, structured=True),
        layout_rules=LayoutRules(font_name="Arial", font_size=11, line_spacing=1.5),
        figure_rules=FigureRules(caption_prefix="Figure"),
        table_rules=TableRules(caption_prefix="Table"),
        section_requirements=SectionRequirements(required=["Introduction"]),
        extraction_source="test",
        extraction_confidence=1.0
    )

@pytest.fixture
def sample_ir():
    """Create a minimum IR for testing transformation."""
    return IRSchema(
        job_id="test_job",
        source_format="docx",
        elements=[
            IRElement(
                element_id="h1",
                element_type=ElementType.HEADING,
                raw_text="introduction",
                level=1,
                content=[TextRun(text="introduction")]
            ),
            IRElement(
                element_id="p1",
                element_type=ElementType.PARAGRAPH,
                raw_text="This is a test paragraph with a citation (Smith, 2020).",
                content=[TextRun(text="This is a test paragraph with a citation (Smith, 2020).")]
            ),
            IRElement(
                element_id="r1",
                element_type=ElementType.REFERENCE,
                raw_text="Smith, J. (2020). A study on testing.",
                content=[TextRun(text="Smith, J. (2020). A study on testing.")]
            )
        ],
        metadata={
            "citations_parsed": [
                {
                    "id": "cit1",
                    "paragraph_id": "p1",
                    "raw_text": "(Smith, 2020)",
                    "ref_ids": ["ref1"]
                }
            ],
            "references_parsed": [
                {
                    "id": "ref1",
                    "authors": ["Smith, John"],
                    "year": "2020",
                    "title": "A study on testing",
                    "journal": "Test Journal"
                }
            ]
        }
    )

def test_record_change_skips_no_op():
    """Verify record_change does not log when values are identical."""
    change_log = []
    transformer = MockTransformer(MagicMock(), change_log)
    transformer.record_change("id", "field", "A", "A", "rule")
    assert len(change_log) == 0

def test_heading_formatter_title_case(sample_jro):
    """Test title case application to headings."""
    change_log = []
    # Force APA-like title case
    sample_jro.heading_rules.capitalization = "title_case"
    sample_jro.heading_rules.numbering_scheme = "none"
    
    ir = IRSchema(job_id="j", source_format="s", elements=[
        IRElement(element_id="h", element_type=ElementType.HEADING, raw_text="methods and results")
    ])
    
    HeadingFormatter(sample_jro, change_log).format_all(ir)
    assert ir.elements[0].raw_text == "Methods and Results"
    assert len(change_log) == 1
    assert change_log[0].field == "heading"

def test_heading_formatter_numeric(sample_jro):
    """Test numeric numbering scheme."""
    change_log = []
    sample_jro.heading_rules.capitalization = "none"
    sample_jro.heading_rules.numbering_scheme = "numeric"
    
    ir = IRSchema(job_id="j", source_format="s", elements=[
        IRElement(element_id="h1", element_type=ElementType.HEADING, raw_text="Intro", level=1),
        IRElement(element_id="h2", element_type=ElementType.HEADING, raw_text="Methods", level=2)
    ])
    
    HeadingFormatter(sample_jro, change_log).format_all(ir)
    assert ir.elements[0].raw_text == "1 Intro"
    assert ir.elements[1].raw_text == "1.1 Methods"

@pytest.mark.asyncio
async def test_full_transformation_orchestration(sample_jro, sample_ir):
    """Integration test for TransformAgent."""
    state = JobState(job_id="test", annotated_ir=sample_ir, jro=sample_jro)
    agent = TransformAgent()
    
    # Mock cache_service to avoid redis connection
    with patch("app.services.cache_service.cache_service.publish_progress", new_callable=AsyncMock):
        updated_state = await agent.run(state)
        
        assert updated_state.status == JobStatus.TRANSFORMING # It completes returning state, LangGraph handles next
        assert updated_state.transformed_ir is not None
        assert len(updated_state.change_log) > 0
        
        # Check rule_ref is populated
        for change in updated_state.change_log:
            assert change.rule_source != ""

class MockTransformer(BaseTransformer):
    def transform(self, ir): return ir
