"""Authentication flows (EPIC-A009)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from auth.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    RefreshTokenReuseError,
    SessionError,
)
from auth.hashing import verify_password
from auth.jwt import JwtService
from auth.models import AuthSession, AuthTokenPair, AuthUser, utc_now
from auth.sessions import SessionManager
from auth.users import UserStore

__all__ = ["AuthenticationService"]


@runtime_checkable
class _AuditPort(Protocol):
    def record(self, event_type: str, **kwargs: Any) -> Any: ...


def _hash_refresh_token(token: str) -> str:
    """Digest a raw refresh JWT for at-rest comparison.

    The token is already an HMAC-signed, unforgeable JWT — this hash is a
    defense-in-depth integrity check (independent of the ``jti`` claim) so
    session storage never has to keep the raw secret around, matching the
    "no plaintext secrets at rest" convention used elsewhere in this
    package (see ``auth.single_use_tokens``, ``auth.secret_box``).
    """
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


class AuthenticationService:
    def __init__(
        self,
        users: UserStore,
        sessions: SessionManager,
        jwt: JwtService | None = None,
        *,
        access_ttl: int = 3600,
        refresh_ttl: int = 86400 * 7,
        audit: _AuditPort | None = None,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.jwt = jwt or JwtService()
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        # Optional — wired post-construction by EnterpriseAuthPlatform onto
        # the shared AuthService singleton so refresh-rotation events land
        # in the same AuditLogger as every other authentication event. A
        # bare AuthService (no enterprise platform) stays fully functional
        # with audit logging simply disabled (no-op).
        self.audit: _AuditPort | None = audit

    def _log(self, event_type: str, **kwargs: Any) -> None:
        if self.audit is not None:
            self.audit.record(event_type, **kwargs)

    def login(
        self,
        *,
        username: str,
        password: str,
        created_at: str | None = None,
        session_id: str | None = None,
        access_jti: str | None = None,
        refresh_jti: str | None = None,
    ) -> dict[str, Any]:
        user = self.users.get_by_username(username)
        if user is None or user.status != "active":
            raise AuthenticationError("invalid credentials")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("invalid credentials")
        created = created_at or utc_now().isoformat()
        refresh_id = refresh_jti or str(uuid.uuid4())
        session = self.sessions.create(
            user_id=user.user_id,
            expires_in=self.refresh_ttl,
            session_id=session_id,
            refresh_token_id=refresh_id,
            created_at=created,
        )
        pair = self._issue_pair(
            user,
            session_id=session.session_id,
            created_at=created,
            access_jti=access_jti,
            refresh_jti=refresh_id,
        )
        self.attach_initial_refresh_token(session, pair)
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status=user.status,
            created_at=user.created_at,
            updated_at=created,
            last_login=created,
            roles=user.roles,
            metadata=user.metadata,
        )
        self.users.save(updated)
        return {
            "user": updated.to_dict(),
            "tokens": pair.to_dict(),
            "session": session.to_public_dict(),
        }

    def logout(self, *, session_id: str, updated_at: str | None = None) -> dict[str, Any]:
        session = self.sessions.revoke(session_id, updated_at=updated_at)
        self._log("session.revoked", user_id=session.user_id, detail=f"{session_id}:logout")
        return {"ok": True, "session": session.to_public_dict()}

    def attach_initial_refresh_token(
        self, session: AuthSession, pair: AuthTokenPair
    ) -> None:
        """Record the hash of a just-issued refresh token and audit its issuance.

        Called once right after the very first token pair for a session is
        minted (login, or an enterprise provider issuing a session) — the
        raw refresh JWT does not exist before ``_issue_pair`` returns it, so
        this cannot happen inside ``sessions.create()`` itself.
        """
        self.sessions.attach_refresh_material(
            session.session_id,
            token_id=session.refresh_token_id or "",
            token_hash=_hash_refresh_token(pair.refresh_token),
        )
        self._log("refresh.issued", user_id=session.user_id, detail=session.session_id)

    def refresh(
        self,
        *,
        refresh_token: str,
        created_at: str | None = None,
        access_jti: str | None = None,
        now: datetime | None = None,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        """Validate a refresh token and issue a fresh, rotated token pair.

        OAuth 2.0 Security BCP rotation: every successful call invalidates
        the presented refresh token and mints a brand-new one bound to the
        same session. Presenting a refresh token that does not match the
        session's *currently* active one — because it was already rotated
        away and is being replayed, because it was forged, or because a
        concurrent request won the rotation race first — revokes the whole
        session (the refresh-token family) and raises
        :class:`RefreshTokenReuseError`.
        """
        payload = self.jwt.decode(refresh_token, now=now)
        if payload.get("token_use") != "refresh":
            raise InvalidTokenError("not a refresh token")
        session_id = str(payload.get("sid") or "")
        if not session_id:
            raise InvalidTokenError("missing session")
        presented_jti = str(payload.get("jti") or "") or None
        presented_hash = _hash_refresh_token(refresh_token)
        try:
            session = self.sessions.require_active(session_id, now=now)
        except SessionError as exc:
            raise InvalidTokenError(str(exc)) from exc

        user = self.users.get(session.user_id)
        if user is None or user.status != "active":
            raise AuthenticationError("user unavailable")

        created = created_at or utc_now().isoformat()
        new_refresh_jti = str(uuid.uuid4())
        pair = self._issue_pair(
            user,
            session_id=session.session_id,
            created_at=created,
            access_jti=access_jti,
            refresh_jti=new_refresh_jti,
        )
        new_hash = _hash_refresh_token(pair.refresh_token)
        try:
            rotated_session = self.sessions.rotate_refresh_token(
                session_id,
                expected_token_id=presented_jti,
                expected_token_hash=presented_hash,
                new_token_id=new_refresh_jti,
                new_token_hash=new_hash,
                updated_at=created,
            )
        except RefreshTokenReuseError:
            self._log(
                "refresh.reused",
                user_id=session.user_id,
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail=session_id,
            )
            self._log(
                "refresh.revoked",
                user_id=session.user_id,
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail=session_id,
            )
            self._log(
                "session.revoked",
                user_id=session.user_id,
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail=f"{session_id}:refresh_reuse",
            )
            raise

        self._log(
            "refresh.rotated",
            user_id=user.user_id,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            detail=session_id,
        )
        return {
            "user": user.to_dict(),
            "tokens": pair.to_dict(),
            "session": rotated_session.to_public_dict(),
        }

    def current_user_from_access_token(
        self, access_token: str, *, now: datetime | None = None
    ) -> AuthUser:
        payload = self.jwt.decode(access_token, now=now)
        if payload.get("token_use") != "access":
            raise InvalidTokenError("not an access token")
        session_id = str(payload.get("sid") or "")
        if session_id:
            self.sessions.require_active(session_id, now=now)
        user = self.users.get(str(payload.get("sub") or ""))
        if user is None:
            raise AuthenticationError("user unavailable")
        return user

    def _issue_pair(
        self,
        user: AuthUser,
        *,
        session_id: str,
        created_at: str,
        access_jti: str | None,
        refresh_jti: str | None,
    ) -> AuthTokenPair:
        claims = {
            "username": user.username,
            "roles": list(user.roles),
            "sid": session_id,
        }
        access = self.jwt.issue(
            subject=user.user_id,
            claims=claims,
            expires_in=self.access_ttl,
            issued_at=created_at,
            token_id=access_jti or str(uuid.uuid4()),
            token_use="access",
        )
        refresh = self.jwt.issue(
            subject=user.user_id,
            claims={"sid": session_id},
            expires_in=self.refresh_ttl,
            issued_at=created_at,
            token_id=refresh_jti or str(uuid.uuid4()),
            token_use="refresh",
        )
        return AuthTokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.access_ttl,
            session_id=session_id,
        )
