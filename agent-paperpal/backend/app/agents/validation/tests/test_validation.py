# backend/app/agents/validation/tests/test_validation.py
"""
Unit tests for Stage 5 — ValidationAgent and its constituent checkers.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.job_state import JobState, JobStatus, ComplianceItem
from app.schemas.ir import IRSchema, IRElement, ElementType, TextRun
from app.schemas.jro_schema import JROSchema, AbstractRules, SectionRequirements
from app.agents.validation.agent import ValidationAgent
from app.agents.validation.citation_checker import CitationConsistencyChecker
from app.agents.validation.structure_checker import StructureChecker
from app.agents.validation.content_checker import ContentChecker


@pytest.fixture
def sample_jro():
    """Create a sample JRO with all required fields."""
    from app.schemas.jro_schema import (
        HeadingRules, AbstractRules, LayoutRules, 
        FigureRules, TableRules, SectionRequirements
    )
    return JROSchema(
        journal_name="Test Journal",
        citation_style="apa",
        heading_rules=HeadingRules(numbering_scheme="numeric", capitalization="title_case"),
        abstract_rules=AbstractRules(max_words=100, structured=False),
        layout_rules=LayoutRules(font_name="Arial", font_size=11, line_spacing=1.5),
        figure_rules=FigureRules(caption_prefix="Figure"),
        table_rules=TableRules(caption_prefix="Table"),
        section_requirements=SectionRequirements(required=["Introduction", "Methods"]),
        extraction_source="test",
        extraction_confidence=1.0
    )


@pytest.fixture
def sample_ir():
    """Create a minimum IR for testing validation."""
    return IRSchema(
        source_format="docx",
        elements=[
            IRElement(
                element_id="h1",
                element_type=ElementType.HEADING,
                raw_text="Introduction",
                level=1,
                content=[TextRun(text="Introduction")]
            ),
            IRElement(
                element_id="abs1",
                element_type=ElementType.ABSTRACT,
                raw_text="This is a test abstract.",
                content=[TextRun(text="This is a test abstract.")]
            ),
            IRElement(
                element_id="p1",
                element_type=ElementType.PARAGRAPH,
                raw_text="Some text with a citation (Smith, 2020).",
                content=[TextRun(text="Some text with a citation (Smith, 2020).")]
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
                    "title": "A study",
                    "journal": "Journal"
                }
            ]
        }
    )


class TestCitationConsistencyChecker:
    def test_matched_citations(self, sample_ir):
        issues, coverage = CitationConsistencyChecker().check(sample_ir)
        assert coverage == 1.0
        assert len([i for i in issues if i.severity == "error"]) == 0

    def test_unmatched_citation(self, sample_ir):
        # Remove the reference
        sample_ir.metadata["references_parsed"] = []
        issues, coverage = CitationConsistencyChecker().check(sample_ir)
        assert coverage == 0.0
        assert any("no matching reference" in i.description for i in issues)

    def test_uncited_reference(self, sample_ir):
        # Add an extra reference that isn't cited
        sample_ir.metadata["references_parsed"].append({
            "id": "ref2",
            "authors": ["Jones, Bob"],
            "year": "2021",
            "title": "Another study"
        })
        issues, coverage = CitationConsistencyChecker().check(sample_ir)
        assert coverage == 1.0
        assert any("is not cited in the text" in i.description for i in issues)


class TestStructureChecker:
    def test_required_sections_present(self, sample_ir, sample_jro):
        # Add missing "Methods" heading
        sample_ir.elements.append(IRElement(
            element_id="h2",
            element_type=ElementType.HEADING,
            raw_text="Methods",
            level=1,
            content=[TextRun(text="Methods")]
        ))
        issues = StructureChecker().check(sample_ir, sample_jro)
        assert not any("Required section missing" in i.description for i in issues)

    def test_required_section_missing(self, sample_ir, sample_jro):
        # "Methods" is required in sample_jro but missing in sample_ir
        issues = StructureChecker().check(sample_ir, sample_jro)
        assert any("Required section missing: Methods" in i.description for i in issues)

    def test_heading_jump(self, sample_ir, sample_jro):
        sample_ir.elements.append(IRElement(
            element_id="h3",
            element_type=ElementType.HEADING,
            raw_text="Sub-sub-section",
            level=3, # Jump from level 1 to level 3
            content=[TextRun(text="Sub-sub-section")]
        ))
        issues = StructureChecker().check(sample_ir, sample_jro)
        assert any("Heading level jump detected" in i.description for i in issues)

    def test_abstract_missing(self, sample_ir, sample_jro):
        # Remove abstract
        sample_ir.elements = [el for el in sample_ir.elements if el.element_type != ElementType.ABSTRACT]
        issues = StructureChecker().check(sample_ir, sample_jro)
        assert any("Abstract is missing" in i.description for i in issues)


class TestContentChecker:
    def test_abstract_word_count(self, sample_ir, sample_jro):
        sample_jro.abstract_rules.max_words = 2
        issues = ContentChecker().check(sample_ir, sample_jro)
        assert any("Abstract is 5 words; limit is 2 words" in i.description for i in issues)

    def test_figure_numbering_gap(self, sample_ir, sample_jro):
        sample_ir.elements.append(IRElement(
            element_id="f1", element_type=ElementType.FIGURE, raw_text="Figure 1. Legend"
        ))
        sample_ir.elements.append(IRElement(
            element_id="f2", element_type=ElementType.FIGURE, raw_text="Figure 3. Legend"
        ))
        issues = ContentChecker().check(sample_ir, sample_jro)
        assert any("Figure numbering gap" in i.description for i in issues)

    def test_statistical_notation(self, sample_ir, sample_jro):
        sample_ir.elements.append(IRElement(
            element_id="p2", element_type=ElementType.PARAGRAPH, raw_text="The result was p < .05"
        ))
        issues = ContentChecker().check(sample_ir, sample_jro)
        assert any("P-value missing leading zero" in i.description for i in issues)


@pytest.mark.asyncio
class TestValidationAgent:
    async def test_successful_validation_flow(self, sample_ir, sample_jro):
        state = JobState(job_id="test_val", transformed_ir=sample_ir, jro=sample_jro)
        agent = ValidationAgent()
        
        with patch("app.services.cache_service.cache_service.publish_progress", new_callable=AsyncMock):
            updated_state = await agent.run(state)
            
            assert updated_state.status == JobStatus.COMPLETED
            assert updated_state.compliance_report is not None
            assert updated_state.compliance_report.overall_score >= 0.0
            assert updated_state.progress_pct == 95.0

    async def test_missing_data_fails(self):
        state = JobState(job_id="test_fail")
        agent = ValidationAgent()
        updated_state = await agent.run(state)
        
        assert updated_state.status == JobStatus.FAILED
        assert any("Validation requires both transformed_ir and jro" in e.message for e in updated_state.errors)
