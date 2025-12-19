from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IntegrationType(str, Enum):
    jira = "jira"
    slack = "slack"


class Integration(Base, TimestampMixin):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "type", name="uq_integrations_user_type"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(255), default="single-user", nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
