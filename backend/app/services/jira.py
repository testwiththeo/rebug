from __future__ import annotations

import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.analysis_result import AnalysisResult
from app.models.integration import Integration, IntegrationType
from app.models.session import Session
from app.services.integrations import (
    IntegrationNeedsReauthError,
    IntegrationNotConfiguredError,
    IntegrationRequestError,
    decrypt_credentials,
    get_integration,
    upsert_integration,
)
from app.services.token_crypto import TokenCrypto

ATLASSIAN_AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ATLASSIAN_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"


class JiraService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.crypto = TokenCrypto(self.settings)

    async def build_authorization_url(self) -> tuple[str, str]:
        if not self.settings.jira_client_id:
            raise IntegrationNotConfiguredError("JIRA_CLIENT_ID is not configured.")

        state = secrets.token_urlsafe(24)
        integration = await get_integration(self.db, IntegrationType.jira.value)
        config = dict(integration.config) if integration else {}
        config["pending_oauth_state"] = state
        config["oauth_started_at"] = int(time.time())
        await upsert_integration(
            self.db,
            IntegrationType.jira.value,
            config=config,
            enabled=bool(integration.enabled) if integration else False,
        )
        query = urlencode(
            {
                "audience": "api.atlassian.com",
                "client_id": self.settings.jira_client_id,
                "scope": self.settings.jira_scopes,
                "redirect_uri": str(self.settings.jira_redirect_uri),
                "state": state,
                "response_type": "code",
                "prompt": "consent",
            }
        )
        return f"{ATLASSIAN_AUTHORIZE_URL}?{query}", state

    async def handle_callback(self, code: str, state: str | None) -> Integration:
        if not self.settings.jira_client_id or not self.settings.jira_client_secret:
            raise IntegrationNotConfiguredError("Jira OAuth client ID and secret are required.")

        integration = await get_integration(self.db, IntegrationType.jira.value)
        expected_state = (integration.config if integration else {}).get("pending_oauth_state")
        if not expected_state or not state or state != expected_state:
            raise IntegrationRequestError("Jira OAuth state did not match the pending authorization.")

        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(
                ATLASSIAN_TOKEN_URL,
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.settings.jira_client_id,
                    "client_secret": self.settings.jira_client_secret,
                    "code": code,
                    "redirect_uri": str(self.settings.jira_redirect_uri),
                },
                headers={"accept": "application/json"},
            )
            token_payload = parse_json_response(token_response, "Jira OAuth token exchange failed")
            resources_response = await client.get(
                ATLASSIAN_RESOURCES_URL,
                headers={
                    "accept": "application/json",
                    "authorization": f"Bearer {token_payload['access_token']}",
                },
            )
            resources = parse_json_response(
                resources_response,
                "Unable to load accessible Jira Cloud sites",
            )

        resource = choose_jira_resource(resources, self.settings.jira_cloud_id)
        now = int(time.time())
        credentials = {
            **token_payload,
            "expires_at": now + int(token_payload.get("expires_in") or 3600),
        }
        config = {
            "cloud_id": resource.get("id"),
            "cloud_name": resource.get("name"),
            "site_url": resource.get("url"),
            "project_key": self.settings.jira_project_key,
            "issue_type": self.settings.jira_issue_type,
            "replay_custom_field": self.settings.jira_replay_custom_field,
        }
        return await upsert_integration(
            self.db,
            IntegrationType.jira.value,
            config=config,
            credentials=credentials,
            crypto=self.crypto,
        )

    async def status(self) -> dict[str, Any]:
        integration = await get_integration(self.db, IntegrationType.jira.value)
        credentials = decrypt_credentials(integration, self.crypto)
        config = integration.config if integration else {}
        connected = bool(credentials.get("access_token") and integration and integration.enabled)
        needs_reauth = connected and not credentials.get("refresh_token") and is_expired(credentials)

        return {
            "type": IntegrationType.jira.value,
            "configured": bool(
                self.settings.jira_client_id
                and self.settings.jira_client_secret
                and (self.settings.jira_project_key or config.get("project_key"))
            ),
            "connected": connected,
            "enabled": bool(integration.enabled) if integration else False,
            "needs_reauth": needs_reauth,
            "display_name": config.get("cloud_name") or config.get("site_url"),
            "detail": build_status_detail(integration, config, "Jira"),
            "config": safe_config(config),
        }

    async def create_ticket(
        self,
        session: Session,
        analysis: AnalysisResult,
        replay_url: str,
    ) -> dict[str, str]:
        integration = await get_integration(self.db, IntegrationType.jira.value)
        credentials = await self.get_valid_credentials(integration)
        config = integration.config if integration else {}
        project_key = self.settings.jira_project_key or config.get("project_key")
        cloud_id = self.settings.jira_cloud_id or config.get("cloud_id")

        if not project_key:
            raise IntegrationNotConfiguredError("JIRA_PROJECT_KEY is required to create Jira issues.")
        if not cloud_id:
            raise IntegrationNotConfiguredError("Jira Cloud site is not connected.")

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": analysis.summary or f"Bug recorded on {session.url}",
            "issuetype": {"name": self.settings.jira_issue_type or config.get("issue_type") or "Bug"},
            "description": build_jira_description(session, analysis, replay_url),
            "priority": {"name": map_jira_priority(analysis.severity_suggestion)},
        }
        replay_field = self.settings.jira_replay_custom_field or config.get("replay_custom_field")
        if replay_field:
            fields[replay_field] = replay_url

        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={
                    "accept": "application/json",
                    "authorization": f"Bearer {credentials['access_token']}",
                    "content-type": "application/json",
                },
                json={"fields": fields},
            )
        payload = parse_json_response(response, "Jira issue creation failed")
        ticket_key = str(payload.get("key") or "")
        ticket_id = str(payload.get("id") or ticket_key)
        site_url = str(config.get("site_url") or "").rstrip("/")
        ticket_url = f"{site_url}/browse/{ticket_key}" if site_url and ticket_key else str(payload.get("self"))
        return {
            "ticket_id": ticket_id,
            "ticket_key": ticket_key,
            "ticket_url": ticket_url,
        }

    async def get_valid_credentials(self, integration: Integration | None) -> dict[str, Any]:
        credentials = decrypt_credentials(integration, self.crypto)
        if not integration or not integration.enabled or not credentials.get("access_token"):
            raise IntegrationNotConfiguredError("Jira is not connected.")

        if not is_expired(credentials):
            return credentials

        refresh_token = credentials.get("refresh_token")
        if not refresh_token:
            raise IntegrationNeedsReauthError("Jira token expired; re-authentication is required.")
        if not self.settings.jira_client_id or not self.settings.jira_client_secret:
            raise IntegrationNotConfiguredError("Jira OAuth client ID and secret are required.")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                ATLASSIAN_TOKEN_URL,
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.settings.jira_client_id,
                    "client_secret": self.settings.jira_client_secret,
                    "refresh_token": refresh_token,
                },
                headers={"accept": "application/json"},
            )
        refreshed = parse_json_response(response, "Jira token refresh failed")
        refreshed.setdefault("refresh_token", refresh_token)
        refreshed["expires_at"] = int(time.time()) + int(refreshed.get("expires_in") or 3600)

        await upsert_integration(
            self.db,
            IntegrationType.jira.value,
            config=integration.config,
            credentials=refreshed,
            enabled=integration.enabled,
            crypto=self.crypto,
        )
        return refreshed


