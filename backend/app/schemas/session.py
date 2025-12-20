from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BrowserPayload(BaseModel):
    name: str = "Chrome"
    version: str = "unknown"
    os: str = "unknown"
    viewport: dict[str, int | None] | None = None
    userAgent: str | None = None


class SessionPackageEventInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sequence: int
    timestamp_ms: int = Field(alias="timestampMs")
    event_type: str = Field(alias="type")
    category: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    masked: bool = False


class SessionPackageInput(BaseModel):
    session_id: UUID
    url: str
    browser: BrowserPayload
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    events: list[SessionPackageEventInput] = Field(default_factory=list)


class SessionIngestResponse(BaseModel):
    id: UUID
    status: str
    size_bytes: int
    event_count: int
    replay_url: str


class SessionResponse(BaseModel):
    id: UUID
    url: str
    browser: BrowserPayload
    duration: int | None
    event_count: int
    status: str
    storage_key: str | None
    size_bytes: int | None
    checksum: str | None
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime


class SessionEventResponse(BaseModel):
    id: int
    session_id: UUID
    sequence: int
    timestamp_ms: int
    event_type: str
    category: str | None
    data: dict[str, Any]
    masked: bool


class SessionEventsPage(BaseModel):
    items: list[SessionEventResponse]
    total: int
    limit: int
    offset: int
