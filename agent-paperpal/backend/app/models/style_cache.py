# backend/app/models/style_cache.py
"""
StyleCache ORM model.

Caches Journal Rule Objects (JROs) to avoid re-extracting
formatting rules for the same journal on every request.
TTL is controlled by JRO_CACHE_TTL_SECONDS in settings.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StyleCache(Base):
    """Cached journal formatting rules (JRO)."""

    __tablename__ = "style_cache"

    # ── Journal identifier ──────────────────────────────────────────────────
    journal_name: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True,
    )
    journal_issn: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    # ── Cached JRO data ────────────────────────────────────────────────────
    jro_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ── Cache metadata ──────────────────────────────────────────────────────
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    hit_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StyleCache(journal={self.journal_name}, hits={self.hit_count})>"
