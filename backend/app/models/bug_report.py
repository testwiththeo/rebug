from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BugReport(Base, TimestampMixin):
    __tablename__ = "bug_reports"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    analysis_result_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), default="single-user", nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    steps: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    root_cause: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    duplicate_check: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    replay_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    jira_ticket_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_ticket_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_ts: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_message_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False)
    jira_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    final_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("Session", back_populates="bug_report")
    impact_links = relationship(
        "ImpactLink",
        back_populates="bug_report",
        cascade="all, delete-orphan",
    )
