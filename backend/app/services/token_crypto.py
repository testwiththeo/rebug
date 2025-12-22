from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings, get_settings


class TokenCrypto:
    def __init__(self, settings: Settings | None = None) -> None:
        secret = (settings or get_settings()).token_encryption_secret
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
        self.fernet = Fernet(key)

    def encrypt_json(self, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        return self.fernet.encrypt(encoded).decode("utf-8")

    def decrypt_json(self, value: str | None) -> dict[str, Any]:
        if not value:
            return {}

        try:
            decoded = self.fernet.decrypt(value.encode("utf-8"))
        except InvalidToken as error:
            raise ValueError("Unable to decrypt stored integration credentials.") from error
        return json.loads(decoded.decode("utf-8"))
