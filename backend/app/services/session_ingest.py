from __future__ import annotations

import gzip
import hashlib
from uuid import UUID

import msgpack
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.session import Session, SessionStatus
from app.models.session_event import SessionEvent
from app.schemas.session import SessionPackageInput
from app.services.object_storage import ObjectStorage


class SessionPackageError(ValueError):
    pass


class SessionAlreadyExistsError(ValueError):
    pass


class SessionIngestService:
    def __init__(
        self,
        db: AsyncSession,
        storage: ObjectStorage | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.storage = storage or ObjectStorage(self.settings)

    async def ingest_package(
        self, package_bytes: bytes, user_id: UUID | None = None
    ) -> Session:
        if not package_bytes:
            raise SessionPackageError("Session package is empty.")

        if len(package_bytes) > self.settings.max_session_package_bytes:
            raise SessionPackageError("Session package exceeds the 50 MB MVP limit.")

        checksum = hashlib.sha256(package_bytes).hexdigest()
        payload = decode_session_package(package_bytes)

        existing = await self.db.get(Session, payload.session_id)
        if existing:
            if existing.checksum == checksum:
                return existing
            raise SessionAlreadyExistsError(
                f"Session already exists: {payload.session_id}"
            )

        storage_key = f"sessions/{payload.session_id}.brpkg"
        await self.storage.put_package(storage_key, package_bytes, checksum)

        viewport = payload.browser.viewport or {}
        duration_sec = (
            round(payload.duration_ms / 1000)
            if payload.duration_ms is not None
            else None
        )

        session = Session(
            id=payload.session_id,
            user_id=user_id,
            url=payload.url,
            browser_name=payload.browser.name,
            browser_version=payload.browser.version,
            os=payload.browser.os,
            viewport_width=viewport.get("width"),
            viewport_height=viewport.get("height"),
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            duration_sec=duration_sec,
            event_count=len(payload.events),
            storage_key=storage_key,
            size_bytes=len(package_bytes),
            status=SessionStatus.packaged.value,
            checksum=checksum,
        )

        self.db.add(session)
        await self.db.flush()

        self.db.add_all(
            [
                SessionEvent(
                    session_id=session.id,
                    sequence=event.sequence,
                    timestamp_ms=event.timestamp_ms,
                    event_type=event.event_type,
                    category=event.category,
                    data=event.data,
                    masked=event.masked,
                )
                for event in sorted(payload.events, key=lambda item: item.sequence)
            ]
        )

        await self.db.commit()
        await self.db.refresh(session)
        return session


def decode_session_package(package_bytes: bytes) -> SessionPackageInput:
    try:
        unpacked = gzip.decompress(package_bytes)
    except OSError as error:
        raise SessionPackageError("Session package is not valid gzip data.") from error

    try:
        payload = msgpack.unpackb(unpacked, raw=False, strict_map_key=False)
    except msgpack.ExtraData as error:
        raise SessionPackageError(
            "Session package has trailing MessagePack data."
        ) from error
    except msgpack.FormatError as error:
        raise SessionPackageError(
            "Session package is not valid MessagePack data."
        ) from error

    try:
        return SessionPackageInput.model_validate(payload)
    except ValidationError as error:
        raise SessionPackageError(
            f"Session package schema is invalid: {error}"
        ) from error


async def get_session_or_none(db: AsyncSession, session_id: UUID) -> Session | None:
    return await db.get(Session, session_id)


async def count_session_events(db: AsyncSession, session_id: UUID) -> int:
    result = await db.execute(
        select(func.count(SessionEvent.id)).where(SessionEvent.session_id == session_id)
    )
    return int(result.scalar_one())
