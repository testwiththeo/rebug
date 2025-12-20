from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: Optional[str] = Field(
        None, max_length=255, description="Friendly name for the API key"
    )


class ApiKeyCreatedResponse(BaseModel):
    """Response when creating an API key - includes the raw key only once."""

    id: UUID
    name: Optional[str] = None
    key: str = Field(
        ..., description="Full API key - save this, it won't be shown again"
    )
    key_prefix: str
    created_at: datetime


class ApiKeyResponse(BaseModel):
    """Response for listing API keys - never includes the full key."""

    id: UUID
    name: Optional[str] = None
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyResponse]
