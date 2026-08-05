"""Session management (EPIC-A009)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from auth.exceptions import RefreshTokenReuseError, SessionError
from auth.models import AuthSession, freeze_mapping, utc_now

__all__ = ["SessionManager"]

_SESSION_PREFIX = "auth-session-"


class SessionManager:
    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service
        # Per-session locks guarding refresh-token rotation so two concurrent
        # refresh attempts for the same session cannot both observe the same
        # "current" refresh_token_id and both succeed (see rotate_refresh_token).
        # Mirrors the per-key lock pattern in auth.single_use_tokens.
        self._locks: dict[str, Lock] = {}
        self._locks_guard = Lock()

    def _lock_for(self, session_id: str) -> Lock:
        with self._locks_guard:
            lock = self._locks.get(session_id)
            if lock is None:
                lock = Lock()
                self._locks[session_id] = lock
            return lock

    def _forget_lock(self, session_id: str) -> None:
        with self._locks_guard:
            self._locks.pop(session_id, None)

    def create(
        self,
        *,
        user_id: str,
        expires_in: int = 86400,
        session_id: str | None = None,
        refresh_token_id: str | None = None,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuthSession:
        created = created_at or utc_now().isoformat()
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        expires = (created_dt + timedelta(seconds=int(expires_in))).isoformat()
        sid = session_id or str(uuid.uuid4())
        meta = {"auth_entity": "session", **(metadata or {})}
        session = AuthSession(
            session_id=sid,
            user_id=user_id,
            created_at=created,
            expires_at=expires,
            revoked=False,
            refresh_token_id=refresh_token_id,
            metadata=freeze_mapping(meta),
        )
        self._persistence.put(
            kind="metadata",
            entity_id=f"{_SESSION_PREFIX}{sid}",
            payload=session.to_dict(),
            refs={"auth_entity": "session", "user_id": user_id},
            created_at=created,
            allow_update=False,
        )
        return session

    def get(self, session_id: str) -> AuthSession | None:
        row = self._persistence.get("metadata", f"{_SESSION_PREFIX}{session_id}")
        if row is None:
            return None
        payload = row.get("payload") or {}
        return AuthSession(
            session_id=str(payload.get("session_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            created_at=str(payload.get("created_at") or ""),
            expires_at=str(payload.get("expires_at") or ""),
            revoked=bool(payload.get("revoked")),
            refresh_token_id=payload.get("refresh_token_id"),
            metadata=freeze_mapping(dict(payload.get("metadata") or {})),
            refresh_token_hash=payload.get("refresh_token_hash"),
            refresh_rotated_at=payload.get("refresh_rotated_at"),
        )

    def require_active(
        self, session_id: str, *, now: datetime | None = None
    ) -> AuthSession:
        session = self.get(session_id)
        if session is None:
            raise SessionError("session not found")
        if session.revoked:
            raise SessionError("session revoked")
        current = now or datetime.now(tz=timezone.utc)
        exp = datetime.fromisoformat(session.expires_at.replace("Z", "+00:00"))
        if exp <= current:
            raise SessionError("session expired")
        return session

    def revoke(self, session_id: str, *, updated_at: str | None = None) -> AuthSession:
        session = self.get(session_id)
        if session is None:
            raise SessionError("session not found")
        revoked = AuthSession(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            revoked=True,
            refresh_token_id=session.refresh_token_id,
            metadata=session.metadata,
            refresh_token_hash=session.refresh_token_hash,
            refresh_rotated_at=session.refresh_rotated_at,
        )
        self._write(revoked, updated_at=updated_at)
        return revoked

    def attach_refresh_material(
        self,
        session_id: str,
        *,
        token_id: str,
        token_hash: str,
        updated_at: str | None = None,
    ) -> AuthSession:
        """Record the hash of a freshly issued refresh token for a session.

        Called exactly once, immediately after initial issuance (login /
        enterprise session creation), since the raw refresh JWT does not
        exist yet at the point ``create()`` allocates the session row. No
        reuse check is performed here — that only applies to *rotation* of
        an already-active token via :meth:`rotate_refresh_token`.
        """
        session = self.get(session_id)
        if session is None:
            raise SessionError("session not found")
        updated = AuthSession(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            revoked=session.revoked,
            refresh_token_id=token_id,
            metadata=session.metadata,
            refresh_token_hash=token_hash,
            refresh_rotated_at=session.refresh_rotated_at,
        )
        self._write(updated, updated_at=updated_at)
        return updated

    def rotate_refresh_token(
        self,
        session_id: str,
        *,
        expected_token_id: str | None,
        expected_token_hash: str | None,
        new_token_id: str,
        new_token_hash: str,
        updated_at: str | None = None,
    ) -> AuthSession:
        """Atomically replace a session's active refresh-token identity.

        This is the single choke point for OAuth 2.0 BCP refresh-token
        rotation: the caller must present the token id/hash it believes is
        currently active, and the swap only takes effect if that matches
        what is actually stored — under a per-session lock so two
        concurrent callers can never both win the swap.

        Raises :class:`RefreshTokenReuseError` (and revokes the session,
        i.e. the entire refresh-token family) when the expected identity
        does not match — either because the presented refresh token was
        already rotated away and is now being replayed, or because a
        second concurrent request lost the race after the first already
        rotated it.
        """
        lock = self._lock_for(session_id)
        try:
            with lock:
                session = self.get(session_id)
                if session is None:
                    raise SessionError("session not found")
                if session.revoked:
                    raise SessionError("session revoked")
                mismatch = (
                    expected_token_id is not None
                    and session.refresh_token_id != expected_token_id
                ) or (
                    expected_token_hash is not None
                    and session.refresh_token_hash is not None
                    and session.refresh_token_hash != expected_token_hash
                )
                if mismatch:
                    revoked = AuthSession(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        created_at=session.created_at,
                        expires_at=session.expires_at,
                        revoked=True,
                        refresh_token_id=session.refresh_token_id,
                        metadata=session.metadata,
                        refresh_token_hash=session.refresh_token_hash,
                        refresh_rotated_at=session.refresh_rotated_at,
                    )
                    self._write(revoked, updated_at=updated_at)
                    raise RefreshTokenReuseError(
                        "Refresh token reuse detected; session revoked."
                    )
                rotated = AuthSession(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    created_at=session.created_at,
                    expires_at=session.expires_at,
                    revoked=False,
                    refresh_token_id=new_token_id,
                    metadata=session.metadata,
                    refresh_token_hash=new_token_hash,
                    refresh_rotated_at=updated_at or utc_now().isoformat(),
                )
                self._write(rotated, updated_at=updated_at)
                return rotated
        finally:
            self._forget_lock(session_id)

    def _write(self, session: AuthSession, *, updated_at: str | None = None) -> None:
        self._persistence.put(
            kind="metadata",
            entity_id=f"{_SESSION_PREFIX}{session.session_id}",
            payload=session.to_dict(),
            refs={"auth_entity": "session", "user_id": session.user_id},
            created_at=updated_at or utc_now().isoformat(),
            allow_update=True,
        )

    def list_for_user(self, user_id: str) -> list[AuthSession]:
        out: list[AuthSession] = []
        for entity_id in self._persistence.list_ids("metadata"):
            if not str(entity_id).startswith(_SESSION_PREFIX):
                continue
            sid = str(entity_id)[len(_SESSION_PREFIX) :]
            session = self.get(sid)
            if session and session.user_id == user_id:
                out.append(session)
        out.sort(key=lambda s: s.created_at)
        return out

    def list_sessions(self, user_id: str | None = None) -> list[AuthSession]:
        if user_id:
            return self.list_for_user(user_id)
        out: list[AuthSession] = []
        for entity_id in self._persistence.list_ids("metadata"):
            if not str(entity_id).startswith(_SESSION_PREFIX):
                continue
            sid = str(entity_id)[len(_SESSION_PREFIX) :]
            session = self.get(sid)
            if session:
                out.append(session)
        out.sort(key=lambda s: s.created_at)
        return out