def choose_jira_resource(resources: Any, configured_cloud_id: str | None) -> dict[str, Any]:
    if not isinstance(resources, list) or not resources:
        raise IntegrationRequestError("No Jira Cloud sites are available for this Atlassian account.")

    if configured_cloud_id:
        for resource in resources:
            if str(resource.get("id")) == configured_cloud_id:
                return resource
        raise IntegrationRequestError("Configured Jira Cloud ID was not available to this account.")
    return resources[0]


def is_expired(credentials: dict[str, Any]) -> bool:
    expires_at = int(credentials.get("expires_at") or 0)
    return expires_at <= int(time.time()) + 60


def build_jira_description(session: Session, analysis: AnalysisResult, replay_url: str) -> dict[str, Any]:
    content = [
        heading("Replay"),
        paragraph_with_link("Replay URL: ", replay_url),
        heading("Environment"),
        paragraph(
            f"{session.browser_name} {session.browser_version} on {session.os}; URL: {session.url}"
        ),
        heading("Reproduction Steps"),
        bullet_list(
            [
                f"{step.get('order', index + 1)}. {step.get('action', 'Step')} {step.get('value', '')} "
                f"(Actual: {step.get('actual', 'n/a')})"
                for index, step in enumerate(analysis.steps or [])
            ]
            or ["No reproduction steps were generated."]
        ),
        heading("Root Cause"),
        paragraph(str((analysis.root_cause or {}).get("summary") or "Unknown")),
    ]
    return {"type": "doc", "version": 1, "content": content}


def heading(text: str) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": text}]}


def paragraph(text: str) -> dict[str, Any]:
    return {"type": "paragraph", "content": [{"type": "text", "text": text[:30000]}]}


def paragraph_with_link(prefix: str, url: str) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "content": [
            {"type": "text", "text": prefix},
            {"type": "text", "text": url, "marks": [{"type": "link", "attrs": {"href": url}}]},
        ],
    }


def bullet_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [paragraph(item)]}
            for item in items[:20]
        ],
    }


def map_jira_priority(severity: str | None) -> str:
    match (severity or "").lower():
        case "blocker" | "critical":
            return "Highest"
        case "major":
            return "High"
        case "trivial":
            return "Low"
        case _:
            return "Medium"


def parse_json_response(response: httpx.Response, message: str) -> Any:
    if response.is_success:
        return response.json()
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    raise IntegrationRequestError(f"{message}: {response.status_code} {detail}")


def build_status_detail(integration: Integration | None, config: dict[str, Any], name: str) -> str:
    if not integration:
        return f"{name} is not connected."
    if not integration.enabled:
        return f"{name} is disabled."
    return str(config.get("site_url") or config.get("cloud_name") or f"{name} is connected.")


def safe_config(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if "token" not in key and "secret" not in key}
