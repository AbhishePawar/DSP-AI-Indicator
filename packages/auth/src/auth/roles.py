"""Role registry (EPIC-A009)."""

from __future__ import annotations

from auth.exceptions import ValidationError
from auth.models import BUILTIN_ROLES, ROLE_PERMISSIONS, RoleDefinition
from auth.permissions import assert_permission

__all__ = ["RoleRegistry", "builtin_roles", "get_role_registry"]


def builtin_roles() -> tuple[RoleDefinition, ...]:
    return tuple(
        RoleDefinition(
            role_id=role,
            name=role.replace("_", " ").title(),
            permissions=ROLE_PERMISSIONS[role],
            configurable=True,
        )
        for role in BUILTIN_ROLES
    )


class RoleRegistry:
    def __init__(self) -> None:
        self._roles: dict[str, RoleDefinition] = {
            r.role_id: r for r in builtin_roles()
        }

    def list_roles(self) -> list[dict[str, object]]:
        return [self._roles[k].to_dict() for k in sorted(self._roles.keys())]

    def get(self, role_id: str) -> RoleDefinition | None:
        return self._roles.get(str(role_id).strip().lower())

    def require(self, role_id: str) -> RoleDefinition:
        role = self.get(role_id)
        if role is None:
            raise ValidationError(f"unknown role {role_id!r}")
        return role

    def upsert(
        self,
        role_id: str,
        *,
        name: str | None = None,
        permissions: list[str] | None = None,
    ) -> RoleDefinition:
        rid = str(role_id).strip().lower()
        if not rid:
            raise ValidationError("role_id is required")
        perms = tuple(
            assert_permission(p) for p in sorted(set(permissions or []))
        )
        if rid in self._roles and not self._roles[rid].configurable:
            raise ValidationError(f"role {rid!r} is not configurable")
        existing = self._roles.get(rid)
        role = RoleDefinition(
            role_id=rid,
            name=name or (existing.name if existing else rid),
            permissions=perms or (existing.permissions if existing else ()),
            configurable=True,
        )
        self._roles[rid] = role
        return role

    def permissions_for(self, roles: list[str] | tuple[str, ...]) -> frozenset[str]:
        out: set[str] = set()
        for role_id in roles:
            role = self.require(role_id)
            out.update(role.permissions)
        return frozenset(out)


_REG: RoleRegistry | None = None


def get_role_registry() -> RoleRegistry:
    global _REG
    if _REG is None:
        _REG = RoleRegistry()
    return _REG


def reset_role_registry_for_tests(registry: RoleRegistry | None = None) -> None:
    global _REG
    _REG = registry
