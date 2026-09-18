"""Serialize / deserialize archive snapshots (EPIC-R004)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dsp_platform.research_archive.models import (
    ARCHIVE_SCHEMA_VERSION,
    ArchiveSnapshot,
    ArchiveVersion,
    freeze_mapping,
)
from dsp_platform.research_archive.validation import (
    ResearchArchiveValidationError,
    validate_archive_snapshot,
)

__all__ = [
    "archive_snapshot_from_dict",
    "archive_snapshot_to_dict",
]


def archive_snapshot_to_dict(snapshot: ArchiveSnapshot) -> dict[str, Any]:
    validate_archive_snapshot(snapshot)
    return snapshot.to_dict()


def archive_snapshot_from_dict(data: Mapping[str, Any]) -> ArchiveSnapshot:
    if not isinstance(data, Mapping):
        raise ResearchArchiveValidationError("snapshot must be a mapping")

    version_raw = data.get("version")
    if not isinstance(version_raw, Mapping):
        raise ResearchArchiveValidationError("missing version")

    version = ArchiveVersion(
        lineage_id=str(version_raw.get("lineage_id") or ""),
        version_number=int(version_raw.get("version_number") or 0),
        parent_snapshot_id=version_raw.get("parent_snapshot_id"),
    )

    payload = data.get("payload")
    if not isinstance(payload, Mapping):
        raise ResearchArchiveValidationError("missing payload")

    subject_ids_raw = data.get("subject_ids")
    provenance_raw = data.get("provenance")
    retention_hooks_raw = data.get("retention_hooks")
    subject_ids: Mapping[str, Any] = (
        subject_ids_raw if isinstance(subject_ids_raw, Mapping) else {}
    )
    provenance: Mapping[str, Any] = (
        provenance_raw if isinstance(provenance_raw, Mapping) else {}
    )
    retention_hooks: Mapping[str, Any] = (
        retention_hooks_raw if isinstance(retention_hooks_raw, Mapping) else {}
    )

    snapshot = ArchiveSnapshot(
        snapshot_id=str(data.get("snapshot_id") or ""),
        kind=str(data.get("kind") or ""),
        version=version,
        archive_schema_version=str(
            data.get("archive_schema_version") or ARCHIVE_SCHEMA_VERSION
        ),
        content_schema_version=str(data.get("content_schema_version") or "unknown"),
        content_sha256=str(data.get("content_sha256") or ""),
        archived_at=str(data.get("archived_at") or ""),
        ticker=data.get("ticker"),
        subject_ids=freeze_mapping(dict(subject_ids)) or {},
        provenance=freeze_mapping(dict(provenance)) or {},
        payload=freeze_mapping(dict(payload)) or {},
        retention_hooks=freeze_mapping(dict(retention_hooks)) or {},
    )
    validate_archive_snapshot(snapshot)
    return snapshot
