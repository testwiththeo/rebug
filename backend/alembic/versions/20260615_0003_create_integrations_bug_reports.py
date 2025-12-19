"""create integrations and bug_reports

Revision ID: 20260615_0003
Revises: 20260614_0002
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260615_0003"
down_revision: str | None = "20260614_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False, server_default="single-user"),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("credentials", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", name="uq_integrations_user_type"),
    )
    op.create_index("ix_integrations_type", "integrations", ["type"])

    op.create_table(
        "bug_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.String(length=255), nullable=False, server_default="single-user"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("root_cause", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("duplicate_check", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("replay_url", sa.Text(), nullable=True),
        sa.Column("jira_ticket_id", sa.String(length=255), nullable=True),
        sa.Column("jira_ticket_key", sa.String(length=255), nullable=True),
        sa.Column("jira_url", sa.Text(), nullable=True),
        sa.Column("slack_channel", sa.String(length=255), nullable=True),
        sa.Column("slack_ts", sa.String(length=255), nullable=True),
        sa.Column("slack_message_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_result_id"], ["analysis_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_bug_reports_analysis_result_id", "bug_reports", ["analysis_result_id"])
    op.create_index("ix_bug_reports_session_id", "bug_reports", ["session_id"])
    op.create_index("ix_bug_reports_jira_ticket_key", "bug_reports", ["jira_ticket_key"])


def downgrade() -> None:
    op.drop_index("ix_bug_reports_jira_ticket_key", table_name="bug_reports")
    op.drop_index("ix_bug_reports_session_id", table_name="bug_reports")
    op.drop_index("ix_bug_reports_analysis_result_id", table_name="bug_reports")
    op.drop_table("bug_reports")

    op.drop_index("ix_integrations_type", table_name="integrations")
    op.drop_table("integrations")
