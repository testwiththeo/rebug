from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OAuthStartResponse(BaseModel):
    auth_url: str
    state: str


class IntegrationStatusItem(BaseModel):
    type: str
    configured: bool
    connected: bool
    enabled: bool
    needs_reauth: bool = False
    display_name: str | None = None
    detail: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationStatusResponse(BaseModel):
    items: list[IntegrationStatusItem]


class JiraCreateTicketRequest(BaseModel):
    session_id: UUID
    replay_url: str | None = None


class JiraTicketResponse(BaseModel):
    ticket_id: str
    ticket_key: str
    ticket_url: str


class SlackNotifyRequest(BaseModel):
    session_id: UUID
    replay_url: str | None = None
    jira_ticket_key: str | None = None
    jira_ticket_url: str | None = None


class SlackNotifyResponse(BaseModel):
    channel: str | None = None
    ts: str | None = None
    message_url: str | None = None


class FileBugResponse(BaseModel):
    session_id: UUID
    bug_report_id: UUID | None = None
    status: str
    replay_url: str
    jira: JiraTicketResponse | None = None
    slack: SlackNotifyResponse | None = None
    error_message: str | None = None
    filed_at: datetime | None = None
