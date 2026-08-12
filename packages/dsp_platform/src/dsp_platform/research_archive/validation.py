"""Validate archive snapshots (EPIC-R004)."""

from __future__ import annotations

from dsp_platform.research_archive.hashing import content_sha256
from dsp_platform.research_archive.models import (
    ARCHIVE_SCHEMA_VERSION,
    SNAPSHOT_KINDS,
    ArchiveSnapshot,
)

__all__ = [
    "ResearchArchiveValidationError",
    "validate_archive_snapshot",
    "validate_snapshot_kind",
]


class ResearchArchiveValidationError(ValueError):
    """Archive snapshot failed structural / integrity validation."""


def validate_snapshot_kind(kind: str) -> str:
    normalized = kind.strip().lower()
    if normalized not in SNAPSHOT_KINDS:
        raise ResearchArchiveValidationError(
            f"unsupported snapshot kind {kind!r}; allowed={SNAPSHOT_KINDS}"
        )
    return normalized


def validate_archive_snapshot(snapshot: ArchiveSnapshot, *, verify_hash: bool = True) -> None:
    if snapshot.archive_schema_version != ARCHIVE_SCHEMA_VERSION:
        raise ResearchArchiveValidationError(
            f"unsupported archive_schema_version {snapshot.archive_schema_version!r}"
        )
    validate_snapshot_kind(snapshot.kind)
    if not snapshot.snapshot_id.strip():
        raise ResearchArchiveValidationError("missing snapshot_id")
    if not snapshot.version.lineage_id.strip():
        raise ResearchArchiveValidationError("missing lineage_id")
    if snapshot.version.version_number < 1:
        raise ResearchArchiveValidationError("version_number must be >= 1")
    if snapshot.version.version_number > 1 and not snapshot.version.parent_snapshot_id:
        raise ResearchArchiveValidationError(
            "parent_snapshot_id required when version_number > 1"
        )
    if not snapshot.archived_at:
        raise ResearchArchiveValidationError("missing archived_at")
    if not snapshot.content_sha256:
        raise ResearchArchiveValidationError("missing content_sha256")
    if snapshot.payload is None:
        raise ResearchArchiveValidationError("missing payload")
    if verify_hash:
        expected = content_sha256(snapshot.payload)
        if expected != snapshot.content_sha256:
            raise ResearchArchiveValidationError(
                "content_sha256 integrity check failed"
            )
