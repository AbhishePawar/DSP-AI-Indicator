"""Permission taxonomy (K1.2)."""

from __future__ import annotations

from enum import StrEnum

from security_platform.security.exceptions import SecurityError

__all__ = [
    "PERMISSIONS",
    "Permission",
    "assert_permission",
]


class Permission(StrEnum):
    """Frozen API capability permissions."""

    ANALYZE_COMPANY = "AnalyzeCompany"
    COMPARE_COMPANIES = "CompareCompanies"
    RUN_WORKFLOW = "RunWorkflow"
    ASK_COPILOT = "AskCopilot"
    VIEW_REPORTS = "ViewReports"
    MANAGE_USERS = "ManageUsers"
    MANAGE_PLATFORM = "ManagePlatform"


PERMISSIONS: frozenset[str] = frozenset(p.value for p in Permission)


def assert_permission(value: str | Permission) -> Permission:
    """Return a validated ``Permission``."""
    if isinstance(value, Permission):
        return value
    cleaned = str(value).strip()
    # Accept enum name or value.
    for perm in Permission:
        if cleaned == perm.value or cleaned.upper() == perm.name:
            return perm
    msg = f"unknown permission: {value!r}"
    raise SecurityError(msg)
