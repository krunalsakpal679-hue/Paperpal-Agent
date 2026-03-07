# backend/app/agents/ingestion/file_validator.py
"""
FileValidator — Stage 1 guard.

Validates uploaded manuscript files before any parsing work begins.
Checks MIME type via python-magic, enforces size limits from config,
and structurally probes .docx and .pdf files for corruption.
"""

import logging
from io import BytesIO
from typing import TypedDict

import fitz  # PyMuPDF
import magic
from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError

from app.config import settings

logger = logging.getLogger(__name__)

# ── Allowed MIME types mapped to canonical extensions ─────────────────────────
ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/x-markdown": "md",
}

# Human-readable extension labels for error messages
ALLOWED_EXTENSIONS: list[str] = ["docx", "pdf", "txt", "md"]


class ValidationError(TypedDict):
    """Structured validation failure returned by FileValidator."""

    code: str
    message: str
    field: str


class FileValidator:
    """
    Validates manuscript files before ingestion.

    Performs three layers of validation:
    1. Size guard — rejects files exceeding MAX_FILE_SIZE_MB
    2. MIME guard — rejects unsupported file formats via libmagic
    3. Structure probe — verifies .docx and .pdf files are not corrupt
    """

    def validate(self, filename: str, file_bytes: bytes) -> list[ValidationError]:
        """
        Run all validation checks on the provided file.

        Args:
            filename: Original filename including extension (used for logging).
            file_bytes: Raw bytes of the uploaded file.

        Returns:
            Empty list if all checks pass.
            List of ValidationError dicts describing each failure.
        """
        errors: list[ValidationError] = []

        # ── 1. Size check ──────────────────────────────────────────────────────
        size_errors = self._check_size(filename, file_bytes)
        errors.extend(size_errors)
        if size_errors:
            # No point probing a potentially malicious oversized file
            return errors

        # ── 2. MIME type check ─────────────────────────────────────────────────
        mime_errors, detected_extension = self._check_mime(filename, file_bytes)
        errors.extend(mime_errors)
        if mime_errors:
            return errors

        # ── 3. Structural probe ────────────────────────────────────────────────
        errors.extend(self._check_structure(filename, file_bytes, detected_extension))

        return errors

    # ── Private helpers ────────────────────────────────────────────────────────

    def _check_size(self, filename: str, file_bytes: bytes) -> list[ValidationError]:
        """Reject files exceeding the configured maximum size."""
        max_bytes = settings.max_file_size_bytes
        actual_bytes = len(file_bytes)
        if actual_bytes > max_bytes:
            logger.warning(
                "File '%s' rejected: size %d bytes exceeds limit %d bytes",
                filename,
                actual_bytes,
                max_bytes,
            )
            return [
                ValidationError(
                    code="FILE_TOO_LARGE",
                    message=(
                        f"File size {actual_bytes / (1024 * 1024):.1f} MB exceeds "
                        f"the maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB."
                    ),
                    field="file",
                )
            ]
        return []

    def _check_mime(
        self, filename: str, file_bytes: bytes
    ) -> tuple[list[ValidationError], str]:
        """
        Detect MIME type using libmagic and reject unsupported types.

        Returns:
            Tuple of (errors_list, detected_extension).
            detected_extension is empty string on error.
        """
        try:
            mime_type: str = magic.from_buffer(file_bytes, mime=True)
        except Exception as exc:
            logger.error("MIME detection failed for '%s': %s", filename, exc)
            mime_type = "application/octet-stream"

        detected_extension = ALLOWED_MIME_TYPES.get(mime_type, "")
        
        # Fallback to extension if MIME is inconclusive (common on Windows)
        if not detected_extension or mime_type == "application/octet-stream":
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXTENSIONS:
                # Map extension back to a canonical one if needed, 
                # but here we just use it as the detected extension.
                detected_extension = ext
                logger.info("MIME returned %s, falling back to extension: %s", mime_type, detected_extension)

        if not detected_extension:
            logger.warning(
                "File '%s' rejected: unsupported MIME type '%s'", filename, mime_type
            )
            return [
                ValidationError(
                    code="UNSUPPORTED_FILE_TYPE",
                    message=(
                        f"File type '{mime_type}' is not supported. "
                        f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}."
                    ),
                    field="file",
                )
            ], ""

        return [], detected_extension

    def _check_structure(
        self, filename: str, file_bytes: bytes, extension: str
    ) -> list[ValidationError]:
        """Probe the internal structure of .docx and .pdf files."""
        errors: list[ValidationError] = []

        if extension == "docx":
            errors.extend(self._probe_docx(filename, file_bytes))
        elif extension == "pdf":
            errors.extend(self._probe_pdf(filename, file_bytes))

        return errors

    def _probe_docx(self, filename: str, file_bytes: bytes) -> list[ValidationError]:
        """Attempt to open the .docx to verify it is a valid OOXML package."""
        try:
            DocxDocument(BytesIO(file_bytes))
            return []
        except PackageNotFoundError as exc:
            logger.warning("Corrupt .docx file '%s': %s", filename, exc)
            return [
                ValidationError(
                    code="CORRUPT_DOCX",
                    message="The .docx file appears to be corrupt or not a valid Word document.",
                    field="file",
                )
            ]
        except Exception as exc:
            logger.warning("Unexpected .docx probe error for '%s': %s", filename, exc)
            return [
                ValidationError(
                    code="DOCX_PARSE_ERROR",
                    message=f"Could not parse .docx structure: {exc}",
                    field="file",
                )
            ]

    def _probe_pdf(self, filename: str, file_bytes: bytes) -> list[ValidationError]:
        """Attempt to open the PDF stream to verify it is readable by PyMuPDF."""
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if doc.page_count == 0:
                return [
                    ValidationError(
                        code="EMPTY_PDF",
                        message="The PDF file contains no pages.",
                        field="file",
                    )
                ]
            doc.close()
            return []
        except fitz.FileDataError as exc:
            logger.warning("Corrupt PDF file '%s': %s", filename, exc)
            return [
                ValidationError(
                    code="CORRUPT_PDF",
                    message="The PDF file appears to be corrupt or encrypted.",
                    field="file",
                )
            ]
        except Exception as exc:
            logger.warning("Unexpected PDF probe error for '%s': %s", filename, exc)
            return [
                ValidationError(
                    code="PDF_PARSE_ERROR",
                    message=f"Could not open PDF: {exc}",
                    field="file",
                )
            ]
