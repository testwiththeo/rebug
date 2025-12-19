"""create sessions and session_events

Revision ID: 20260614_0001
Revises:
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260614_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("browser_name", sa.String(length=50), nullable=False),
        sa.Column("browser_version", sa.String(length=50), nullable=False),
        sa.Column("os", sa.String(length=80), nullable=False),
        sa.Column("viewport_width", sa.Integer(), nullable=True),
        sa.Column("viewport_height", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="packaged"),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_created_at", "sessions", ["created_at"])
    op.create_index("ix_sessions_status", "sessions", ["status"])

    op.create_table(
        "session_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("masked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_session_events_session_id_sequence", "session_events", ["session_id", "sequence"])
    op.create_index("ix_session_events_session_id_event_type", "session_events", ["session_id", "event_type"])
    op.create_index("ix_session_events_session_id", "session_events", ["session_id"])
    op.create_index("ix_session_events_event_type", "session_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_session_events_event_type", table_name="session_events")
    op.drop_index("ix_session_events_session_id", table_name="session_events")
    op.drop_index("ix_session_events_session_id_event_type", table_name="session_events")
    op.drop_index("ix_session_events_session_id_sequence", table_name="session_events")
    op.drop_table("session_events")

    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_created_at", table_name="sessions")
    op.drop_table("sessions")
