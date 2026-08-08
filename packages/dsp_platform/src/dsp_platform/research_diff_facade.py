"""Platform façade helpers for Research Diff (EPIC-R005)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_diff import (
    DIFF_ENGINE_VERSION,
    DIFF_SCHEMA_VERSION,
    RESEARCH_OBJECT_DIFF_SECTIONS,
    diff_research_snapshots,
    research_diff_to_dict,
)

__all__ = [
    "diff_canonical_research_snapshots",
    "research_diff_schema",
]


def research_diff_schema() -> dict[str, Any]:
    return {
        "schema_version": DIFF_SCHEMA_VERSION,
        "engine_version": DIFF_ENGINE_VERSION,
        "immutable": True,
        "read_only": True,
        "source": "research_archive_snapshots",
        "sections": list(RESEARCH_OBJECT_DIFF_SECTIONS),
        "statuses": ["unchanged", "added", "removed", "changed"],
    }


def diff_canonical_research_snapshots(
    left_snapshot_id: str,
    right_snapshot_id: str,
    *,
    diff_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Diff two archived snapshots by id (read-only)."""
    result = diff_research_snapshots(
        left_snapshot_id,
        right_snapshot_id,
        diff_id=diff_id,
        created_at=created_at,
    )
    return research_diff_to_dict(result)


def diff_canonical_research_snapshot_dicts(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    diff_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Diff two snapshot dicts without archive lookup."""
    result = diff_research_snapshots(
        left,
        right,
        diff_id=diff_id,
        created_at=created_at,
    )
    return research_diff_to_dict(result)
