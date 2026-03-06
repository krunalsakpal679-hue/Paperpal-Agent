# backend/app/agents/ingestion/ocr_reader.py
"""
OcrReader — OCR-based reader for scanned / image-only PDFs.

Converts each PDF page to a high-resolution PIL Image (300 DPI) and
runs Tesseract OCR to extract text, reconstruct paragraph flow, and
detect heading-like lines based on confidence and relative font size.
"""

import logging
import statistics
from typing import Any

from app.schemas.ir import ElementType, IRElement, IRSchema, TextRun

logger = logging.getLogger(__name__)

# Word grouping tolerances (pixels at 300 DPI)
_LINE_Y_TOLERANCE_PX: int = 5   # words within 5 px of each other share a line
_PARA_GAP_PX: int = 15          # vertical gap > 15 px separates paragraphs
# Minimum OCR word-level confidence to include a word
_MIN_WORD_CONF: float = 30.0
# Words in a heading: confidence > this AND font size > body median
_HEADING_CONF_THRESHOLD: float = 90.0


class OcrReader:
    """
    Extracts text from scanned PDFs using pdf2image + pytesseract.

    Algorithm:
    1. Convert each PDF page to a 300-DPI PIL Image.
    2. Run pytesseract.image_to_data() to get word-level bounding boxes + confidence.
    3. Group words → lines by Y-coordinate proximity (±5 px).
    4. Group lines → paragraphs by vertical gap > 15 px.
    5. Classify heading-like paragraphs by confidence and relative height.
    6. Return an IRSchema with the same structure as PdfReader / DocxReader.
    """

    async def read(self, file_bytes: bytes, job_id: str) -> IRSchema:
        """
        OCR-extract a scanned PDF into an IRSchema.

        Args:
            file_bytes: Raw PDF bytes.
            job_id: UUID4 job identifier (used for logging).

        Returns:
            IRSchema with reconstructed paragraphs and basic heading detection.
        """
        # Import heavy OCR dependencies lazily to keep startup time low
        try:
            from pdf2image import convert_from_bytes  # type: ignore[import]
            import pytesseract  # type: ignore[import]
            from pytesseract import Output  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "OCR dependencies not installed. "
                "Run: pip install pdf2image pytesseract"
            ) from exc

        logger.info("OcrReader: starting OCR for job %s", job_id)

        # ── Convert PDF pages to PIL images ───────────────────────────────────
        pages = convert_from_bytes(file_bytes, dpi=300)
        logger.debug("OcrReader: %d pages to process for job %s", len(pages), job_id)

        all_elements: list[IRElement] = []
        word_count = 0

        for page_num, page_image in enumerate(pages):
            # ── Tesseract word-level extraction ───────────────────────────────
            ocr_data: dict[str, Any] = pytesseract.image_to_data(
                page_image, output_type=Output.DICT
            )

            words = self._collect_words(ocr_data)
            if not words:
                continue

            # ── Compute median word height for heading heuristic ──────────────
            heights = [w["height"] for w in words if w["height"] > 0]
            median_height = statistics.median(heights) if heights else 10.0

            # ── Group words → lines → paragraphs ─────────────────────────────
            lines = self._group_into_lines(words)
            paragraphs = self._group_into_paragraphs(lines)

            for para_idx, para_lines in enumerate(paragraphs):
                para_text = " ".join(
                    word["text"] for line in para_lines for word in line
                ).strip()
                if not para_text:
                    continue

                avg_conf = self._avg_confidence(para_lines)
                avg_height = self._avg_height(para_lines)
                element_type, level = self._classify_paragraph(
                    para_text, avg_conf, avg_height, median_height
                )
                word_count += len(para_text.split())

                all_elements.append(
                    IRElement(
                        element_id=f"ocr_p{page_num}_{para_idx}",
                        element_type=element_type,
                        content=[TextRun(text=para_text)],
                        raw_text=para_text,
                        level=level,
                        metadata={
                            "page": page_num + 1,
                            "ocr_confidence": avg_conf,
                            "avg_word_height_px": avg_height,
                        },
                    )
                )

        logger.info(
            "OcrReader completed job %s: %d elements, ~%d words",
            job_id,
            len(all_elements),
            word_count,
        )

        return IRSchema(
            document_title="",
            authors=[],
            elements=all_elements,
            source_format="pdf",
            word_count=word_count,
            metadata={"ocr_processed": True, "page_count": len(pages)},
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _collect_words(self, ocr_data: dict[str, Any]) -> list[dict]:
        """
        Filter and normalise Tesseract word-level output.

        Returns a list of dicts with keys: text, top, height, conf.
        """
        words: list[dict] = []
        n = len(ocr_data.get("text", []))
        for i in range(n):
            text = (ocr_data["text"][i] or "").strip()
            conf = float(ocr_data["conf"][i])
            top = int(ocr_data["top"][i])
            height = int(ocr_data["height"][i])
            if text and conf >= _MIN_WORD_CONF:
                words.append({"text": text, "top": top, "height": height, "conf": conf})
        return words

    def _group_into_lines(self, words: list[dict]) -> list[list[dict]]:
        """
        Group words into lines by Y-coordinate proximity.

        Words whose `top` value is within ±_LINE_Y_TOLERANCE_PX of the
        current line anchor are placed on the same line.
        """
        if not words:
            return []
        sorted_words = sorted(words, key=lambda w: (w["top"], w.get("left", 0)))
        lines: list[list[dict]] = []
        current_line: list[dict] = [sorted_words[0]]
        current_top = sorted_words[0]["top"]

        for word in sorted_words[1:]:
            if abs(word["top"] - current_top) <= _LINE_Y_TOLERANCE_PX:
                current_line.append(word)
            else:
                lines.append(current_line)
                current_line = [word]
                current_top = word["top"]
        lines.append(current_line)
        return lines

    def _group_into_paragraphs(
        self, lines: list[list[dict]]
    ) -> list[list[list[dict]]]:
        """
        Group lines into paragraphs separated by vertical gaps > _PARA_GAP_PX.

        Returns a list of paragraphs, each a list of lines.
        """
        if not lines:
            return []
        paragraphs: list[list[list[dict]]] = []
        current_para: list[list[dict]] = [lines[0]]
        prev_bottom = lines[0][0]["top"] + lines[0][0]["height"]

        for line in lines[1:]:
            line_top = line[0]["top"]
            gap = line_top - prev_bottom
            if gap > _PARA_GAP_PX:
                paragraphs.append(current_para)
                current_para = [line]
            else:
                current_para.append(line)
            prev_bottom = line[0]["top"] + line[0].get("height", 0)

        paragraphs.append(current_para)
        return paragraphs

    def _avg_confidence(self, para_lines: list[list[dict]]) -> float:
        """Compute mean OCR confidence across all words in a paragraph."""
        confs = [
            w["conf"] for line in para_lines for w in line if w.get("conf", 0) > 0
        ]
        return statistics.mean(confs) if confs else 0.0

    def _avg_height(self, para_lines: list[list[dict]]) -> float:
        """Compute mean word height across all words in a paragraph."""
        heights = [w["height"] for line in para_lines for w in line if w["height"] > 0]
        return statistics.mean(heights) if heights else 0.0

    def _classify_paragraph(
        self,
        text: str,
        avg_conf: float,
        avg_height: float,
        median_height: float,
    ) -> tuple[ElementType, int]:
        """
        Classify a reconstructed OCR paragraph.

        Headings are identified by:
        - High confidence (> _HEADING_CONF_THRESHOLD) AND
        - Average word height significantly larger than page body median

        Returns:
            Tuple of (ElementType, heading_level).
        """
        lower = text.strip().lower()
        if lower in ("references", "bibliography", "works cited"):
            return ElementType.HEADING, 1

        if avg_conf > _HEADING_CONF_THRESHOLD and median_height > 0:
            ratio = avg_height / median_height
            if ratio > 1.8:
                return ElementType.HEADING, 1
            if ratio > 1.4:
                return ElementType.HEADING, 2

        return ElementType.PARAGRAPH, 0
