"""In-memory enterprise store — process-local foundation / test adapter."""

from __future__ import annotations

from threading import Lock
from typing import Any

from enterprise.models import (
    ApiKeyRecord,
    AuditRecord,
    Invitation,
    License,
    Organization,
    OrgMember,
    OrgSession,
    Team,
)

__all__ = ["InMemoryEnterpriseStore"]


class InMemoryEnterpriseStore:
    """Thread-safe in-memory persistence for enterprise domain objects.

    Implements ``EnterpriseStorePort``. Prefer ``DatabaseEnterpriseStore``
    for production durability (EPIC-016).
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self.organizations: dict[str, Organization] = {}
        self.teams: dict[str, Team] = {}
        self.members: dict[str, OrgMember] = {}  # key: org_id:user_id
        self.invitations: dict[str, Invitation] = {}
        self.licenses: dict[str, License] = {}  # key: org_id (one active)
        self.audit: list[AuditRecord] = []
        self.api_keys: dict[str, ApiKeyRecord] = {}
        self.sessions: dict[str, OrgSession] = {}
        self.custom_roles: dict[str, dict[str, Any]] = {}  # org_id:role_id
        self.usage_counters: dict[str, dict[str, int]] = {}

    @staticmethod
    def member_key(org_id: str, user_id: str) -> str:
        return f"{org_id}:{user_id}"

    def clear(self) -> None:
        with self._lock:
            self.organizations.clear()
            self.teams.clear()
            self.members.clear()
            self.invitations.clear()
            self.licenses.clear()
            self.audit.clear()
            self.api_keys.clear()
            self.sessions.clear()
            self.custom_roles.clear()
            self.usage_counters.clear()

    def ensure_fresh(self) -> None:
        """No-op — in-memory adapter has no shared backend."""

    def flush(self) -> None:
        """No-op — in-memory adapter has no durable backend."""
