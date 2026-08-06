"""Research collection helpers (EPIC-A010) — references only."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from workspace.models import ResearchCollection, freeze_mapping, utc_now
from workspace.validation import (
    assert_collection_kind,
    assert_non_empty,
    normalize_refs,
)

__all__ = ["build_collection"]


def build_collection(
    *,
    workspace_id: str,
    name: str,
    kind: str,
    artifact_refs: list[Mapping[str, Any]] | None = None,
    project_id: str | None = None,
    collection_id: str | None = None,
    created_at: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ResearchCollection:
    created = created_at or utc_now().isoformat()
    return ResearchCollection(
        collection_id=collection_id or str(uuid.uuid4()),
        workspace_id=assert_non_empty(workspace_id, "workspace_id"),
        project_id=project_id,
        name=assert_non_empty(name, "collection name"),
        kind=assert_collection_kind(kind),
        artifact_refs=normalize_refs(artifact_refs),
        created_at=created,
        updated_at=created,
        metadata=freeze_mapping(dict(metadata or {})),
    )
