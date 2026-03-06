# backend/app/agents/parsing/tests/test_parsing.py
"""
Test suite for Stage 2 — DocParseAgent and its sub-components.

Covers:
  TestStructureDetector  — element labelling accuracy on known fixtures
  TestCitationParser     — APA, IEEE, MLA extraction from known paragraphs
  TestCitationStyleClassifier — dominant style detection
  TestReferenceParser    — field extraction from APA/Vancouver/IEEE strings
  TestDocParseAgent      — end-to-end pipeline integration
  TestSuccessCriteria    — 50-paragraph IR < 5s, < 5% unparsed citations
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.ir import ElementType, IRElement, IRSchema, TextRun

# ── Fixture directory ─────────────────────────────────────────────────────────
_FIXTURE_DIR = Path(__file__).parent / "fixtures"


# ═══════════════════════════════════════════════════════════════════════════════
# Builders
# ═══════════════════════════════════════════════════════════════════════════════

def _make_element(
    eid: str,
    text: str,
    etype: ElementType = ElementType.PARAGRAPH,
    style: str = "Normal",
    font_size: float | None = None,
    level: int = 0,
    is_footnote: bool = False,
) -> IRElement:
    run = TextRun(
        text=text,
        bold=False,
        italic=False,
        font_name="Times New Roman",
        font_size_pt=font_size,
    )
    meta: dict = {"style_name": style}
    if is_footnote:
        meta["is_footnote"] = True
    return IRElement(
        element_id=eid,
        element_type=etype,
        content=[run],
        raw_text=text,
        level=level,
        metadata=meta,
    )


def _make_ir(elements: list[IRElement], source_format: str = "docx") -> IRSchema:
    return IRSchema(
        document_title="",
        authors=[],
        elements=elements,
        metadata={},
        source_format=source_format,
        word_count=0,
    )


def _load_fixture_ir() -> IRSchema:
    """Load the sample_paper_ir.json fixture."""
    raw = json.loads((_FIXTURE_DIR / "sample_paper_ir.json").read_text())
    return IRSchema.model_validate(raw)


# ═══════════════════════════════════════════════════════════════════════════════
# TestStructureDetector
# ═══════════════════════════════════════════════════════════════════════════════

class TestStructureDetector:
    """Tests for StructureDetector rule cascade."""

    def _detector(self):
        from app.agents.parsing.structure_detector import StructureDetector
        return StructureDetector(use_spacy=False)  # rules only — no spaCy dep

    def test_title_detected_by_style(self):
        ir = _make_ir([
            _make_element("e0", "My Paper Title", style="Title", font_size=24.0),
            _make_element("e1", "Some body text here.", font_size=12.0),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.TITLE
        assert result.elements[0].metadata["confidence"] == 0.95

    def test_title_detected_by_large_font_at_index_0(self):
        ir = _make_ir([
            _make_element("e0", "Large Font Title", style="Normal", font_size=24.0),
            _make_element("e1", "Body body body.", font_size=12.0),
            _make_element("e2", "More body text.", font_size=12.0),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.TITLE

    def test_abstract_detected_by_style(self):
        ir = _make_ir([
            _make_element("e0", "My Title", style="Title", font_size=20.0),
            _make_element("e1", "This is the abstract text.", style="Abstract", font_size=12.0),
        ])
        result = self._detector().detect(ir)
        assert result.elements[1].element_type == ElementType.ABSTRACT
        assert result.elements[1].metadata["confidence"] == 0.95

    def test_abstract_detected_by_prefix(self):
        ir = _make_ir([
            _make_element("e0", "Title", style="Normal", font_size=18.0),
            _make_element("e1", "Abstract: This paper presents a new approach to solving " * 10,
                          style="Normal", font_size=12.0),
        ])
        result = self._detector().detect(ir)
        assert result.elements[1].element_type == ElementType.ABSTRACT

    def test_keyword_detected(self):
        ir = _make_ir([
            _make_element("e0", "Keywords: NLP, machine learning, transformers"),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.KEYWORD

    def test_keyword_variant_detected(self):
        ir = _make_ir([
            _make_element("e0", "Key words: neural networks, deep learning"),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.KEYWORD

    def test_heading_detected_by_style(self):
        ir = _make_ir([
            _make_element("e0", "Introduction", style="Heading 1", font_size=16.0),
            _make_element("e1", "Related Work", style="Heading 2", font_size=14.0),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.HEADING
        assert result.elements[0].level == 1
        assert result.elements[1].element_type == ElementType.HEADING
        assert result.elements[1].level == 2

    def test_heading_detected_by_large_font(self):
        ir = _make_ir([
            _make_element("e0", "Section A", font_size=20.0),
            _make_element("e1", "Body text " * 20, font_size=12.0),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.HEADING
        assert result.elements[0].metadata["confidence"] == 0.80

    def test_reference_section_after_heading(self):
        ir = _make_ir([
            _make_element("e0", "Introduction", style="Heading 1"),
            _make_element("e1", "Body text here."),
            _make_element("e2", "References", style="Heading 1"),
            _make_element("e3", "Smith, J. (2020). Some paper. Journal, 1(1), 1-10."),
            _make_element("e4", "Jones, A. (2021). Another paper. Journal, 2(2), 20-30."),
        ])
        result = self._detector().detect(ir)
        assert result.elements[3].element_type == ElementType.REFERENCE
        assert result.elements[4].element_type == ElementType.REFERENCE

    def test_figure_caption_detected(self):
        ir = _make_ir([
            _make_element("e0", "Figure 1. BLEU scores across benchmarks."),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.FIGURE_CAPTION

    def test_table_caption_detected(self):
        ir = _make_ir([
            _make_element("e0", "Table 2. Comparison of NMT systems."),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.TABLE_CAPTION

    def test_footnote_detected_by_metadata_flag(self):
        el = _make_element("e0", "This is a footnote.", is_footnote=True)
        ir = _make_ir([el])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.FOOTNOTE

    def test_default_paragraph_fallback(self):
        ir = _make_ir([
            _make_element("e0", "Some random body text that has no special features."),
        ])
        result = self._detector().detect(ir)
        assert result.elements[0].element_type == ElementType.PARAGRAPH

    def test_fixture_detection_accuracy_above_90pct(self):
        """
        SC: Element detection accuracy > 90% on tests/fixtures/sample_paper_ir.json.

        Expected element types (by position in fixture):
          el_0  → TITLE        (style=Title, font_size=24)
          el_1  → ABSTRACT     (style=Abstract)
          el_2  → KEYWORD      (starts with 'Keywords:')
          el_3  → HEADING      (style=Heading 1)
          el_4  → PARAGRAPH    (body)
          el_5  → HEADING      (style=Heading 1)
          el_6  → PARAGRAPH    (body)
          el_7  → FIGURE_CAPTION (starts with 'Figure 1.')
          el_8  → TABLE_CAPTION  (starts with 'Table 1.')
          el_9  → HEADING      (style=Heading 1 — "References")
          el_10 → REFERENCE    (after References heading)
          el_11 → REFERENCE
          el_12 → REFERENCE
        """
        expected = {
            "el_0": ElementType.TITLE,
            "el_1": ElementType.ABSTRACT,
            "el_2": ElementType.KEYWORD,
            "el_3": ElementType.HEADING,
            "el_4": ElementType.PARAGRAPH,
            "el_5": ElementType.HEADING,
            "el_6": ElementType.PARAGRAPH,
            "el_7": ElementType.FIGURE_CAPTION,
            "el_8": ElementType.TABLE_CAPTION,
            "el_9": ElementType.HEADING,
            "el_10": ElementType.REFERENCE,
            "el_11": ElementType.REFERENCE,
            "el_12": ElementType.REFERENCE,
        }
        ir = _load_fixture_ir()
        result = self._detector().detect(ir)

        correct = 0
        total = len(expected)
        for el in result.elements:
            if el.element_id in expected:
                got = el.element_type
                want = expected[el.element_id]
                if got == want:
                    correct += 1
                else:
                    print(f"  MISMATCH {el.element_id}: got={got.value} want={want.value}")

        accuracy = correct / total
        assert accuracy >= 0.90, (
            f"Detection accuracy {accuracy:.1%} < 90% "
            f"({correct}/{total} correct)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TestCitationParser
# ═══════════════════════════════════════════════════════════════════════════════

class TestCitationParser:
    """Tests for CitationParser pattern extraction."""

    def _parser(self):
        from app.agents.parsing.citation_parser import CitationParser
        return CitationParser()

    def test_apa_basic(self):
        text = "The results confirm prior findings (Smith, 2020)."
        ir = _make_ir([_make_element("e0", text)])
        cits = self._parser().parse_all(ir)
        apa = [c for c in cits if c.style_hint == "apa"]
        assert len(apa) == 1
        assert apa[0].authors == ["Smith"]
        assert apa[0].year == "2020"

    def test_apa_et_al(self):
        text = "As shown in previous work (Vaswani et al., 2017)."
        ir = _make_ir([_make_element("e0", text)])
        cits = self._parser().parse_all(ir)
        apa = [c for c in cits if c.style_hint == "apa"]
        assert len(apa) == 1
        assert "Vaswani" in apa[0].authors[0]
        assert apa[0].year == "2017"

    def test_apa_with_page(self):
        text = "The author argues (Jones, 2019, p. 42) that results hold."
        ir = _make_ir([_make_element("e0", text)])
        cits = self._parser().parse_all(ir)
        apa = [c for c in cits if c.style_hint == "apa"]
        assert len(apa) == 1
        assert apa[0].pages == "42"

    def test_apa_multiple_in_paragraph(self):
        text = (
            "Both (Smith, 2018) and (Jones, 2019) support the hypothesis. "
            "(Brown et al., 2020) provides further evidence."
        )
        ir = _make_ir([_make_element("e0", text)])
        cits = self._parser().parse_all(ir)
        apa = [c for c in cits if c.style_hint == "apa"]
        assert len(apa) == 3

    def test_ieee_single(self):
        text = "The method was first described in [1]."
        ir = _make_ir([_make_element("e0", text)])
        cits = self._parser().parse_all(ir)
        ieee = [c for c in cits if c.style_hint == "ieee"]
        assert len(ieee) == 1
        assert ieee[0].raw_text == "[1]"

    def test_ieee_multiple_inline(self):
        text = "As shown in previous work [1,2,3] and further confirmed [4,5]."
        ir = _make_ir([_make_element("e0", text)])
        cits = self._parser().parse_all(ir)
        ieee = [c for c in cits if c.style_hint == "ieee"]
        assert len(ieee) == 2

    def test_mla_author_page(self):
        text = "The author states exactly this point (Williams 47)."
        ir = _make_ir([_make_element("e0", text)])
        cits = self._parser().parse_all(ir)
        mla = [c for c in cits if c.style_hint == "mla"]
        assert len(mla) == 1
        assert mla[0].authors == ["Williams"]
        assert mla[0].pages == "47"

    def test_no_citations_in_heading(self):
        """Citations inside HEADING elements must be ignored."""
        from app.schemas.ir import ElementType
        el_heading = _make_element(
            "h0", "Introduction (Smith, 2020)", etype=ElementType.HEADING
        )
        ir = _make_ir([el_heading])
        cits = self._parser().parse_all(ir)
        assert len(cits) == 0

    def test_empty_ir(self):
        ir = _make_ir([])
        cits = self._parser().parse_all(ir)
        assert cits == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestCitationStyleClassifier
# ═══════════════════════════════════════════════════════════════════════════════

class TestCitationStyleClassifier:
    """Tests for CitationStyleClassifier voting logic."""

    def _clf(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleClassifier
        return CitationStyleClassifier()

    def _make_cits(self, style: str, n: int):
        from app.schemas.ir_schema import CitationObject
        return [
            CitationObject(id=f"c{i}", raw_text=f"cit {i}", style_hint=style)
            for i in range(n)
        ]

    def test_apa_majority(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        cits = self._make_cits("apa", 8) + self._make_cits("ieee", 2)
        style, conf = self._clf().classify(cits)
        assert style == CitationStyleEnum.APA
        assert conf >= 0.7

    def test_ieee_majority(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        cits = self._make_cits("ieee", 10) + self._make_cits("apa", 2)
        style, conf = self._clf().classify(cits)
        assert style == CitationStyleEnum.IEEE
        assert conf >= 0.7

    def test_vancouver_majority(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        cits = self._make_cits("vancouver", 7)
        style, conf = self._clf().classify(cits)
        assert style == CitationStyleEnum.VANCOUVER
        assert conf == 1.0

    def test_mla_majority(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        cits = self._make_cits("mla", 5) + self._make_cits("apa", 1)
        style, conf = self._clf().classify(cits)
        assert style == CitationStyleEnum.MLA

    def test_unknown_for_fewer_than_3(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        from app.schemas.ir_schema import CitationObject
        cits = [CitationObject(id="c0", raw_text="x", style_hint="apa"),
                CitationObject(id="c1", raw_text="y", style_hint="apa")]
        style, conf = self._clf().classify(cits)
        assert style == CitationStyleEnum.UNKNOWN
        assert conf == 0.0

    def test_empty_returns_unknown(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        style, conf = self._clf().classify([])
        assert style == CitationStyleEnum.UNKNOWN
        assert conf == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TestReferenceParser
# ═══════════════════════════════════════════════════════════════════════════════

class TestReferenceParser:
    """Tests for ReferenceParser structured field extraction."""

    def _parser(self):
        from app.agents.parsing.reference_parser import ReferenceParser
        return ReferenceParser()

    @pytest.mark.asyncio
    async def test_apa_reference_parses_correctly(self):
        """Extract authors, year, title, journal from an APA reference."""
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        ref_el = _make_element(
            "r0",
            "Bahdanau, D., Cho, K., & Bengio, Y. (2015). "
            "Neural machine translation by jointly learning to align and translate. "
            "ICLR 2015.",
            etype=ElementType.REFERENCE,
        )
        ir = _make_ir([ref_el])
        refs = await self._parser().parse_all(ir, CitationStyleEnum.APA)
        assert len(refs) == 1
        r = refs[0]
        assert r.year == "2015"
        assert "Bahdanau" in (r.authors[0] if r.authors else "")
        assert r.title is not None and len(r.title) > 5

    @pytest.mark.asyncio
    async def test_apa_ref_with_volume_and_pages(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        ref_el = _make_element(
            "r1",
            "Vaswani, A., Shazeer, N., & Parmar, N. (2017). "
            "Attention is all you need. "
            "Advances in Neural Information Processing Systems, 30, 5998-6008.",
            etype=ElementType.REFERENCE,
        )
        ir = _make_ir([ref_el])
        refs = await self._parser().parse_all(ir, CitationStyleEnum.APA)
        assert len(refs) == 1
        r = refs[0]
        assert r.year == "2017"
        assert r.volume == "30"
        assert r.pages == "5998-6008"

    @pytest.mark.asyncio
    async def test_apa_three_refs_parsed(self):
        """Parse 3 known APA references; all must have year extracted."""
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        raw_refs = [
            "Smith, J. A., & Jones, B. (2020). Deep learning in NLP. Journal of AI, 10(2), 100-120.",
            "Lee, C., & Park, D. (2018). Transfer learning approaches. Nature ML, 5, 50-60.",
            "Brown, T., Mann, B., & Ryder, N. (2020). Language models are few-shot learners. NeurIPS, 33, 1877-1901.",
        ]
        elements = [
            _make_element(f"r{i}", r, etype=ElementType.REFERENCE)
            for i, r in enumerate(raw_refs)
        ]
        ir = _make_ir(elements)
        refs = await self._parser().parse_all(ir, CitationStyleEnum.APA)
        assert len(refs) == 3
        years = [r.year for r in refs]
        assert "2020" in years
        assert "2018" in years

    @pytest.mark.asyncio
    async def test_empty_ir_returns_empty_list(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        refs = await self._parser().parse_all(_make_ir([]), CitationStyleEnum.APA)
        assert refs == []

    @pytest.mark.asyncio
    async def test_doi_extracted(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        ref_el = _make_element(
            "r0",
            "Smith, J. (2021). Some title. Journal X, 5(1), 1-10. "
            "doi:10.1000/xyz123",
            etype=ElementType.REFERENCE,
        )
        ir = _make_ir([ref_el])
        refs = await self._parser().parse_all(ir, CitationStyleEnum.APA)
        assert refs[0].doi == "10.1000/xyz123"

    @pytest.mark.asyncio
    async def test_vancouver_parsed(self):
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum
        ref_el = _make_element(
            "v0",
            "Smith JA, Jones B. Deep learning in medicine. Nat Med. 2020;26(3):345-350.",
            etype=ElementType.REFERENCE,
        )
        ir = _make_ir([ref_el])
        refs = await self._parser().parse_all(ir, CitationStyleEnum.VANCOUVER)
        assert len(refs) >= 1
        # Vancouver parser picks up raw_text regardless
        assert refs[0].raw_text is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TestDocParseAgent — integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocParseAgent:
    """Integration tests for the full DocParseAgent.run() pipeline."""

    def _make_state(self, ir: IRSchema | None = None):
        from app.schemas.job_state import JobState
        state = JobState(job_id="parse_test_job", metadata={})
        if ir:
            state.raw_ir = ir
        return state

    @pytest.mark.asyncio
    async def test_successful_parse(self):
        from app.agents.parsing.agent import DocParseAgent
        from app.schemas.job_state import JobStatus

        ir = _load_fixture_ir()
        state = self._make_state(ir=ir)

        with patch(
            "app.agents.parsing.agent.cache_service.publish_progress",
            new_callable=AsyncMock,
        ):
            agent = DocParseAgent(use_spacy=False)
            updated = await agent.run(state)

        assert updated.status == JobStatus.PARSING
        assert updated.annotated_ir is not None
        assert updated.progress_pct == 40.0
        assert updated.errors == []

    @pytest.mark.asyncio
    async def test_missing_raw_ir_fails(self):
        from app.agents.parsing.agent import DocParseAgent
        from app.schemas.job_state import JobStatus

        state = self._make_state(ir=None)
        agent = DocParseAgent(use_spacy=False)
        updated = await agent.run(state)

        assert updated.status == JobStatus.FAILED
        assert len(updated.errors) == 1
        assert "raw_ir is None" in updated.errors[0].message

    @pytest.mark.asyncio
    async def test_annotated_ir_has_citations_in_metadata(self):
        from app.agents.parsing.agent import DocParseAgent

        ir = _load_fixture_ir()
        state = self._make_state(ir=ir)

        with patch(
            "app.agents.parsing.agent.cache_service.publish_progress",
            new_callable=AsyncMock,
        ):
            agent = DocParseAgent(use_spacy=False)
            updated = await agent.run(state)

        meta = updated.annotated_ir.metadata
        assert "citations_parsed" in meta
        assert "detected_style" in meta
        assert "references_parsed" in meta

    @pytest.mark.asyncio
    async def test_raw_ir_not_mutated(self):
        """raw_ir elements must not be mutated by DocParseAgent (deep copy)."""
        from app.agents.parsing.agent import DocParseAgent

        ir = _load_fixture_ir()
        original_types = [el.element_type for el in ir.elements]
        state = self._make_state(ir=ir)

        with patch(
            "app.agents.parsing.agent.cache_service.publish_progress",
            new_callable=AsyncMock,
        ):
            agent = DocParseAgent(use_spacy=False)
            await agent.run(state)

        # After run, raw_ir element types must be unchanged
        for orig_type, el in zip(original_types, state.raw_ir.elements):
            assert el.element_type == orig_type

    @pytest.mark.asyncio
    async def test_progress_published_on_success(self):
        from app.agents.parsing.agent import DocParseAgent

        ir = _load_fixture_ir()
        state = self._make_state(ir=ir)

        with patch(
            "app.agents.parsing.agent.cache_service.publish_progress",
            new_callable=AsyncMock,
        ) as mock_pub:
            agent = DocParseAgent(use_spacy=False)
            await agent.run(state)

        mock_pub.assert_called_once()
        kwargs = mock_pub.call_args.kwargs
        assert kwargs["job_id"] == "parse_test_job"
        assert kwargs["event_dict"]["agent"] == "parsing"
        assert kwargs["event_dict"]["pct"] == 40


# ═══════════════════════════════════════════════════════════════════════════════
# TestSuccessCriteria
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuccessCriteria:
    """
    Validate the explicit success criteria from the prompt:
      SC-1  Detection accuracy > 90% on sample_paper_ir.json fixture
      SC-2  50-paragraph IR completes in < 5 seconds
      SC-3  < 5% of citations in test manuscripts result in unparsed objects
    """

    def test_sc1_fixture_detection_accuracy_above_90pct(self):
        """Same test as in TestStructureDetector — duplicated here for CI clarity."""
        from app.agents.parsing.structure_detector import StructureDetector

        expected = {
            "el_0": ElementType.TITLE,
            "el_1": ElementType.ABSTRACT,
            "el_2": ElementType.KEYWORD,
            "el_3": ElementType.HEADING,
            "el_4": ElementType.PARAGRAPH,
            "el_5": ElementType.HEADING,
            "el_6": ElementType.PARAGRAPH,
            "el_7": ElementType.FIGURE_CAPTION,
            "el_8": ElementType.TABLE_CAPTION,
            "el_9": ElementType.HEADING,
            "el_10": ElementType.REFERENCE,
            "el_11": ElementType.REFERENCE,
            "el_12": ElementType.REFERENCE,
        }
        ir = _load_fixture_ir()
        result = StructureDetector(use_spacy=False).detect(ir)

        correct = sum(
            1 for el in result.elements
            if el.element_id in expected and el.element_type == expected[el.element_id]
        )
        accuracy = correct / len(expected)
        assert accuracy >= 0.90, f"SC-1 accuracy {accuracy:.1%} < 90%"

    @pytest.mark.asyncio
    async def test_sc2_50_paragraph_ir_under_5_seconds(self):
        """50-paragraph IR must complete through DocParseAgent in < 5 seconds."""
        from app.agents.parsing.agent import DocParseAgent
        from app.schemas.job_state import JobState

        elements = []
        for i in range(50):
            if i % 10 == 0:
                elements.append(_make_element(
                    f"h{i}", f"Section {i // 10 + 1}: Analysis", style="Heading 1",
                ))
            else:
                para = (
                    f"Paragraph {i}: This study demonstrates significant improvements "
                    f"over prior methods (Smith, 20{20 + i % 5}). "
                    f"The results align with predictions from [1] and [2]."
                )
                elements.append(_make_element(f"p{i}", para))

        # Add a references section
        elements.append(_make_element("ref_head", "References", style="Heading 1"))
        for j in range(5):
            elements.append(_make_element(
                f"ref_{j}",
                f"Author{j}, A. (202{j}). Title {j}. Journal {j}, {j + 1}({j + 2}), {j * 10}-{j * 10 + 9}.",
                etype=ElementType.REFERENCE,
            ))

        ir = _make_ir(elements)
        state = JobState(job_id="sc2_job", metadata={})
        state.raw_ir = ir

        with patch(
            "app.agents.parsing.agent.cache_service.publish_progress",
            new_callable=AsyncMock,
        ):
            agent = DocParseAgent(use_spacy=False)
            t0 = time.perf_counter()
            updated = await agent.run(state)
            elapsed = time.perf_counter() - t0

        assert elapsed < 5.0, f"SC-2: 50-para IR took {elapsed:.3f}s >= 5s"
        assert updated.annotated_ir is not None

    @pytest.mark.asyncio
    async def test_sc3_less_than_5_pct_unparsed_citations(self):
        """
        SC-3: < 5% of citations in a citation-rich manuscript should
        result in CitationObject with style_hint == None (unparsed).

        We build a paragraph with 20 APA citations and verify the
        unparsed rate is below the threshold.
        """
        from app.agents.parsing.citation_parser import CitationParser

        # Use realistic author surnames (no digits) so APA regex matches
        _SURNAMES = [
            "Smith", "Jones", "Brown", "Taylor", "Wilson",
            "Moore", "Anderson", "Thomas", "Jackson", "White",
            "Harris", "Martin", "Thompson", "Garcia", "Martinez",
            "Robinson", "Clark", "Rodriguez", "Lewis", "Lee",
        ]

        paras = []
        expected_total = 0
        for i in range(10):
            text_parts = []
            for j in range(2):
                author = _SURNAMES[(i * 2 + j) % len(_SURNAMES)]
                year = 2010 + i
                text_parts.append(f"({author}, {year})")
                expected_total += 1
            text = "Body text here. " + " and ".join(text_parts) + " confirm findings."
            paras.append(_make_element(f"p{i}", text))

        ir = _make_ir(paras)
        parser = CitationParser()
        cits = parser.parse_all(ir)

        unparsed = [c for c in cits if not c.style_hint or c.style_hint == "unknown"]
        unparsed_rate = len(unparsed) / max(len(cits), 1)

        assert unparsed_rate < 0.05, (
            f"SC-3: {unparsed_rate:.1%} of citations unparsed "
            f"(found {len(unparsed)}/{len(cits)})"
        )
        assert len(cits) >= expected_total * 0.95, (
            f"SC-3: Expected at least {expected_total} citations, got {len(cits)}"
        )
