"""Authentication flows (EPIC-A009)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from auth.exceptions import AuthenticationError, InvalidTokenError, SessionError
from auth.hashing import verify_password
from auth.jwt import JwtService
from auth.models import AuthTokenPair, AuthUser, utc_now
from auth.sessions import SessionManager
from auth.users import UserStore

__all__ = ["AuthenticationService"]


class AuthenticationService:
    def __init__(
        self,
        users: UserStore,
        sessions: SessionManager,
        jwt: JwtService | None = None,
        *,
        access_ttl: int = 3600,
        refresh_ttl: int = 86400 * 7,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.jwt = jwt or JwtService()
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl

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
            "session": session.to_dict(),
        }

    def logout(self, *, session_id: str, updated_at: str | None = None) -> dict[str, Any]:
        session = self.sessions.revoke(session_id, updated_at=updated_at)
        return {"ok": True, "session": session.to_dict()}

    def refresh(
        self,
        *,
        refresh_token: str,
        created_at: str | None = None,
        access_jti: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        payload = self.jwt.decode(refresh_token, now=now)
        if payload.get("token_use") != "refresh":
            raise InvalidTokenError("not a refresh token")
        session_id = str(payload.get("sid") or "")
        if not session_id:
            raise InvalidTokenError("missing session")
        try:
            session = self.sessions.require_active(session_id, now=now)
        except SessionError as exc:
            raise InvalidTokenError(str(exc)) from exc
        if session.refresh_token_id and payload.get("jti") != session.refresh_token_id:
            raise InvalidTokenError("refresh token revoked")
        user = self.users.get(session.user_id)
        if user is None or user.status != "active":
            raise AuthenticationError("user unavailable")
        created = created_at or utc_now().isoformat()
        pair = self._issue_pair(
            user,
            session_id=session.session_id,
            created_at=created,
            access_jti=access_jti,
            refresh_jti=session.refresh_token_id,
        )
        return {"user": user.to_dict(), "tokens": pair.to_dict(), "session": session.to_dict()}

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
