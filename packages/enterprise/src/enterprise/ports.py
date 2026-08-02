"""Enterprise persistence port (EPIC-016) — Clean Architecture boundary."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

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

__all__ = ["EnterpriseStorePort"]


@runtime_checkable
class EnterpriseStorePort(Protocol):
    """Durable or in-memory enterprise persistence surface.

    Implementations must expose the working collections used by
    ``EnterpriseService``. Tests use ``InMemoryEnterpriseStore``;
    production uses ``DatabaseEnterpriseStore`` over ``DatabasePort``.
    """

    organizations: dict[str, Organization]
    teams: dict[str, Team]
    members: dict[str, OrgMember]
    invitations: dict[str, Invitation]
    licenses: dict[str, License]
    audit: list[AuditRecord]
    api_keys: dict[str, ApiKeyRecord]
    sessions: dict[str, OrgSession]
    custom_roles: dict[str, dict[str, Any]]
    usage_counters: dict[str, dict[str, int]]

    @staticmethod
    def member_key(org_id: str, user_id: str) -> str: ...

    def clear(self) -> None: ...

    def flush(self) -> None:
        """Persist working set when backed by durable storage (no-op in memory)."""
