from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ImpactLink(Base, TimestampMixin):
    __tablename__ = "impact_links"
    __table_args__ = (
        UniqueConstraint("bug_report_id", "incident_url", name="uq_impact_links_bug_incident_url"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    bug_report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bug_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("production_incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    incident_title: Mapped[str] = mapped_column(Text, nullable=False)
    incident_url: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    match_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    notification_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    bug_report = relationship("BugReport", back_populates="impact_links")
    incident = relationship("ProductionIncident", back_populates="impact_links")
