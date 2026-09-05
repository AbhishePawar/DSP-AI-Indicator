"""Durable MFA pending-challenge store (A008 metadata).

Login step-up identity is a signed JWT (shared ``DSP_AUTH_JWT_SECRET``).
Single-use, TOTP enrollment secrets, and WebAuthn ceremony challenges still
need a shared store so Cloud Run instance B can complete what instance A
started.

Pending TOTP seeds are stored encrypted (same Fernet box as enrolled secrets).
WebAuthn challenges are random ceremony bytes, not passwords; they are stored
as base64url and consumed atomically.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from auth.credential_boundary import resolve_auth_jwt_secret
from auth.secret_box import decrypt_secret, encrypt_secret

__all__ = ["MfaPendingStore"]

logger = logging.getLogger(__name__)

_ENTITY_KIND = "metadata"
_TOTP_PREFIX = "auth-mfa-totp-pending-"
_WEBAUTHN_PREFIX = "auth-webauthn-pending-"
_STEPUP_PREFIX = "auth-mfa-stepup-"
_HMAC_TOTP = b"dsp.mfa.totp-pending.v1"
_HMAC_WEBAUTHN = b"dsp.mfa.webauthn.v1"
_KEEP_AFTER_EXPIRY = timedelta(hours=1)


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


def _hmac_id(info: bytes, message: str) -> str:
    key = resolve_auth_jwt_secret().encode("utf-8")
    material = info + b":" + message.encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def _totp_entity_id(user_id: str) -> str:
    return f"{_TOTP_PREFIX}{_hmac_id(_HMAC_TOTP, user_id)}"


def _webauthn_entity_id(state: str) -> str:
    return f"{_WEBAUTHN_PREFIX}{_hmac_id(_HMAC_WEBAUTHN, state)}"


def _stepup_entity_id(jti: str) -> str:
    return f"{_STEPUP_PREFIX}{jti}"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


@dataclass(frozen=True, slots=True)
class TotpPendingRecord:
    user_id: str
    secret: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class WebAuthnPendingRecord:
    kind: str
    challenge: bytes
    created_at: datetime
    user_id: str | None = None


@dataclass(frozen=True, slots=True)
class StepupPendingRecord:
    user_id: str
    jti: str


class MfaPendingStore:
    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service

    def put_totp_pending(
        self, user_id: str, *, secret: str, ttl_seconds: int
    ) -> None:
        now = _now()
        expires = now + timedelta(seconds=int(ttl_seconds))
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_totp_entity_id(user_id),
            payload={
                "auth_entity": "mfa_totp_pending",
                "user_id": user_id,
                "secret": encrypt_secret(secret),
                "created_at": now.isoformat(),
                "expires_at": expires.isoformat(),
                "consumed_at": None,
            },
            refs={"auth_entity": "mfa_totp_pending"},
            created_at=now.isoformat(),
            allow_update=True,
        )
        logger.info("mfa totp pending stored")

    def get_totp_pending(self, user_id: str, *, now: datetime | None = None) -> TotpPendingRecord | None:
        ts = now or _now()
        row = self._persistence.get(_ENTITY_KIND, _totp_entity_id(user_id))
        if row is None:
            return None
        payload = dict(row.get("payload") or {})
        if payload.get("consumed_at"):
            return None
        expires = _parse_dt(payload.get("expires_at"))
        if expires is not None and ts > expires + _KEEP_AFTER_EXPIRY:
            self._persistence.delete(_ENTITY_KIND, _totp_entity_id(user_id))
            return None
        if expires is not None and ts >= expires:
            return None
        stored_user = str(payload.get("user_id") or "")
        if stored_user != user_id:
            return None
        secret = decrypt_secret(str(payload.get("secret") or ""))
        created = _parse_dt(payload.get("created_at")) or ts
        return TotpPendingRecord(
            user_id=stored_user,
            secret=secret,
            created_at=created,
            expires_at=expires or created,
        )

    def consume_totp_pending(
        self, user_id: str, *, now: datetime | None = None
    ) -> TotpPendingRecord | None:
        ts = now or _now()
        stored = self._persistence.atomic_consume_unexpired(
            _ENTITY_KIND,
            _totp_entity_id(user_id),
            now_iso=ts.isoformat(),
            consumed_at=ts.isoformat(),
        )
        if stored is None:
            return None
        payload = dict(stored.get("payload") or {})
        if str(payload.get("user_id") or "") != user_id:
            return None
        secret = decrypt_secret(str(payload.get("secret") or ""))
        created = _parse_dt(payload.get("created_at")) or ts
        expires = _parse_dt(payload.get("expires_at")) or created
        logger.info("mfa totp pending consumed")
        return TotpPendingRecord(
            user_id=user_id, secret=secret, created_at=created, expires_at=expires
        )

    def delete_totp_pending(self, user_id: str) -> None:
        self._persistence.delete(_ENTITY_KIND, _totp_entity_id(user_id))

    def put_webauthn_pending(
        self,
        state: str,
        *,
        kind: str,
        challenge: bytes,
        ttl_seconds: int,
        user_id: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        now = created_at or _now()
        expires = now + timedelta(seconds=int(ttl_seconds))
        payload: dict[str, Any] = {
            "auth_entity": "mfa_webauthn_pending",
            "kind": kind,
            "challenge_b64": _b64url_encode(challenge),
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "consumed_at": None,
        }
        if user_id:
            payload["user_id"] = user_id
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_webauthn_entity_id(state),
            payload=payload,
            refs={"auth_entity": "mfa_webauthn_pending"},
            created_at=now.isoformat(),
            allow_update=True,
        )
        logger.info("mfa webauthn pending stored")

    def consume_webauthn_pending(
        self, state: str, *, now: datetime | None = None
    ) -> WebAuthnPendingRecord | None:
        ts = now or _now()
        stored = self._persistence.atomic_consume_unexpired(
            _ENTITY_KIND,
            _webauthn_entity_id(state),
            now_iso=ts.isoformat(),
            consumed_at=ts.isoformat(),
        )
        if stored is None:
            return None
        payload = dict(stored.get("payload") or {})
        raw_user = payload.get("user_id")
        logger.info("mfa webauthn pending consumed")
        return WebAuthnPendingRecord(
            kind=str(payload.get("kind") or ""),
            challenge=_b64url_decode(str(payload.get("challenge_b64") or "")),
            created_at=_parse_dt(payload.get("created_at")) or ts,
            user_id=None if raw_user in (None, "") else str(raw_user),
        )

    def put_stepup(self, *, jti: str, user_id: str, ttl_seconds: int) -> None:
        now = _now()
        expires = now + timedelta(seconds=int(ttl_seconds))
        self._persistence.put(
            kind=_ENTITY_KIND,
            entity_id=_stepup_entity_id(jti),
            payload={
                "auth_entity": "mfa_stepup",
                "jti": jti,
                "user_id": user_id,
                "created_at": now.isoformat(),
                "expires_at": expires.isoformat(),
                "consumed_at": None,
            },
            refs={"auth_entity": "mfa_stepup"},
            created_at=now.isoformat(),
            allow_update=False,
        )
        logger.info("mfa stepup pending stored")

    def get_stepup(self, jti: str, *, now: datetime | None = None) -> StepupPendingRecord | None:
        ts = now or _now()
        row = self._persistence.get(_ENTITY_KIND, _stepup_entity_id(jti))
        if row is None:
            return None
        payload = dict(row.get("payload") or {})
        if payload.get("consumed_at"):
            return None
        expires = _parse_dt(payload.get("expires_at"))
        if expires is not None and ts >= expires:
            return None
        user_id = str(payload.get("user_id") or "")
        if not user_id:
            return None
        return StepupPendingRecord(user_id=user_id, jti=jti)

    def consume_stepup(self, jti: str, *, now: datetime | None = None) -> StepupPendingRecord | None:
        ts = now or _now()
        stored = self._persistence.atomic_consume_unexpired(
            _ENTITY_KIND,
            _stepup_entity_id(jti),
            now_iso=ts.isoformat(),
            consumed_at=ts.isoformat(),
        )
        if stored is None:
            return None
        payload = dict(stored.get("payload") or {})
        user_id = str(payload.get("user_id") or "")
        if not user_id:
            return None
        logger.info("mfa stepup pending consumed")
        return StepupPendingRecord(user_id=user_id, jti=jti)
