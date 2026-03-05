"""initial tables with exact prompt specifications

Revision ID: 001_initial
Revises: None
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum for JobStatus
    status_enum = sa.Enum('queued', 'ingesting', 'parsing', 'interpreting', 'transforming', 'validating', 'rendering', 'completed', 'failed', name='jobstatus')

    # ── Users table ─────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Jobs table ──────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", status_enum, server_default='queued', nullable=False, index=True),
        sa.Column("source_format", sa.String(10), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("raw_s3_key", sa.String(1000), nullable=True),
        sa.Column("output_s3_key", sa.String(1000), nullable=True),
        sa.Column("latex_s3_key", sa.String(1000), nullable=True),
        sa.Column("journal_identifier", sa.String(255), nullable=True),
        sa.Column("style_name", sa.String(255), nullable=True),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("total_changes", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("progress_pct", sa.Float(), default=0.0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Style Cache table ───────────────────────────────────────────────────
    op.create_table(
        "style_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("journal_name", sa.String(500), nullable=False),
        sa.Column("issn", sa.String(20), nullable=True),
        sa.Column("jro_json", JSONB, nullable=False),
        sa.Column("extraction_source", sa.String(100), nullable=False),
        sa.Column("extraction_confidence", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("style_cache")
    op.drop_table("jobs")
    op.drop_table("users")
    
    # Drop enum
    status_enum = sa.Enum('queued', 'ingesting', 'parsing', 'interpreting', 'transforming', 'validating', 'rendering', 'completed', 'failed', name='jobstatus')
    status_enum.drop(op.get_bind(), checkfirst=True)
