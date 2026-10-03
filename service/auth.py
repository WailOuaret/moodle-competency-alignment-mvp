"""Bearer-token authentication for the service API."""

from __future__ import annotations

import hashlib
import hmac

from service.config import Settings
from service.errors import ErrorCode, ServiceError


BEARER_SCHEME = "bearer"
CHALLENGE_HEADERS = {"WWW-Authenticate": "Bearer"}


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def authenticate(settings: Settings, authorization: str | None) -> None:
    """Raise ``ServiceError`` unless ``authorization`` carries the service token.

    The check fails closed: with no token configured every protected request is
    refused. Tokens are compared as fixed-length digests in constant time, so
    neither the content nor the length of the real token leaks through timing.
    """

    if not settings.service_token:
        raise ServiceError(
            ErrorCode.SERVICE_NOT_CONFIGURED,
            "The alignment service is not configured to accept requests.",
            status_code=503,
        )

    header = (authorization or "").strip()

    if not header:
        raise ServiceError(
            ErrorCode.AUTH_MISSING,
            "Authentication is required.",
            status_code=401,
            headers=CHALLENGE_HEADERS,
        )

    scheme, _, credentials = header.partition(" ")
    credentials = credentials.strip()

    if scheme.casefold() != BEARER_SCHEME or not credentials:
        raise ServiceError(
            ErrorCode.AUTH_INVALID,
            "The credentials were not accepted.",
            status_code=401,
            headers=CHALLENGE_HEADERS,
        )

    if not hmac.compare_digest(
        _digest(credentials),
        _digest(settings.service_token),
    ):
        raise ServiceError(
            ErrorCode.AUTH_INVALID,
            "The credentials were not accepted.",
            status_code=401,
            headers=CHALLENGE_HEADERS,
        )
