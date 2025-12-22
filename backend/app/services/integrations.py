from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration, IntegrationType
from app.services.token_crypto import TokenCrypto

SINGLE_USER_ID = "single-user"


class IntegrationError(RuntimeError):
    status_code = 502


class IntegrationNotConfiguredError(IntegrationError):
    status_code = 424


class IntegrationNeedsReauthError(IntegrationError):
    status_code = 401


class IntegrationRequestError(IntegrationError):
    status_code = 502


async def get_integration(
    db: AsyncSession,
    integration_type: IntegrationType | str,
    user_id: str = SINGLE_USER_ID,
) -> Integration | None:
    type_value = integration_type.value if isinstance(integration_type, IntegrationType) else str(integration_type)
    return await db.scalar(
        select(Integration)
        .where(Integration.user_id == user_id)
        .where(Integration.type == type_value)
    )


async def upsert_integration(
    db: AsyncSession,
    integration_type: IntegrationType | str,
    *,
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
    enabled: bool = True,
    crypto: TokenCrypto | None = None,
    user_id: str = SINGLE_USER_ID,
) -> Integration:
    type_value = integration_type.value if isinstance(integration_type, IntegrationType) else str(integration_type)
    integration = await get_integration(db, integration_type, user_id=user_id)
    if not integration:
        integration = Integration(
            user_id=user_id,
            type=type_value,
            config={},
            enabled=enabled,
        )
        db.add(integration)

    if config is not None:
        integration.config = config
    if credentials is not None:
        integration.credentials = (crypto or TokenCrypto()).encrypt_json(credentials)
    integration.enabled = enabled

    await db.commit()
    await db.refresh(integration)
    return integration


def decrypt_credentials(integration: Integration | None, crypto: TokenCrypto) -> dict[str, Any]:
    if not integration or not integration.enabled:
        return {}
    return crypto.decrypt_json(integration.credentials)
