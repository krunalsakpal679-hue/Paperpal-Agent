# backend/app/agents/ingestion/agent.py
"""
Stage 1 — DocIngestionAgent.

Orchestrator entry-point for the document ingestion pipeline stage.

Responsibilities:
  1. Download manuscript bytes from S3 using the job's raw_s3_key.
  2. Validate the file via FileValidator.
  3. Route to DocxReader / PdfReader / TextReader based on source_format.
  4. Build the raw IRSchema from reader output.
  5. Detect document language (langdetect).
  6. Publish a progress event to Redis pub/sub.
  7. Return the updated JobState.

Input:  JobState with job_id + raw_s3_key + source_format set by the API layer.
Output: JobState with raw_ir populated and status = INGESTING → next stage.
"""

import logging
from datetime import datetime
from pathlib import PurePosixPath

from langdetect import LangDetectException, detect  # type: ignore[import]

from app.agents.ingestion.docx_reader import DocxReader
from app.agents.ingestion.file_validator import FileValidator
from app.agents.ingestion.ocr_reader import OcrReader
from app.agents.ingestion.pdf_reader import PdfReader
from app.agents.ingestion.text_reader import TextReader
from app.schemas.job_state import AgentError, JobState, JobStatus
from app.services.cache_service import cache_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

AGENT_NAME = "DocIngestionAgent"

# ── Format → reader mapping ────────────────────────────────────────────────────
_FORMAT_READERS: dict[str, type[DocxReader | PdfReader | TextReader | OcrReader]] = {
    "docx": DocxReader,
    "pdf": PdfReader,
    "txt": TextReader,
    "md": TextReader,
}


class DocIngestionAgent:
    """
    Stage 1 agent — converts a raw uploaded file into an IRSchema.

    This class wraps the stateless reader classes and the FileValidator,
    providing the LangGraph-compatible async run() interface.

    Usage:
        agent = DocIngestionAgent()
        updated_state = await agent.run(state)
    """

    def __init__(self) -> None:
        self._validator = FileValidator()
        self._readers: dict[
            str, DocxReader | PdfReader | TextReader | OcrReader
        ] = {
            "docx": DocxReader(),
            "pdf": PdfReader(),
            "txt": TextReader(),
            "md": TextReader(),
        }

    async def run(self, state: JobState) -> JobState:
        """
        Execute the ingestion stage for the given pipeline state.

        Args:
            state: Current LangGraph pipeline state. Must have:
                   - state.job_id (str, UUID4)
                   - state.metadata["raw_s3_key"] (str) — S3 object key
                   - state.metadata["source_format"] (str) — one of: docx, pdf, txt, md

        Returns:
            Updated JobState with raw_ir populated on success, or
            errors appended and status = FAILED on failure.
        """
        logger.info("[%s] Starting ingestion for job %s", AGENT_NAME, state.job_id)
        state.status = JobStatus.INGESTING
        state.progress_pct = 5.0

        try:
            # ── 1. Retrieve file bytes from S3 ─────────────────────────────────
            raw_s3_key: str = state.metadata.get("raw_s3_key", "")  # type: ignore[union-attr]
            if not raw_s3_key:
                raise ValueError(
                    "JobState.metadata['raw_s3_key'] is not set. "
                    "The API layer must populate this before dispatching the job."
                )

            source_format: str = state.metadata.get("source_format", "")  # type: ignore[union-attr]
            if not source_format:
                # Attempt to infer from the S3 key extension
                source_format = PurePosixPath(raw_s3_key).suffix.lstrip(".").lower()

            logger.debug(
                "[%s] Downloading s3_key='%s' for job %s",
                AGENT_NAME,
                raw_s3_key,
                state.job_id,
            )
            file_bytes: bytes = await storage_service.download_raw(raw_s3_key)

            # ── 2. Validate file ───────────────────────────────────────────────
            filename = PurePosixPath(raw_s3_key).name
            validation_errors = self._validator.validate(filename, file_bytes)
            if validation_errors:
                for ve in validation_errors:
                    state.errors.append(
                        AgentError(
                            agent=AGENT_NAME,
                            error_type=ve["code"],
                            message=ve["message"],
                            timestamp=datetime.utcnow(),
                            recoverable=False,
                        )
                    )
                state.status = JobStatus.FAILED
                logger.warning(
                    "[%s] Validation failed for job %s: %s",
                    AGENT_NAME,
                    state.job_id,
                    [ve["code"] for ve in validation_errors],
                )
                return state

            # ── 3. Route to correct reader ─────────────────────────────────────
            reader = self._readers.get(source_format)
            if reader is None:
                raise ValueError(
                    f"No reader registered for format '{source_format}'. "
                    f"Supported formats: {list(_FORMAT_READERS.keys())}"
                )

            logger.info(
                "[%s] Routing job %s to %s",
                AGENT_NAME,
                state.job_id,
                type(reader).__name__,
            )
            ir_schema = await reader.read(file_bytes, state.job_id)

            # ── 4. Language detection ──────────────────────────────────────────
            sample_text = " ".join(
                el.raw_text for el in ir_schema.elements[:20] if el.raw_text
            )[:500]
            if sample_text.strip():
                try:
                    detected_lang = detect(sample_text)
                    ir_schema.metadata["detected_language"] = detected_lang
                    logger.debug(
                        "[%s] Detected language '%s' for job %s",
                        AGENT_NAME,
                        detected_lang,
                        state.job_id,
                    )
                except LangDetectException:
                    logger.warning(
                        "[%s] Language detection failed for job %s — insufficient text",
                        AGENT_NAME,
                        state.job_id,
                    )

            # ── 5. Populate state ──────────────────────────────────────────────
            state.raw_ir = ir_schema
            state.progress_pct = 20.0

            # ── 6. Publish progress event to Redis ────────────────────────────
            await self._publish_progress(state.job_id)

            logger.info(
                "[%s] Ingestion completed for job %s: %d elements, format=%s",
                AGENT_NAME,
                state.job_id,
                len(ir_schema.elements),
                source_format,
            )

        except Exception as exc:
            logger.exception(
                "[%s] Unhandled exception for job %s: %s",
                AGENT_NAME,
                state.job_id,
                exc,
            )
            state.errors.append(
                AgentError(
                    agent=AGENT_NAME,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    timestamp=datetime.utcnow(),
                    recoverable=False,
                )
            )
            state.status = JobStatus.FAILED

        return state

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _publish_progress(self, job_id: str) -> None:
        """Publish a progress event to the Redis job channel."""
        try:
            await cache_service.publish_progress(
                job_id=job_id,
                event_dict={
                    "agent": "ingestion",
                    "status": "processing",
                    "progress": 20,
                    "message": "Manuscript ingestion and validation complete."
                },
            )
        except Exception as pub_exc:
            # Progress publishing failure is non-fatal
            logger.warning(
                "[%s] Could not publish progress for job %s: %s",
                AGENT_NAME,
                job_id,
                pub_exc,
            )


# ── LangGraph-compatible module-level entry point ─────────────────────────────

_agent_instance = DocIngestionAgent()


async def run_ingestion(state: JobState) -> JobState:
    """
    Module-level LangGraph node function.

    LangGraph expects nodes to be plain async functions. This shim
    delegates to the singleton DocIngestionAgent instance, preserving
    the class-based design whilst satisfying LangGraph's interface.

    Args:
        state: JobState passed in by the LangGraph scheduler.

    Returns:
        Updated JobState.
    """
    return await _agent_instance.run(state)
