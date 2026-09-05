"""Session management (EPIC-A009)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from auth.exceptions import RefreshTokenReuseError, SessionError
from auth.models import AuthSession, freeze_mapping, utc_now

__all__ = ["SessionManager"]

_SESSION_PREFIX = "auth-session-"


class SessionManager:
    def __init__(self, persistence_service: Any) -> None:
        self._persistence = persistence_service

    def _entity_id(self, session_id: str) -> str:
        return f"{_SESSION_PREFIX}{session_id}"

    def _from_payload(self, payload: Mapping[str, Any]) -> AuthSession:
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

    def _from_row(self, row: Mapping[str, Any]) -> AuthSession:
        return self._from_payload(row.get("payload") or {})

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
            entity_id=self._entity_id(sid),
            payload=session.to_dict(),
            refs={"auth_entity": "session", "user_id": user_id},
            created_at=created,
            allow_update=False,
        )
        return session

    def get(self, session_id: str) -> AuthSession | None:
        row = self._persistence.get("metadata", self._entity_id(session_id))
        if row is None:
            return None
        return self._from_row(row)

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
        now = updated_at or utc_now().isoformat()
        stored = self._persistence.atomic_merge_payload(
            "metadata",
            self._entity_id(session_id),
            fields={"revoked": True},
            updated_at=now,
            match={"revoked": False},
        )
        if stored is not None:
            return self._from_row(stored)
        session = self.get(session_id)
        if session is None:
            raise SessionError("session not found")
        return session

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
        now = updated_at or utc_now().isoformat()
        stored = self._persistence.atomic_merge_payload(
            "metadata",
            self._entity_id(session_id),
            fields={"refresh_token_id": token_id, "refresh_token_hash": token_hash},
            updated_at=now,
            match={"revoked": False},
        )
        if stored is None:
            raise SessionError("session not found")
        return self._from_row(stored)

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
        what is actually stored — via A008 ``atomic_merge_payload`` so two
        Cloud Run instances cannot both win the swap.

        Raises :class:`RefreshTokenReuseError` (and revokes the session,
        i.e. the entire refresh-token family) when the expected identity
        does not match — either because the presented refresh token was
        already rotated away and is now being replayed, or because a
        second concurrent request lost the race after the first already
        rotated it.
        """
        now = updated_at or utc_now().isoformat()
        entity_id = self._entity_id(session_id)
        match: dict[str, Any] = {"revoked": False}
        if expected_token_id is not None:
            match["refresh_token_id"] = expected_token_id
        if expected_token_hash is not None:
            match["refresh_token_hash"] = expected_token_hash
        stored = self._persistence.atomic_merge_payload(
            "metadata",
            entity_id,
            fields={
                "refresh_token_id": new_token_id,
                "refresh_token_hash": new_token_hash,
                "refresh_rotated_at": now,
            },
            updated_at=now,
            match=match,
        )
        if stored is not None:
            return self._from_row(stored)
        session = self.get(session_id)
        if session is None:
            raise SessionError("session not found")
        if session.revoked:
            raise SessionError("session revoked")
        self._persistence.atomic_merge_payload(
            "metadata",
            entity_id,
            fields={"revoked": True},
            updated_at=now,
            match={"revoked": False},
        )
        raise RefreshTokenReuseError("Refresh token reuse detected; session revoked.")

    def _write(self, session: AuthSession, *, updated_at: str | None = None) -> None:
        self._persistence.put(
            kind="metadata",
            entity_id=self._entity_id(session.session_id),
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
