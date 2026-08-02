"""EPIC-011B Research Intelligence unit tests."""

from __future__ import annotations

import pytest

from dsp_platform.research_intelligence import (
    InMemoryResearchSnapshotStore,
    ResearchIntelligenceService,
    SnapshotAlreadyExistsError,
    UNAVAILABLE_MESSAGE,
    UNABLE_MESSAGE,
    build_snapshot_from_analyse_payload,
    measure_outcome,
    reset_research_intelligence_for_tests,
)

FIXED = "2026-08-02T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    store = InMemoryResearchSnapshotStore()
    reset_research_intelligence_for_tests(ResearchIntelligenceService(store=store))
    yield
    reset_research_intelligence_for_tests(None)


def _payload(**overrides: object) -> dict:
    base = {
        "symbol": "AAPL",
        "company": "Apple Inc",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "price": 100.0,
        "intrinsic_value": 120.0,
        "margin_of_safety": 0.2,
        "investment_recommendation": {
            "decision": "Buy",
            "confidence": 0.8,
            "margin_of_safety": 0.2,
        },
        "investment_committee": {"decision": "Approve"},
        "explainability": {"summary": "MoS and quality support the stance."},
        "business_quality": {"score": 0.75},
        "management": {"score": 0.7},
        "economic_moat": {"score": 0.65},
        "risk": {"score": 0.4},
        "evidence_refs": ["ev-1", "ev-2"],
        "source_confidence": 0.9,
        "research_version": "1.0.0",
        "model_version": "m-1",
    }
    base.update(overrides)
    return base


def test_snapshot_immutability_no_overwrite() -> None:
    svc = ResearchIntelligenceService(store=InMemoryResearchSnapshotStore())
    first = svc.capture_from_payload(
        _payload(),
        research_id="ri-1",
        timestamp=FIXED,
        ticker="AAPL",
    )
    assert first["ok"] is True
    assert first["snapshot"]["content_sha256"]
    with pytest.raises(SnapshotAlreadyExistsError):
        svc.capture_from_payload(
            _payload(price=200.0),
            research_id="ri-1",
            timestamp=FIXED,
            ticker="AAPL",
        )
    # Original unchanged
    got = svc.get_snapshot("ri-1")
    assert got is not None
    assert got["price"] == 100.0
    assert got["content_sha256"] == first["snapshot"]["content_sha256"]


def test_outcome_math_with_fixture_prices() -> None:
    snap = build_snapshot_from_analyse_payload(
        _payload(),
        research_id="ri-out-1",
        timestamp=FIXED,
        ticker="AAPL",
    )
    # Bullish + price up → correct
    out = measure_outcome(snap, window_months=12, price_at_horizon=115.0, measured_at=FIXED)
    assert out.price_change_pct == pytest.approx(0.15)
    assert out.recommendation_accuracy == "correct"
    assert out.success_failure == "success"
    assert out.message is None

    # Missing horizon → honest unavailable
    missing = measure_outcome(snap, window_months=12, price_at_horizon=None, measured_at=FIXED)
    assert missing.recommendation_accuracy is None
    assert missing.message == UNAVAILABLE_MESSAGE


def test_bearish_outcome_and_unable() -> None:
    snap = build_snapshot_from_analyse_payload(
        _payload(
            investment_recommendation={"decision": "Sell", "confidence": 0.3},
            price=0.0,
        ),
        research_id="ri-out-2",
        timestamp=FIXED,
    )
    # price 0 → unable to calculate change even with horizon
    out = measure_outcome(snap, window_months=6, price_at_horizon=90.0, measured_at=FIXED)
    assert out.price_change_pct is None
    assert out.message in {UNABLE_MESSAGE, UNAVAILABLE_MESSAGE}


def test_historical_windows_and_timeline() -> None:
    svc = ResearchIntelligenceService(store=InMemoryResearchSnapshotStore())
    for i, conf in enumerate((0.8, 0.55, 0.2)):
        svc.capture_from_payload(
            _payload(
                investment_recommendation={
                    "decision": "Buy" if i < 2 else "Hold",
                    "confidence": conf,
                }
            ),
            research_id=f"ri-hist-{i}",
            timestamp=f"2026-0{i+1}-01T00:00:00+00:00",
            ticker="AAPL",
        )
    listing = svc.list_snapshots(symbol="AAPL")
    assert listing["total"] == 3
    assert listing["windows_supported"] == [3, 6, 12, 24, 36]
    timeline = svc.timeline(symbol="AAPL")
    assert len(timeline["timeline"]) == 3
    assert timeline["provenance"]["immutable"] is True


def test_calibration_and_dashboard_with_fixtures() -> None:
    svc = ResearchIntelligenceService(store=InMemoryResearchSnapshotStore())
    # high conf correct, high conf incorrect, medium correct
    cases = [
        ("ri-c1", "Buy", 0.85, 120.0),
        ("ri-c2", "Buy", 0.9, 90.0),
        ("ri-c3", "Buy", 0.5, 110.0),
    ]
    for rid, dec, conf, _ in cases:
        svc.capture_from_payload(
            _payload(
                investment_recommendation={"decision": dec, "confidence": conf},
                price=100.0,
            ),
            research_id=rid,
            timestamp=FIXED,
            ticker="MSFT",
        )
    prices = {"ri-c1": 120.0, "ri-c2": 90.0, "ri-c3": 110.0}
    cal = svc.calibration(
        window_months=12,
        horizon_prices=prices,
        result_id="cal-1",
        created_at=FIXED,
        measured_at=FIXED,
    )
    assert cal["ok"] is True
    assert cal["calibration"]["sample_size"] == 3
    assert cal["calibration"]["provenance"]["engines_called"] is False

    dash = svc.performance_dashboard(
        window_months=12,
        horizon_prices=prices,
        result_id="dash-1",
        created_at=FIXED,
        measured_at=FIXED,
    )
    assert dash["ok"] is True
    assert dash["dashboard"]["overall_accuracy"] == pytest.approx(2 / 3)
    assert dash["dashboard"]["provenance"]["measurement_only"] is True

    insights = svc.insights(
        window_months=12,
        horizon_prices=prices,
        result_id="ins-1",
        created_at=FIXED,
        measured_at=FIXED,
    )
    assert insights["ok"] is True
    assert len(insights["insights"]["best_performers"]) >= 1


def test_empty_registry_honest_unavailable() -> None:
    svc = ResearchIntelligenceService(store=InMemoryResearchSnapshotStore())
    dash = svc.performance_dashboard(window_months=12, result_id="empty", created_at=FIXED)
    assert dash["dashboard"]["message"] == UNAVAILABLE_MESSAGE
    assert dash["dashboard"]["overall_accuracy"] == UNAVAILABLE_MESSAGE
