from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Rebug API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "local"

    database_url: str = "postgresql+asyncpg://rebug:rebug@localhost:5432/rebug"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "chrome-extension://*",
        ]
    )

    viewer_base_url: Annotated[str, AnyHttpUrl] | str = "http://localhost:3000"
    backend_public_base_url: Annotated[str, AnyHttpUrl] | str = "http://localhost:8000"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    analysis_system_prompt_path: str = "../prompts/system-prompt-gpt.md"
    analysis_max_events: int = 1_000
    duplicate_threshold: float = 0.8

    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region_name: str = "us-east-1"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "rebug-sessions"

    max_session_package_bytes: int = 50 * 1024 * 1024

    token_encryption_secret: str = "dev-insecure-change-me"

    jira_client_id: str | None = None
    jira_client_secret: str | None = None
    jira_redirect_uri: Annotated[str, AnyHttpUrl] | str = (
        "http://localhost:8000/api/v1/integrations/jira/callback"
    )
    jira_scopes: str = "read:jira-work write:jira-work offline_access"
    jira_project_key: str | None = None
    jira_issue_type: str = "Bug"
    jira_replay_custom_field: str | None = None
    jira_cloud_id: str | None = None

    slack_client_id: str | None = None
    slack_client_secret: str | None = None
    slack_redirect_uri: Annotated[str, AnyHttpUrl] | str = (
        "http://localhost:8000/api/v1/integrations/slack/callback"
    )
    slack_scopes: str = "incoming-webhook,chat:write"
    slack_default_channel: str | None = None
    slack_incoming_webhook_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
