"""Admin console models (EPIC-A010) — read-only operational views."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

__all__ = [
    "ADMIN_SCHEMA_VERSION",
    "ADMIN_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "AdminDashboard",
    "freeze_mapping",
    "utc_now",
]

ADMIN_SCHEMA_VERSION = "1.0.0"
ADMIN_SERVICE_VERSION = "1.0.0"
UNAVAILABLE_MESSAGE = "Data unavailable."


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return MappingProxyType({str(k): _freeze(v) for k, v in obj.items()})
        if isinstance(obj, list):
            return tuple(_freeze(v) for v in obj)
        if isinstance(obj, tuple):
            return tuple(_freeze(v) for v in obj)
        return obj

    return _freeze(value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class AdminDashboard:
    generated_at: str
    users_count: int
    sessions_count: int
    active_sessions_count: int
    audit_records_count: int
    workflow_records_count: int
    research_refs_count: int
    roles_count: int
    permissions_count: int
    health_status: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "users_count": self.users_count,
            "sessions_count": self.sessions_count,
            "active_sessions_count": self.active_sessions_count,
            "audit_records_count": self.audit_records_count,
            "workflow_records_count": self.workflow_records_count,
            "research_refs_count": self.research_refs_count,
            "roles_count": self.roles_count,
            "permissions_count": self.permissions_count,
            "health_status": self.health_status,
            "metadata": dict(self.metadata),
        }
