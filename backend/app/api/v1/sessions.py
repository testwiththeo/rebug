from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.session import Session
from app.models.session_event import SessionEvent
from app.models.user import User
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisTaskResponse,
    DuplicateCheckResponse,
)
from app.schemas.integration import FileBugResponse
from app.schemas.session import (
    BrowserPayload,
    SessionEventResponse,
    SessionEventsPage,
    SessionIngestResponse,
    SessionResponse,
)
from app.services.analysis_agent import AnalysisAgentService
from app.services.analysis_results import (
    get_analysis_result,
    queue_analysis_result,
    to_analysis_response,
)
from app.services.bug_filing import BugFilingService
from app.services.integrations import IntegrationError
from app.services.session_ingest import (
    SessionAlreadyExistsError,
    SessionIngestService,
    SessionPackageError,
    get_session_or_none,
)
from app.tasks.analysis import run_session_analysis

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[SessionResponse]:
    result = await db.execute(
        select(Session)
        .order_by(Session.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [to_session_response(session) for session in sessions]


@router.post(
    "",
    response_model=SessionIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> SessionIngestResponse:
    package_bytes = await request.body()
    service = SessionIngestService(db=db, settings=settings)

    try:
        session = await service.ingest_package(package_bytes, user_id=current_user.id)
    except SessionAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except SessionPackageError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error

    return SessionIngestResponse(
        id=session.id,
        status="uploaded",
        size_bytes=session.size_bytes or len(package_bytes),
        event_count=session.event_count,
        replay_url=f"{settings.viewer_base_url}/replay/{session.id}",
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    session = await get_session_or_404(db, session_id)
    return to_session_response(session)


@router.get("/{session_id}/events", response_model=SessionEventsPage)
async def get_session_events(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=500, ge=1, le=2_000),
    offset: int = Query(default=0, ge=0),
) -> SessionEventsPage:
    await get_session_or_404(db, session_id)

    total_result = await db.execute(
        select(func.count(SessionEvent.id)).where(SessionEvent.session_id == session_id)
    )
    total = int(total_result.scalar_one())

    events_result = await db.execute(
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.sequence)
        .offset(offset)
        .limit(limit)
    )
    events = events_result.scalars().all()

    return SessionEventsPage(
        items=[to_event_response(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}/replay")
async def replay_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    await get_session_or_404(db, session_id)
    return RedirectResponse(f"{settings.viewer_base_url}/replay/{session_id}")


@router.post("/{session_id}/analyze", response_model=AnalysisTaskResponse)
async def analyze_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    force: bool = Query(default=False),
) -> AnalysisTaskResponse:
    await get_session_or_404(db, session_id)

    existing = await get_analysis_result(db, session_id)
    if existing and existing.status in {"queued", "running"} and not force:
        return AnalysisTaskResponse(
            session_id=session_id,
            status=existing.status,
            task_id=existing.task_id,
        )

    if existing and existing.status == "completed" and not force:
        return AnalysisTaskResponse(
            session_id=session_id,
            status=existing.status,
            task_id=existing.task_id,
        )

    try:
        task = run_session_analysis.delay(str(session_id))
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to queue analysis task: {error}",
        ) from error

    result = await queue_analysis_result(db, session_id, task.id)
    return AnalysisTaskResponse(
        session_id=session_id,
        status=result.status,
        task_id=result.task_id,
    )


@router.get("/{session_id}/analysis", response_model=AnalysisResponse)
async def get_session_analysis(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    await get_session_or_404(db, session_id)
    analysis = await get_analysis_result(db, session_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found."
        )
    return to_analysis_response(analysis)


@router.post("/{session_id}/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DuplicateCheckResponse:
    await get_session_or_404(db, session_id)
    service = AnalysisAgentService(db)
    duplicate_check = await service.check_duplicate(session_id)
    return DuplicateCheckResponse(
        session_id=session_id, duplicate_check=duplicate_check
    )


@router.post("/{session_id}/file", response_model=FileBugResponse)
async def file_session_bug(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileBugResponse:
    await get_session_or_404(db, session_id)
    try:
        return await BugFilingService(db, settings).file_bug(session_id)
    except IntegrationError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error


async def get_session_or_404(db: AsyncSession, session_id: UUID) -> Session:
    session = await get_session_or_none(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    return session


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        url=session.url,
        browser=BrowserPayload(
            name=session.browser_name,
            version=session.browser_version,
            os=session.os,
            viewport={
                "width": session.viewport_width,
                "height": session.viewport_height,
            },
        ),
        duration=session.duration_sec,
        event_count=session.event_count,
        status=session.status,
        storage_key=session.storage_key,
        size_bytes=session.size_bytes,
        checksum=session.checksum,
        started_at=session.started_at,
        ended_at=session.ended_at,
        created_at=session.created_at,
    )


def to_event_response(event: SessionEvent) -> SessionEventResponse:
    return SessionEventResponse(
        id=event.id,
        session_id=event.session_id,
        sequence=event.sequence,
        timestamp_ms=event.timestamp_ms,
        event_type=event.event_type,
        category=event.category,
        data=event.data,
        masked=event.masked,
    )
