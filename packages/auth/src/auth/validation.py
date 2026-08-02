"""Identity validation (EPIC-A009)."""

from __future__ import annotations

import re

from auth.exceptions import ValidationError
from auth.roles import get_role_registry

__all__ = [
    "assert_email",
    "assert_roles",
    "assert_status",
    "assert_username",
]

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,64}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def assert_username(username: str) -> str:
    value = str(username or "").strip()
    if not _USERNAME_RE.match(value):
        raise ValidationError("invalid username")
    return value


def assert_email(email: str) -> str:
    value = str(email or "").strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValidationError("invalid email")
    return value


def assert_status(status: str) -> str:
    s = str(status or "active").strip().lower()
    if s not in {"active", "disabled"}:
        raise ValidationError(f"invalid status {status!r}")
    return s


def assert_roles(roles: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    cleaned = tuple(sorted({str(r).strip().lower() for r in (roles or []) if str(r).strip()}))
    registry = get_role_registry()
    for role in cleaned:
        registry.require(role)
    return cleaned
