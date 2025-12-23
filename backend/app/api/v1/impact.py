from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.bug_report import BugReport
from app.models.session import Session
from app.schemas.impact import (
    ImpactLinkResponse,
    ImpactScanResponse,
    IncidentIngestResponse,
    JiraWebhookResponse,
    ProductionIncidentCreate,
)
from app.services.impact_tracking import (
    ImpactTrackingService,
    to_impact_link_response,
    to_incident_response,
)

router = APIRouter(prefix="/impact", tags=["impact"])


@router.get("/links", response_model=list[ImpactLinkResponse])
async def list_impact_links(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[ImpactLinkResponse]:
    return await ImpactTrackingService(db, settings).list_links(limit=limit)


@router.post("/incidents", response_model=IncidentIngestResponse)
async def ingest_incident(
    payload: ProductionIncidentCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IncidentIngestResponse:
    incident, links = await ImpactTrackingService(db, settings).ingest_incident(payload)
    responses = []
    for link in links:
        report = await db.get(BugReport, link.bug_report_id)
        if not report:
            continue
        session = await db.get(Session, report.session_id)
        if not session:
            continue
        responses.append(to_impact_link_response(link, report, session))
    return IncidentIngestResponse(incident=to_incident_response(incident), matches=responses)


@router.post("/scan", response_model=ImpactScanResponse)
async def scan_impact_links(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImpactScanResponse:
    incidents_scanned, links_created = await ImpactTrackingService(db, settings).scan_open_incidents()
    return ImpactScanResponse(incidents_scanned=incidents_scanned, links_created=links_created)


@router.post("/jira-webhook", response_model=JiraWebhookResponse)
async def jira_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JiraWebhookResponse:
    report, matched_links = await ImpactTrackingService(db, settings).handle_jira_webhook(payload)
    issue = payload.get("issue") or {}
    fields = issue.get("fields") or {}
    jira_status = fields.get("status") or {}
    status_name = jira_status.get("name") if isinstance(jira_status, dict) else payload.get("status")
    issue_key = issue.get("key") or payload.get("issue_key")
    return JiraWebhookResponse(
        jira_ticket_key=str(issue_key) if issue_key else None,
        status=str(status_name) if status_name else None,
        final_status=report.final_status if report else None,
        matched_links=matched_links,
    )
