# backend/app/agents/ingestion/text_reader.py
"""
TextReader — Plain-text and Markdown manuscript reader.

Parses .txt and .md files into a structured IRSchema by detecting
headings via multiple heuristics, grouping lines into paragraphs by
blank-line boundaries, and identifying reference list sections.
"""

import logging
import re

from app.schemas.ir import ElementType, IRElement, IRSchema, TextRun

logger = logging.getLogger(__name__)

# ── Heading detection patterns ─────────────────────────────────────────────────
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$")
_NUMBERED_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+[A-Z]")

# Section headers that begin the bibliography / references block
_REFERENCE_SECTION_HEADERS: frozenset[str] = frozenset(
    {
        "references",
        "bibliography",
        "works cited",
        "literature cited",
        "reference list",
    }
)


class TextReader:
    """
    Reads plain-text (.txt) and Markdown (.md) manuscripts into IRSchema.

    Heading detection heuristics (in priority order):
    1. Markdown ATX headings: ^#{1-4} ...
    2. ALL CAPS lines ≤ 80 characters
    3. Lines ending with ':' that are ≤ 60 characters
    4. Numbered section headers: r'^\\d+\\.\\s[A-Z]'

    Paragraphs are reconstructed from blank-line boundaries.
    Everything after a "References" / "Bibliography" heading is
    classified as REFERENCE elements.
    """

    async def read(self, file_bytes: bytes, job_id: str) -> IRSchema:
        """
        Parse a plain-text or Markdown file into an IRSchema.

        Args:
            file_bytes: Raw bytes of the .txt or .md file.
            job_id: UUID4 job identifier (for logging).

        Returns:
            Fully populated IRSchema.
        """
        # ── Decode bytes ───────────────────────────────────────────────────────
        text_content = self._decode(file_bytes)
        lines = text_content.splitlines()

        # ── Group lines into raw paragraphs (split on blank lines) ────────────
        raw_paragraphs = self._group_into_paragraphs(lines)

        # ── Convert to IRElements with heading / reference classification ──────
        elements: list[IRElement] = []
        word_count = 0
        in_references = False

        for para_idx, para_lines in enumerate(raw_paragraphs):
            para_text = " ".join(para_lines).strip()
            if not para_text:
                continue

            element_type, level = self._classify_paragraph(
                para_lines, para_text, in_references
            )

            # Detect transition into the reference section
            if element_type == ElementType.HEADING and self._is_reference_header(
                para_text
            ):
                in_references = True

            word_count += len(para_text.split())
            elements.append(
                IRElement(
                    element_id=f"txt_{para_idx}",
                    element_type=element_type,
                    content=[TextRun(text=para_text)],
                    raw_text=para_text,
                    level=level,
                    metadata={"in_reference_section": in_references},
                )
            )

        logger.info(
            "TextReader: %d elements, ~%d words for job %s",
            len(elements),
            word_count,
            job_id,
        )

        return IRSchema(
            document_title=self._infer_title(elements),
            authors=[],
            elements=elements,
            source_format="txt",
            word_count=word_count,
            metadata={"line_count": len(lines)},
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _decode(self, file_bytes: bytes) -> str:
        """Decode bytes as UTF-8 with latin-1 fallback."""
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.debug("TextReader: UTF-8 decode failed, falling back to latin-1")
            return file_bytes.decode("latin-1")

    def _group_into_paragraphs(self, lines: list[str]) -> list[list[str]]:
        """
        Split lines into paragraph groups separated by one or more blank lines.

        Returns:
            List of paragraph groups, each a list of non-empty lines.
        """
        paragraphs: list[list[str]] = []
        current: list[str] = []

        for line in lines:
            if line.strip() == "":
                if current:
                    paragraphs.append(current)
                    current = []
            else:
                current.append(line.rstrip())

        if current:
            paragraphs.append(current)

        return paragraphs

    def _classify_paragraph(
        self,
        para_lines: list[str],
        para_text: str,
        in_references: bool,
    ) -> tuple[ElementType, int]:
        """
        Classify a paragraph group using heading heuristics.

        Args:
            para_lines: The raw lines of this paragraph.
            para_text: Joined single-string form of the paragraph.
            in_references: Whether we have already entered the reference section.

        Returns:
            Tuple of (ElementType, heading_level).
        """
        if in_references:
            # After the References heading, treat each paragraph as a reference entry
            return ElementType.REFERENCE, 0

        # Only single-line paragraphs can be headings
        if len(para_lines) == 1:
            line = para_lines[0].strip()

            # 1. Markdown heading: # / ## / ### / ####
            md_match = _MARKDOWN_HEADING_RE.match(line)
            if md_match:
                level = len(md_match.group(1))  # number of '#' characters
                return ElementType.HEADING, level

            # 2. ALL CAPS  (allow spaces, punctuation, but no lowercase alpha)
            if (
                len(line) <= 80
                and len(line) >= 2
                and line == line.upper()
                and any(c.isalpha() for c in line)
            ):
                return ElementType.HEADING, 2

            # 3. Short line ending with ':'
            if line.endswith(":") and len(line) <= 60:
                return ElementType.HEADING, 3

            # 4. Numbered section header: "1. Introduction", "2.3 Methods"
            if _NUMBERED_HEADING_RE.match(line):
                # Estimate level from number of numeric parts (1=1, 1.2=2, 1.2.3=3)
                numeric_part = line.split()[0].rstrip(".")
                level = len(numeric_part.split("."))
                return ElementType.HEADING, level

        return ElementType.PARAGRAPH, 0

    def _is_reference_header(self, text: str) -> bool:
        """Return True if this heading marks the start of the bibliography."""
        cleaned = re.sub(r"^#+\s*", "", text).strip().lower()
        return cleaned in _REFERENCE_SECTION_HEADERS

    def _infer_title(self, elements: list[IRElement]) -> str:
        """
        Attempt to infer document title from first HEADING or TITLE element.

        Returns empty string if no suitable candidate found.
        """
        for el in elements:
            if el.element_type in (ElementType.HEADING, ElementType.TITLE) and el.level <= 1:
                return el.raw_text
        return ""
