"""Research Diff models (EPIC-R005).

Read-only structural comparison of R004 archive snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "DIFF_SCHEMA_VERSION",
    "DIFF_ENGINE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "DIFF_STATUSES",
    "FieldDiff",
    "ResearchDiffResult",
    "SectionDiff",
    "freeze_mapping",
    "utc_now",
]

DIFF_SCHEMA_VERSION = "1.0.0"
DIFF_ENGINE_VERSION = "1.0.0"
DIFF_STATUSES = ("unchanged", "added", "removed", "changed")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class FieldDiff:
    path: str
    status: str
    left_value: Any
    right_value: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status": self.status,
            "left_value": self.left_value,
            "right_value": self.right_value,
        }


@dataclass(frozen=True, slots=True)
class SectionDiff:
    name: str
    status: str
    left_present: bool
    right_present: bool
    field_diffs: tuple[FieldDiff, ...]
    unchanged_field_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "left_present": self.left_present,
            "right_present": self.right_present,
            "unchanged_field_count": self.unchanged_field_count,
            "field_diffs": [f.to_dict() for f in self.field_diffs],
        }


@dataclass(frozen=True, slots=True)
class ResearchDiffResult:
    """Immutable diff result — comparison only, no interpretation."""

    diff_id: str
    schema_version: str
    engine_version: str
    created_at: str
    left_snapshot_id: str
    right_snapshot_id: str
    kind: str
    archive_comparison: Mapping[str, Any]
    schema_comparison: Mapping[str, Any]
    version_comparison: Mapping[str, Any]
    sections: tuple[SectionDiff, ...]
    change_summary: Mapping[str, Any]
    provenance: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "diff_id": self.diff_id,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "created_at": self.created_at,
            "left_snapshot_id": self.left_snapshot_id,
            "right_snapshot_id": self.right_snapshot_id,
            "kind": self.kind,
            "archive_comparison": _plain(self.archive_comparison),
            "schema_comparison": _plain(self.schema_comparison),
            "version_comparison": _plain(self.version_comparison),
            "sections": [s.to_dict() for s in self.sections],
            "change_summary": _plain(self.change_summary),
            "provenance": _plain(self.provenance),
        }
