"""OAuth2 / OIDC / SSO architecture ports and local adapters (EPIC-016).

No vendor IdP integration — production interfaces + Null/Local adapters only.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Protocol, runtime_checkable

from security_platform.security.exceptions import SecurityError

__all__ = [
    "AuthorizationCodeRecord",
    "DeviceSessionPort",
    "InMemoryDeviceSessionStore",
    "LocalOidcClientAdapter",
    "LocalSsoAdapter",
    "NullOAuth2AuthorizationServer",
    "NullSsoProvider",
    "OAuth2AuthorizationPort",
    "OidcDiscoveryDocument",
    "PasswordResetPort",
    "EmailVerificationPort",
    "SsoProviderPort",
    "SsoSession",
]


@dataclass(frozen=True, slots=True)
class OidcDiscoveryDocument:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "jwks_uri": self.jwks_uri,
            "userinfo_endpoint": self.userinfo_endpoint,
        }


@dataclass(frozen=True, slots=True)
class AuthorizationCodeRecord:
    code: str
    client_id: str
    redirect_uri: str
    subject: str
    scope: str
    expires_at: datetime
    code_challenge: str | None = None
    nonce: str | None = None


@dataclass(frozen=True, slots=True)
class SsoSession:
    sso_session_id: str
    provider: str
    subject: str
    email: str | None
    created_at: datetime
    expires_at: datetime
    claims: dict[str, Any]


@runtime_checkable
class OAuth2AuthorizationPort(Protocol):
    """OAuth2 authorization-code (+ PKCE) server abstraction."""

    def create_authorization_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        subject: str,
        scope: str = "openid profile",
        code_challenge: str | None = None,
        nonce: str | None = None,
    ) -> AuthorizationCodeRecord: ...

    def exchange_code(
        self,
        code: str,
        *,
        client_id: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> dict[str, Any]: ...

    def discovery(self) -> OidcDiscoveryDocument: ...


@runtime_checkable
class SsoProviderPort(Protocol):
    """Enterprise SSO abstraction over OIDC/SAML-shaped flows."""

    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def begin_login(self, *, redirect_uri: str, state: str | None = None) -> dict[str, Any]: ...

    def complete_login(self, *, code: str, state: str | None = None) -> SsoSession: ...

    def logout(self, sso_session_id: str) -> None: ...


@runtime_checkable
class DeviceSessionPort(Protocol):
    """Device / session inventory for rotation and revocation."""

    def register(
        self,
        *,
        session_id: str,
        user_id: str,
        device_label: str,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]: ...

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]: ...

    def rotate(self, session_id: str) -> dict[str, Any]: ...

    def revoke(self, session_id: str) -> None: ...

    def revoke_all(self, user_id: str) -> int: ...


@runtime_checkable
class PasswordResetPort(Protocol):
    def request_reset(self, username: str) -> str: ...

    def confirm_reset(self, token: str, new_password: str) -> Any: ...


@runtime_checkable
class EmailVerificationPort(Protocol):
    def issue(self, user_id: str) -> str: ...

    def confirm(self, token: str) -> Any: ...


class NullOAuth2AuthorizationServer:
    """Honest unavailable OAuth2 AS — architecture placeholder."""

    def create_authorization_code(self, **kwargs: Any) -> AuthorizationCodeRecord:
        raise SecurityError("OAuth2 authorization server not configured")

    def exchange_code(self, code: str, **kwargs: Any) -> dict[str, Any]:
        raise SecurityError("OAuth2 authorization server not configured")

    def discovery(self) -> OidcDiscoveryDocument:
        raise SecurityError("OAuth2 authorization server not configured")


class NullSsoProvider:
    def provider_name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def begin_login(self, *, redirect_uri: str, state: str | None = None) -> dict[str, Any]:
        return {
            "available": False,
            "provider": self.provider_name(),
            "message": "SSO provider unavailable.",
            "redirect_uri": redirect_uri,
            "state": state,
            "authorization_url": None,
        }

    def complete_login(self, *, code: str, state: str | None = None) -> SsoSession:
        raise SecurityError("SSO provider unavailable.")

    def logout(self, sso_session_id: str) -> None:
        _ = sso_session_id


class LocalOidcClientAdapter:
    """Local/dev OIDC-shaped client — no external vendor calls."""

    def __init__(self, *, issuer: str = "https://local.dsp.invalid") -> None:
        self._issuer = issuer
        self._codes: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def exchange_code(self, code: str, *, redirect_uri: str) -> dict[str, Any]:
        with self._lock:
            payload = self._codes.pop(code, None)
        if payload is None:
            raise SecurityError("invalid authorization code")
        if payload.get("redirect_uri") != redirect_uri:
            raise SecurityError("redirect_uri mismatch")
        return {
            "access_token": secrets.token_urlsafe(24),
            "id_token": secrets.token_urlsafe(24),
            "token_type": "bearer",
            "expires_in": 3600,
            "claims": payload.get("claims") or {},
        }

    def seed_code(
        self,
        *,
        subject: str,
        redirect_uri: str,
        email: str | None = None,
    ) -> str:
        code = secrets.token_urlsafe(16)
        with self._lock:
            self._codes[code] = {
                "redirect_uri": redirect_uri,
                "claims": {
                    "sub": subject,
                    "email": email,
                    "iss": self._issuer,
                },
            }
        return code

    def discovery(self) -> OidcDiscoveryDocument:
        return OidcDiscoveryDocument(
            issuer=self._issuer,
            authorization_endpoint=f"{self._issuer}/oauth/authorize",
            token_endpoint=f"{self._issuer}/oauth/token",
            jwks_uri=f"{self._issuer}/.well-known/jwks.json",
            userinfo_endpoint=f"{self._issuer}/oauth/userinfo",
        )


class LocalSsoAdapter:
    """Local SSO adapter wrapping LocalOidcClientAdapter — not production IdP."""

    def __init__(self, oidc: LocalOidcClientAdapter | None = None) -> None:
        self._oidc = oidc or LocalOidcClientAdapter()
        self._sessions: dict[str, SsoSession] = {}
        self._lock = Lock()

    def provider_name(self) -> str:
        return "local"

    def is_available(self) -> bool:
        return True

    def begin_login(self, *, redirect_uri: str, state: str | None = None) -> dict[str, Any]:
        st = state or secrets.token_urlsafe(12)
        return {
            "available": True,
            "provider": self.provider_name(),
            "message": None,
            "redirect_uri": redirect_uri,
            "state": st,
            "authorization_url": (
                f"{self._oidc.discovery().authorization_endpoint}"
                f"?response_type=code&redirect_uri={redirect_uri}&state={st}"
            ),
        }

    def complete_login(self, *, code: str, state: str | None = None) -> SsoSession:
        _ = state
        tokens = self._oidc.exchange_code(code, redirect_uri="local://callback")
        claims = dict(tokens.get("claims") or {})
        now = datetime.now(tz=UTC)
        session = SsoSession(
            sso_session_id=f"sso_{uuid.uuid4().hex[:12]}",
            provider=self.provider_name(),
            subject=str(claims.get("sub") or "unknown"),
            email=claims.get("email"),
            created_at=now,
            expires_at=now + timedelta(hours=8),
            claims=claims,
        )
        with self._lock:
            self._sessions[session.sso_session_id] = session
        return session

    def logout(self, sso_session_id: str) -> None:
        with self._lock:
            self._sessions.pop(sso_session_id, None)


class InMemoryDeviceSessionStore:
    """Device/session management for rotation + inventory."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def register(
        self,
        *,
        session_id: str,
        user_id: str,
        device_label: str,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(tz=UTC).isoformat()
        row = {
            "session_id": session_id,
            "user_id": user_id,
            "device_label": device_label or "unknown",
            "ip_hint": ip_hint,
            "user_agent_hint": user_agent_hint,
            "status": "active",
            "created_at": now,
            "last_seen_at": now,
            "rotated_at": None,
        }
        with self._lock:
            self._items[session_id] = row
        return dict(row)

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._items.values() if v["user_id"] == user_id]

    def rotate(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._items.get(session_id)
            if row is None:
                raise SecurityError("session not found")
            row = dict(row)
            row["rotated_at"] = datetime.now(tz=UTC).isoformat()
            row["last_seen_at"] = row["rotated_at"]
            row["session_id"] = f"rot_{uuid.uuid4().hex[:12]}"
            old_id = session_id
            self._items.pop(old_id, None)
            self._items[row["session_id"]] = row
            return dict(row)

    def revoke(self, session_id: str) -> None:
        with self._lock:
            row = self._items.get(session_id)
            if row is not None:
                row["status"] = "revoked"

    def revoke_all(self, user_id: str) -> int:
        count = 0
        with self._lock:
            for row in self._items.values():
                if row["user_id"] == user_id and row["status"] == "active":
                    row["status"] = "revoked"
                    count += 1
        return count
