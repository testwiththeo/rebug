"""create impact tracking tables

Revision ID: 20260615_0004
Revises: 20260615_0003
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260615_0004"
down_revision: str | None = "20260615_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bug_reports", sa.Column("jira_status", sa.String(length=255), nullable=True))
    op.add_column("bug_reports", sa.Column("final_status", sa.String(length=64), nullable=True))
    op.add_column("bug_reports", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_bug_reports_final_status", "bug_reports", ["final_status"])

    op.create_table(
        "production_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("incident_url", sa.Text(), nullable=False),
        sa.Column("affected_url", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_production_incidents_created_at", "production_incidents", ["created_at"])
    op.create_index("ix_production_incidents_incident_url", "production_incidents", ["incident_url"])

    op.create_table(
        "impact_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bug_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incident_title", sa.Text(), nullable=False),
        sa.Column("incident_url", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("notification_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("notification_error", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bug_report_id"], ["bug_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["production_incidents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bug_report_id", "incident_url", name="uq_impact_links_bug_incident_url"),
    )
    op.create_index("ix_impact_links_bug_report_id", "impact_links", ["bug_report_id"])
    op.create_index("ix_impact_links_incident_id", "impact_links", ["incident_id"])
    op.create_index("ix_impact_links_detected_at", "impact_links", ["detected_at"])


def downgrade() -> None:
    op.drop_index("ix_impact_links_detected_at", table_name="impact_links")
    op.drop_index("ix_impact_links_incident_id", table_name="impact_links")
    op.drop_index("ix_impact_links_bug_report_id", table_name="impact_links")
    op.drop_table("impact_links")

    op.drop_index("ix_production_incidents_incident_url", table_name="production_incidents")
    op.drop_index("ix_production_incidents_created_at", table_name="production_incidents")
    op.drop_table("production_incidents")

    op.drop_index("ix_bug_reports_final_status", table_name="bug_reports")
    op.drop_column("bug_reports", "resolved_at")
    op.drop_column("bug_reports", "final_status")
    op.drop_column("bug_reports", "jira_status")
