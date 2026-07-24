"""API key manager — in-memory hashed secrets only."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from security_platform.security.exceptions import AuthenticationError, SecurityError
from security_platform.security.roles import Role, assert_role

__all__ = ["ApiKeyManager", "ApiKeyRecord"]


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    """Stored API key metadata — raw secret is never retained."""

    key_id: str
    name: str
    role: Role
    secret_hash: str
    active: bool = True
    created_at: datetime | None = None
    owner_user_id: str | None = None

    def __post_init__(self) -> None:
        if not self.key_id.strip():
            msg = "key_id must not be empty"
            raise SecurityError(msg)
        object.__setattr__(self, "role", assert_role(self.role))


class ApiKeyManager:
    """Issue and verify API keys (process-local registry)."""

    def __init__(self) -> None:
        self._keys: dict[str, ApiKeyRecord] = {}

    def issue(
        self,
        *,
        name: str,
        role: Role | str = Role.API,
        key_id: str | None = None,
        owner_user_id: str | None = None,
        raw_secret: str | None = None,
    ) -> tuple[ApiKeyRecord, str]:
        """Create a key; returns ``(record, raw_secret)`` — secret shown once."""
        if not name.strip():
            msg = "API key name must not be empty"
            raise SecurityError(msg)
        kid = (key_id or f"ak_{secrets.token_hex(8)}").strip()
        if kid.lower() in self._keys:
            msg = f"duplicate API key id: {kid!r}"
            raise SecurityError(msg)
        secret = raw_secret or f"dsp_{secrets.token_urlsafe(24)}"
        record = ApiKeyRecord(
            key_id=kid,
            name=name.strip(),
            role=assert_role(role),
            secret_hash=_hash_secret(secret),
            created_at=datetime.now(tz=UTC),
            owner_user_id=owner_user_id,
        )
        self._keys[kid.lower()] = record
        return record, secret

    def revoke(self, key_id: str) -> None:
        record = self.get(key_id)
        self._keys[key_id.strip().lower()] = ApiKeyRecord(
            key_id=record.key_id,
            name=record.name,
            role=record.role,
            secret_hash=record.secret_hash,
            active=False,
            created_at=record.created_at,
            owner_user_id=record.owner_user_id,
        )

    def get(self, key_id: str) -> ApiKeyRecord:
        key = key_id.strip().lower()
        if key not in self._keys:
            msg = f"unknown API key: {key_id!r}"
            raise SecurityError(msg)
        return self._keys[key]

    def verify(self, key_id: str, raw_secret: str) -> ApiKeyRecord:
        """Verify key id + secret; raises ``AuthenticationError`` on failure."""
        try:
            record = self.get(key_id)
        except SecurityError as exc:
            raise AuthenticationError(str(exc)) from exc
        if not record.active:
            msg = f"API key revoked: {key_id!r}"
            raise AuthenticationError(msg)
        digest = _hash_secret(raw_secret)
        if not hmac.compare_digest(digest, record.secret_hash):
            msg = "invalid API key secret"
            raise AuthenticationError(msg)
        return record

    def verify_bearer(self, token: str) -> ApiKeyRecord:
        """Accept ``key_id.secret`` or ``key_id:secret`` bearer material."""
        cleaned = token.strip()
        for sep in (".", ":", "|"):
            if sep in cleaned:
                key_id, secret = cleaned.split(sep, 1)
                return self.verify(key_id, secret)
        msg = "API key bearer must be key_id.secret"
        raise AuthenticationError(msg)

    def list_keys(self) -> tuple[ApiKeyRecord, ...]:
        return tuple(self._keys[k] for k in sorted(self._keys))
