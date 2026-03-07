# backend/app/config.py
"""
Centralised application configuration using Pydantic BaseSettings.

All environment variables are loaded from .env file or system environment.
This is the single source of truth for configuration across the entire backend.
"""

from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = Field(
        ...,
        description="Google Gemini API key for free-tier LLM-powered agents",
    )

    ANTHROPIC_API_KEY: str | None = Field(
        default=None,
        description="Anthropic API key (optional fallback)",
    )

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection string (async driver)",
    )

    # ── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: RedisDsn = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL for caching and pub/sub",
    )

    # ── Celery ──────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(
        default="redis://redis:6379/1",
        description="Celery broker URL (Redis DB 1)",
    )

    # ── AWS S3 / MinIO ──────────────────────────────────────────────────────
    AWS_S3_BUCKET: str = Field(
        default="paperpal-uploads",
        description="S3 bucket name for document storage",
    )
    AWS_ACCESS_KEY_ID: str = Field(
        default="minioadmin",
        description="AWS / MinIO access key ID",
    )
    AWS_SECRET_ACCESS_KEY: str = Field(
        default="minioadmin",
        description="AWS / MinIO secret access key",
    )
    AWS_S3_ENDPOINT_URL: str | None = Field(
        default="http://minio:9000",
        description="S3 endpoint URL (set for MinIO, None for real AWS)",
    )

    # ── Security ────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        ...,
        min_length=16,
        description="Secret key for JWT token signing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="JWT access token expiration in minutes",
    )

    # ── Application ─────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Current deployment environment",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=50,
        description="Maximum file upload size in megabytes",
    )
    JRO_CACHE_TTL_SECONDS: int = Field(
        default=604800,
        description="Journal Rule Object cache TTL (default: 7 days)",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def max_file_size_bytes(self) -> int:
        """Return max file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


# Singleton settings instance — import this anywhere
settings = Settings()
