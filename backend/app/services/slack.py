from __future__ import annotations

import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.analysis_result import AnalysisResult
from app.models.bug_report import BugReport
from app.models.impact_link import ImpactLink
from app.models.integration import Integration, IntegrationType
from app.models.session import Session
from app.services.integrations import (
    IntegrationNotConfiguredError,
    IntegrationRequestError,
    decrypt_credentials,
    get_integration,
    upsert_integration,
)
from app.services.token_crypto import TokenCrypto

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_CHAT_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_PERMALINK_URL = "https://slack.com/api/chat.getPermalink"


class SlackService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.crypto = TokenCrypto(self.settings)

    async def build_authorization_url(self) -> tuple[str, str]:
        if not self.settings.slack_client_id:
            raise IntegrationNotConfiguredError("SLACK_CLIENT_ID is not configured.")

        state = secrets.token_urlsafe(24)
        integration = await get_integration(self.db, IntegrationType.slack.value)
        config = dict(integration.config) if integration else {}
        config["pending_oauth_state"] = state
        config["oauth_started_at"] = int(time.time())
        await upsert_integration(
            self.db,
            IntegrationType.slack.value,
            config=config,
            enabled=bool(integration.enabled) if integration else False,
        )
        query = urlencode(
            {
                "client_id": self.settings.slack_client_id,
                "scope": self.settings.slack_scopes,
                "redirect_uri": str(self.settings.slack_redirect_uri),
                "state": state,
            }
        )
        return f"{SLACK_AUTHORIZE_URL}?{query}", state

    async def handle_callback(self, code: str, state: str | None) -> Integration:
        if not self.settings.slack_client_id or not self.settings.slack_client_secret:
            raise IntegrationNotConfiguredError("Slack OAuth client ID and secret are required.")

        integration = await get_integration(self.db, IntegrationType.slack.value)
        expected_state = (integration.config if integration else {}).get("pending_oauth_state")
        if not expected_state or not state or state != expected_state:
            raise IntegrationRequestError("Slack OAuth state did not match the pending authorization.")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                SLACK_TOKEN_URL,
                data={
                    "client_id": self.settings.slack_client_id,
                    "client_secret": self.settings.slack_client_secret,
                    "code": code,
                    "redirect_uri": str(self.settings.slack_redirect_uri),
                },
                headers={"accept": "application/json"},
            )
        payload = parse_slack_response(response, "Slack OAuth token exchange failed")
        webhook = payload.get("incoming_webhook") or {}
        team = payload.get("team") or {}
        config = {
            "team_id": team.get("id"),
            "team_name": team.get("name"),
            "channel": webhook.get("channel") or self.settings.slack_default_channel,
            "channel_id": webhook.get("channel_id"),
            "configuration_url": webhook.get("configuration_url"),
        }
        credentials = {
            "access_token": payload.get("access_token"),
            "bot_user_id": payload.get("bot_user_id"),
            "scope": payload.get("scope"),
            "incoming_webhook_url": webhook.get("url"),
            "installed_at": int(time.time()),
        }
        return await upsert_integration(
            self.db,
            IntegrationType.slack.value,
            config=config,
            credentials=credentials,
            crypto=self.crypto,
        )

    async def status(self) -> dict[str, Any]:
        integration = await get_integration(self.db, IntegrationType.slack.value)
        credentials = decrypt_credentials(integration, self.crypto)
        config = integration.config if integration else {}
        has_static_webhook = bool(self.settings.slack_incoming_webhook_url)
        connected = bool(
            has_static_webhook
            or (
                integration
                and integration.enabled
                and (credentials.get("incoming_webhook_url") or credentials.get("access_token"))
            )
        )
        return {
            "type": IntegrationType.slack.value,
            "configured": bool(
                self.settings.slack_incoming_webhook_url
                or (self.settings.slack_client_id and self.settings.slack_client_secret)
                or connected
            ),
            "connected": connected,
            "enabled": bool(integration.enabled) if integration else bool(self.settings.slack_incoming_webhook_url),
            "needs_reauth": False,
            "display_name": config.get("team_name") or config.get("channel"),
            "detail": "Slack webhook configured." if has_static_webhook else build_status_detail(integration, config),
            "config": safe_config(config),
        }

    async def notify(
        self,
        session: Session,
        analysis: AnalysisResult,
        replay_url: str,
        jira_ticket_key: str | None = None,
        jira_ticket_url: str | None = None,
    ) -> dict[str, str | None]:
        integration = await get_integration(self.db, IntegrationType.slack.value)
        credentials = decrypt_credentials(integration, self.crypto)
        config = integration.config if integration else {}
        webhook_url = (
            self.settings.slack_incoming_webhook_url
            or credentials.get("incoming_webhook_url")
        )
        payload = build_slack_payload(session, analysis, replay_url, jira_ticket_key, jira_ticket_url)

        if webhook_url:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(webhook_url, json=payload)
            if not response.is_success:
                raise IntegrationRequestError(
                    f"Slack incoming webhook failed: {response.status_code} {response.text}"
                )
            return {
                "channel": config.get("channel") or config.get("channel_id"),
                "ts": None,
                "message_url": None,
            }

        token = credentials.get("access_token")
        channel = self.settings.slack_default_channel or config.get("channel_id") or config.get("channel")
        if not token or not channel or not integration or not integration.enabled:
            raise IntegrationNotConfiguredError("Slack is not connected.")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                SLACK_CHAT_POST_MESSAGE_URL,
                headers={
                    "authorization": f"Bearer {token}",
                    "content-type": "application/json; charset=utf-8",
                },
                json={**payload, "channel": channel},
            )
            posted = parse_slack_response(response, "Slack chat.postMessage failed")
            permalink_response = await client.get(
                SLACK_PERMALINK_URL,
                headers={"authorization": f"Bearer {token}"},
                params={"channel": posted["channel"], "message_ts": posted["ts"]},
            )
        permalink = parse_slack_response(permalink_response, "Slack permalink lookup failed")
        return {
            "channel": posted.get("channel"),
            "ts": posted.get("ts"),
            "message_url": permalink.get("permalink"),
        }

    async def notify_impact_link(
        self,
        report: BugReport,
        session: Session,
        link: ImpactLink,
    ) -> dict[str, str | None]:
        integration = await get_integration(self.db, IntegrationType.slack.value)
        credentials = decrypt_credentials(integration, self.crypto)
        config = integration.config if integration else {}
        webhook_url = self.settings.slack_incoming_webhook_url or credentials.get("incoming_webhook_url")
        payload = build_impact_payload(report, session, link)

        if webhook_url:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(webhook_url, json=payload)
            if not response.is_success:
                raise IntegrationRequestError(
                    f"Slack incoming webhook failed: {response.status_code} {response.text}"
                )
            return {
                "channel": config.get("channel") or config.get("channel_id"),
                "ts": None,
                "message_url": None,
            }

        token = credentials.get("access_token")
        channel = self.settings.slack_default_channel or config.get("channel_id") or config.get("channel")
        if not token or not channel or not integration or not integration.enabled:
            raise IntegrationNotConfiguredError("Slack is not connected.")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                SLACK_CHAT_POST_MESSAGE_URL,
                headers={
                    "authorization": f"Bearer {token}",
                    "content-type": "application/json; charset=utf-8",
                },
                json={**payload, "channel": channel},
            )
            posted = parse_slack_response(response, "Slack impact notification failed")
        return {
            "channel": posted.get("channel"),
            "ts": posted.get("ts"),
            "message_url": None,
        }


