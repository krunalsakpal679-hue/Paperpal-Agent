"""initial tables — users, jobs, style_cache

Revision ID: 001_initial
Revises: None
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users table ─────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Jobs table ──────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("target_journal", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), default="pending", nullable=False, index=True),
        sa.Column("progress_pct", sa.Float(), default=0.0, nullable=False),
        sa.Column("input_s3_key", sa.String(1024), nullable=True),
        sa.Column("output_s3_urls", JSON, nullable=True),
        sa.Column("change_log", JSON, nullable=True),
        sa.Column("compliance_report", JSON, nullable=True),
        sa.Column("errors", JSON, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Style Cache table ───────────────────────────────────────────────────
    op.create_table(
        "style_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("journal_name", sa.String(512), unique=True, nullable=False, index=True),
        sa.Column("journal_issn", sa.String(32), nullable=True, index=True),
        sa.Column("jro_data", JSON, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("hit_count", sa.Integer(), default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("style_cache")
    op.drop_table("jobs")
    op.drop_table("users")
