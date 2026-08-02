"""Identity admin helpers — wraps A009 auth (no auth package changes)."""

from __future__ import annotations

from typing import Any

__all__ = ["IdentityAdmin"]


class IdentityAdmin:
    """User / role / permission / session views via AuthService."""

    def __init__(self, auth_service: Any) -> None:
        self._auth = auth_service

    def list_users(self) -> list[dict[str, Any]]:
        return sorted(self._auth.list_users(), key=lambda u: u.get("username") or "")

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._auth.get_user(user_id)

    def create_user(self, **kwargs: Any) -> dict[str, Any]:
        return self._auth.create_user(**kwargs)

    def set_user_roles(self, user_id: str, roles: list[str]) -> dict[str, Any]:
        return self._auth.set_user_roles(user_id, roles)

    def list_roles(self) -> list[dict[str, Any]]:
        return sorted(self._auth.list_roles(), key=lambda r: r.get("role_id") or "")

    def upsert_role(self, **kwargs: Any) -> dict[str, Any]:
        return self._auth.upsert_role(**kwargs)

    def list_permissions(self) -> list[str]:
        return list(self._auth.list_permissions())

    def list_sessions(self, *, user_id: str | None = None) -> list[dict[str, Any]]:
        sessions = self._auth.sessions
        if user_id:
            rows = [s.to_dict() for s in sessions.list_for_user(user_id)]
        else:
            rows = []
            persistence = self._auth.persistence
            for entity_id in persistence.list_ids("metadata"):
                if not str(entity_id).startswith("auth-session-"):
                    continue
                sid = str(entity_id)[len("auth-session-") :]
                session = sessions.get(sid)
                if session is not None:
                    rows.append(session.to_dict())
        rows.sort(key=lambda s: (s.get("created_at") or "", s.get("session_id") or ""))
        return rows
