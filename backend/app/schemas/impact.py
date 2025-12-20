from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProductionIncidentCreate(BaseModel):
    title: str
    incident_url: str
    affected_url: str | None = None
    error_message: str | None = None
    source: str = "manual"
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class ProductionIncidentResponse(BaseModel):
    id: UUID
    title: str
    incident_url: str
    affected_url: str | None
    error_message: str | None
    source: str
    occurred_at: datetime | None
    created_at: datetime


class ImpactLinkResponse(BaseModel):
    id: UUID
    bug_report_id: UUID
    session_id: UUID
    bug_title: str
    bug_status: str | None
    jira_ticket_key: str | None
    jira_url: str | None
    replay_url: str | None
    original_url: str
    incident_title: str
    incident_url: str
    detected_at: datetime
    match_score: float | None
    match_reason: str | None
    notification_status: str
    notification_error: str | None
    evidence: dict[str, Any] = Field(default_factory=dict)


class IncidentIngestResponse(BaseModel):
    incident: ProductionIncidentResponse
    matches: list[ImpactLinkResponse] = Field(default_factory=list)


class ImpactScanResponse(BaseModel):
    incidents_scanned: int
    links_created: int


class JiraWebhookResponse(BaseModel):
    jira_ticket_key: str | None
    status: str | None
    final_status: str | None
    matched_links: int = 0
