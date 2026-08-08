"""Research Archive & Versioning (EPIC-R004)."""

from __future__ import annotations

from dsp_platform.research_archive.hashing import (
    canonical_json_bytes,
    content_sha256,
    extract_subject_ids,
    infer_content_schema_version,
    infer_ticker,
)
from dsp_platform.research_archive.models import (
    ARCHIVE_SCHEMA_VERSION,
    ARCHIVE_SERVICE_VERSION,
    SNAPSHOT_KINDS,
    UNAVAILABLE_MESSAGE,
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
    TimeToLivePolicy,
)
from dsp_platform.research_archive.serde import (
    archive_snapshot_from_dict,
    archive_snapshot_to_dict,
)
from dsp_platform.research_archive.service import (
    ResearchArchiveService,
    get_research_archive,
    reset_research_archive_for_tests,
)
from dsp_platform.research_archive.store import (
    ArchiveStore,
    InMemoryArchiveStore,
    SnapshotAlreadyExistsError,
    SnapshotNotFoundError,
)
from dsp_platform.research_archive.validation import (
    ResearchArchiveValidationError,
    validate_archive_snapshot,
    validate_snapshot_kind,
)

__all__ = [
    "ARCHIVE_SCHEMA_VERSION",
    "ARCHIVE_SERVICE_VERSION",
    "SNAPSHOT_KINDS",
    "UNAVAILABLE_MESSAGE",
    "ArchiveSnapshot",
    "ArchiveStore",
    "ArchiveVersion",
    "ComparisonMetadata",
    "InMemoryArchiveStore",
    "ResearchArchiveService",
    "ResearchArchiveValidationError",
    "RetainForeverPolicy",
    "RetentionDecision",
    "RetentionPolicy",
    "SnapshotAlreadyExistsError",
    "SnapshotNotFoundError",
    "TimeToLivePolicy",
    "archive_snapshot_from_dict",
    "archive_snapshot_to_dict",
    "canonical_json_bytes",
    "content_sha256",
    "extract_subject_ids",
    "freeze_mapping",
    "get_research_archive",
    "infer_content_schema_version",
    "infer_ticker",
    "reset_research_archive_for_tests",
    "utc_now",
    "validate_archive_snapshot",
    "validate_snapshot_kind",
]
