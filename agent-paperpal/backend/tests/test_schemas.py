# backend/tests/test_schemas.py
"""Tests for Pydantic schema validation."""

import pytest

from app.schemas.ir import ElementType, IRElement, IRSchema, TextRun
from app.schemas.jro import JROSchema, FontRule
from app.schemas.job_state import JobState, JobStatus, ChangeEntry, AgentError


class TestIRSchema:
    """Tests for the Intermediate Representation schema."""

    def test_create_minimal_ir(self):
        """Should create an IR with required fields only."""
        ir = IRSchema(document_title="Test Paper")
        assert ir.document_title == "Test Paper"
        assert ir.elements == []
        assert ir.word_count == 0

    def test_create_ir_with_elements(self):
        """Should create an IR with typed elements."""
        element = IRElement(
            element_id="elem-001",
            element_type=ElementType.PARAGRAPH,
            content=[TextRun(text="Hello world")],
            raw_text="Hello world",
        )
        ir = IRSchema(
            document_title="Test",
            elements=[element],
        )
        assert len(ir.elements) == 1
        assert ir.elements[0].element_type == ElementType.PARAGRAPH


class TestJROSchema:
    """Tests for the Journal Rule Object schema."""

    def test_create_default_jro(self):
        """Should create a JRO with sensible defaults."""
        jro = JROSchema(journal_name="Test Journal")
        assert jro.journal_name == "Test Journal"
        assert jro.body_font.family == "Times New Roman"
        assert jro.body_font.size_pt == 12.0

    def test_custom_font_rule(self):
        """Should accept custom font specifications."""
        font = FontRule(family="Arial", size_pt=11.0, line_spacing=1.5)
        jro = JROSchema(journal_name="Custom Journal", body_font=font)
        assert jro.body_font.family == "Arial"
        assert jro.body_font.size_pt == 11.0


class TestJobState:
    """Tests for the pipeline shared state schema."""

    def test_create_initial_state(self):
        """Should create a JobState with None optionals."""
        state = JobState(job_id="test-uuid-1234")
        assert state.job_id == "test-uuid-1234"
        assert state.status == JobStatus.PENDING
        assert state.raw_ir is None
        assert state.progress_pct == 0.0
        assert state.errors == []

    def test_append_error(self):
        """Should allow appending structured errors."""
        state = JobState(job_id="test-uuid")
        error = AgentError(
            agent="TestAgent",
            error_type="ValueError",
            message="Something went wrong",
        )
        state.errors.append(error)
        assert len(state.errors) == 1
        assert state.errors[0].agent == "TestAgent"

    def test_change_entry(self):
        """Should validate ChangeEntry fields."""
        entry = ChangeEntry(
            element_id="elem-001",
            field="font_size_pt",
            old_value="11.0",
            new_value="12.0",
            rule_source="jro.body_font.size_pt",
        )
        assert entry.field == "font_size_pt"
