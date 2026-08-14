"""EPIC-R004 Research Archive unit tests."""

from __future__ import annotations

import pytest

from dsp_platform.research_archive import (
    ARCHIVE_SCHEMA_VERSION,
    InMemoryArchiveStore,
    ResearchArchiveService,
    SnapshotAlreadyExistsError,
    TimeToLivePolicy,
    archive_snapshot_from_dict,
    archive_snapshot_to_dict,
    content_sha256,
    reset_research_archive_for_tests,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict
from dsp_platform.institutional_report import (
    generate_institutional_report,
    institutional_report_to_dict,
)
from dsp_platform.institutional_export import (
    export_artifact_to_dict,
    export_institutional_report,
)

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_research_archive_for_tests(ResearchArchiveService(InMemoryArchiveStore()))
    yield
    reset_research_archive_for_tests(None)


def _ro_payload() -> dict:
    ro = build_research_object(
        symbol="AAPL",
        object_id="ro-arch-1",
        created_at=FIXED,
        analysis_payload={
            "ok": True,
            "recommendation_summary": {"label": "Research Mode"},
        },
    )
    return research_object_to_dict(ro)


def test_snapshot_creation_and_hash() -> None:
    from dsp_platform.research_archive import get_research_archive

    payload = _ro_payload()
    service = get_research_archive()
    snap = service.archive(
        "research_object",
        payload,
        snapshot_id="snap-1",
        archived_at=FIXED,
        lineage_id="line-1",
    )
    assert snap.archive_schema_version == ARCHIVE_SCHEMA_VERSION
    assert snap.content_sha256 == content_sha256(payload)
    assert snap.version.version_number == 1
    assert snap.version.parent_snapshot_id is None


def test_versioning_parent_chain() -> None:
    from dsp_platform.research_archive import get_research_archive

    service = get_research_archive()
    payload = _ro_payload()
    v1 = service.archive(
        "research_object",
        payload,
        snapshot_id="snap-v1",
        archived_at=FIXED,
        lineage_id="line-a",
    )
    payload2 = {**payload, "note": "second"}
    v2 = service.archive(
        "research_object",
        payload2,
        snapshot_id="snap-v2",
        archived_at=FIXED,
        parent_snapshot_id=v1.snapshot_id,
    )
    assert v2.version.version_number == 2
    assert v2.version.parent_snapshot_id == "snap-v1"
    assert v2.version.lineage_id == "line-a"
    history = service.history("line-a")
    assert [s.snapshot_id for s in history] == ["snap-v1", "snap-v2"]


def test_immutability_no_overwrite() -> None:
    from dsp_platform.research_archive import get_research_archive

    service = get_research_archive()
    payload = _ro_payload()
    service.archive(
        "research_object", payload, snapshot_id="snap-x", archived_at=FIXED
    )
    with pytest.raises(SnapshotAlreadyExistsError):
        service.archive(
            "research_object", payload, snapshot_id="snap-x", archived_at=FIXED
        )


def test_serialization_roundtrip() -> None:
    from dsp_platform.research_archive import get_research_archive

    service = get_research_archive()
    snap = service.archive(
        "research_object",
        _ro_payload(),
        snapshot_id="snap-ser",
        archived_at=FIXED,
        lineage_id="line-ser",
    )
    raw = archive_snapshot_to_dict(snap)
    restored = archive_snapshot_from_dict(raw)
    assert archive_snapshot_to_dict(restored) == raw


def test_retrieval_and_compare() -> None:
    from dsp_platform.research_archive import get_research_archive

    service = get_research_archive()
    payload = _ro_payload()
    a = service.archive(
        "research_object",
        payload,
        snapshot_id="snap-a",
        archived_at=FIXED,
        lineage_id="line-c",
    )
    b = service.archive(
        "research_object",
        {**payload, "extra": 1},
        snapshot_id="snap-b",
        archived_at=FIXED,
        parent_snapshot_id=a.snapshot_id,
    )
    got = service.get("snap-a")
    assert got.content_sha256 == a.content_sha256
    cmp_ = service.compare("snap-a", "snap-b")
    assert cmp_.same_lineage is True
    assert cmp_.same_content_hash is False
    assert cmp_.left_version_number == 1
    assert cmp_.right_version_number == 2


def test_determinism() -> None:
    store1 = InMemoryArchiveStore()
    store2 = InMemoryArchiveStore()
    s1 = ResearchArchiveService(store1)
    s2 = ResearchArchiveService(store2)
    payload = _ro_payload()
    a = archive_snapshot_to_dict(
        s1.archive(
            "research_object",
            payload,
            snapshot_id="snap-d",
            archived_at=FIXED,
            lineage_id="line-d",
        )
    )
    b = archive_snapshot_to_dict(
        s2.archive(
            "research_object",
            payload,
            snapshot_id="snap-d",
            archived_at=FIXED,
            lineage_id="line-d",
        )
    )
    assert a == b


def test_report_and_export_kinds() -> None:
    from dsp_platform.research_archive import get_research_archive

    service = get_research_archive()
    ro = _ro_payload()
    report = institutional_report_to_dict(
        generate_institutional_report(ro, report_id="rpt-1", generated_at=FIXED)
    )
    export = export_artifact_to_dict(
        export_institutional_report(
            report, format="json", export_id="exp-1", exported_at=FIXED
        )
    )
    r = service.archive(
        "institutional_report", report, snapshot_id="snap-r", archived_at=FIXED
    )
    e = service.archive(
        "export_metadata", export, snapshot_id="snap-e", archived_at=FIXED
    )
    assert r.kind == "institutional_report"
    assert e.kind == "export_metadata"
    assert e.subject_ids.get("export_id") == "exp-1"


def test_retention_hook_advisory() -> None:
    store = InMemoryArchiveStore()
    service = ResearchArchiveService(store)
    snap = service.archive(
        "research_object",
        _ro_payload(),
        snapshot_id="snap-ttl",
        archived_at="2020-01-01T00:00:00+00:00",
        lineage_id="line-ttl",
    )
    decision = service.evaluate_retention(
        snap.snapshot_id, policy=TimeToLivePolicy(ttl_seconds=1)
    )
    assert decision.retain is False
    # content still present — never mutated/deleted
    assert service.get(snap.snapshot_id).snapshot_id == "snap-ttl"
