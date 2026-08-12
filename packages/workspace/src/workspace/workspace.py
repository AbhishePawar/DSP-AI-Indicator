"""Workspace entity helpers (EPIC-A010)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from workspace.members import ensure_owner_member
from workspace.models import Workspace, freeze_mapping, utc_now
from workspace.validation import assert_non_empty, assert_unique_name, assert_workspace_status

__all__ = ["build_workspace"]


def build_workspace(
    *,
    name: str,
    owner_id: str,
    description: str | None = None,
    status: str = "active",
    workspace_id: str | None = None,
    created_at: str | None = None,
    existing_names: set[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Workspace:
    cleaned = assert_unique_name(existing_names or set(), name, entity="workspace")
    owner = assert_non_empty(owner_id, "owner_id")
    created = created_at or utc_now().isoformat()
    ws = Workspace(
        workspace_id=workspace_id or str(uuid.uuid4()),
        name=cleaned,
        description=description,
        owner_id=owner,
        created_at=created,
        updated_at=created,
        status=assert_workspace_status(status),
        members=(),
        metadata=freeze_mapping(dict(metadata or {})),
    )
    return Workspace(
        workspace_id=ws.workspace_id,
        name=ws.name,
        description=ws.description,
        owner_id=ws.owner_id,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        status=ws.status,
        members=ensure_owner_member(ws, created),
        project_ids=(),
        watchlist_ids=(),
        collection_ids=(),
        note_ids=(),
        tag_ids=(),
        metadata=ws.metadata,
    )
