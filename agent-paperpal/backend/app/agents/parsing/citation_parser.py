# backend/app/agents/parsing/citation_parser.py
"""
CitationParser — Stage 2 component.

Scans every BODY / PARAGRAPH element in the IR for in-text citation patterns
and returns a list of CitationObjects.

Supported patterns (compiled once at import time):
  APA_AUTHOR_YEAR   (Smith, 2020) or (Smith et al., 2020) or (Smith, 2020, p. 15)
  IEEE_NUMBERED     [1] or [1,2,3] or [1–3]
  NUMERIC_SUPER     superscript-style numerals in reference-dense paragraphs
  MLA_NO_YEAR       (Smith 42) — author + page
"""

from __future__ import annotations

import logging
import re

from app.schemas.ir import ElementType, IRSchema
from app.schemas.ir_schema import CitationObject

logger = logging.getLogger(__name__)

# ── Compiled patterns ──────────────────────────────────────────────────────────

# APA/Harvard: (Smith, 2020) | (Smith et al., 2020) | (Smith, 2020, p. 15)
_APA = re.compile(
    r"\(([A-Z][a-zA-Zé'-]+(?:\s+et\s+al\.)?),?\s+(\d{4})"
    r"(?:,?\s+p\.?\s*(\d+(?:[-–]\d+)?))?\)"
)

# IEEE / Vancouver: [1] [1,2] [1–3] [1-3]
_IEEE = re.compile(r"\[([\d,\s;–\-]+)\]")

# Numeric superscript: bare digits 1–3 chars — only used in high-citation context
_NUMERIC_SUP = re.compile(r"(?<!\d)(\d{1,3})(?=\D|\Z)")

# MLA: (Smith 42) — author surname + page number
_MLA = re.compile(r"\(([A-Z][a-zA-Zé'-]+)\s+(\d+)\)")


class CitationParser:
    """
    Scan an IR for in-text citations and emit CitationObject records.

    Usage::
        parser = CitationParser()
        citations = parser.parse_all(ir)
    """

    # Minimum IEEE citations in a paragraph to trust _IEEE pattern
    _IEEE_THRESHOLD = 1
    # Minimum APA citations in document to consider _NUMERIC_SUP
    _SUPER_CTX_THRESHOLD = 5

    def parse_all(self, ir: IRSchema) -> list[CitationObject]:
        """
        Scan all PARAGRAPH / BODY elements for in-text citations.

        Args:
            ir: The IRSchema after structure detection (elements annotated).

        Returns:
            list of CitationObject, ordered by appearance in the document.
        """
        citations: list[CitationObject] = []
        counter = 0

        for element in ir.elements:
            # Only scan body-level paragraphs (not headings, tables, references)
            if element.element_type not in (
                ElementType.PARAGRAPH,
                ElementType.ABSTRACT,
                ElementType.UNKNOWN,
            ):
                continue

            text = element.raw_text
            if not text.strip():
                continue

            # ── APA ────────────────────────────────────────────────────────────
            for m in _APA.finditer(text):
                author_raw = m.group(1).strip()
                year = m.group(2)
                pages = m.group(3)
                citations.append(
                    CitationObject(
                        id=f"cit_{counter}",
                        authors=self._split_authors(author_raw),
                        year=year,
                        pages=pages,
                        raw_text=m.group(0),
                        style_hint="apa",
                    )
                )
                counter += 1

            # ── IEEE / Vancouver numbered ──────────────────────────────────────
            for m in _IEEE.finditer(text):
                inner = m.group(1).strip()
                # Expand ranges like "1–3" → ["1","2","3"]
                ref_nums = self._expand_range(inner)
                citations.append(
                    CitationObject(
                        id=f"cit_{counter}",
                        authors=[],
                        year=None,
                        pages=None,
                        raw_text=m.group(0),
                        style_hint="ieee",
                    )
                )
                counter += 1

            # ── MLA ────────────────────────────────────────────────────────────
            for m in _MLA.finditer(text):
                # Avoid double-counting APA matches (APA has year, MLA has page)
                if _APA.search(m.group(0)):
                    continue
                citations.append(
                    CitationObject(
                        id=f"cit_{counter}",
                        authors=[m.group(1)],
                        year=None,
                        pages=m.group(2),
                        raw_text=m.group(0),
                        style_hint="mla",
                    )
                )
                counter += 1

        # ── Numeric superscripts (only if high IEEE/Vancouver context) ─────────
        ieee_count = sum(1 for c in citations if c.style_hint == "ieee")
        if ieee_count >= self._SUPER_CTX_THRESHOLD:
            for element in ir.elements:
                if element.element_type not in (
                    ElementType.PARAGRAPH, ElementType.ABSTRACT
                ):
                    continue
                for m in _NUMERIC_SUP.finditer(element.raw_text):
                    # Only add if NOT already captured by [N] pattern
                    surrounding = element.raw_text[
                        max(0, m.start() - 1): m.end() + 1
                    ]
                    if "[" not in surrounding and "]" not in surrounding:
                        citations.append(
                            CitationObject(
                                id=f"cit_{counter}",
                                authors=[],
                                year=None,
                                pages=None,
                                raw_text=m.group(0),
                                style_hint="numeric_super",
                            )
                        )
                        counter += 1

        logger.debug("[CitationParser] Extracted %d citations", len(citations))
        return citations

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _split_authors(author_raw: str) -> list[str]:
        """Split 'Smith et al.' or 'Smith' into a list."""
        if "et al" in author_raw.lower():
            base = re.sub(r"\s+et\s+al\.?", "", author_raw, flags=re.IGNORECASE).strip()
            return [base, "et al."]
        return [author_raw.strip()]

    @staticmethod
    def _expand_range(inner: str) -> list[str]:
        """Expand '1,2,3' or '1–3' into individual ref number strings."""
        result: list[str] = []
        # Normalize en-dash
        inner = inner.replace("–", "-").replace(";", ",")
        for part in inner.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    result.extend(str(i) for i in range(int(start), int(end) + 1))
                except ValueError:
                    result.append(part)
            elif part.isdigit():
                result.append(part)
        return result
