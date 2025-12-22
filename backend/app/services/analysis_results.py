from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_result import AnalysisResult, AnalysisStatus
from app.models.session import Session, SessionStatus
from app.schemas.analysis import AnalysisResponse


async def queue_analysis_result(
    db: AsyncSession,
    session_id: UUID,
    task_id: str | None = None,
) -> AnalysisResult:
    result = await get_or_create_analysis_result(db, session_id)
    result.status = AnalysisStatus.queued.value
    result.task_id = task_id
    result.error_message = None
    result.completed_at = None
    await db.commit()
    await db.refresh(result)
    return result


async def mark_analysis_running(
    db: AsyncSession,
    session_id: UUID,
    task_id: str | None,
) -> AnalysisResult:
    result = await get_or_create_analysis_result(db, session_id)
    result.status = AnalysisStatus.running.value
    result.task_id = task_id
    result.error_message = None
    await db.commit()
    await db.refresh(result)
    return result


async def store_completed_analysis(
    db: AsyncSession,
    session_id: UUID,
    payload: dict[str, Any],
    task_id: str | None,
) -> AnalysisResult:
    result = await get_or_create_analysis_result(db, session_id)
    analysis = payload.get("analysis", {})
    root_cause = payload.get("root_cause", {})
    confidence = payload.get("_confidence", root_cause.get("confidence"))

    result.status = AnalysisStatus.completed.value
    result.task_id = task_id
    result.summary = analysis.get("summary")
    result.severity_suggestion = analysis.get("severity_suggestion")
    result.steps = payload.get("reproduction_steps", [])
    result.root_cause = root_cause
    result.duplicate_check = payload.get("duplicate_check", {})
    result.coverage_note = payload.get("coverage_note")
    result.data_sensitivity_warning = payload.get("data_sensitivity_warning")
    result.raw_response = payload
    result.error_message = None
    result.confidence = to_decimal_confidence(confidence)
    result.completed_at = datetime.now(UTC)

    session = await db.get(Session, session_id)
    if session:
        session.status = SessionStatus.analyzed.value

    await db.commit()
    await db.refresh(result)
    return result


async def store_failed_analysis(
    db: AsyncSession,
    session_id: UUID,
    error_message: str,
    task_id: str | None,
) -> AnalysisResult:
    result = await get_or_create_analysis_result(db, session_id)
    result.status = AnalysisStatus.failed.value
    result.task_id = task_id
    result.error_message = error_message
    result.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(result)
    return result


async def get_or_create_analysis_result(db: AsyncSession, session_id: UUID) -> AnalysisResult:
    existing = await get_analysis_result(db, session_id)
    if existing:
        return existing

    result = AnalysisResult(
        id=uuid4(),
        session_id=session_id,
        status=AnalysisStatus.queued.value,
        steps=[],
        root_cause={},
        duplicate_check={},
    )
    db.add(result)
    await db.flush()
    return result


async def get_analysis_result(db: AsyncSession, session_id: UUID) -> AnalysisResult | None:
    return await db.scalar(select(AnalysisResult).where(AnalysisResult.session_id == session_id))


def to_analysis_response(result: AnalysisResult) -> AnalysisResponse:
    return AnalysisResponse(
        id=result.id,
        session_id=result.session_id,
        status=result.status,
        confidence=float(result.confidence) if result.confidence is not None else None,
        summary=result.summary,
        severity_suggestion=result.severity_suggestion,
        steps=result.steps,
        root_cause=result.root_cause,
        duplicate_check=result.duplicate_check,
        coverage_note=result.coverage_note,
        data_sensitivity_warning=result.data_sensitivity_warning,
        error_message=result.error_message,
        task_id=result.task_id,
        completed_at=result.completed_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def to_decimal_confidence(value: Any) -> Decimal | None:
    try:
        numeric = max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None
    return Decimal(str(round(numeric, 2)))
