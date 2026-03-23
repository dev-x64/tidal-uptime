from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import Response

from app.settings import Settings


class AuthManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify_password(self, password: str) -> bool:
        return hmac.compare_digest(password, self.settings.admin_password)

    def create_cookie_value(self) -> str:
        expires_at = int(time.time()) + self.settings.auth_cookie_max_age_seconds
        payload = str(expires_at).encode("utf-8")
        signature = hmac.new(
            self.settings.auth_cookie_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).digest()
        token = b".".join(
            (
                payload,
                base64.urlsafe_b64encode(signature).rstrip(b"="),
            )
        )
        return token.decode("utf-8")

    def is_cookie_valid(self, cookie_value: str | None) -> bool:
        if not cookie_value:
            return False

        try:
            payload_part, signature_part = cookie_value.split(".", 1)
            expires_at = int(payload_part)
            provided_signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        except (ValueError, TypeError):
            return False

        expected_signature = hmac.new(
            self.settings.auth_cookie_secret.encode("utf-8"),
            payload_part.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            return False

        return expires_at >= int(time.time())

    def apply_login_cookie(self, response: Response) -> None:
        response.set_cookie(
            key=self.settings.auth_cookie_name,
            value=self.create_cookie_value(),
            max_age=self.settings.auth_cookie_max_age_seconds,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )

    def clear_login_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=self.settings.auth_cookie_name,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )
