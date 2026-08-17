"""Short-lived JWT access tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError

from backend.app.core.config import get_settings

ALGORITHM = "HS256"


class InvalidAccessToken(ValueError):
    """Raised when the token cannot be trusted or decoded."""


def _secret() -> str:
    secret = get_settings().jwt_secret
    if len(secret) < 32 or secret.startswith("change-me"):
        raise RuntimeError("JWT_SECRET debe configurarse con al menos 32 caracteres.")
    return secret


def create_access_token(subject: str) -> str:
    """Create an access token containing only the user identifier."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=get_settings().jwt_access_token_minutes)
    payload = {"sub": subject, "iat": now, "exp": expires, "type": "access"}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """Decode and validate an access token, returning its subject."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except (InvalidTokenError, RuntimeError) as error:
        raise InvalidAccessToken from error

    subject = payload.get("sub")
    if not isinstance(subject, str) or payload.get("type") != "access":
        raise InvalidAccessToken
    return subject
