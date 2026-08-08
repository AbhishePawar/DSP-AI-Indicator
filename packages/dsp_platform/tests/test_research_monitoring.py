"""EPIC-A003 Continuous Research Monitoring unit tests."""

from __future__ import annotations

import pytest

from dsp_platform.research_archive import (
    InMemoryArchiveStore,
    ResearchArchiveService,
    reset_research_archive_for_tests,
)
from dsp_platform.research_monitoring import (
    MONITORING_SCHEMA_VERSION,
    UNAVAILABLE_MESSAGE,
    evaluate_research_monitoring,
    monitoring_result_from_dict,
    monitoring_result_to_dict,
    reset_monitoring_registry_for_tests,
)
from dsp_platform.research_monitoring.alerts import (
    alerts_from_diff,
    alerts_from_portfolio_intelligence,
    severity_from_diff,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_research_archive_for_tests(ResearchArchiveService(InMemoryArchiveStore()))
    reset_monitoring_registry_for_tests()
    yield
    reset_research_archive_for_tests(None)
    reset_monitoring_registry_for_tests()


def _archive_pair(symbol: str = "AAPL") -> tuple[str, str]:
    from dsp_platform.research_archive import get_research_archive

    base = research_object_to_dict(
        build_research_object(
            symbol=symbol,
            object_id=f"ro-mon-{symbol.lower()}-1",
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
        snapshot_id=f"mon-{symbol.lower()}-a",
        archived_at=FIXED,
        lineage_id=f"mon-{symbol.lower()}",
    )
    b = service.archive(
        "research_object",
        changed,
        snapshot_id=f"mon-{symbol.lower()}-b",
        archived_at=FIXED,
        parent_snapshot_id=a.snapshot_id,
    )
    return a.snapshot_id, b.snapshot_id


def test_monitoring_evaluate_detects_change() -> None:
    left, right = _archive_pair()
    result = evaluate_research_monitoring(
        snapshot_pairs={
            "AAPL": {
                "baseline_snapshot_id": left,
                "current_snapshot_id": right,
            }
        },
        register_watchlist_symbols=["AAPL"],
        result_id="mon-1",
        created_at=FIXED,
    )
    assert result["schema_version"] == MONITORING_SCHEMA_VERSION
    assert result["provenance"]["providers_called"] is False
    assert result["provenance"]["engines_called"] is False
    assert len(result["alerts"]) == 1
    alert = result["alerts"][0]
    assert alert["alert_type"] == "research_change"
    assert alert["severity"] in {"watch", "important"}
    assert alert["citations"]
    assert all(c.get("section") for c in alert["citations"])


def test_change_detection_identical_no_alert() -> None:
    from dsp_platform.research_archive import get_research_archive

    payload = research_object_to_dict(
        build_research_object(symbol="MSFT", object_id="ro-same", created_at=FIXED)
    )
    service = get_research_archive()
    a = service.archive(
        "research_object",
        payload,
        snapshot_id="mon-same-a",
        archived_at=FIXED,
        lineage_id="mon-same",
    )
    b = service.archive(
        "research_object",
        payload,
        snapshot_id="mon-same-b",
        archived_at=FIXED,
        parent_snapshot_id=a.snapshot_id,
    )
    result = evaluate_research_monitoring(
        snapshot_pairs={
            "MSFT": {
                "baseline_snapshot_id": a.snapshot_id,
                "current_snapshot_id": b.snapshot_id,
            }
        },
        result_id="mon-same",
        created_at=FIXED,
    )
    assert result["alerts"] == []


def test_missing_snapshot_unavailable() -> None:
    result = evaluate_research_monitoring(
        snapshot_pairs={
            "IBM": {
                "baseline_snapshot_id": "missing-a",
                "current_snapshot_id": "missing-b",
            }
        },
        result_id="mon-miss",
        created_at=FIXED,
    )
    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["severity"] == "unavailable"
    assert result["alerts"][0]["message"] == UNAVAILABLE_MESSAGE


def test_portfolio_tracking_alerts() -> None:
    baseline = {
        "result_id": "pi-b",
        "portfolio": {"portfolio_id": "pf-1"},
        "missing_research": [{"symbol": "XYZ"}],
        "margin_of_safety_summary": {
            "positions": [{"symbol": "AAPL", "margin_of_safety": 0.2}]
        },
    }
    current = {
        "result_id": "pi-c",
        "portfolio": {"portfolio_id": "pf-1"},
        "missing_research": [{"symbol": "XYZ"}, {"symbol": "QQQ"}],
        "margin_of_safety_summary": {
            "positions": [{"symbol": "AAPL", "margin_of_safety": 0.3}]
        },
    }
    result = evaluate_research_monitoring(
        portfolio_intelligence_baseline=baseline,
        portfolio_intelligence_current=current,
        portfolio_id="pf-1",
        result_id="mon-pi",
        created_at=FIXED,
    )
    types = {a["alert_type"] for a in result["alerts"]}
    assert "portfolio_missing_research" in types
    assert "portfolio_mos_change" in types
    for alert in result["alerts"]:
        assert alert["citations"]
        assert alert["provenance"]["source"] == "research_monitoring"


def test_alert_generation_severity() -> None:
    diff = {
        "diff_id": "d1",
        "change_summary": {
            "identical_content": False,
            "fields_changed": 2,
            "sections_changed": 1,
        },
        "sections": [
            {
                "name": "valuation",
                "status": "changed",
                "field_diffs": [{"path": "valuation.fv", "status": "changed"}],
            }
        ],
    }
    assert severity_from_diff(diff) == "important"
    alert = alerts_from_diff(
        subject="AAPL",
        subject_kind="symbol",
        diff=diff,
        baseline_snapshot_id="a",
        current_snapshot_id="b",
        alert_id="x",
    )
    assert alert is not None
    assert alert.severity == "important"
    assert alert.citations


def test_citations_and_provenance() -> None:
    left, right = _archive_pair("GOOG")
    result = evaluate_research_monitoring(
        snapshot_pairs={
            "GOOG": {
                "baseline_snapshot_id": left,
                "current_snapshot_id": right,
            }
        },
        result_id="mon-cite",
        created_at=FIXED,
    )
    alert = result["alerts"][0]
    assert alert["citations"]
    assert alert["provenance"]["via"] == "research_diff"
    assert result["audit"]["created_at"] == FIXED
    assert result["provenance"]["diff_engine"] == "research_diff"


def test_determinism_and_serde() -> None:
    left, right = _archive_pair("META")
    kwargs = dict(
        snapshot_pairs={
            "META": {
                "baseline_snapshot_id": left,
                "current_snapshot_id": right,
            }
        },
        register_watchlist_symbols=["META"],
        result_id="mon-det",
        created_at=FIXED,
    )
    a = evaluate_research_monitoring(**kwargs)
    b = evaluate_research_monitoring(**kwargs)
    assert a == b
    restored = monitoring_result_from_dict(a)
    assert monitoring_result_to_dict(restored) == a


def test_portfolio_context_missing() -> None:
    alerts = alerts_from_portfolio_intelligence(
        portfolio_id="pf-x",
        baseline={"result_id": "b"},
        current=None,
        alert_id_prefix="t",
    )
    assert len(alerts) == 1
    assert alerts[0].severity == "unavailable"
    assert alerts[0].message == UNAVAILABLE_MESSAGE


def test_registry_track_used_when_pairs_omitted() -> None:
    from dsp_platform.research_monitoring import ResearchMonitoringService

    left, right = _archive_pair("NFLX")
    svc = ResearchMonitoringService()
    svc.register_watchlist(["NFLX"])
    svc.track_snapshot(
        "NFLX",
        baseline_snapshot_id=left,
        current_snapshot_id=right,
        tracked_at=FIXED,
    )
    result = evaluate_research_monitoring(result_id="mon-reg", created_at=FIXED)
    assert any(a["subject"] == "NFLX" for a in result["alerts"])
    assert "NFLX" in result["watchlist"]["symbols"]
