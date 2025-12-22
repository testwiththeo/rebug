from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, email: str, name: Optional[str] = None) -> User:
        """Create a new user."""
        user = User(email=email, name=name)
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.db.get(User, user_id)

    async def create_api_key(
        self,
        user_id: UUID,
        name: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple[ApiKey, str]:
        """Create a new API key for a user. Returns (ApiKey, raw_key)."""
        raw_key = ApiKey.generate_key()
        key_hash = ApiKey.hash_key(raw_key)
        key_prefix = ApiKey.get_prefix(raw_key)

        api_key = ApiKey(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        await self.db.flush()
        return api_key, raw_key

    async def validate_api_key(self, raw_key: str) -> Optional[User]:
        """Validate an API key and return the associated user."""
        key_hash = ApiKey.hash_key(raw_key)

        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.key_hash == key_hash)
            .where(ApiKey.is_active == True)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # Update last used
        api_key.last_used_at = datetime.utcnow()
        await self.db.flush()

        # Get user
        user = await self.db.get(User, api_key.user_id)
        if not user or not user.is_active:
            return None

        return user

    async def list_api_keys(self, user_id: UUID) -> list[ApiKey]:
        """List all API keys for a user."""
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke (deactivate) an API key."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return False

        api_key.is_active = False
        await self.db.flush()
        return True
