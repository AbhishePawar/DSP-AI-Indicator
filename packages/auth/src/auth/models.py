"""Auth / RBAC models (EPIC-A009)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

__all__ = [
    "AUTH_SCHEMA_VERSION",
    "AUTH_SERVICE_VERSION",
    "BUILTIN_ROLES",
    "PERMISSIONS",
    "ROLE_PERMISSIONS",
    "UNAVAILABLE_MESSAGE",
    "AuthSession",
    "AuthTokenPair",
    "AuthUser",
    "RoleDefinition",
    "freeze_mapping",
    "utc_now",
]

AUTH_SCHEMA_VERSION = "1.0.0"
AUTH_SERVICE_VERSION = "1.0.0"
UNAVAILABLE_MESSAGE = "Data unavailable."

PERMISSIONS = (
    "read_research",
    "create_research",
    "edit_drafts",
    "submit_workflow",
    "approve_workflow",
    "reject_workflow",
    "publish_research",
    "view_audit",
    "manage_users",
    "manage_roles",
    "configure_platform",
)

BUILTIN_ROLES = (
    "super_admin",
    "administrator",
    "research_analyst",
    "senior_analyst",
    "reviewer",
    "compliance_officer",
    "investment_committee",
    "portfolio_manager",
    "read_only",
    # Enterprise product roles (map to permission-based RBAC; UI must not hardcode)
    "viewer",
    "enterprise_client",
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "super_admin": PERMISSIONS,
    "administrator": PERMISSIONS,
    "research_analyst": (
        "read_research",
        "create_research",
        "edit_drafts",
        "submit_workflow",
    ),
    "senior_analyst": (
        "read_research",
        "create_research",
        "edit_drafts",
        "submit_workflow",
        "approve_workflow",
        "view_audit",
    ),
    "reviewer": (
        "read_research",
        "approve_workflow",
        "reject_workflow",
        "view_audit",
    ),
    "compliance_officer": (
        "read_research",
        "approve_workflow",
        "reject_workflow",
        "view_audit",
        "manage_roles",
    ),
    "investment_committee": (
        "read_research",
        "approve_workflow",
        "reject_workflow",
        "publish_research",
        "view_audit",
    ),
    "portfolio_manager": (
        "read_research",
        "view_audit",
        "submit_workflow",
    ),
    "read_only": ("read_research",),
    "viewer": ("read_research",),  # UI alias: Read Only Viewer → prefer read_only
    "enterprise_client": ("read_research",),
}


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
class RoleDefinition:
    role_id: str
    name: str
    permissions: tuple[str, ...]
    configurable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "permissions": list(self.permissions),
            "configurable": self.configurable,
        }


@dataclass(frozen=True, slots=True)
class AuthUser:
    user_id: str
    username: str
    email: str
    display_name: str
    password_hash: str
    status: str  # active | disabled | locked | pending_verification | pending_approval
    created_at: str
    updated_at: str
    last_login: str | None = None
    roles: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_hash: bool = False) -> dict[str, Any]:
        row = {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "roles": list(self.roles),
            "metadata": dict(self.metadata),
        }
        if include_hash:
            row["password_hash"] = self.password_hash
        return row


@dataclass(frozen=True, slots=True)
class AuthSession:
    session_id: str
    user_id: str
    created_at: str
    expires_at: str
    revoked: bool = False
    refresh_token_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    # Refresh-token-rotation (EPIC-A009 BCP hardening): SHA-256 digest of the
    # *currently active* raw refresh JWT. Never the raw token itself — see
    # ``auth.authentication._hash_refresh_token``. Compared on every refresh
    # attempt in addition to ``refresh_token_id`` as defense in depth; any
    # mismatch on an active session means the presented token was already
    # rotated away (replay) or forged, and triggers family-wide revocation.
    refresh_token_hash: str | None = None
    # ISO-8601 timestamp of the most recent successful rotation, or None for
    # a session whose refresh token has never been rotated (freshly issued).
    refresh_rotated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Full internal representation, including the refresh-token digest.

        Used for persistence round-tripping only. API responses and other
        client-facing surfaces should use :meth:`to_public_dict` instead so
        the at-rest security digest is never echoed back over the wire.
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "refresh_token_id": self.refresh_token_id,
            "metadata": dict(self.metadata),
            "refresh_token_hash": self.refresh_token_hash,
            "refresh_rotated_at": self.refresh_rotated_at,
        }

    def to_public_dict(self) -> dict[str, Any]:
        """Client/API-facing view — omits the internal refresh-token digest."""
        row = self.to_dict()
        row.pop("refresh_token_hash", None)
        return row


@dataclass(frozen=True, slots=True)
class AuthTokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "session_id": self.session_id,
        }
