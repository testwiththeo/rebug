"""create analysis_results

Revision ID: 20260614_0002
Revises: 20260614_0001
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260614_0002"
down_revision: str | None = "20260614_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("severity_suggestion", sa.String(length=32), nullable=True),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("root_cause", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("duplicate_check", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("coverage_note", sa.Text(), nullable=True),
        sa.Column("data_sensitivity_warning", sa.Text(), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_analysis_results_session_id", "analysis_results", ["session_id"])
    op.create_index("ix_analysis_results_status", "analysis_results", ["status"])


def downgrade() -> None:
    op.drop_index("ix_analysis_results_status", table_name="analysis_results")
    op.drop_index("ix_analysis_results_session_id", table_name="analysis_results")
    op.drop_table("analysis_results")
