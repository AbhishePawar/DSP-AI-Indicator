"""Session + refresh-token stores and token service (PEP-001)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from security_platform.security.exceptions import AuthenticationError, TokenError
from security_platform.security.identity.ports import (
    RefreshTokenRecord,
    RefreshTokenStorePort,
    SessionRecord,
    SessionTrackerPort,
)
from security_platform.security.jwt import JWTManager
from security_platform.security.roles import Role
from security_platform.security.users import UserRecord

__all__ = [
    "InMemoryRefreshTokenStore",
    "InMemorySessionTracker",
    "Pep002SessionTracker",
    "TokenPair",
    "TokenService",
]


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    session_id: str = ""


class InMemoryRefreshTokenStore:
    def __init__(self) -> None:
        self._items: dict[str, RefreshTokenRecord] = {}
        self._lock = Lock()

    def save(self, record: RefreshTokenRecord) -> None:
        with self._lock:
            self._items[record.token_hash] = record

    def get(self, token_hash: str) -> RefreshTokenRecord | None:
        with self._lock:
            return self._items.get(token_hash)

    def revoke(self, token_hash: str) -> None:
        with self._lock:
            rec = self._items.get(token_hash)
            if rec is not None:
                rec.revoked = True

    def revoke_all_for_user(self, user_id: str) -> int:
        count = 0
        with self._lock:
            for rec in self._items.values():
                if rec.user_id == user_id and not rec.revoked:
                    rec.revoked = True
                    count += 1
        return count


class InMemorySessionTracker:
    def __init__(self) -> None:
        self._items: dict[str, SessionRecord] = {}
        self._lock = Lock()

    def create(self, record: SessionRecord) -> None:
        with self._lock:
            self._items[record.session_id] = record

    def get(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            return self._items.get(session_id)

    def touch(self, session_id: str) -> None:
        with self._lock:
            rec = self._items.get(session_id)
            if rec is not None:
                rec.last_seen_at = datetime.now(tz=UTC)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._items.pop(session_id, None)

    def delete_all_for_user(self, user_id: str) -> int:
        with self._lock:
            doomed = [k for k, v in self._items.items() if v.user_id == user_id]
            for k in doomed:
                del self._items[k]
            return len(doomed)


class Pep002SessionTracker:
    """SessionTrackerPort adapter over production_platform SessionPort."""

    def __init__(self, session_port: Any) -> None:
        self._port = session_port

    def create(self, record: SessionRecord) -> None:
        ttl = max(1.0, (record.expires_at - datetime.now(tz=UTC)).total_seconds())
        self._port.set(
            record.session_id,
            {
                "user_id": record.user_id,
                "expires_at": record.expires_at.isoformat(),
                "remember_me": record.remember_me,
                "created_at": record.created_at.isoformat(),
                "last_seen_at": record.last_seen_at.isoformat(),
                "client_fingerprint": record.client_fingerprint,
            },
            ttl_seconds=ttl,
        )

    def get(self, session_id: str) -> SessionRecord | None:
        payload = self._port.get(session_id)
        if not payload:
            return None
        return SessionRecord(
            session_id=session_id,
            user_id=str(payload["user_id"]),
            expires_at=datetime.fromisoformat(str(payload["expires_at"])),
            remember_me=bool(payload.get("remember_me", False)),
            created_at=datetime.fromisoformat(str(payload.get("created_at"))),
            last_seen_at=datetime.fromisoformat(str(payload.get("last_seen_at"))),
            client_fingerprint=payload.get("client_fingerprint"),
        )

    def touch(self, session_id: str) -> None:
        rec = self.get(session_id)
        if rec is None:
            return
        rec.last_seen_at = datetime.now(tz=UTC)
        self.create(rec)

    def delete(self, session_id: str) -> None:
        self._port.delete(session_id)

    def delete_all_for_user(self, user_id: str) -> int:
        # SessionPort has no list API — best-effort no-op count.
        _ = user_id
        return 0


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class TokenService:
    """Access JWT + refresh rotation / revocation."""

    def __init__(
        self,
        *,
        jwt: JWTManager,
        refresh_store: RefreshTokenStorePort,
        sessions: SessionTrackerPort,
        access_ttl_seconds: int = 3600,
        refresh_ttl_seconds: int = 7 * 24 * 3600,
        remember_me_ttl_seconds: int = 30 * 24 * 3600,
    ) -> None:
        self._jwt = jwt
        self._refresh = refresh_store
        self._sessions = sessions
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds
        self._remember_ttl = remember_me_ttl_seconds

    def issue_pair(
        self,
        user: UserRecord,
        *,
        remember_me: bool = False,
        client_fingerprint: str | None = None,
    ) -> TokenPair:
        session_id = str(uuid.uuid4())
        refresh_ttl = self._remember_ttl if remember_me else self._refresh_ttl
        now = datetime.now(tz=UTC)
        session = SessionRecord(
            session_id=session_id,
            user_id=user.user_id,
            expires_at=now + timedelta(seconds=refresh_ttl),
            remember_me=remember_me,
            client_fingerprint=client_fingerprint,
        )
        self._sessions.create(session)
        jti = str(uuid.uuid4())
        access = self._jwt.issue(
            subject=user.user_id,
            role=user.role,
            username=user.username,
            ttl_seconds=self._access_ttl,
            token_id=jti,
            extra={"sid": session_id},
        )
        raw_refresh = secrets.token_urlsafe(48)
        self._refresh.save(
            RefreshTokenRecord(
                token_hash=hash_token(raw_refresh),
                user_id=user.user_id,
                session_id=session_id,
                expires_at=now + timedelta(seconds=refresh_ttl),
                family_id=str(uuid.uuid4()),
            )
        )
        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self._access_ttl,
            session_id=session_id,
        )

    def rotate(self, refresh_token: str, *, user: UserRecord) -> TokenPair:
        rec = self._refresh.get(hash_token(refresh_token))
        if rec is None or rec.revoked:
            raise AuthenticationError("invalid refresh token")
        if rec.expires_at <= datetime.now(tz=UTC):
            raise AuthenticationError("refresh token expired")
        if rec.user_id != user.user_id:
            raise AuthenticationError("refresh token user mismatch")
        self._refresh.revoke(rec.token_hash)
        remember = False
        session = self._sessions.get(rec.session_id)
        if session is not None:
            remember = session.remember_me
            self._sessions.delete(rec.session_id)
        return self.issue_pair(user, remember_me=remember)

    def revoke_refresh(self, refresh_token: str) -> None:
        self._refresh.revoke(hash_token(refresh_token))

    def revoke_user(self, user_id: str) -> None:
        self._refresh.revoke_all_for_user(user_id)
        self._sessions.delete_all_for_user(user_id)
