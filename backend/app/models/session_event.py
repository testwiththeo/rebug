from enum import Enum
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SessionEventType(str, Enum):
    dom_mutation = "dom_mutation"
    network_request = "network_request"
    console_log = "console_log"
    user_interaction = "user_interaction"
    screenshot = "screenshot"
    bug_marker = "bug_marker"


class SessionEvent(Base):
    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    masked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session = relationship("Session", back_populates="events")
