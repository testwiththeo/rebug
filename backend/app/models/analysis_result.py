from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AnalysisStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AnalysisResult(Base, TimestampMixin):
    __tablename__ = "analysis_results"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=AnalysisStatus.queued.value,
        nullable=False,
        index=True,
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_suggestion: Mapped[str | None] = mapped_column(String(32), nullable=True)
    steps: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    root_cause: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    duplicate_check: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    coverage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_sensitivity_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("Session", back_populates="analysis_result")
