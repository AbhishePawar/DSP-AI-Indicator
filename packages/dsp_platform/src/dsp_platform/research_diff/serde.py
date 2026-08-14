"""Serialize / deserialize research diffs (EPIC-R005)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_diff.models import (
    DIFF_ENGINE_VERSION,
    DIFF_SCHEMA_VERSION,
    FieldDiff,
    ResearchDiffResult,
    SectionDiff,
    freeze_mapping,
)
from dsp_platform.research_diff.validation import (
    ResearchDiffValidationError,
    validate_research_diff,
)

__all__ = [
    "research_diff_from_dict",
    "research_diff_to_dict",
]


def research_diff_to_dict(result: ResearchDiffResult) -> dict[str, Any]:
    validate_research_diff(result)
    return result.to_dict()


def _section_from_dict(data: Mapping[str, Any]) -> SectionDiff:
    fields_raw = data.get("field_diffs") or []
    fields: list[FieldDiff] = []
    if isinstance(fields_raw, list):
        for row in fields_raw:
            if not isinstance(row, Mapping):
                continue
            fields.append(
                FieldDiff(
                    path=str(row.get("path") or ""),
                    status=str(row.get("status") or ""),
                    left_value=row.get("left_value"),
                    right_value=row.get("right_value"),
                )
            )
    return SectionDiff(
        name=str(data.get("name") or ""),
        status=str(data.get("status") or ""),
        left_present=bool(data.get("left_present")),
        right_present=bool(data.get("right_present")),
        field_diffs=tuple(fields),
        unchanged_field_count=int(data.get("unchanged_field_count") or 0),
    )


def research_diff_from_dict(data: Mapping[str, Any]) -> ResearchDiffResult:
    if not isinstance(data, Mapping):
        raise ResearchDiffValidationError("diff must be a mapping")
    sections_raw = data.get("sections") or []
    sections = tuple(
        _section_from_dict(s) for s in sections_raw if isinstance(s, Mapping)
    )
    result = ResearchDiffResult(
        diff_id=str(data.get("diff_id") or ""),
        schema_version=str(data.get("schema_version") or DIFF_SCHEMA_VERSION),
        engine_version=str(data.get("engine_version") or DIFF_ENGINE_VERSION),
        created_at=str(data.get("created_at") or ""),
        left_snapshot_id=str(data.get("left_snapshot_id") or ""),
        right_snapshot_id=str(data.get("right_snapshot_id") or ""),
        kind=str(data.get("kind") or ""),
        archive_comparison=freeze_mapping(dict(data.get("archive_comparison") or {}))
        or freeze_mapping({}),
        schema_comparison=freeze_mapping(dict(data.get("schema_comparison") or {}))
        or freeze_mapping({}),
        version_comparison=freeze_mapping(dict(data.get("version_comparison") or {}))
        or freeze_mapping({}),
        sections=sections,
        change_summary=freeze_mapping(dict(data.get("change_summary") or {}))
        or freeze_mapping({}),
        provenance=freeze_mapping(dict(data.get("provenance") or {}))
        or freeze_mapping({}),
    )
    validate_research_diff(result)
    return result
