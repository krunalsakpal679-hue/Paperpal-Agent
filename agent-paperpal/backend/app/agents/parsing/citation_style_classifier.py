# backend/app/agents/parsing/citation_style_classifier.py
"""
CitationStyleClassifier — Stage 2 component.

Determines the dominant citation style used in a manuscript by voting
over the style_hint labels produced by CitationParser.

Method 1 — Voting (always used):
  Count style_hint values; return the mode + fraction as confidence.

Method 2 — DistilBERT (optional, enabled if > 20 citations AND
  ml_models/citation_clf/artifacts/ contains a saved model):
  Concatenate first 20 citation raw texts → classify with the saved model.
  Falls back to Method 1 if the model directory is missing.

If < 3 citations found, returns (CitationStyleEnum.UNKNOWN, 0.0).
"""

from __future__ import annotations

import logging
import statistics
from collections import Counter
from enum import Enum
from pathlib import Path

from app.schemas.ir_schema import CitationObject

logger = logging.getLogger(__name__)

# ── Model artifacts location ───────────────────────────────────────────────────
_MODEL_DIR = (
    Path(__file__).parent.parent.parent.parent  # project root
    / "ml_models"
    / "citation_clf"
    / "artifacts"
)


class CitationStyleEnum(str, Enum):
    """Supported citation / reference styles."""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    VANCOUVER = "vancouver"
    HARVARD = "harvard"
    NUMERIC = "numeric"          # generic numbered
    NUMERIC_SUPER = "numeric_super"
    UNKNOWN = "unknown"


# Mapping from CitationParser style_hint strings → CitationStyleEnum
_HINT_MAP: dict[str, CitationStyleEnum] = {
    "apa": CitationStyleEnum.APA,
    "mla": CitationStyleEnum.MLA,
    "chicago": CitationStyleEnum.CHICAGO,
    "ieee": CitationStyleEnum.IEEE,
    "vancouver": CitationStyleEnum.VANCOUVER,
    "harvard": CitationStyleEnum.HARVARD,
    "numeric": CitationStyleEnum.NUMERIC,
    "numeric_super": CitationStyleEnum.NUMERIC_SUPER,
}

# Styles where numeric/IEEE patterns are merged for display
_NUMERIC_STYLES = frozenset({
    CitationStyleEnum.IEEE,
    CitationStyleEnum.VANCOUVER,
    CitationStyleEnum.NUMERIC,
    CitationStyleEnum.NUMERIC_SUPER,
})

_MIN_CITATIONS = 3
_DISTILBERT_THRESHOLD = 20


class CitationStyleClassifier:
    """
    Classify citation style by majority voting and optional DistilBERT.

    Usage::
        classifier = CitationStyleClassifier()
        style, confidence = classifier.classify(citations)
    """

    def classify(
        self, citations: list[CitationObject]
    ) -> tuple[CitationStyleEnum, float]:
        """
        Determine the dominant citation style.

        Args:
            citations: List of CitationObject from CitationParser.parse_all().

        Returns:
            Tuple of (dominant_style, confidence) where confidence ∈ [0.0, 1.0].
            Returns (UNKNOWN, 0.0) if fewer than 3 citations found.
        """
        if len(citations) < _MIN_CITATIONS:
            logger.debug(
                "[CitationStyleClassifier] Only %d citations — returning UNKNOWN",
                len(citations),
            )
            return CitationStyleEnum.UNKNOWN, 0.0

        # ── Method 2: DistilBERT (optional) ───────────────────────────────────
        if len(citations) > _DISTILBERT_THRESHOLD and _MODEL_DIR.exists():
            try:
                result = self._classify_distilbert(citations)
                if result is not None:
                    return result
            except Exception as exc:
                logger.warning(
                    "[CitationStyleClassifier] DistilBERT failed (%s) — falling back to voting",
                    exc,
                )

        # ── Method 1: Voting ──────────────────────────────────────────────────
        return self._classify_voting(citations)

    # ── Private ────────────────────────────────────────────────────────────────

    def _classify_voting(
        self, citations: list[CitationObject]
    ) -> tuple[CitationStyleEnum, float]:
        hints = [c.style_hint or "unknown" for c in citations]
        counts = Counter(hints)
        mode_hint, mode_count = counts.most_common(1)[0]
        confidence = mode_count / len(hints)
        style = _HINT_MAP.get(mode_hint, CitationStyleEnum.UNKNOWN)

        # Consolidate IEEE / vanilla numeric under IEEE when confidence is split
        if style in _NUMERIC_STYLES and confidence < 0.5:
            numeric_total = sum(
                counts[h]
                for h in counts
                if _HINT_MAP.get(h, CitationStyleEnum.UNKNOWN) in _NUMERIC_STYLES
            )
            if numeric_total / len(hints) >= 0.5:
                style = CitationStyleEnum.IEEE
                confidence = numeric_total / len(hints)

        logger.debug(
            "[CitationStyleClassifier] Voting result: %s (confidence=%.2f)",
            style, confidence,
        )
        return style, confidence

    def _classify_distilbert(
        self, citations: list[CitationObject]
    ) -> tuple[CitationStyleEnum, float] | None:
        """Optional DistilBERT-based classifier, returns None if unavailable."""
        try:
            from transformers import pipeline  # type: ignore[import]
        except ImportError:
            return None

        model_path = str(_MODEL_DIR)
        try:
            clf = pipeline(
                "text-classification",
                model=model_path,
                tokenizer=model_path,
                top_k=1,
            )
        except Exception:
            return None

        sample = " [SEP] ".join(
            c.raw_text or "" for c in citations[:20] if c.raw_text
        )[:512]
        result = clf(sample)
        if not result:
            return None

        label = result[0][0]["label"].lower()
        score = result[0][0]["score"]
        style = _HINT_MAP.get(label, CitationStyleEnum.UNKNOWN)
        return style, score
