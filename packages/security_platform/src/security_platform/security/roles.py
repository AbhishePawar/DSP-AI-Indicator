"""Role taxonomy (K1.2) — additive only after freeze."""

from __future__ import annotations

from enum import StrEnum

from security_platform.security.exceptions import SecurityError
from security_platform.security.permissions import Permission

__all__ = [
    "ROLES",
    "ROLE_PERMISSIONS",
    "Role",
    "RoleManager",
    "assert_role",
]


class Role(StrEnum):
    """Frozen platform roles."""

    ADMIN = "ADMIN"
    ADVISOR = "ADVISOR"
    CLIENT = "CLIENT"
    RESEARCHER = "RESEARCHER"
    API = "API"
    GUEST = "GUEST"


ROLES: frozenset[str] = frozenset(r.value for r in Role)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.ADVISOR: frozenset(
        {
            Permission.ANALYZE_COMPANY,
            Permission.COMPARE_COMPANIES,
            Permission.RUN_WORKFLOW,
            Permission.ASK_COPILOT,
            Permission.VIEW_REPORTS,
        }
    ),
    Role.CLIENT: frozenset(
        {
            Permission.ASK_COPILOT,
            Permission.VIEW_REPORTS,
        }
    ),
    Role.RESEARCHER: frozenset(
        {
            Permission.ANALYZE_COMPANY,
            Permission.COMPARE_COMPANIES,
            Permission.ASK_COPILOT,
            Permission.VIEW_REPORTS,
        }
    ),
    Role.API: frozenset(
        {
            Permission.ANALYZE_COMPANY,
            Permission.COMPARE_COMPANIES,
            Permission.RUN_WORKFLOW,
            Permission.ASK_COPILOT,
            Permission.VIEW_REPORTS,
        }
    ),
    Role.GUEST: frozenset(
        {
            Permission.VIEW_REPORTS,
        }
    ),
}


def assert_role(value: str | Role) -> Role:
    """Return a validated ``Role``."""
    if isinstance(value, Role):
        return value
    cleaned = str(value).strip().upper()
    try:
        return Role(cleaned)
    except ValueError as exc:
        msg = f"unknown role: {value!r}"
        raise SecurityError(msg) from exc


class RoleManager:
    """Resolves role → permission sets — no business logic."""

    def permissions_for(self, role: Role | str) -> frozenset[Permission]:
        resolved = assert_role(role)
        return ROLE_PERMISSIONS[resolved]

    def has_permission(
        self, role: Role | str, permission: Permission | str
    ) -> bool:
        from security_platform.security.permissions import assert_permission

        perm = assert_permission(permission)
        return perm in self.permissions_for(role)

    def list_roles(self) -> tuple[Role, ...]:
        return tuple(Role)
