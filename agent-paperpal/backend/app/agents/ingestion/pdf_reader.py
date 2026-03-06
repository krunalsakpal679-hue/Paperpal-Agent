# backend/app/agents/ingestion/pdf_reader.py
"""
PdfReader — Native PDF text extraction reader.

Uses PyMuPDF (fitz) to extract text, infer document structure (headings vs.
body), and detect embedded images. Falls back to OcrReader when the document
is identified as a scanned/image-only PDF.
"""

import asyncio
import logging
import statistics
from io import BytesIO

import fitz  # PyMuPDF

from app.schemas.ir import ElementType, IRElement, IRSchema, TextRun
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

# Threshold: pages with text density below this value are considered "image-only"
_SCANNED_TEXT_DENSITY_THRESHOLD: float = 0.5
# Fraction of pages that must be scanned to trigger OCR fallback
_SCANNED_PAGE_FRACTION: float = 0.5
# A span's font size must be this factor above the body median to be a heading
_HEADING_SIZE_FACTOR: float = 1.3


class PdfReader:
    """
    Extracts structured content from native (text-layer) PDF documents.

    Algorithm:
    1. Open the PDF stream with fitz.
    2. Measure per-page text density; delegate to OcrReader if > 50% pages are scanned.
    3. Reconstruct paragraphs from text blocks ordered by vertical position.
    4. Infer heading hierarchy from font-size heuristics.
    5. Extract and upload embedded images to S3.
    """

    async def read(self, file_bytes: bytes, job_id: str) -> IRSchema:
        """
        Parse a PDF and produce an IRSchema.

        Args:
            file_bytes: Raw PDF bytes.
            job_id: UUID4 for S3 key namespacing.

        Returns:
            IRSchema with all extracted elements.
        """
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # ── Scanned-PDF detection ──────────────────────────────────────────────
        if self._is_scanned(doc):
            logger.info(
                "PdfReader: detected scanned PDF for job %s — delegating to OcrReader",
                job_id,
            )
            doc.close()
            from app.agents.ingestion.ocr_reader import OcrReader  # lazy import

            return await OcrReader().read(file_bytes, job_id)

        # ── Collect all text spans for font-size statistics ────────────────────
        all_spans = self._collect_spans(doc)
        median_font_size = self._compute_median_font_size(all_spans)
        logger.debug(
            "PdfReader: %d pages, median font size %.1f pt for job %s",
            doc.page_count,
            median_font_size,
            job_id,
        )

        elements: list[IRElement] = []
        word_count = 0
        block_index = 0

        # ── Per-page text extraction ───────────────────────────────────────────
        for page_num, page in enumerate(doc):
            page_blocks = page.get_text("dict")["blocks"]
            # Sort blocks top-to-bottom, then left-to-right
            text_blocks = sorted(
                [b for b in page_blocks if b["type"] == 0],  # 0 = text block
                key=lambda b: (b["bbox"][1], b["bbox"][0]),
            )

            for block in text_blocks:
                para_text, runs, max_font_size = self._extract_block(block)
                if not para_text.strip():
                    continue

                element_type, level = self._classify_block(
                    para_text, max_font_size, median_font_size
                )
                word_count += len(para_text.split())

                elements.append(
                    IRElement(
                        element_id=f"pdf_p{page_num}_{block_index}",
                        element_type=element_type,
                        content=runs,
                        raw_text=para_text.strip(),
                        level=level,
                        metadata={"page": page_num + 1, "max_font_size": max_font_size},
                    )
                )
                block_index += 1

        # ── Image extraction ───────────────────────────────────────────────────
        figure_elements = await self._extract_page_images(doc, job_id)
        elements.extend(figure_elements)

        page_count = doc.page_count
        doc.close()

        logger.info(
            "PdfReader extracted %d elements, %d words, %d figures for job %s",
            len(elements),
            word_count,
            len(figure_elements),
            job_id,
        )

        return IRSchema(
            document_title="",
            authors=[],
            elements=elements,
            source_format="pdf",
            word_count=word_count,
            metadata={"page_count": page_count},
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _is_scanned(self, doc: fitz.Document) -> bool:
        """
        Return True if more than 50% of pages appear to be image-only.

        Text density = number of text characters / page width in points.
        """
        scanned_pages = 0
        for page in doc:
            width = page.rect.width if page.rect.width > 0 else 1.0
            density = len(page.get_text()) / width
            if density < _SCANNED_TEXT_DENSITY_THRESHOLD:
                scanned_pages += 1
        return (scanned_pages / max(doc.page_count, 1)) > _SCANNED_PAGE_FRACTION

    def _collect_spans(self, doc: fitz.Document) -> list[dict]:
        """Flatten all text spans from the entire document for statistics."""
        spans: list[dict] = []
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block.get("lines", []):
                    spans.extend(line.get("spans", []))
        return spans

    def _compute_median_font_size(self, spans: list[dict]) -> float:
        """Compute median font size across all text spans."""
        sizes = [s["size"] for s in spans if s.get("size", 0) > 0]
        if not sizes:
            return 12.0
        return statistics.median(sizes)

    def _extract_block(
        self, block: dict
    ) -> tuple[str, list[TextRun], float]:
        """
        Extract plain text, TextRuns, and max font size from a fitz text block.

        Returns:
            Tuple of (plain_text, runs, max_font_size_pt).
        """
        runs: list[TextRun] = []
        max_size = 0.0
        para_parts: list[str] = []

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                size = span.get("size", 0.0)
                flags = span.get("flags", 0)
                # fitz flags: bit 0=superscript,1=italic,2=serifed(N/A),3=mono,4=bold
                is_bold = bool(flags & (1 << 4))
                is_italic = bool(flags & (1 << 1))
                font_name = span.get("font", None)

                if size > max_size:
                    max_size = size

                para_parts.append(text)
                runs.append(
                    TextRun(
                        text=text,
                        bold=is_bold,
                        italic=is_italic,
                        font_name=font_name,
                        font_size_pt=size if size > 0 else None,
                    )
                )

        return " ".join(para_parts), runs, max_size

    def _classify_block(
        self, text: str, block_max_size: float, median_size: float
    ) -> tuple[ElementType, int]:
        """
        Classify a text block as HEADING, PARAGRAPH, REFERENCE, etc.

        Returns:
            Tuple of (ElementType, level).
        """
        # Reference list detection
        lower = text.strip().lower()
        if lower in ("references", "bibliography", "works cited"):
            return ElementType.HEADING, 1

        # Font-size based heading inference
        if median_size > 0 and block_max_size > median_size * _HEADING_SIZE_FACTOR:
            # Estimate heading level by how much larger it is
            ratio = block_max_size / median_size
            level = 1 if ratio > 1.8 else 2 if ratio > 1.5 else 3
            return ElementType.HEADING, level

        return ElementType.PARAGRAPH, 0

    async def _extract_page_images(
        self, doc: fitz.Document, job_id: str
    ) -> list[IRElement]:
        """Upload all embedded PDF images to S3 and return FIGURE IRElements."""
        figure_elements: list[IRElement] = []
        upload_tasks: list[tuple[int, str]] = []
        image_data: list[bytes] = []

        global_idx = 0
        for page in doc:
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    ext = base_image.get("ext", "png")
                    filename = f"fig_{global_idx}.{ext}"
                    image_data.append(img_bytes)
                    upload_tasks.append((global_idx, filename))
                    global_idx += 1
                except Exception as exc:
                    logger.warning(
                        "Could not extract image xref=%d for job %s: %s",
                        xref,
                        job_id,
                        exc,
                    )

        if upload_tasks:
            coros = [
                storage_service.upload_raw(job_id, fname, image_data[idx])
                for idx, fname in upload_tasks
            ]
            results = await asyncio.gather(*coros, return_exceptions=True)
            for (fig_idx, fname), result in zip(upload_tasks, results):
                s3_key = None if isinstance(result, Exception) else result
                figure_elements.append(
                    IRElement(
                        element_id=f"fig_{fig_idx}",
                        element_type=ElementType.FIGURE,
                        content=[],
                        raw_text="",
                        metadata={"s3_key": s3_key, "filename": fname},
                    )
                )

        return figure_elements
