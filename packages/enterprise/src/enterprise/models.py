"""Enterprise domain models (EPS-002).

Honest empty states — never fabricate commercial or operational data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

__all__ = [
    "ENTERPRISE_SCHEMA_VERSION",
    "ENTERPRISE_SERVICE_VERSION",
    "LICENSE_TIERS",
    "MEMBER_STATUSES",
    "ORG_STATUSES",
    "TEAM_KINDS",
    "UNAVAILABLE_MESSAGES",
    "ApiKeyRecord",
    "AuditRecord",
    "Invitation",
    "License",
    "Organization",
    "OrgMember",
    "OrgSession",
    "Team",
    "UsageSnapshot",
    "freeze_mapping",
    "utc_now",
]

ENTERPRISE_SCHEMA_VERSION = "1.1.0"
ENTERPRISE_SERVICE_VERSION = "0.2.0"

UNAVAILABLE_MESSAGES = MappingProxyType(
    {
        "organizations": "No organizations available.",
        "license": "No license assigned.",
        "billing": "Billing unavailable.",
        "billing_provider": "Billing provider unavailable.",
        "audit": "No audit records.",
        "api_keys": "No API keys.",
        "sessions": "No active sessions.",
        "usage": "Usage analytics unavailable.",
        "invoices": "No invoices available.",
        "teams": "No teams available.",
        "members": "No members available.",
        "sso": "SSO provider unavailable.",
        "oidc": "OIDC client not configured.",
    }
)

ORG_STATUSES = ("active", "suspended", "pending", "archived")
MEMBER_STATUSES = ("active", "invited", "disabled", "removed")
TEAM_KINDS = (
    "department",
    "research",
    "investment",
    "analyst",
    "read_only",
    "committee",
    "custom",
)
LICENSE_TIERS = (
    "trial",
    "research",
    "professional",
    "institutional",
    "enterprise",
)


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
class Organization:
    org_id: str
    name: str
    slug: str
    status: str
    owner_user_id: str
    created_at: str
    updated_at: str
    branding: Mapping[str, Any] = field(default_factory=dict)
    preferences: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    seat_limit: int | None = None
    parent_org_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "name": self.name,
            "slug": self.slug,
            "status": self.status,
            "owner_user_id": self.owner_user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "branding": dict(self.branding),
            "preferences": dict(self.preferences),
            "metadata": dict(self.metadata),
            "seat_limit": self.seat_limit,
            "parent_org_id": self.parent_org_id,
        }


@dataclass(frozen=True, slots=True)
class Team:
    team_id: str
    org_id: str
    name: str
    kind: str
    created_at: str
    updated_at: str
    parent_team_id: str | None = None
    member_user_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "org_id": self.org_id,
            "name": self.name,
            "kind": self.kind,
            "parent_team_id": self.parent_team_id,
            "member_user_ids": list(self.member_user_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class OrgMember:
    org_id: str
    user_id: str
    role_id: str
    status: str
    joined_at: str
    permissions: tuple[str, ...] = ()
    team_ids: tuple[str, ...] = ()
    display_name: str | None = None
    email: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "status": self.status,
            "joined_at": self.joined_at,
            "permissions": list(self.permissions),
            "team_ids": list(self.team_ids),
            "display_name": self.display_name,
            "email": self.email,
        }


@dataclass(frozen=True, slots=True)
class Invitation:
    invitation_id: str
    org_id: str
    email: str
    role_id: str
    status: str
    created_at: str
    expires_at: str | None = None
    invited_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "invitation_id": self.invitation_id,
            "org_id": self.org_id,
            "email": self.email,
            "role_id": self.role_id,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "invited_by": self.invited_by,
        }


@dataclass(frozen=True, slots=True)
class License:
    license_id: str
    org_id: str
    tier: str
    status: str
    seats: int
    created_at: str
    expires_at: str | None = None
    usage_limits: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "license_id": self.license_id,
            "org_id": self.org_id,
            "tier": self.tier,
            "status": self.status,
            "seats": self.seats,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "usage_limits": dict(self.usage_limits),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuditRecord:
    event_id: str
    org_id: str | None
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    created_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    immutable: bool = True
    before_state: Mapping[str, Any] | None = None
    after_state: Mapping[str, Any] | None = None
    ip_address: str | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "org_id": self.org_id,
            "actor_user_id": self.actor_user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
            "immutable": True,
            "before": dict(self.before_state) if self.before_state is not None else None,
            "after": dict(self.after_state) if self.after_state is not None else None,
            "ip_address": self.ip_address,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    key_id: str
    org_id: str
    name: str
    scopes: tuple[str, ...]
    status: str
    created_at: str
    secret_hash: str
    expires_at: str | None = None
    created_by: str | None = None
    last_used_at: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        """Never expose secret_hash to clients."""
        return {
            "key_id": self.key_id,
            "org_id": self.org_id,
            "name": self.name,
            "scopes": list(self.scopes),
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "created_by": self.created_by,
            "last_used_at": self.last_used_at,
        }


@dataclass(frozen=True, slots=True)
class OrgSession:
    session_id: str
    org_id: str
    user_id: str
    device_label: str
    created_at: str
    last_seen_at: str
    status: str
    ip_hint: str | None = None
    user_agent_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "device_label": self.device_label,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "status": self.status,
            "ip_hint": self.ip_hint,
            "user_agent_hint": self.user_agent_hint,
        }


@dataclass(frozen=True, slots=True)
class UsageSnapshot:
    org_id: str
    generated_at: str
    dau: int | None
    research_count: int | None
    export_count: int | None
    comparison_count: int | None
    api_request_count: int | None
    storage_bytes: int | None
    available: bool
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if not self.available:
            return {
                "org_id": self.org_id,
                "generated_at": self.generated_at,
                "available": False,
                "message": self.message or UNAVAILABLE_MESSAGES["usage"],
                "dau": None,
                "research_count": None,
                "export_count": None,
                "comparison_count": None,
                "api_request_count": None,
                "storage_bytes": None,
            }
        return {
            "org_id": self.org_id,
            "generated_at": self.generated_at,
            "available": True,
            "message": None,
            "dau": self.dau if self.dau is not None else 0,
            "research_count": self.research_count if self.research_count is not None else 0,
            "export_count": self.export_count if self.export_count is not None else 0,
            "comparison_count": (
                self.comparison_count if self.comparison_count is not None else 0
            ),
            "api_request_count": (
                self.api_request_count if self.api_request_count is not None else 0
            ),
            "storage_bytes": self.storage_bytes if self.storage_bytes is not None else 0,
        }
