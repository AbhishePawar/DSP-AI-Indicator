"""Shared single-use authentication token service.

Every "one-time link" flow in the platform — email verification, password
reset, email magic-link sign-in, enterprise invitation acceptance, and any
future one-time authentication feature — needs the exact same primitive:
issue an opaque secret, bind it to a purpose (and optionally a user /
organization), let it be redeemed **exactly once** before an expiry, and
reject or replay-protect everything else.

Previously each flow re-implemented this by hand with its own in-process
dict plus an un-expiring, never-deleted persistence fallback — a real
replay hole (a token consumed via the in-memory path stayed valid forever
in the persistence-backed path) and a SOLID violation (four copies of the
same logic drifting independently). This module is now the single
implementation; :class:`auth.enterprise_platform.EnterpriseAuthPlatform`
wires one instance of it and every flow calls through it.

Design notes
------------
* **No duplicate storage.** Tokens are persisted through whatever generic
  metadata port the platform already uses (``PersistenceService`` /
  ``StorageProviderPort``, the same one backing users, sessions, devices,
  OTP challenges, etc.) — see :mod:`persistence`. No new storage engine,
  table, or file is introduced.
* **No plaintext secrets at rest.** Only a keyed digest of the raw token
  is ever written to storage; the raw token exists only in memory long
  enough to email/return it to the caller once.
* **Constant-time comparisons.** Purpose and user/organization binding
  checks use :func:`hmac.compare_digest` rather than ``==`` so a timing
  side channel cannot leak how much of a value matched.
* **Atomic consumption.** ``consume()`` deletes the persisted record
  before validating it, and serializes concurrent attempts for the same
  token hash behind a per-hash lock — so two concurrent requests racing
  to redeem the same token cannot both succeed (single-process
  deployments, which is this platform's current persistence topology,
  are fully covered; the design leaves room for an atomic
  compare-and-delete primitive at the storage layer later without any
  caller-visible change).
* **Key rotation ready.** The digest is namespaced by a ``key_version``
  and, when ``DSP_TOKEN_HASH_SECRET`` is configured, computed with HMAC
  under that secret. Rotating the secret/version simply means older
  in-flight tokens (which are short-lived by design, minutes to hours)
  age out naturally instead of colliding with the new key.
* **Audit logging built in.** When an :class:`auth.audit.AuditLogger` is
  supplied, every issue / successful consume / failed consume / revoke is
  recorded automatically — callers get audit coverage for free instead of
  having to remember to log each flow individually.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Mapping, Protocol, runtime_checkable

__all__ = [
    "SingleUseTokenError",
    "TokenRecord",
    "SingleUseTokenService",
]

_TOKEN_PREFIX = "auth-token-"
_DEFAULT_KEY_VERSION = "v1"


class SingleUseTokenError(Exception):
    """Raised when a single-use token is missing, expired, or invalid.

    Call sites may pass their own ``error_cls`` to :meth:`consume` /
    :meth:`revoke` to preserve pre-existing, flow-specific exception
    types (e.g. ``AuthenticationError`` for magic links) — this is the
    default used when the caller does not need a specific type.
    """


@runtime_checkable
class _PersistencePort(Protocol):
    def put(
        self,
        *,
        kind: str,
        entity_id: str,
        payload: dict[str, Any],
        refs: dict[str, Any],
        created_at: str,
        allow_update: bool,
    ) -> Any: ...

    def get(self, kind: str, entity_id: str) -> dict[str, Any] | None: ...

    def delete(self, kind: str, entity_id: str) -> bool: ...

    def list_ids(self, kind: str) -> list[str]: ...


@runtime_checkable
class _AuditPort(Protocol):
    def record(self, event_type: str, **kwargs: Any) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class TokenRecord:
    """A redeemed (or peeked) single-use token's bound data."""

    purpose: str
    user_id: str | None
    organization_id: str | None
    data: Mapping[str, Any]
    created_at: str
    expires_at: str


