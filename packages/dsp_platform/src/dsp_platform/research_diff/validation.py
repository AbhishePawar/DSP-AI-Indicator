"""Validate research diff results (EPIC-R005)."""

from __future__ import annotations

from dsp_platform.research_diff.models import (
    DIFF_SCHEMA_VERSION,
    DIFF_STATUSES,
    ResearchDiffResult,
    SectionDiff,
)

__all__ = [
    "ResearchDiffValidationError",
    "validate_research_diff",
]


class ResearchDiffValidationError(ValueError):
    """Diff result failed structural validation."""


def _validate_section(section: SectionDiff) -> None:
    if section.status not in DIFF_STATUSES:
        raise ResearchDiffValidationError(
            f"invalid section status {section.status!r}"
        )
    for field in section.field_diffs:
        if field.status not in DIFF_STATUSES:
            raise ResearchDiffValidationError(
                f"invalid field status {field.status!r} at {field.path!r}"
            )
        if field.status == "unchanged":
            raise ResearchDiffValidationError(
                "field_diffs must omit unchanged entries"
            )


def validate_research_diff(result: ResearchDiffResult) -> None:
    if result.schema_version != DIFF_SCHEMA_VERSION:
        raise ResearchDiffValidationError(
            f"unsupported schema_version {result.schema_version!r}"
        )
    if not result.diff_id.strip():
        raise ResearchDiffValidationError("missing diff_id")
    if not result.left_snapshot_id.strip() or not result.right_snapshot_id.strip():
        raise ResearchDiffValidationError("missing snapshot ids")
    if not result.created_at:
        raise ResearchDiffValidationError("missing created_at")
    if not result.kind:
        raise ResearchDiffValidationError("missing kind")
    if result.archive_comparison is None or result.change_summary is None:
        raise ResearchDiffValidationError("missing comparison blocks")
    for section in result.sections:
        _validate_section(section)
