"""Research Diff Engine (EPIC-R005).

Compares R004 snapshots structurally — no calculations or interpretation.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.research_diff.loader import LoadedSnapshot, load_snapshot
from dsp_platform.research_diff.models import (
    DIFF_ENGINE_VERSION,
    DIFF_SCHEMA_VERSION,
    ResearchDiffResult,
    SectionDiff,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_diff.validation import validate_research_diff
from dsp_platform.research_diff.walker import (
    EXPORT_DIFF_SECTIONS,
    MISSING,
    REPORT_DIFF_SECTIONS,
    RESEARCH_OBJECT_DIFF_SECTIONS,
    diff_mapping,
    section_payload,
)

__all__ = [
    "DIFF_ENGINE_VERSION",
    "ResearchDiffEngine",
    "diff_research_snapshots",
]


def _sections_for_kind(kind: str) -> tuple[str, ...]:
    if kind == "research_object":
        return RESEARCH_OBJECT_DIFF_SECTIONS
    if kind == "institutional_report":
        return REPORT_DIFF_SECTIONS
    if kind == "export_metadata":
        return EXPORT_DIFF_SECTIONS
    # Unknown kind: compare entire payload as one section
    return ("payload",)


def _build_section(
    name: str,
    left_payload: Mapping[str, Any],
    right_payload: Mapping[str, Any],
) -> SectionDiff:
    if name == "payload":
        left_val: Any = left_payload
        right_val: Any = right_payload
        left_present = True
        right_present = True
    else:
        left_val = section_payload(left_payload, name)
        right_val = section_payload(right_payload, name)
        left_present = left_val is not MISSING
        right_present = right_val is not MISSING

    if not left_present and not right_present:
        return SectionDiff(
            name=name,
            status="unchanged",
            left_present=False,
            right_present=False,
            field_diffs=(),
            unchanged_field_count=0,
        )
    if not left_present:
        diffs = diff_mapping(MISSING, right_val, prefix=name)
    elif not right_present:
        diffs = diff_mapping(left_val, MISSING, prefix=name)
    else:
        diffs = diff_mapping(left_val, right_val, prefix=name)

    unchanged = sum(1 for d in diffs if d.status == "unchanged")
    changed_diffs = tuple(d for d in diffs if d.status != "unchanged")
    if not left_present:
        status = "added"
    elif not right_present:
        status = "removed"
    elif changed_diffs:
        status = "changed"
    else:
        status = "unchanged"

    return SectionDiff(
        name=name,
        status=status,
        left_present=left_present,
        right_present=right_present,
        field_diffs=changed_diffs,
        unchanged_field_count=unchanged,
    )


def _change_summary(sections: tuple[SectionDiff, ...]) -> dict[str, Any]:
    fields_added = fields_removed = fields_changed = fields_unchanged = 0
    sections_changed = sections_added = sections_removed = sections_unchanged = 0
    for section in sections:
        if section.status == "unchanged":
            sections_unchanged += 1
        elif section.status == "added":
            sections_added += 1
        elif section.status == "removed":
            sections_removed += 1
        else:
            sections_changed += 1
        fields_unchanged += section.unchanged_field_count
        for fd in section.field_diffs:
            if fd.status == "added":
                fields_added += 1
            elif fd.status == "removed":
                fields_removed += 1
            elif fd.status == "changed":
                fields_changed += 1
    return {
        "sections_total": len(sections),
        "sections_unchanged": sections_unchanged,
        "sections_changed": sections_changed,
        "sections_added": sections_added,
        "sections_removed": sections_removed,
        "fields_unchanged": fields_unchanged,
        "fields_changed": fields_changed,
        "fields_added": fields_added,
        "fields_removed": fields_removed,
        "identical_content": (
            fields_changed == 0
            and fields_added == 0
            and fields_removed == 0
            and sections_added == 0
            and sections_removed == 0
        ),
    }


class ResearchDiffEngine:
    """Fluent read-only diff engine."""

    def __init__(self) -> None:
        self._left: LoadedSnapshot | None = None
        self._right: LoadedSnapshot | None = None
        self._diff_id: str | None = None
        self._created_at: str | None = None

    def with_left(self, snapshot: str | Mapping[str, Any]) -> ResearchDiffEngine:
        self._left = load_snapshot(snapshot)
        return self

    def with_right(self, snapshot: str | Mapping[str, Any]) -> ResearchDiffEngine:
        self._right = load_snapshot(snapshot)
        return self

    def with_diff_id(self, diff_id: str) -> ResearchDiffEngine:
        self._diff_id = diff_id
        return self

    def with_created_at(self, created_at: str) -> ResearchDiffEngine:
        self._created_at = created_at
        return self

    def diff(self) -> ResearchDiffResult:
        if self._left is None or self._right is None:
            raise ValueError("left and right snapshots are required")
        left, right = self._left, self._right
        if left.kind != right.kind:
            raise ValueError(
                f"snapshot kind mismatch: {left.kind!r} vs {right.kind!r}"
            )

        created_at = self._created_at or utc_now().isoformat()
        diff_id = self._diff_id or str(uuid.uuid4())

        archive_comparison = {
            "left_snapshot_id": left.snapshot_id,
            "right_snapshot_id": right.snapshot_id,
            "same_kind": left.kind == right.kind,
            "same_lineage": left.version.get("lineage_id")
            == right.version.get("lineage_id"),
            "same_content_hash": left.content_sha256 == right.content_sha256,
            "left_version_number": left.version.get("version_number"),
            "right_version_number": right.version.get("version_number"),
            "left_content_sha256": left.content_sha256,
            "right_content_sha256": right.content_sha256,
            "left_archived_at": left.archived_at,
            "right_archived_at": right.archived_at,
            "left_content_schema_version": left.content_schema_version,
            "right_content_schema_version": right.content_schema_version,
        }

        schema_comparison = {
            "left_archive_schema_version": left.archive_schema_version,
            "right_archive_schema_version": right.archive_schema_version,
            "left_content_schema_version": left.content_schema_version,
            "right_content_schema_version": right.content_schema_version,
            "archive_schema_match": left.archive_schema_version
            == right.archive_schema_version,
            "content_schema_match": left.content_schema_version
            == right.content_schema_version,
        }

        version_comparison = {
            "left": dict(left.version),
            "right": dict(right.version),
            "same_lineage": left.version.get("lineage_id")
            == right.version.get("lineage_id"),
            "same_version_number": left.version.get("version_number")
            == right.version.get("version_number"),
        }

        section_names = _sections_for_kind(left.kind)
        sections = tuple(
            _build_section(name, left.payload, right.payload) for name in section_names
        )
        # Also compare top-level schema_version key when present on RO/report
        # (already covered under metadata/version for those kinds)

        summary = _change_summary(sections)
        provenance = {
            "source": "research_diff",
            "engine_version": DIFF_ENGINE_VERSION,
            "left_snapshot_id": left.snapshot_id,
            "right_snapshot_id": right.snapshot_id,
            "kind": left.kind,
            "read_only": True,
        }

        result = ResearchDiffResult(
            diff_id=diff_id,
            schema_version=DIFF_SCHEMA_VERSION,
            engine_version=DIFF_ENGINE_VERSION,
            created_at=created_at,
            left_snapshot_id=left.snapshot_id,
            right_snapshot_id=right.snapshot_id,
            kind=left.kind,
            archive_comparison=freeze_mapping(archive_comparison) or {},
            schema_comparison=freeze_mapping(schema_comparison) or {},
            version_comparison=freeze_mapping(version_comparison) or {},
            sections=sections,
            change_summary=freeze_mapping(summary) or {},
            provenance=freeze_mapping(provenance) or {},
        )
        validate_research_diff(result)
        return result


def diff_research_snapshots(
    left: str | Mapping[str, Any],
    right: str | Mapping[str, Any],
    *,
    diff_id: str | None = None,
    created_at: str | None = None,
) -> ResearchDiffResult:
    engine = ResearchDiffEngine().with_left(left).with_right(right)
    if diff_id:
        engine = engine.with_diff_id(diff_id)
    if created_at:
        engine = engine.with_created_at(created_at)
    return engine.diff()
