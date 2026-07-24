"""User / principal models and permission helpers (in-memory only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from security_platform.security.exceptions import SecurityError
from security_platform.security.permissions import Permission, assert_permission
from security_platform.security.roles import ROLE_PERMISSIONS, Role, assert_role

__all__ = [
    "PermissionManager",
    "SecurityContext",
    "UserPrincipal",
    "UserRecord",
    "UserStore",
]


@dataclass(frozen=True, slots=True)
class UserRecord:
    """In-memory user record — not a database entity."""

    user_id: str
    username: str
    role: Role
    active: bool = True
    display_name: str | None = None
    extra_permissions: tuple[Permission, ...] = ()

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            msg = "user_id must not be empty"
            raise SecurityError(msg)
        if not self.username.strip():
            msg = "username must not be empty"
            raise SecurityError(msg)
        object.__setattr__(self, "role", assert_role(self.role))
        object.__setattr__(
            self,
            "extra_permissions",
            tuple(assert_permission(p) for p in self.extra_permissions),
        )


@dataclass(frozen=True, slots=True)
class UserPrincipal:
    """Authenticated principal identity."""

    subject: str
    role: Role
    permissions: frozenset[Permission]
    auth_method: str
    username: str | None = None
    api_key_id: str | None = None

    def has_permission(self, permission: Permission | str) -> bool:
        return assert_permission(permission) in self.permissions


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Request-scoped security context attached by middleware."""

    principal: UserPrincipal
    authenticated: bool
    guest: bool
    request_id: str | None = None
    issued_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def require(self, permission: Permission | str) -> None:
        from security_platform.security.exceptions import AuthorizationError

        perm = assert_permission(permission)
        if not self.principal.has_permission(perm):
            msg = (
                f"permission denied: {perm.value} "
                f"(role={self.principal.role.value})"
            )
            raise AuthorizationError(msg)


class UserStore:
    """Process-local user registry — no durable database."""

    def __init__(self) -> None:
        self._by_id: dict[str, UserRecord] = {}
        self._by_username: dict[str, str] = {}

    def add(self, user: UserRecord, *, replace: bool = False) -> UserRecord:
        key = user.user_id.strip().lower()
        uname = user.username.strip().lower()
        if key in self._by_id and not replace:
            msg = f"duplicate user_id: {user.user_id!r}"
            raise SecurityError(msg)
        if uname in self._by_username and self._by_username[uname] != key:
            if not replace:
                msg = f"duplicate username: {user.username!r}"
                raise SecurityError(msg)
        self._by_id[key] = user
        self._by_username[uname] = key
        return user

    def get(self, user_id: str) -> UserRecord:
        key = user_id.strip().lower()
        if key not in self._by_id:
            msg = f"unknown user: {user_id!r}"
            raise SecurityError(msg)
        return self._by_id[key]

    def get_by_username(self, username: str) -> UserRecord:
        key = self._by_username.get(username.strip().lower())
        if key is None:
            msg = f"unknown username: {username!r}"
            raise SecurityError(msg)
        return self._by_id[key]

    def list_users(self) -> tuple[UserRecord, ...]:
        return tuple(self._by_id[k] for k in sorted(self._by_id))

    def __len__(self) -> int:
        return len(self._by_id)


class PermissionManager:
    """Aggregates role + extra permissions for a user / principal."""

    def permissions_for_user(self, user: UserRecord) -> frozenset[Permission]:
        base = set(ROLE_PERMISSIONS[user.role])
        base.update(user.extra_permissions)
        return frozenset(base)

    def permissions_for_role(self, role: Role | str) -> frozenset[Permission]:
        return ROLE_PERMISSIONS[assert_role(role)]
