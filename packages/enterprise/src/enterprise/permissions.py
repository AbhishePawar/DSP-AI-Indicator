"""Enterprise permission catalogue — permission-key based, never role-hardcoded in UI."""

from __future__ import annotations

from enterprise.exceptions import ValidationError

__all__ = [
    "ENTERPRISE_PERMISSIONS",
    "ROLE_PERMISSIONS",
    "BUILTIN_ENTERPRISE_ROLES",
    "assert_permission",
    "permissions_for_role",
    "has_permission",
]

ENTERPRISE_PERMISSIONS = (
    # Org
    "org.view",
    "org.manage",
    "org.branding",
    "org.settings",
    # Members / teams
    "members.view",
    "members.invite",
    "members.manage",
    "teams.view",
    "teams.manage",
    # Roles
    "roles.view",
    "roles.manage",
    # Licensing / billing / portal
    "license.view",
    "license.manage",
    "billing.view",
    "usage.view",
    "api_keys.view",
    "api_keys.manage",
    "sessions.view",
    "sessions.revoke",
    # Audit / ops / admin
    "audit.view",
    "audit.export",
    "ops.view",
    "ops.manage",
    "admin.view",
    "admin.manage",
    # Collaboration architecture (ports only)
    "collaboration.view",
    "collaboration.comment",
    "collaboration.approve",
)

BUILTIN_ENTERPRISE_ROLES = (
    "owner",
    "administrator",
    "research_director",
    "senior_analyst",
    "analyst",
    "portfolio_manager",
    "investment_committee",
    "viewer",
    "guest",
)

_ALL = ENTERPRISE_PERMISSIONS

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "owner": _ALL,
    "administrator": (
        "org.view",
        "org.manage",
        "org.branding",
        "org.settings",
        "members.view",
        "members.invite",
        "members.manage",
        "teams.view",
        "teams.manage",
        "roles.view",
        "roles.manage",
        "license.view",
        "license.manage",
        "billing.view",
        "usage.view",
        "api_keys.view",
        "api_keys.manage",
        "sessions.view",
        "sessions.revoke",
        "audit.view",
        "audit.export",
        "ops.view",
        "admin.view",
        "collaboration.view",
        "collaboration.comment",
        "collaboration.approve",
    ),
    "research_director": (
        "org.view",
        "members.view",
        "members.invite",
        "teams.view",
        "teams.manage",
        "roles.view",
        "license.view",
        "usage.view",
        "api_keys.view",
        "sessions.view",
        "audit.view",
        "collaboration.view",
        "collaboration.comment",
        "collaboration.approve",
    ),
    "senior_analyst": (
        "org.view",
        "members.view",
        "teams.view",
        "license.view",
        "usage.view",
        "sessions.view",
        "audit.view",
        "collaboration.view",
        "collaboration.comment",
        "collaboration.approve",
    ),
    "analyst": (
        "org.view",
        "members.view",
        "teams.view",
        "license.view",
        "usage.view",
        "collaboration.view",
        "collaboration.comment",
    ),
    "portfolio_manager": (
        "org.view",
        "members.view",
        "teams.view",
        "license.view",
        "usage.view",
        "audit.view",
        "collaboration.view",
        "collaboration.comment",
        "collaboration.approve",
    ),
    "investment_committee": (
        "org.view",
        "members.view",
        "teams.view",
        "license.view",
        "audit.view",
        "collaboration.view",
        "collaboration.approve",
    ),
    "viewer": (
        "org.view",
        "members.view",
        "teams.view",
        "license.view",
        "usage.view",
        "collaboration.view",
    ),
    "guest": ("org.view", "collaboration.view"),
}


def assert_permission(permission: str) -> str:
    p = str(permission or "").strip().lower()
    if p not in ENTERPRISE_PERMISSIONS:
        raise ValidationError(f"unknown permission {permission!r}")
    return p


def permissions_for_role(role_id: str) -> tuple[str, ...]:
    rid = str(role_id or "").strip().lower()
    if rid not in ROLE_PERMISSIONS:
        raise ValidationError(f"unknown role {role_id!r}")
    return ROLE_PERMISSIONS[rid]


def has_permission(granted: tuple[str, ...] | list[str], permission: str) -> bool:
    p = assert_permission(permission)
    return p in set(granted)
