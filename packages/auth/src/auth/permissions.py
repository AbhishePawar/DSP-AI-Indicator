"""Permission catalogue (EPIC-A009)."""

from __future__ import annotations

from auth.exceptions import ValidationError
from auth.models import PERMISSIONS

__all__ = ["assert_permission", "list_permissions"]


def list_permissions() -> list[str]:
    return list(PERMISSIONS)


def assert_permission(permission: str) -> str:
    p = str(permission or "").strip().lower()
    if p not in PERMISSIONS:
        raise ValidationError(f"unknown permission {permission!r}")
    return p
