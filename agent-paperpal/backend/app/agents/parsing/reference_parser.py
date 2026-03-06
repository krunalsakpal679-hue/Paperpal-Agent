# backend/app/agents/parsing/reference_parser.py
"""
ReferenceParser — Stage 2 component.

Extracts structured ReferenceObject records from REFERENCE-typed elements
in the annotated IR using style-specific regex strategies.

Supported strategies:
  APA / MLA / Chicago — Author-year format:
    Author, A. A., & Author, B. B. (Year). Title. Journal, Vol(Issue), pages. DOI

  Vancouver — numeric list format:
    [1] Author AA, Author BB. Title. Journal. Year;Vol(Issue):Pages.

  IEEE — numeric with quoted title:
    [1] A. Author and B. Author, "Title," Journal, vol. V, pp. P, Year.

  UNKNOWN / fallback — greedy best-effort extraction

CrossRef enrichment: if a DOI is found and CROSSREF_API_KEY is configured,
the parser fetches missing metadata from the CrossRef API (async via httpx).
This is optional and non-blocking; failures are logged and ignored.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

from app.schemas.ir import ElementType, IRSchema
from app.schemas.ir_schema import ReferenceObject

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Compiled patterns ──────────────────────────────────────────────────────────

# Strip leading [1] or 1. numbering from reference lines
_STRIP_LEAD_NUM = re.compile(r"^\s*[\[\(]?\d+[\]\)\.]?\s*")

# APA/MLA/Chicago: anchored on the (Year). part, split before/after.
# Two-pass: we find the year-anchor first, then parse surrounding fields.
# Pattern is intentionally simple to avoid catastrophic backtracking.
_APA_YEAR_ANCHOR = re.compile(
    r"^(?P<authors_raw>.+?)\s*"
    r"\((?P<year>\d{4}[a-z]?)\)\.\s*"
    r"(?P<remainder>.+)$",
    re.DOTALL,
)

# After the year anchor, parse title + optional venue details
_APA_REMAINDER = re.compile(
    r"^(?P<title>[^.]+?)\."   # title (up to first period)
    r"\s*"
    r"(?P<venue>.*?)$",       # everything after title is 'venue'
    re.DOTALL,
)

# From venue string: extract volume(issue), pages, and optional DOI
_APA_VENUE_VOL = re.compile(
    r"(?P<journal>.+?),\s*(?P<volume>\d+)"
    r"(?:\((?P<issue>[^)]+)\))?"
    r"(?:,\s*(?:pp?\.\s*)?(?P<pages>[\d\-–]+))?",
)

_APA_DOI_IN_VENUE = re.compile(r"(?:doi:\s*|https?://doi\.org/)(\S+)", re.IGNORECASE)

# Vancouver: Author AA. Title. Journal. Year;Vol(Issue):Pages.
_VANCOUVER_REF = re.compile(
    r"^(?P<authors_raw>.+?)\.\s+"
    r"(?P<title>[^.]+?)\.\s+"
    r"(?P<journal>[^.]+?)\.\s+"
    r"(?P<year>\d{4})"
    r"(?:;(?P<volume>\d+)"
    r"(?:\((?P<issue>[^)]+)\))?"
    r"(?::(?P<pages>[\d\-–]+))?)?\s*"
    r"(?:(?:https?://doi\.org/|doi:\s*)(?P<doi>\S+))?"
    r"\s*[.]?\s*$",
    re.DOTALL,
)

# IEEE: A. Author and B. Author, "Title," Journal, vol. V, pp. P, Year.
# Quote characters: straight " (0x22), left/right curly " (0x201C/0x201D)
_IEEE_QUOTE = r'["\u201c\u201d]'
_IEEE_REF = re.compile(
    r"^(?P<authors_raw>.+?),\s+"
    + _IEEE_QUOTE + r"(?P<title>[^" + '"\u201c\u201d' + r"]+)" + _IEEE_QUOTE + r",?\s+"
    r"(?P<journal>[^,]+?)?"
    r"(?:,?\s*vol\.\s*(?P<volume>[^,]+))?"
    r"(?:,?\s*(?:no\.\s*(?P<issue>[^,]+)))?"
    r"(?:,?\s*pp\.\s*(?P<pages>[^,]+))?"
    r"(?:,?\s*(?P<year>\d{4}))?"
    r"(?:[.,]\s*(?:doi:\s*|https?://doi\.org/)(?P<doi>\S+))?"
    r"\s*[.]?\s*$",
    re.DOTALL,
)

# DOI anywhere in string
_DOI_RE = re.compile(r"(?:doi:\s*|https?://doi\.org/)(\S+)", re.IGNORECASE)


class ReferenceParser:
    """
    Parse structured reference data from REFERENCE elements in the IR.

    Usage::
        ref_parser = ReferenceParser()
        refs = await ref_parser.parse_all(ir, detected_style)
    """

    async def parse_all(
        self,
        ir: IRSchema,
        detected_style: "CitationStyleEnum",  # type: ignore[name-defined]  # noqa: F821
    ) -> list[ReferenceObject]:
        """
        Parse all REFERENCE elements.

        Args:
            ir: Annotated IRSchema.
            detected_style: Style enum from CitationStyleClassifier.

        Returns:
            Ordered list of ReferenceObject (one per reference line).
        """
        from app.agents.parsing.citation_style_classifier import CitationStyleEnum

        ref_elements = [
            el for el in ir.elements
            if el.element_type == ElementType.REFERENCE and el.raw_text.strip()
        ]
        if not ref_elements:
            return []

        style_str = (
            detected_style.value
            if isinstance(detected_style, CitationStyleEnum)
            else str(detected_style)
        )

        results: list[ReferenceObject] = []
        for idx, el in enumerate(ref_elements):
            raw = el.raw_text.strip()
            raw_no_lead = _STRIP_LEAD_NUM.sub("", raw).strip()

            ref_obj = self._parse_one(raw_no_lead, idx, style_str)
            ref_obj.raw_text = raw

            results.append(ref_obj)

        # Optional CrossRef enrichment (fire-and-forget per ref with a DOI)
        doi_refs = [r for r in results if r.doi]
        if doi_refs:
            await self._enrich_crossref(doi_refs)

        logger.debug("[ReferenceParser] Parsed %d references", len(results))
        return results

    # ── Private ────────────────────────────────────────────────────────────────

    def _parse_one(self, text: str, idx: int, style: str) -> ReferenceObject:
        """Dispatch to the correct strategy and return a ReferenceObject."""
        ref_id = f"ref_{idx}"
        obj: ReferenceObject | None = None

        if style in ("ieee",):
            obj = self._parse_ieee(text, ref_id)
        elif style in ("vancouver", "numeric", "numeric_super"):
            obj = self._parse_vancouver(text, ref_id)
        elif style in ("apa", "mla", "chicago", "harvard"):
            obj = self._parse_apa(text, ref_id)

        # If strategy-specific parser failed (None), try all in order
        if obj is None:
            obj = (
                self._parse_apa(text, ref_id)
                or self._parse_vancouver(text, ref_id)
                or self._parse_ieee(text, ref_id)
                or ReferenceObject(id=ref_id, raw_text=text)
            )

        # DOI anywhere wins
        doi_m = _DOI_RE.search(text)
        if doi_m and obj.doi is None:
            obj.doi = doi_m.group(1).rstrip(".")

        return obj

    def _parse_apa(self, text: str, ref_id: str) -> ReferenceObject | None:
        """Two-pass APA parser: anchor on (YEAR). then parse title + venue."""
        anchor = _APA_YEAR_ANCHOR.match(text)
        if not anchor:
            return None

        authors_raw = anchor.group("authors_raw").strip()
        year = anchor.group("year")
        remainder = anchor.group("remainder").strip()

        # Extract title (up to first full-stop)
        rem_m = _APA_REMAINDER.match(remainder)
        title = rem_m.group("title").strip(".,").strip() if rem_m else remainder.split(".")[0].strip()
        venue = rem_m.group("venue").strip() if rem_m else ""

        # Try to extract volume/issue/pages from venue
        journal: str | None = None
        volume: str | None = None
        issue: str | None = None
        pages: str | None = None
        doi: str | None = None

        doi_m = _APA_DOI_IN_VENUE.search(venue)
        if doi_m:
            doi = doi_m.group(1).rstrip(".")

        venue_vol = _APA_VENUE_VOL.search(venue)
        if venue_vol:
            journal = venue_vol.group("journal").strip().strip(",").strip() or None
            volume = venue_vol.group("volume")
            issue = venue_vol.group("issue")
            pages = venue_vol.group("pages")
        elif venue.strip(". "):
            journal = venue.strip("., ") or None

        return ReferenceObject(
            id=ref_id,
            authors=self._split_authors_apa(authors_raw),
            year=year,
            title=title or None,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
        )


    def _parse_vancouver(self, text: str, ref_id: str) -> ReferenceObject | None:
        m = _VANCOUVER_REF.match(text)
        if not m:
            return None
        return ReferenceObject(
            id=ref_id,
            authors=self._split_authors_vancouver(m.group("authors_raw") or ""),
            year=m.group("year"),
            title=(m.group("title") or "").strip(".").strip(),
            journal=(m.group("journal") or "").strip(".").strip() or None,
            volume=m.group("volume"),
            issue=m.group("issue"),
            pages=m.group("pages"),
            doi=m.group("doi"),
        )

    def _parse_ieee(self, text: str, ref_id: str) -> ReferenceObject | None:
        m = _IEEE_REF.match(text)
        if not m:
            return None
        return ReferenceObject(
            id=ref_id,
            authors=self._split_authors_ieee(m.group("authors_raw") or ""),
            year=m.group("year"),
            title=(m.group("title") or "").strip(".").strip(),
            journal=(m.group("journal") or "").strip(".").strip() or None,
            volume=(m.group("volume") or "").strip() or None,
            issue=(m.group("issue") or "").strip() or None,
            pages=(m.group("pages") or "").strip() or None,
            doi=m.group("doi"),
        )

    # ── Author splitting utilities ─────────────────────────────────────────────

    @staticmethod
    def _split_authors_apa(raw: str) -> list[str]:
        """Split 'Smith, J. A., & Jones, B.' → ['Smith, J. A.', 'Jones, B.']"""
        parts = re.split(r",?\s*&\s*|;\s*", raw)
        return [p.strip().rstrip(",") for p in parts if p.strip()]

    @staticmethod
    def _split_authors_vancouver(raw: str) -> list[str]:
        """Split 'Smith JA, Jones B' → ['Smith JA', 'Jones B']"""
        parts = re.split(r",\s*(?=[A-Z])", raw)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _split_authors_ieee(raw: str) -> list[str]:
        """Split 'A. Smith and B. Jones' → ['A. Smith', 'B. Jones']"""
        parts = re.split(r"\s+and\s+|,\s+(?=[A-Z]\.)", raw, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    # ── CrossRef enrichment ────────────────────────────────────────────────────

    async def _enrich_crossref(self, refs: list[ReferenceObject]) -> None:
        """
        Fill missing fields from CrossRef API for refs that already have a DOI.
        Non-fatal: errors are logged and ignored.
        """
        try:
            import httpx  # type: ignore[import]
        except ImportError:
            return

        try:
            from app.config import settings
            api_key = getattr(settings, "CROSSREF_API_KEY", None)
        except Exception:
            api_key = None

        headers = {}
        if api_key:
            headers["Crossref-Plus-API-Token"] = f"Bearer {api_key}"

        async def fetch_one(ref: ReferenceObject) -> None:
            url = f"https://api.crossref.org/works/{ref.doi}"
            try:
                async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        return
                    data = resp.json().get("message", {})
                    if not ref.title:
                        titles = data.get("title", [])
                        ref.title = titles[0] if titles else ref.title
                    if not ref.journal:
                        containers = data.get("container-title", [])
                        ref.journal = containers[0] if containers else ref.journal
                    if not ref.volume:
                        ref.volume = data.get("volume")
                    if not ref.issue:
                        ref.issue = data.get("issue")
                    if not ref.pages:
                        ref.pages = data.get("page")
                    if not ref.url:
                        ref.url = data.get("URL")
            except Exception as exc:
                logger.debug("[ReferenceParser] CrossRef fetch failed for %s: %s", ref.doi, exc)

        await asyncio.gather(*[fetch_one(r) for r in refs], return_exceptions=True)
