"""Research Archive models (EPIC-R004).

Immutable versioned snapshots of R001 / R002 / R003 outputs only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "ARCHIVE_SCHEMA_VERSION",
    "ARCHIVE_SERVICE_VERSION",
    "SNAPSHOT_KINDS",
    "UNAVAILABLE_MESSAGE",
    "ArchiveSnapshot",
    "ArchiveVersion",
    "ComparisonMetadata",
    "RetentionDecision",
    "freeze_mapping",
    "utc_now",
]

ARCHIVE_SCHEMA_VERSION = "1.0.0"
ARCHIVE_SERVICE_VERSION = "1.0.0"
SNAPSHOT_KINDS = (
    "research_object",
    "institutional_report",
    "export_metadata",
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ArchiveVersion:
    """Version node in an immutable lineage."""

    lineage_id: str
    version_number: int
    parent_snapshot_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "version_number": self.version_number,
            "parent_snapshot_id": self.parent_snapshot_id,
        }


@dataclass(frozen=True, slots=True)
class RetentionDecision:
    """Advisory retention result — never mutates archived content."""

    retain: bool
    reason: str
    policy_id: str
    expires_at: str | None = None
    evaluated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "retain": self.retain,
            "reason": self.reason,
            "policy_id": self.policy_id,
            "expires_at": self.expires_at,
            "evaluated_at": self.evaluated_at,
        }


@dataclass(frozen=True, slots=True)
class ComparisonMetadata:
    """Read-only comparison of two snapshots — metadata only, no content mutation."""

    left_snapshot_id: str
    right_snapshot_id: str
    same_kind: bool
    same_lineage: bool
    same_content_hash: bool
    left_version_number: int
    right_version_number: int
    left_content_sha256: str
    right_content_sha256: str
    left_archived_at: str
    right_archived_at: str
    left_content_schema_version: str
    right_content_schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_snapshot_id": self.left_snapshot_id,
            "right_snapshot_id": self.right_snapshot_id,
            "same_kind": self.same_kind,
            "same_lineage": self.same_lineage,
            "same_content_hash": self.same_content_hash,
            "left_version_number": self.left_version_number,
            "right_version_number": self.right_version_number,
            "left_content_sha256": self.left_content_sha256,
            "right_content_sha256": self.right_content_sha256,
            "left_archived_at": self.left_archived_at,
            "right_archived_at": self.right_archived_at,
            "left_content_schema_version": self.left_content_schema_version,
            "right_content_schema_version": self.right_content_schema_version,
        }


@dataclass(frozen=True, slots=True)
class ArchiveSnapshot:
    """Immutable archived snapshot — payload is frozen and never updated."""

    snapshot_id: str
    kind: str
    version: ArchiveVersion
    archive_schema_version: str
    content_schema_version: str
    content_sha256: str
    archived_at: str
    ticker: str | None
    subject_ids: Mapping[str, Any]
    provenance: Mapping[str, Any]
    payload: Mapping[str, Any]
    retention_hooks: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "snapshot_id": self.snapshot_id,
            "kind": self.kind,
            "version": self.version.to_dict(),
            "archive_schema_version": self.archive_schema_version,
            "content_schema_version": self.content_schema_version,
            "content_sha256": self.content_sha256,
            "archived_at": self.archived_at,
            "ticker": self.ticker,
            "subject_ids": _plain(self.subject_ids),
            "provenance": _plain(self.provenance),
            "payload": _plain(self.payload),
            "retention_hooks": _plain(self.retention_hooks),
        }
