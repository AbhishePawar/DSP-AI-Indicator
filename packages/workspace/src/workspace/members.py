"""Membership & permission helpers (EPIC-A010).

Integrates with existing RBAC without modifying security_platform:
- Workspace roles enforced locally
- Optional platform Permission check via injectable callable (A009-ready)
"""

from __future__ import annotations

from typing import Callable

from workspace.exceptions import WorkspacePermissionError
from workspace.models import MEMBER_ROLES, Member, Workspace

__all__ = [
    "ROLE_RANK",
    "assert_workspace_role",
    "member_role",
    "platform_permission_allowed",
]

# Higher rank = more privilege
ROLE_RANK: dict[str, int] = {
    "read_only": 1,
    "reviewer": 2,
    "analyst": 3,
    "administrator": 4,
    "owner": 5,
}

# Map workspace actions → minimum role
ACTION_MIN_ROLE: dict[str, str] = {
    "workspace.read": "read_only",
    "workspace.update": "administrator",
    "workspace.delete": "owner",
    "member.manage": "administrator",
    "project.write": "analyst",
    "project.read": "read_only",
    "collection.write": "analyst",
    "collection.read": "read_only",
    "watchlist.write": "analyst",
    "watchlist.read": "read_only",
    "note.write": "analyst",
    "note.read": "read_only",
    "tag.write": "analyst",
    "tag.read": "read_only",
    "search": "read_only",
}

# Optional mapping to frozen security_platform Permission values (no enum edits)
ACTION_PLATFORM_PERMISSION: dict[str, str] = {
    "workspace.create": "ManagePlatform",
    "workspace.delete": "ManagePlatform",
    "member.manage": "ManageUsers",
    "project.write": "ViewReports",
    "collection.write": "ViewReports",
    "watchlist.write": "ViewReports",
    "note.write": "ViewReports",
    "search": "ViewReports",
    "workspace.read": "ViewReports",
}


def member_role(workspace: Workspace, user_id: str) -> str | None:
    uid = str(user_id or "").strip()
    if workspace.owner_id == uid:
        return "owner"
    for member in workspace.members:
        if member.user_id == uid:
            return member.role
    return None


def assert_workspace_role(
    workspace: Workspace,
    user_id: str,
    action: str,
) -> str:
    required = ACTION_MIN_ROLE.get(action, "administrator")
    role = member_role(workspace, user_id)
    if role is None:
        raise WorkspacePermissionError(
            f"user {user_id!r} is not a member of workspace {workspace.workspace_id}"
        )
    if ROLE_RANK.get(role, 0) < ROLE_RANK.get(required, 99):
        raise WorkspacePermissionError(
            f"role {role!r} cannot perform {action!r} (requires {required})"
        )
    return role


def platform_permission_allowed(
    action: str,
    *,
    has_permission: Callable[[str], bool] | None,
) -> bool:
    """A009-ready gate using existing Permission values only."""
    if has_permission is None:
        return True  # open when no auth context (tests / offline)
    required = ACTION_PLATFORM_PERMISSION.get(action)
    if not required:
        return True
    return bool(has_permission(required))


def ensure_owner_member(workspace: Workspace, created_at: str) -> tuple[Member, ...]:
    members = list(workspace.members)
    if not any(m.user_id == workspace.owner_id for m in members):
        members.append(
            Member(
                user_id=workspace.owner_id,
                role="owner",
                display_name=None,
                added_at=created_at,
            )
        )
    members.sort(key=lambda m: (ROLE_RANK.get(m.role, 0) * -1, m.user_id))
    # validate roles
    for m in members:
        if m.role not in MEMBER_ROLES:
            raise WorkspacePermissionError(f"invalid role {m.role!r}")
    return tuple(members)
