from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.analysis_result import AnalysisStatus
from app.schemas.integration import (
    IntegrationStatusItem,
    IntegrationStatusResponse,
    JiraCreateTicketRequest,
    JiraTicketResponse,
    OAuthStartResponse,
    SlackNotifyRequest,
    SlackNotifyResponse,
)
from app.services.analysis_results import get_analysis_result
from app.services.integrations import IntegrationError
from app.services.jira import JiraService
from app.services.session_ingest import get_session_or_none
from app.services.slack import SlackService

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IntegrationStatusResponse:
    jira = await JiraService(db, settings).status()
    slack = await SlackService(db, settings).status()
    return IntegrationStatusResponse(
        items=[IntegrationStatusItem(**jira), IntegrationStatusItem(**slack)]
    )


@router.post("/jira/auth", response_model=OAuthStartResponse)
async def start_jira_auth(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OAuthStartResponse:
    try:
        auth_url, state = await JiraService(db, settings).build_authorization_url()
    except IntegrationError as error:
        raise integration_http_error(error) from error
    return OAuthStartResponse(auth_url=auth_url, state=state)


@router.get("/jira/callback")
async def jira_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    if error:
        return oauth_html("Jira authorization failed", error, ok=False)
    if not code:
        return oauth_html("Jira authorization failed", "Missing OAuth code.", ok=False)

    try:
        await JiraService(db, settings).handle_callback(code, state)
    except IntegrationError as caught_error:
        raise integration_http_error(caught_error) from caught_error
    return oauth_html("Jira connected", "You can close this tab and return to Rebug.", ok=True)


@router.post("/jira/create-ticket", response_model=JiraTicketResponse)
async def create_jira_ticket(
    payload: JiraCreateTicketRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JiraTicketResponse:
    session = await get_session_or_404(db, payload.session_id)
    analysis = await get_completed_analysis_or_409(db, payload.session_id)
    replay_url = payload.replay_url or f"{str(settings.viewer_base_url).rstrip('/')}/replay/{session.id}"

    try:
        ticket = await JiraService(db, settings).create_ticket(session, analysis, replay_url)
    except IntegrationError as error:
        raise integration_http_error(error) from error
    return JiraTicketResponse(**ticket)


@router.post("/slack/auth", response_model=OAuthStartResponse)
async def start_slack_auth(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OAuthStartResponse:
    try:
        auth_url, state = await SlackService(db, settings).build_authorization_url()
    except IntegrationError as error:
        raise integration_http_error(error) from error
    return OAuthStartResponse(auth_url=auth_url, state=state)


@router.get("/slack/callback")
async def slack_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    if error:
        return oauth_html("Slack authorization failed", error, ok=False)
    if not code:
        return oauth_html("Slack authorization failed", "Missing OAuth code.", ok=False)

    try:
        await SlackService(db, settings).handle_callback(code, state)
    except IntegrationError as caught_error:
        raise integration_http_error(caught_error) from caught_error
    return oauth_html("Slack connected", "You can close this tab and return to Rebug.", ok=True)


@router.post("/slack/notify", response_model=SlackNotifyResponse)
async def notify_slack(
    payload: SlackNotifyRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SlackNotifyResponse:
    session = await get_session_or_404(db, payload.session_id)
    analysis = await get_completed_analysis_or_409(db, payload.session_id)
    replay_url = payload.replay_url or f"{str(settings.viewer_base_url).rstrip('/')}/replay/{session.id}"

    try:
        notification = await SlackService(db, settings).notify(
            session,
            analysis,
            replay_url,
            jira_ticket_key=payload.jira_ticket_key,
            jira_ticket_url=payload.jira_ticket_url,
        )
    except IntegrationError as error:
        raise integration_http_error(error) from error
    return SlackNotifyResponse(**notification)


async def get_session_or_404(db: AsyncSession, session_id: UUID):
    session = await get_session_or_none(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return session


async def get_completed_analysis_or_409(db: AsyncSession, session_id: UUID):
    analysis = await get_analysis_result(db, session_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Analysis has not run.")
    if analysis.status != AnalysisStatus.completed.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis is {analysis.status}; wait for completion before filing.",
        )
    return analysis


def integration_http_error(error: IntegrationError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


def oauth_html(title: str, detail: str, *, ok: bool) -> HTMLResponse:
    color = "#166534" if ok else "#991b1b"
    background = "#f0fdf4" if ok else "#fff1f2"
    html = f"""
    <!doctype html>
    <html lang="en">
      <head><meta charset="utf-8"><title>{title}</title></head>
      <body style="font-family: system-ui, sans-serif; background: {background}; color: {color}; padding: 32px;">
        <h1>{title}</h1>
        <p>{detail}</p>
      </body>
    </html>
    """
    return HTMLResponse(html)
