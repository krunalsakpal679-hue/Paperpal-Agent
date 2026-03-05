# backend/app/models/style_cache.py
"""
StyleCache ORM model.

Caches JRO (Journal Rule Object) data for fast retrieval.
"""

from datetime import datetime
from sqlalchemy import String, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StyleCache(Base):
    """Caches Journal Rule Objects (JRO)."""
    __tablename__ = "style_cache"

    cache_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    journal_name: Mapped[str] = mapped_column(String(500), nullable=False)
    issn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    jro_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    extraction_source: Mapped[str] = mapped_column(String(100), nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