class SingleUseTokenService:
    """Issue, redeem, and revoke opaque single-use authentication tokens."""

    def __init__(
        self,
        persistence: _PersistencePort,
        *,
        audit: _AuditPort | None = None,
        secret: str | None = None,
        key_version: str = _DEFAULT_KEY_VERSION,
    ) -> None:
        self._persistence = persistence
        self._audit = audit
        self._secret = secret if secret is not None else os.environ.get(
            "DSP_TOKEN_HASH_SECRET", ""
        )
        self._key_version = key_version
        self._locks: dict[str, Lock] = {}
        self._locks_guard = Lock()

    # --- internal ----------------------------------------------------

    def _digest(self, token: str) -> str:
        data = (token or "").encode("utf-8")
        if self._secret:
            return hmac.new(self._secret.encode("utf-8"), data, hashlib.sha256).hexdigest()
        return hashlib.sha256(data).hexdigest()

    def _entity_id(self, purpose: str, token: str) -> str:
        return f"{_TOKEN_PREFIX}{purpose}-{self._key_version}-{self._digest(token)}"

    def _lock_for(self, entity_id: str) -> Lock:
        with self._locks_guard:
            lock = self._locks.get(entity_id)
            if lock is None:
                lock = Lock()
                self._locks[entity_id] = lock
            return lock

    def _forget_lock(self, entity_id: str) -> None:
        with self._locks_guard:
            self._locks.pop(entity_id, None)

    def _log(self, event_type: str, **kwargs: Any) -> None:
        if self._audit is not None:
            self._audit.record(event_type, **kwargs)

    # --- public API ----------------------------------------------------

    def issue(
        self,
        *,
        purpose: str,
        ttl: timedelta,
        user_id: str | None = None,
        organization_id: str | None = None,
        data: Mapping[str, Any] | None = None,
        ip_hint: str | None = None,
    ) -> str:
        """Generate and persist a new single-use token; return the raw secret.

        The raw token is the only artifact the caller should hand to the
        user (via a link, an API response in dev mode, etc.) — it is
        never written to storage in plaintext.
        """
        if not purpose or not purpose.strip():
            raise ValueError("purpose is required")
        token = secrets.token_urlsafe(32)
        now = datetime.now(tz=timezone.utc)
        expires_at = (now + ttl).isoformat()
        entity_id = self._entity_id(purpose, token)
        refs: dict[str, Any] = {"auth_entity": f"single_use_token:{purpose}"}
        if user_id:
            refs["user_id"] = user_id
        if organization_id:
            refs["organization_id"] = organization_id
        self._persistence.put(
            kind="metadata",
            entity_id=entity_id,
            payload={
                "auth_entity": f"single_use_token:{purpose}",
                "purpose": purpose,
                "user_id": user_id,
                "organization_id": organization_id,
                "data": dict(data or {}),
                "created_at": now.isoformat(),
                "expires_at": expires_at,
                "key_version": self._key_version,
            },
            refs=refs,
            created_at=now.isoformat(),
            allow_update=False,
        )
        self._log(
            "single_use_token.issued",
            user_id=user_id,
            organization_id=organization_id,
            ip_hint=ip_hint,
            detail=purpose,
        )
        return token

    def peek(self, *, purpose: str, token: str) -> TokenRecord | None:
        """Read a pending token's bound data without consuming it."""
        row = self._persistence.get("metadata", self._entity_id(purpose, token))
        if row is None:
            return None
        return self._to_record(dict(row.get("payload") or {}))

    def consume(
        self,
        *,
        purpose: str,
        token: str,
        user_id: str | None = None,
        organization_id: str | None = None,
        ip_hint: str | None = None,
        error_cls: type[Exception] = SingleUseTokenError,
        error_message: str = "Invalid or expired token.",
    ) -> TokenRecord:
        """Atomically redeem a token exactly once.

        Validates purpose, expiry, and (when provided) user/organization
        binding using constant-time comparisons. The persisted record is
        deleted unconditionally as the very first step — a token that
        fails validation is burned, not left available for further replay
        attempts.
        """
        entity_id = self._entity_id(purpose, token)
        lock = self._lock_for(entity_id)
        with lock:
            row = self._persistence.get("metadata", entity_id)
            if row is not None:
                self._persistence.delete("metadata", entity_id)
        self._forget_lock(entity_id)

        if row is None:
            self._log(
                "single_use_token.consume_failed",
                user_id=user_id,
                organization_id=organization_id,
                ip_hint=ip_hint,
                detail=f"{purpose}:not_found_or_already_used",
            )
            raise error_cls(error_message)

        payload = dict(row.get("payload") or {})
        record = self._to_record(payload)

        if not hmac.compare_digest(str(payload.get("purpose") or ""), purpose):
            self._log(
                "single_use_token.consume_failed",
                user_id=user_id,
                organization_id=organization_id,
                ip_hint=ip_hint,
                detail=f"{purpose}:purpose_mismatch",
            )
            raise error_cls(error_message)

        if self._is_expired(record.expires_at):
            self._log(
                "single_use_token.consume_failed",
                user_id=record.user_id or user_id,
                organization_id=organization_id,
                ip_hint=ip_hint,
                detail=f"{purpose}:expired",
            )
            raise error_cls(error_message)

        if user_id is not None and record.user_id is not None:
            if not hmac.compare_digest(str(record.user_id), str(user_id)):
                self._log(
                    "single_use_token.consume_failed",
                    user_id=user_id,
                    organization_id=organization_id,
                    ip_hint=ip_hint,
                    detail=f"{purpose}:user_binding_mismatch",
                )
                raise error_cls(error_message)

        if organization_id is not None and record.organization_id is not None:
            if not hmac.compare_digest(str(record.organization_id), str(organization_id)):
                self._log(
                    "single_use_token.consume_failed",
                    user_id=record.user_id,
                    organization_id=organization_id,
                    ip_hint=ip_hint,
                    detail=f"{purpose}:organization_binding_mismatch",
                )
                raise error_cls(error_message)

        self._log(
            "single_use_token.consumed",
            user_id=record.user_id or user_id,
            organization_id=record.organization_id or organization_id,
            ip_hint=ip_hint,
            detail=purpose,
        )
        return record

    def revoke(self, *, purpose: str, token: str) -> bool:
        """Explicitly invalidate a pending token before it is ever redeemed."""
        entity_id = self._entity_id(purpose, token)
        lock = self._lock_for(entity_id)
        with lock:
            existed = self._persistence.delete("metadata", entity_id)
        self._forget_lock(entity_id)
        if existed:
            self._log("single_use_token.revoked", detail=purpose)
        return existed

    def revoke_all_for_user(self, *, purpose: str, user_id: str) -> int:
        """Invalidate every pending token of a given purpose for a user.

        Used e.g. when a user changes their password through another
        channel and any outstanding reset links should stop working, or
        when an admin force-resets a user's credentials.
        """
        prefix = f"{_TOKEN_PREFIX}{purpose}-"
        revoked = 0
        for entity_id in list(self._persistence.list_ids("metadata")):
            if not str(entity_id).startswith(prefix):
                continue
            row = self._persistence.get("metadata", entity_id)
            if not row:
                continue
            payload = row.get("payload") or {}
            if payload.get("user_id") != user_id:
                continue
            if self._persistence.delete("metadata", entity_id):
                revoked += 1
        if revoked:
            self._log(
                "single_use_token.revoked_all",
                user_id=user_id,
                detail=f"{purpose}:{revoked}",
            )
        return revoked

    # --- helpers ---------------------------------------------------------

    @staticmethod
    def _is_expired(expires_at: str) -> bool:
        if not expires_at:
            return False
        exp = datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(tz=timezone.utc) > exp

    @staticmethod
    def _to_record(payload: dict[str, Any]) -> TokenRecord:
        return TokenRecord(
            purpose=str(payload.get("purpose") or ""),
            user_id=payload.get("user_id"),
            organization_id=payload.get("organization_id"),
            data=dict(payload.get("data") or {}),
            created_at=str(payload.get("created_at") or ""),
            expires_at=str(payload.get("expires_at") or ""),
        )
