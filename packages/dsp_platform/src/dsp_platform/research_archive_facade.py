"""Platform façade helpers for Research Archive (EPIC-R004)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_archive import (
    ARCHIVE_SCHEMA_VERSION,
    ARCHIVE_SERVICE_VERSION,
    SNAPSHOT_KINDS,
    archive_snapshot_to_dict,
    get_research_archive,
)

__all__ = [
    "archive_research_snapshot",
    "compare_research_snapshots",
    "evaluate_research_retention",
    "get_research_snapshot",
    "list_research_version_history",
    "research_archive_schema",
]


def research_archive_schema() -> dict[str, Any]:
    return {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "service_version": ARCHIVE_SERVICE_VERSION,
        "immutable": True,
        "read_only": True,
        "kinds": list(SNAPSHOT_KINDS),
        "features": [
            "snapshot",
            "versioning",
            "sha256_integrity",
            "parent_version",
            "history",
            "compare_metadata",
            "retention_hooks",
        ],
    }


def archive_research_snapshot(
    kind: str,
    payload: Mapping[str, Any],
    *,
    lineage_id: str | None = None,
    parent_snapshot_id: str | None = None,
    snapshot_id: str | None = None,
    archived_at: str | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    service = get_research_archive()
    snap = service.archive(
        kind,
        payload,
        lineage_id=lineage_id,
        parent_snapshot_id=parent_snapshot_id,
        snapshot_id=snapshot_id,
        archived_at=archived_at,
        provenance=provenance,
    )
    return archive_snapshot_to_dict(snap)


def get_research_snapshot(snapshot_id: str) -> dict[str, Any]:
    return get_research_archive().get_dict(snapshot_id)


def list_research_version_history(lineage_id: str) -> list[dict[str, Any]]:
    return get_research_archive().history_dicts(lineage_id)


def compare_research_snapshots(left_id: str, right_id: str) -> dict[str, Any]:
    return get_research_archive().compare(left_id, right_id).to_dict()


def evaluate_research_retention(snapshot_id: str) -> dict[str, Any]:
    return get_research_archive().evaluate_retention(snapshot_id).to_dict()
