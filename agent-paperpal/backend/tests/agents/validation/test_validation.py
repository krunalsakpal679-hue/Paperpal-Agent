# backend/tests/agents/validation/test_validation.py
"""
Unit tests for Stage 5 — ValidationAgent and checkers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.schemas.job_state import JobState, JobStatus, ComplianceItem
from app.schemas.jro_schema import (
    JROSchema, HeadingRules, AbstractRules, LayoutRules,
    FigureRules, TableRules, SectionRequirements
)
from app.schemas.ir import IRSchema, IRElement, ElementType, TextRun

from app.agents.validation.agent import ValidationAgent
from app.agents.validation.citation_checker import CitationConsistencyChecker
from app.agents.validation.compliance_scorer import ComplianceScorer

@pytest.fixture
def perfect_ir():
    """Create an IR with matching citations and references."""
    return IRSchema(
        job_id="test",
        source_format="docx",
        elements=[
            IRElement(element_id="h1", element_type=ElementType.HEADING, raw_text="Introduction", level=1, content=[TextRun(text="Introduction")]),
            IRElement(element_id="p1", element_type=ElementType.PARAGRAPH, raw_text="Citation (Smith, 2020).", content=[TextRun(text="Citation (Smith, 2020).")]),
            IRElement(element_id="a1", element_type=ElementType.ABSTRACT, raw_text="Short abstract.", content=[TextRun(text="Short abstract.")])
        ],
        metadata={
            "citations_parsed": [{"id": "c1", "ref_ids": ["r1"], "raw_text": "(Smith, 2020)"}],
            "references_parsed": [{"id": "r1", "authors": ["Smith, J."], "year": "2020"}]
        }
    )

@pytest.fixture
def sample_jro():
    return JROSchema(
        journal_name="Test J",
        citation_style="apa",
        heading_rules=HeadingRules(),
        layout_rules=LayoutRules(),
        figure_rules=FigureRules(),
        table_rules=TableRules(),
        section_requirements=SectionRequirements(required=["Introduction"]),
        abstract_rules=AbstractRules(max_words=100),
        extraction_source="test",
        extraction_confidence=1.0
    )

@pytest.mark.asyncio
async def test_perfect_ir_score(perfect_ir, sample_jro):
    """Test perfect IR (all citations matched) scores > 95%."""
    state = JobState(job_id="test", transformed_ir=perfect_ir, jro=sample_jro)
    agent = ValidationAgent()
    
    with patch("app.services.cache_service.cache_service.publish_progress", new_callable=AsyncMock):
        updated_state = await agent.run(state)
        
        assert updated_state.compliance_report is not None
        assert updated_state.compliance_report.overall_score > 95.0
        assert len(updated_state.compliance_report.items) == 0

def test_unmatched_citations():
    """Test IR with 3 unmatched citations generates exactly 3 error issues."""
    ir = IRSchema(
        job_id="test", source_format="docx", elements=[],
        metadata={
            "citations_parsed": [
                {"id": "c1", "ref_ids": ["none1"], "raw_text": "(A, 2020)"},
                {"id": "c2", "ref_ids": ["none2"], "raw_text": "(B, 2021)"},
                {"id": "c3", "ref_ids": ["none3"], "raw_text": "(C, 2022)"}
            ],
            "references_parsed": []
        }
    )
    issues, cov = CitationConsistencyChecker().check(ir)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 3
    assert cov == 0.0

@pytest.mark.asyncio
async def test_missing_required_section(perfect_ir, sample_jro):
    """Test missing required section generates error with correct rule_ref."""
    sample_jro.section_requirements.required = ["Conclusion"]
    state = JobState(job_id="test", transformed_ir=perfect_ir, jro=sample_jro)
    agent = ValidationAgent()
    
    with patch("app.services.cache_service.cache_service.publish_progress", new_callable=AsyncMock):
        updated_state = await agent.run(state)
        
        conclusion_error = next((i for i in updated_state.compliance_report.items if "Conclusion" in i.description), None)
        assert conclusion_error is not None
        assert conclusion_error.severity == "error"
        assert conclusion_error.rule_ref == "Journal structural requirements"

@pytest.mark.asyncio
async def test_abstract_word_limit(perfect_ir, sample_jro):
    """Test abstract over word limit generates warning (not error)."""
    sample_jro.abstract_rules.max_words = 2
    perfect_ir.elements[2].raw_text = "This abstract is way too long for the limit."
    
    state = JobState(job_id="test", transformed_ir=perfect_ir, jro=sample_jro)
    agent = ValidationAgent()
    
    with patch("app.services.cache_service.cache_service.publish_progress", new_callable=AsyncMock):
        updated_state = await agent.run(state)
        
        warning = next((i for i in updated_state.compliance_report.items if "Abstract is" in i.description), None)
        assert warning is not None
        assert warning.severity == "warning"

def test_compliance_scorer_range(perfect_ir):
    """Test ComplianceScorer returns values between 0.0 and 1.0."""
    # Create some issues
    issues = [
        ComplianceItem(passed=False, severity="error", rule_ref="citation"),
        ComplianceItem(passed=False, severity="warning", rule_ref="heading")
    ]
    scores = ComplianceScorer().score(issues, perfect_ir)
    for cat, score in scores.items():
        assert 0.0 <= score <= 1.0
