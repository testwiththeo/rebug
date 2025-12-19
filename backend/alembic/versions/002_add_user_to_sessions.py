"""add user_id to sessions table

Revision ID: 002_add_user_to_sessions
Revises: 001_auth_tables
Create Date: 2026-06-15 04:15:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_add_user_to_sessions"
down_revision = "001_auth_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column to sessions table
    op.add_column(
        "sessions",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "user_id")
