"""Authorization evaluation (EPIC-A009)."""

from __future__ import annotations

from auth.exceptions import AuthorizationError
from auth.models import AuthUser
from auth.permissions import assert_permission
from auth.roles import RoleRegistry, get_role_registry

__all__ = ["AuthorizationService"]


class AuthorizationService:
    def __init__(self, roles: RoleRegistry | None = None) -> None:
        self._roles = roles or get_role_registry()

    def permissions_for_user(self, user: AuthUser) -> frozenset[str]:
        return self._roles.permissions_for(user.roles)

    def has_permission(self, user: AuthUser, permission: str) -> bool:
        perm = assert_permission(permission)
        return perm in self.permissions_for_user(user)

    def require_permission(self, user: AuthUser, permission: str) -> None:
        if not self.has_permission(user, permission):
            raise AuthorizationError(
                f"user {user.username!r} missing permission {permission!r}"
            )

    def evaluate(self, user: AuthUser, permission: str) -> dict[str, object]:
        allowed = self.has_permission(user, permission)
        return {
            "user_id": user.user_id,
            "permission": assert_permission(permission),
            "allowed": allowed,
            "roles": list(user.roles),
            "permissions": sorted(self.permissions_for_user(user)),
        }
