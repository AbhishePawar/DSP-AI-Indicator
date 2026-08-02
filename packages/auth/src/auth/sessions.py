"""Session management (EPIC-A009)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from auth.exceptions import SessionError
from auth.models import AuthSession, freeze_mapping, utc_now

__all__ = ["SessionManager"]

_SESSION_PREFIX = "auth-session-"


class SessionManager:
    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service

    def create(
        self,
        *,
        user_id: str,
        expires_in: int = 86400,
        session_id: str | None = None,
        refresh_token_id: str | None = None,
        created_at: str | None = None,
    ) -> AuthSession:
        created = created_at or utc_now().isoformat()
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        expires = (created_dt + timedelta(seconds=int(expires_in))).isoformat()
        sid = session_id or str(uuid.uuid4())
        session = AuthSession(
            session_id=sid,
            user_id=user_id,
            created_at=created,
            expires_at=expires,
            revoked=False,
            refresh_token_id=refresh_token_id,
            metadata=freeze_mapping({"auth_entity": "session"}),
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
        )
        self._persistence.put(
            kind="metadata",
            entity_id=f"{_SESSION_PREFIX}{session_id}",
            payload=revoked.to_dict(),
            refs={"auth_entity": "session", "user_id": session.user_id},
            created_at=updated_at or utc_now().isoformat(),
            allow_update=True,
        )
        return revoked

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
