"""Research Archive service (EPIC-R004).

Archives existing R001 / R002 / R003 outputs only — never mutates snapshots.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.research_archive.hashing import (
    content_sha256,
    extract_subject_ids,
    infer_content_schema_version,
    infer_ticker,
    to_plain_jsonable,
)
from dsp_platform.research_archive.models import (
    ARCHIVE_SCHEMA_VERSION,
    ARCHIVE_SERVICE_VERSION,
    ArchiveSnapshot,
    ArchiveVersion,
    ComparisonMetadata,
    RetentionDecision,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_archive.retention import (
    RetainForeverPolicy,
    RetentionPolicy,
)
from dsp_platform.research_archive.serde import archive_snapshot_to_dict
from dsp_platform.research_archive.store import (
    ArchiveStore,
    InMemoryArchiveStore,
    SnapshotNotFoundError,
)
from dsp_platform.research_archive.validation import (
    validate_archive_snapshot,
    validate_snapshot_kind,
)

__all__ = [
    "ARCHIVE_SERVICE_VERSION",
    "ResearchArchiveService",
    "get_research_archive",
    "reset_research_archive_for_tests",
]

_ARCHIVE: ResearchArchiveService | None = None


class ResearchArchiveService:
    """Immutable archive of research outputs."""

    def __init__(
        self,
        store: ArchiveStore | None = None,
        *,
        default_retention: RetentionPolicy | None = None,
    ) -> None:
        self._store = store or InMemoryArchiveStore()
        self._default_retention = default_retention or RetainForeverPolicy()

    def archive(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        lineage_id: str | None = None,
        parent_snapshot_id: str | None = None,
        snapshot_id: str | None = None,
        archived_at: str | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> ArchiveSnapshot:
        """Create an immutable snapshot. Never overwrites existing ids."""
        kind_n = validate_snapshot_kind(kind)
        if not isinstance(payload, Mapping) or not payload:
            raise ValueError("payload mapping is required")

        # Deep-freeze a plain copy so callers cannot mutate archived content
        plain_payload = to_plain_jsonable(payload)
        if not isinstance(plain_payload, dict):
            raise ValueError("payload must be a mapping")
        digest = content_sha256(plain_payload)
        content_schema = infer_content_schema_version(kind_n, plain_payload)
        ticker = infer_ticker(kind_n, plain_payload)
        subject_ids = extract_subject_ids(kind_n, plain_payload)

        parent = None
        version_number = 1
        resolved_lineage = lineage_id
        if parent_snapshot_id:
            parent = self._store.get(parent_snapshot_id)
            if parent is None:
                raise SnapshotNotFoundError(parent_snapshot_id)
            if parent.kind != kind_n:
                raise ValueError(
                    f"parent kind {parent.kind!r} does not match {kind_n!r}"
                )
            version_number = parent.version.version_number + 1
            resolved_lineage = parent.version.lineage_id
        if not resolved_lineage:
            # Prefer stable subject id when present
            resolved_lineage = (
                str(subject_ids.get("research_object_id")
                    or subject_ids.get("report_id")
                    or subject_ids.get("export_id")
                    or uuid.uuid4())
            )

        snap_id = snapshot_id or str(uuid.uuid4())
        archived = archived_at or utc_now().isoformat()
        prov = {
            "source": "research_archive",
            "kind": kind_n,
            "archive_service_version": ARCHIVE_SERVICE_VERSION,
            **(dict(provenance) if provenance else {}),
        }
        retention_hooks = {
            "default_policy_id": getattr(
                self._default_retention, "policy_id", "unknown"
            ),
            "note": "retention is advisory; snapshots are never mutated",
        }

        snapshot = ArchiveSnapshot(
            snapshot_id=snap_id,
            kind=kind_n,
            version=ArchiveVersion(
                lineage_id=str(resolved_lineage),
                version_number=version_number,
                parent_snapshot_id=parent_snapshot_id,
            ),
            archive_schema_version=ARCHIVE_SCHEMA_VERSION,
            content_schema_version=content_schema,
            content_sha256=digest,
            archived_at=archived,
            ticker=ticker,
            subject_ids=freeze_mapping(subject_ids) or freeze_mapping({}),
            provenance=freeze_mapping(prov) or freeze_mapping({}),
            payload=freeze_mapping(plain_payload) or freeze_mapping({}),
            retention_hooks=freeze_mapping(retention_hooks) or freeze_mapping({}),
        )
        validate_archive_snapshot(snapshot)
        self._store.put_if_absent(snapshot)
        return snapshot

    def get(self, snapshot_id: str) -> ArchiveSnapshot:
        snap = self._store.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        validate_archive_snapshot(snap)
        return snap

    def get_dict(self, snapshot_id: str) -> dict[str, Any]:
        return archive_snapshot_to_dict(self.get(snapshot_id))

    def history(self, lineage_id: str) -> tuple[ArchiveSnapshot, ...]:
        return self._store.list_by_lineage(lineage_id)

    def history_dicts(self, lineage_id: str) -> list[dict[str, Any]]:
        return [archive_snapshot_to_dict(s) for s in self.history(lineage_id)]

    def compare(self, left_id: str, right_id: str) -> ComparisonMetadata:
        left = self.get(left_id)
        right = self.get(right_id)
        return ComparisonMetadata(
            left_snapshot_id=left.snapshot_id,
            right_snapshot_id=right.snapshot_id,
            same_kind=left.kind == right.kind,
            same_lineage=left.version.lineage_id == right.version.lineage_id,
            same_content_hash=left.content_sha256 == right.content_sha256,
            left_version_number=left.version.version_number,
            right_version_number=right.version.version_number,
            left_content_sha256=left.content_sha256,
            right_content_sha256=right.content_sha256,
            left_archived_at=left.archived_at,
            right_archived_at=right.archived_at,
            left_content_schema_version=left.content_schema_version,
            right_content_schema_version=right.content_schema_version,
        )

    def evaluate_retention(
        self,
        snapshot_id: str,
        policy: RetentionPolicy | None = None,
    ) -> RetentionDecision:
        """Advisory retention evaluation — never deletes or mutates content."""
        snap = self.get(snapshot_id)
        pol = policy or self._default_retention
        return pol.evaluate(snap)


def get_research_archive() -> ResearchArchiveService:
    global _ARCHIVE
    if _ARCHIVE is None:
        _ARCHIVE = ResearchArchiveService()
    return _ARCHIVE


def reset_research_archive_for_tests(
    service: ResearchArchiveService | None = None,
) -> None:
    global _ARCHIVE
    _ARCHIVE = service
