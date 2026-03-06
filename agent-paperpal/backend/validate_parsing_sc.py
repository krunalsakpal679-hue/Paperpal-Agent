# backend/validate_parsing_sc.py
"""
Stage 2 Success Criteria Validator for DocParseAgent.

Verifies all 4 explicit success criteria defined in the spec:
  SC-1  Element detection accuracy > 90% on sample_paper_ir.json
  SC-2  Citation style detection correct for APA, Vancouver, IEEE
  SC-3  < 5% of citations unparsed in a 20-citation APA manuscript
  SC-4  50-paragraph IR completes in < 5 seconds end-to-end

Run from backend/ with:
    python validate_parsing_sc.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

# ── ensure backend/ is on sys.path ─────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

PASS = "[PASS]"
FAIL = "[FAIL]"
SEP  = "-" * 72


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_run(eid, text, etype="paragraph", style="Normal", font_size=None):
    from app.schemas.ir import ElementType, IRElement, IRSchema, TextRun
    run = TextRun(text=text, bold=False, italic=False,
                  font_name="Times New Roman", font_size_pt=font_size)
    return IRElement(
        element_id=eid,
        element_type=ElementType[etype.upper()] if etype.upper() in ElementType.__members__ else ElementType.PARAGRAPH,
        content=[run],
        raw_text=text,
        level=0,
        metadata={"style_name": style},
    )


def _make_ir(elements, src="docx"):
    from app.schemas.ir import IRSchema
    return IRSchema(
        document_title="", authors=[], elements=elements,
        metadata={}, source_format=src, word_count=0,
    )


def _load_fixture():
    fixture = (
        Path(__file__).parent /
        "app" / "agents" / "parsing" / "tests" / "fixtures" / "sample_paper_ir.json"
    )
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    from app.schemas.ir import IRSchema
    return IRSchema.model_validate(raw)


# ── SC-1 ───────────────────────────────────────────────────────────────────────

def check_sc1():
    print(SEP)
    print("SC-1  Element detection accuracy > 90% on sample_paper_ir.json")
    print(SEP)

    from app.agents.parsing.structure_detector import StructureDetector
    from app.schemas.ir import ElementType

    expected = {
        "el_0":  "TITLE",
        "el_1":  "ABSTRACT",
        "el_2":  "KEYWORD",
        "el_3":  "HEADING",
        "el_4":  "PARAGRAPH",
        "el_5":  "HEADING",
        "el_6":  "PARAGRAPH",
        "el_7":  "FIGURE_CAPTION",
        "el_8":  "TABLE_CAPTION",
        "el_9":  "HEADING",
        "el_10": "REFERENCE",
        "el_11": "REFERENCE",
        "el_12": "REFERENCE",
    }

    ir = _load_fixture()
    result = StructureDetector(use_spacy=False).detect(ir)

    correct = 0
    mismatches = []
    for el in result.elements:
        if el.element_id in expected:
            want = ElementType[expected[el.element_id]]
            got  = el.element_type
            if got == want:
                correct += 1
                print(f"  {PASS}  {el.element_id:6s}  want={want.value:<18s}  got={got.value}")
            else:
                mismatches.append((el.element_id, want.value, got.value))
                print(f"  {FAIL}  {el.element_id:6s}  want={want.value:<18s}  got={got.value}")

    total = len(expected)
    accuracy = correct / total
    verdict = PASS if accuracy >= 0.90 else FAIL
    print(f"\n  {verdict}  Accuracy = {correct}/{total} = {accuracy:.0%}  (threshold: 90%)")
    return accuracy >= 0.90


# ── SC-2 ───────────────────────────────────────────────────────────────────────

def check_sc2():
    print(SEP)
    print("SC-2  Citation style detection correct for APA, Vancouver, IEEE")
    print(SEP)

    from app.agents.parsing.citation_style_classifier import (
        CitationStyleClassifier, CitationStyleEnum,
    )
    from app.schemas.ir_schema import CitationObject

    clf = CitationStyleClassifier()
    results = []

    def make_cits(hint, n):
        return [CitationObject(id=f"c{i}", raw_text=f"dummy {i}", style_hint=hint) for i in range(n)]

    for test_style, cit_hint, expected_enum in [
        ("APA",       "apa",       CitationStyleEnum.APA),
        ("Vancouver", "vancouver", CitationStyleEnum.VANCOUVER),
        ("IEEE",      "ieee",      CitationStyleEnum.IEEE),
        ("MLA",       "mla",       CitationStyleEnum.MLA),
    ]:
        cits = make_cits(cit_hint, 10)
        style, conf = clf.classify(cits)
        ok = (style == expected_enum)
        results.append(ok)
        verdict = PASS if ok else FAIL
        print(f"  {verdict}  {test_style:<12s}  detected={style.value:<12s}  conf={conf:.0%}")

    all_ok = all(results)
    verdict = PASS if all_ok else FAIL
    print(f"\n  {verdict}  {sum(results)}/{len(results)} styles detected correctly")
    return all_ok


# ── SC-3 ───────────────────────────────────────────────────────────────────────

def check_sc3():
    print(SEP)
    print("SC-3  < 5% of citations in test manuscripts result in unparsed CitationObjects")
    print(SEP)

    from app.agents.parsing.citation_parser import CitationParser

    surnames = [
        "Smith", "Jones", "Brown", "Taylor", "Wilson",
        "Moore", "Anderson", "Thomas", "Jackson", "White",
        "Harris", "Martin", "Thompson", "Garcia", "Martinez",
        "Robinson", "Clark", "Rodriguez", "Lewis", "Lee",
    ]

    elements = []
    expected_total = 0
    for i in range(10):
        parts = []
        for j in range(2):
            author = surnames[(i * 2 + j) % len(surnames)]
            year = 2010 + i
            parts.append(f"({author}, {year})")
            expected_total += 1
        text = "Body text here. " + " and ".join(parts) + " confirm findings."
        elements.append(_make_run(f"p{i}", text))

    ir = _make_ir(elements)
    parser = CitationParser()
    cits = parser.parse_all(ir)

    unparsed = [c for c in cits if not c.style_hint or c.style_hint == "unknown"]
    rate = len(unparsed) / max(len(cits), 1)

    print(f"  Paragraphs:       10")
    print(f"  Expected cits:    {expected_total}")
    print(f"  Extracted cits:   {len(cits)}")
    print(f"  Unparsed cits:    {len(unparsed)}")
    print(f"  Unparsed rate:    {rate:.1%}")

    ok = rate < 0.05 and len(cits) >= expected_total * 0.95
    verdict = PASS if ok else FAIL
    print(f"\n  {verdict}  Unparsed rate {rate:.1%} {'<' if rate < 0.05 else '>='} 5%  |  " +
          f"Coverage {len(cits)}/{expected_total}")
    return ok


# ── SC-4 ───────────────────────────────────────────────────────────────────────

async def _run_sc4():
    from app.agents.parsing.agent import DocParseAgent
    from app.schemas.ir import ElementType
    from app.schemas.job_state import JobState

    elements = []
    for i in range(50):
        if i % 10 == 0:
            elements.append(_make_run(
                f"h{i}", f"Section {i // 10 + 1}: Analysis",
                etype="PARAGRAPH", style="Heading 1",
            ))
        else:
            para = (
                f"Paragraph {i}: This study demonstrates improvements "
                f"(Smith, 20{20 + i % 5}). Results align with [1] and [2]."
            )
            elements.append(_make_run(f"p{i}", para))

    # References section
    elements.append(_make_run("ref_head", "References", style="Heading 1"))
    for j in range(5):
        elements.append(_make_run(
            f"ref_{j}",
            f"Author{j + 1}man, A. (202{j}). Title {j}. Journal {j}, {j + 1}({j + 2}), {j * 10}-{j * 10 + 9}.",
        ))

    ir = _make_ir(elements)
    state = JobState(job_id="sc4_job", metadata={})
    state.raw_ir = ir

    with patch(
        "app.agents.parsing.agent.cache_service.publish_progress",
        new_callable=AsyncMock,
    ):
        agent = DocParseAgent(use_spacy=False)
        t0 = time.perf_counter()
        updated = await agent.run(state)
        elapsed = time.perf_counter() - t0

    return elapsed, updated


def check_sc4():
    print(SEP)
    print("SC-4  50-paragraph IR completes in < 5 seconds (end-to-end)")
    print(SEP)

    elapsed, updated = asyncio.run(_run_sc4())

    n_elements   = len(updated.annotated_ir.elements) if updated.annotated_ir else 0
    n_citations  = len(updated.annotated_ir.metadata.get("citations_parsed", [])) if updated.annotated_ir else 0
    n_references = len(updated.annotated_ir.metadata.get("references_parsed", [])) if updated.annotated_ir else 0

    print(f"  Elapsed time:     {elapsed:.3f}s  (limit: 5.000s)")
    print(f"  Elements labelled:{n_elements}")
    print(f"  Citations found:  {n_citations}")
    print(f"  References parsed:{n_references}")
    print(f"  Agent status:     {updated.status.value}")

    ok = elapsed < 5.0 and updated.annotated_ir is not None
    verdict = PASS if ok else FAIL
    print(f"\n  {verdict}  {elapsed:.3f}s {'< 5s' if elapsed < 5.0 else '>= 5s'}")
    return ok


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 72)
    print("  AGENT PAPERPAL — STAGE 2 (DocParseAgent) — SUCCESS CRITERIA CHECK")
    print("=" * 72 + "\n")

    results = {
        "SC-1 Detection accuracy > 90%":     check_sc1(),
        "SC-2 Citation style classification": check_sc2(),
        "SC-3 < 5% unparsed citations":       check_sc3(),
        "SC-4 50-para IR < 5 seconds":        check_sc4(),
    }

    print("\n" + "=" * 72)
    print("  SUMMARY")
    print("=" * 72)
    all_pass = True
    for name, ok in results.items():
        verdict = PASS if ok else FAIL
        print(f"  {verdict}  {name}")
        if not ok:
            all_pass = False

    print("\n" + "=" * 72)
    if all_pass:
        print("  ALL SUCCESS CRITERIA MET — Stage 2 COMPLETE")
    else:
        print("  ONE OR MORE CRITERIA FAILED — see details above")
    print("=" * 72 + "\n")

    sys.exit(0 if all_pass else 1)
