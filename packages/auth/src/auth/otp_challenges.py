"""Durable OTP challenge store (A008 metadata).

OTP request/verify on Cloud Run cannot use process-local dicts. Challenges,
resend pointers, send-window counters, and IP verify-failure windows are
persisted through A008 (Postgres in production).

The plaintext OTP is never stored. Only ``sha256$salt$digest`` is persisted.
Destination is stored on the challenge so a successful verify can bind the
session; the database identifier is HMAC-SHA256(destination), not the raw
mobile number.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from auth.credential_boundary import resolve_auth_jwt_secret
from auth.enterprise_models import OtpChallenge
from auth.exceptions import AuthenticationError

__all__ = [
    "OTP_KEEP_AFTER_EXPIRY",
    "OtpChallengeRecord",
    "OtpChallengeStore",
]

logger = logging.getLogger(__name__)

_ENTITY_KIND = "metadata"
_CHALLENGE_PREFIX = "auth-otp-"
_DEST_PREFIX = "auth-otp-dest-"
_IP_PREFIX = "auth-otp-ip-"
_HMAC_INFO = b"dsp.otp.id.v1"
OTP_KEEP_AFTER_EXPIRY = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _hmac_id(message: str) -> str:
    key = resolve_auth_jwt_secret().encode("utf-8")
    material = _HMAC_INFO + b":" + message.encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def _challenge_entity_id(challenge_id: str) -> str:
    return f"{_CHALLENGE_PREFIX}{challenge_id}"


def _dest_entity_id(destination: str) -> str:
    return f"{_DEST_PREFIX}{_hmac_id(destination)}"


def _ip_entity_id(ip_hint: str) -> str:
    return f"{_IP_PREFIX}{_hmac_id(ip_hint)}"


@dataclass(frozen=True, slots=True)
class OtpChallengeRecord:
    challenge: OtpChallenge
    consumed_at: str | None


class OtpChallengeStore:
    """Put/get/consume OTP challenges on the shared A008 persistence service."""

    def __init__(self, persistence_service: Any | None = None) -> None:
        if persistence_service is None:
            from persistence import get_persistence_service

            persistence_service = get_persistence_service()
        self._persistence = persistence_service

    def put_challenge(self, challenge: OtpChallenge) -> None:
        created_iso = challenge.created_at
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_challenge_entity_id(challenge.challenge_id),
            payload={
                "auth_entity": "otp_challenge",
                "challenge_id": challenge.challenge_id,
                "channel": challenge.channel,
                "destination": challenge.resolved_destination(),
                "mobile": challenge.mobile,
                "code_hash": challenge.code_hash,
                "created_at": challenge.created_at,
                "expires_at": challenge.expires_at,
                "resend_available_at": challenge.resend_available_at,
                "attempts": int(challenge.attempts),
                "consumed_at": None,
            },
            refs={"auth_entity": "otp_challenge"},
            created_at=created_iso,
            allow_update=False,
        )
        logger.info("otp challenge stored")

    def get_challenge(
        self, challenge_id: str, *, now: datetime | None = None
    ) -> OtpChallengeRecord | None:
        ts = now or _now()
        row = self._persistence.get(_ENTITY_KIND, _challenge_entity_id(challenge_id))
        if row is None:
            return None
        payload = dict(row.get("payload") or {})
        expires = _parse_dt(payload.get("expires_at"))
        if expires is not None and ts > expires + OTP_KEEP_AFTER_EXPIRY:
            self._persistence.delete(_ENTITY_KIND, _challenge_entity_id(challenge_id))
            return None
        return _record_from_payload(payload)

    def consume_success(
        self,
        challenge_id: str,
        *,
        now_iso: str,
        max_attempts: int,
    ) -> OtpChallengeRecord | None:
        stored = self._persistence.atomic_consume_unexpired(
            _ENTITY_KIND,
            _challenge_entity_id(challenge_id),
            now_iso=now_iso,
            consumed_at=now_iso,
            attempts_field=("payload", "attempts"),
            max_attempts=max_attempts,
        )
        if stored is None:
            return None
        payload = dict(stored.get("payload") or {})
        return _record_from_payload(payload)

    def increment_attempts(
        self,
        challenge_id: str,
        *,
        now_iso: str,
        max_attempts: int,
    ) -> OtpChallengeRecord | None:
        stored = self._persistence.atomic_increment_unexpired(
            _ENTITY_KIND,
            _challenge_entity_id(challenge_id),
            now_iso=now_iso,
            max_value=max_attempts,
        )
        if stored is None:
            return None
        payload = dict(stored.get("payload") or {})
        return _record_from_payload(payload)

    def get_destination(self, destination: str) -> dict[str, Any] | None:
        row = self._persistence.get(_ENTITY_KIND, _dest_entity_id(destination))
        if row is None:
            return None
        return dict(row.get("payload") or {})

    def put_destination(
        self,
        destination: str,
        *,
        challenge_id: str,
        send_times: list[str],
        resend_available_at: str | None,
        created_at: str,
    ) -> None:
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_dest_entity_id(destination),
            payload={
                "auth_entity": "otp_destination",
                "challenge_id": challenge_id,
                "send_times": list(send_times),
                "resend_available_at": resend_available_at,
            },
            refs={"auth_entity": "otp_destination"},
            created_at=created_at,
            allow_update=True,
        )

    def get_ip_failures(self, ip_hint: str) -> list[str]:
        row = self._persistence.get(_ENTITY_KIND, _ip_entity_id(ip_hint))
        if row is None:
            return []
        payload = dict(row.get("payload") or {})
        raw = payload.get("failures") or []
        return [str(item) for item in raw] if isinstance(raw, list) else []

    def put_ip_failures(
        self, ip_hint: str, *, failures: list[str], created_at: str
    ) -> None:
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_ip_entity_id(ip_hint),
            payload={
                "auth_entity": "otp_ip_failures",
                "failures": list(failures),
            },
            refs={"auth_entity": "otp_ip_failures"},
            created_at=created_at,
            allow_update=True,
        )


def _record_from_payload(payload: dict[str, Any]) -> OtpChallengeRecord:
    consumed_at = payload.get("consumed_at") or None
    if consumed_at is not None:
        consumed_at = str(consumed_at)
    destination = str(payload.get("destination") or payload.get("mobile") or "")
    challenge = OtpChallenge(
        challenge_id=str(payload.get("challenge_id") or ""),
        mobile=str(payload.get("mobile") or destination),
        code_hash=str(payload.get("code_hash") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        created_at=str(payload.get("created_at") or ""),
        attempts=int(payload.get("attempts") or 0),
        consumed=bool(consumed_at),
        resend_available_at=payload.get("resend_available_at"),
        channel=str(payload.get("channel") or "mobile"),
        destination=destination,
    )
    return OtpChallengeRecord(challenge=challenge, consumed_at=consumed_at)


def default_otp_store() -> OtpChallengeStore:
    """Production uses the process A008 registry; tests get an isolated store."""
    environment = (os.environ.get("DSP_ENVIRONMENT") or "").strip().lower()
    if environment == "production":
        return OtpChallengeStore()
    from persistence import InMemoryStorageProvider, PersistenceService, RepositoryRegistry

    return OtpChallengeStore(
        PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))
    )
