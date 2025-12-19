from __future__ import annotations

import secrets
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return (
            f"<ApiKey(id={self.id}, prefix={self.key_prefix}, user_id={self.user_id})>"
        )

    @staticmethod
    def generate_key() -> str:
        """Generate a new API key with format: rbg_<32-char-random>"""
        random_part = secrets.token_urlsafe(32)
        return f"rbg_{random_part}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for storage."""
        import hashlib

        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def get_prefix(key: str) -> str:
        """Extract prefix from API key for display."""
        if "_" in key:
            return key.split("_", 1)[0] + "_" + key.split("_", 1)[1][:8]
        return key[:10]
