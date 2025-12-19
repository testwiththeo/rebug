from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class SessionStatus(str, Enum):
    recording = "recording"
    packaged = "packaged"
    analyzed = "analyzed"
    submitted = "submitted"
    archived = "archived"


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    browser_name: Mapped[str] = mapped_column(String(50), nullable=False)
    browser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    os: Mapped[str] = mapped_column(String(80), nullable=False)
    viewport_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewport_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=SessionStatus.packaged.value,
        nullable=False,
    )
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="sessions")
    events = relationship(
        "SessionEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionEvent.sequence",
    )
    analysis_result = relationship(
        "AnalysisResult",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    bug_report = relationship(
        "BugReport",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
