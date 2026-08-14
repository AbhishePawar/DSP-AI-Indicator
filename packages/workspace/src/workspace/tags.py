"""Tags and labels (EPIC-A010)."""

from __future__ import annotations

import uuid

from workspace.models import Tag, utc_now
from workspace.validation import assert_non_empty

__all__ = ["build_tag"]


def build_tag(
    *,
    name: str,
    scope: str = "workspace",
    workspace_id: str | None = None,
    project_id: str | None = None,
    colour: str | None = None,
    label: str | None = None,
    tag_id: str | None = None,
    created_at: str | None = None,
) -> Tag:
    scope_n = str(scope or "workspace").strip().lower()
    if scope_n not in {"global", "workspace", "project"}:
        from workspace.exceptions import WorkspaceValidationError

        raise WorkspaceValidationError(f"invalid tag scope {scope!r}")
    return Tag(
        tag_id=tag_id or str(uuid.uuid4()),
        name=assert_non_empty(name, "tag name"),
        scope=scope_n,
        workspace_id=workspace_id,
        project_id=project_id,
        colour=colour,
        label=label or name,
        created_at=created_at or utc_now().isoformat(),
    )
