"""EPIC-R005 Research Diff unit tests."""

from __future__ import annotations

import pytest

from dsp_platform.research_archive import (
    InMemoryArchiveStore,
    ResearchArchiveService,
    reset_research_archive_for_tests,
)
from dsp_platform.research_diff import (
    DIFF_SCHEMA_VERSION,
    diff_research_snapshots,
    research_diff_from_dict,
    research_diff_to_dict,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_research_archive_for_tests(ResearchArchiveService(InMemoryArchiveStore()))
    yield
    reset_research_archive_for_tests(None)


def _archive_pair() -> tuple[str, str]:
    from dsp_platform.research_archive import get_research_archive

    base = research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-diff-1",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.2,
                },
            },
        )
    )
    changed = {
        **base,
        "recommendation": {
            **base["recommendation"],
            "payload": {
                **dict(base["recommendation"]["payload"] or {}),
                "margin_of_safety": 0.35,
            },
        },
    }
    service = get_research_archive()
    a = service.archive(
        "research_object",
        base,
        snapshot_id="diff-snap-a",
        archived_at=FIXED,
        lineage_id="diff-line",
    )
    b = service.archive(
        "research_object",
        changed,
        snapshot_id="diff-snap-b",
        archived_at=FIXED,
        parent_snapshot_id=a.snapshot_id,
    )
    return a.snapshot_id, b.snapshot_id


def test_snapshot_comparison_detects_change() -> None:
    left, right = _archive_pair()
    result = diff_research_snapshots(
        left, right, diff_id="diff-1", created_at=FIXED
    )
    assert result.schema_version == DIFF_SCHEMA_VERSION
    assert result.kind == "research_object"
    assert result.change_summary["identical_content"] is False
    assert result.change_summary["fields_changed"] >= 1
    rec = next(s for s in result.sections if s.name == "recommendation")
    assert rec.status == "changed"
    assert any("margin_of_safety" in f.path for f in rec.field_diffs)


def test_schema_and_version_comparison() -> None:
    left, right = _archive_pair()
    result = diff_research_snapshots(left, right, diff_id="diff-2", created_at=FIXED)
    assert result.schema_comparison["content_schema_match"] is True
    assert result.version_comparison["same_lineage"] is True
    assert result.archive_comparison["same_content_hash"] is False


def test_identical_snapshots() -> None:
    from dsp_platform.research_archive import get_research_archive

    payload = research_object_to_dict(
        build_research_object(symbol="MSFT", object_id="ro-same", created_at=FIXED)
    )
    service = get_research_archive()
    a = service.archive(
        "research_object",
        payload,
        snapshot_id="same-a",
        archived_at=FIXED,
        lineage_id="same-line",
    )
    # Second archive of identical content under new id
    b = service.archive(
        "research_object",
        payload,
        snapshot_id="same-b",
        archived_at=FIXED,
        parent_snapshot_id=a.snapshot_id,
    )
    result = diff_research_snapshots(
        a.snapshot_id, b.snapshot_id, diff_id="diff-same", created_at=FIXED
    )
    assert result.change_summary["identical_content"] is True
    assert result.archive_comparison["same_content_hash"] is True


def test_determinism() -> None:
    left, right = _archive_pair()
    a = research_diff_to_dict(
        diff_research_snapshots(left, right, diff_id="d", created_at=FIXED)
    )
    b = research_diff_to_dict(
        diff_research_snapshots(left, right, diff_id="d", created_at=FIXED)
    )
    assert a == b


def test_serialization_roundtrip() -> None:
    left, right = _archive_pair()
    result = diff_research_snapshots(left, right, diff_id="ser", created_at=FIXED)
    raw = research_diff_to_dict(result)
    restored = research_diff_from_dict(raw)
    assert research_diff_to_dict(restored) == raw


def test_kind_mismatch() -> None:
    from dsp_platform.research_archive import get_research_archive
    from dsp_platform.institutional_report import (
        generate_institutional_report,
        institutional_report_to_dict,
    )

    service = get_research_archive()
    ro = research_object_to_dict(
        build_research_object(symbol="X", object_id="ro-x", created_at=FIXED)
    )
    report = institutional_report_to_dict(
        generate_institutional_report(ro, report_id="rpt-x", generated_at=FIXED)
    )
    service.archive(
        "research_object", ro, snapshot_id="km-a", archived_at=FIXED, lineage_id="km"
    )
    service.archive(
        "institutional_report",
        report,
        snapshot_id="km-b",
        archived_at=FIXED,
        lineage_id="km-r",
    )
    with pytest.raises(ValueError, match="kind mismatch"):
        diff_research_snapshots("km-a", "km-b")
