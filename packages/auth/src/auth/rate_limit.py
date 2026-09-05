"""Durable authentication rate limiter (A008 metadata).

``EnterpriseAuthPlatform._rate`` was a process-local dict. On Cloud Run that
lets an attacker reset the window by hitting another instance — brute-force
and abuse protection must be shared.

Counters live in A008 (Postgres in production) keyed by HMAC of the rate key,
not the raw IP/email. Persistence failure fails closed.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from auth.credential_boundary import resolve_auth_jwt_secret
from auth.exceptions import AuthenticationError

__all__ = ["AuthRateLimiter"]

logger = logging.getLogger(__name__)

_ENTITY_KIND = "metadata"
_PREFIX = "auth-rate-"
_HMAC_INFO = b"dsp.auth.rate.v1"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _hmac_id(message: str) -> str:
    key = resolve_auth_jwt_secret().encode("utf-8")
    material = _HMAC_INFO + b":" + message.encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


class AuthRateLimiter:
    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service

    def check(self, key: str, *, limit: int, window_sec: int) -> None:
        """Allow at most ``limit`` events in the current aligned ``window_sec`` bucket."""
        if limit < 1 or window_sec < 1:
            raise AuthenticationError("Rate limit exceeded. Try again later.")
        ts = _now()
        window_id = int(ts.timestamp()) // int(window_sec)
        entity_id = f"{_PREFIX}{_hmac_id(f'{key}|{int(window_sec)}|{int(limit)}|{window_id}')}"
        window_end = datetime.fromtimestamp(
            (window_id + 1) * int(window_sec), tz=timezone.utc
        )
        expires = window_end + timedelta(hours=1)
        now_iso = ts.isoformat()
        try:
            self._persistence.atomic_put_if_absent(
                kind=_ENTITY_KIND,
                entity_id=entity_id,
                payload={
                    "auth_entity": "auth_rate",
                    "count": 0,
                    "expires_at": expires.isoformat(),
                    "consumed_at": None,
                },
                refs={"auth_entity": "auth_rate"},
                created_at=now_iso,
            )
            stored = self._persistence.atomic_increment_unexpired(
                _ENTITY_KIND,
                entity_id,
                now_iso=now_iso,
                counter_field=("payload", "count"),
                max_value=int(limit),
            )
        except Exception as exc:  # noqa: BLE001 — fail closed; never bypass on storage errors
            logger.info("auth rate limiter unavailable")
            raise AuthenticationError("Rate limit exceeded. Try again later.") from exc
        if stored is None:
            logger.info("auth rate limited")
            raise AuthenticationError("Rate limit exceeded. Try again later.")