def build_slack_payload(
    session: Session,
    analysis: AnalysisResult,
    replay_url: str,
    jira_ticket_key: str | None,
    jira_ticket_url: str | None,
) -> dict[str, Any]:
    title = analysis.summary or f"Bug recorded on {session.url}"
    severity = analysis.severity_suggestion or "unknown"
    environment = f"{session.browser_name} {session.browser_version} on {session.os}"
    buttons: list[dict[str, Any]] = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "View Replay"},
            "url": replay_url,
            "action_id": "view_replay",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Assign to Me"},
            "value": str(session.id),
            "action_id": "assign_to_me",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Dismiss"},
            "value": str(session.id),
            "style": "danger",
            "action_id": "dismiss_bug",
        },
    ]
    if jira_ticket_url:
        buttons.insert(
            1,
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View in Jira"},
                "url": jira_ticket_url,
                "action_id": "view_jira",
            },
        )

    return {
        "text": f"{title} ({severity})",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n*Severity:* {severity}\n*Environment:* {environment}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Source:* {session.url}"
                    + (f"\n*Jira:* {jira_ticket_key}" if jira_ticket_key else ""),
                },
            },
            {"type": "actions", "elements": buttons},
        ],
    }


def build_impact_payload(report: BugReport, session: Session, link: ImpactLink) -> dict[str, Any]:
    match_score = f"{round(float(link.match_score or 0) * 100)}%"
    ticket_text = f"<{report.jira_url}|{report.jira_ticket_key}>" if report.jira_url else report.jira_ticket_key
    incident_text = f"<{link.incident_url}|{link.incident_title}>"
    bug_status = report.final_status or report.status
    buttons = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "View Incident"},
            "url": link.incident_url,
            "action_id": "view_incident",
        }
    ]
    if report.replay_url:
        buttons.insert(
            0,
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Replay"},
                "url": report.replay_url,
                "action_id": "view_original_replay",
            },
        )

    return {
        "text": f"This bug was reported earlier and later caused production impact: {link.incident_title}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":warning: *This bug was reported earlier and closed as "
                        f"`{bug_status}`.*\nIt now matches production incident {incident_text}."
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Original bug:*\n{ticket_text or report.title}"},
                    {"type": "mrkdwn", "text": f"*Match:*\n{match_score}"},
                    {"type": "mrkdwn", "text": f"*Original URL:*\n{session.url}"},
                    {"type": "mrkdwn", "text": f"*Reason:*\n{link.match_reason or 'URL and error similarity'}"},
                ],
            },
            {
                "type": "actions",
                "elements": buttons,
            },
        ],
    }


def parse_slack_response(response: httpx.Response, message: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as error:
        raise IntegrationRequestError(f"{message}: invalid JSON response") from error

    if response.is_success and payload.get("ok") is True:
        return payload
    raise IntegrationRequestError(f"{message}: {response.status_code} {payload}")


def build_status_detail(integration: Integration | None, config: dict[str, Any]) -> str:
    if not integration:
        return "Slack is not connected."
    if not integration.enabled:
        return "Slack is disabled."
    return str(config.get("channel") or config.get("team_name") or "Slack is connected.")


def safe_config(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if "token" not in key and "secret" not in key}
