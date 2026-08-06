"""Tests for dsp_platform.portfolio_intelligence_engine — orchestration façade.

Verifies the façade correctly combines ``portfolio_analytics`` (quantitative)
and ``portfolio_intelligence.linker`` (EPIC-A002 pass-through) into the pure
``portfolio_intelligence_engine`` combination package, and that
``DSPPlatform`` delegates correctly. Never re-derives a valuation/risk
number — only checks that already-tested engine outputs flow through.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from data_engine.historical_series.adapters import (
    InMemoryAuthenticatedHistoricalAdapter,
)
from data_engine.historical_series.models import (
    AuthenticatedHistoricalBundle,
    AuthenticatedOhlcvBar,
    HistoricalCompanyIdentity,
    HistoricalField,
    HistoricalProvenance,
)
from data_engine.historical_series.service import HistoricalSeriesService
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.historical_series import reset_historical_series_service_for_tests
from dsp_platform.portfolio_intelligence_engine import (
    evaluate_portfolio_health,
    evaluate_portfolio_intelligence_engine,
    evaluate_portfolio_opportunities,
    evaluate_portfolio_recommendations,
    evaluate_portfolio_scenario,
    portfolio_intelligence_engine_health,
)


def _bundle(
    symbol: str, closes: list[tuple[date, float]]
) -> AuthenticatedHistoricalBundle:
    bars = tuple(
        AuthenticatedOhlcvBar(
            bar_date=bar_date,
            open=HistoricalField.of(close),
            high=HistoricalField.of(close),
            low=HistoricalField.of(close),
            close=HistoricalField.of(close),
            volume=HistoricalField.of(1_000_000),
        )
        for bar_date, close in closes
    )
    return AuthenticatedHistoricalBundle(
        identity=HistoricalCompanyIdentity(symbol=symbol),
        series_kind="ohlcv",
        frequency="daily",
        start_date=closes[0][0],
        end_date=closes[-1][0],
        bars=bars,
        points=(),
        snapshots=(),
        provenance=HistoricalProvenance(
            provider_id="memory_authenticated_historical",
            provider_name="In-Memory Test Fixture",
            source_type="test_fixture",
            retrieved_at=datetime.now(),
        ),
    )


def _closes_from_returns(
    start: date, initial_price: float, returns: list[float]
) -> list[tuple[date, float]]:
    price = initial_price
    out = [(start, price)]
    for i, r in enumerate(returns):
        price = price * (1 + r)
        out.append((start + timedelta(days=i + 1), price))
    return out


@pytest.fixture(autouse=True)
def _seeded_historical_series():
    adapter = InMemoryAuthenticatedHistoricalAdapter(api_key="test-key")
    base = date(2023, 1, 1)
    adapter.put(
        _bundle(
            "AAA",
            _closes_from_returns(
                base,
                100.0,
                [0.01, -0.02, 0.03, 0.005, -0.01, 0.02, 0.015, -0.005, 0.01, 0.02],
            ),
        )
    )
    adapter.put(
        _bundle(
            "BBB",
            _closes_from_returns(
                base,
                50.0,
                [0.02, 0.01, -0.01, 0.0, 0.015, -0.02, 0.01, 0.02, -0.015, 0.01],
            ),
        )
    )
    reset_historical_series_service_for_tests(HistoricalSeriesService(adapter))
    yield
    reset_historical_series_service_for_tests(None)


def _portfolio() -> dict[str, object]:
    return {
        "holdings": [
            {"symbol": "AAA", "weight": 0.6, "sector": "Information Technology"},
            {"symbol": "BBB", "weight": 0.4, "sector": "Energy"},
        ]
    }


def _research_objects() -> dict[str, object]:
    return {
        "AAA": {
            "metadata": {"ticker": "AAA"},
            "margin_of_safety": {
                "available": True,
                "payload": {"margin_of_safety": 0.25},
            },
            "recommendation": {
                "available": True,
                "payload": {"confidence": 0.8, "margin_of_safety": 0.25},
            },
            "business_quality": {"available": True, "payload": {"score": 82}},
        },
        "BBB": {
            "metadata": {"ticker": "BBB"},
            "margin_of_safety": {
                "available": True,
                "payload": {"margin_of_safety": -0.20},
            },
            "recommendation": {
                "available": True,
                "payload": {"confidence": 0.5, "margin_of_safety": -0.20},
            },
            "business_quality": {"available": True, "payload": {"score": 35}},
        },
    }


@pytest.fixture
def platform():
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


class TestEvaluatePortfolioIntelligenceEngine:
    def test_unavailable_without_holdings(self) -> None:
        result = evaluate_portfolio_intelligence_engine({"holdings": []})
        assert result["available"] is False
        assert result["message"] == "Data unavailable."

    def test_available_with_holdings_only(self) -> None:
        result = evaluate_portfolio_intelligence_engine(
            _portfolio(), as_of="2023-01-11"
        )
        assert result["available"] is True
        assert result["holding_count"] == 2
        for key in (
            "health_score",
            "concentration",
            "valuation_heatmap",
            "risk_summary",
            "recommendations",
            "drift",
            "diversification",
            "opportunities",
            "scenario",
        ):
            assert key in result

    def test_risk_summary_reuses_performance_and_risk_attribution(self) -> None:
        result = evaluate_portfolio_intelligence_engine(
            _portfolio(), as_of="2023-01-11"
        )
        risk = result["risk_summary"]
        assert risk["beta"] is None  # no benchmark supplied
        assert risk["annualized_volatility"] is not None
        assert len(risk["highest_risk_holdings"]) > 0

    def test_valuation_and_quality_flow_through_from_research_objects(self) -> None:
        result = evaluate_portfolio_intelligence_engine(
            _portfolio(), research_objects=_research_objects(), as_of="2023-01-11"
        )
        heatmap = result["valuation_heatmap"]
        aaa_row = next(r for r in heatmap["rows"] if r["symbol"] == "AAA")
        assert aaa_row["valuation_class"] == "undervalued"
        assert aaa_row["margin_of_safety"] == 0.25

        recs = {r["symbol"]: r for r in result["recommendations"]}
        assert recs["AAA"]["action"] == "increase"
        assert recs["BBB"]["action"] == "reduce"

    def test_health_score_complete_with_full_data(self) -> None:
        result = evaluate_portfolio_intelligence_engine(
            _portfolio(),
            research_objects=_research_objects(),
            cash_weight=0.05,
            as_of="2023-01-11",
        )
        health = result["health_score"]
        assert health["status"] == "complete"
        assert 0.0 <= health["score"] <= 100.0

    def test_scenario_expected_cagr_reuses_performance_annualized_return(self) -> None:
        result = evaluate_portfolio_intelligence_engine(
            _portfolio(), research_objects=_research_objects(), as_of="2023-01-11"
        )
        scenario = result["scenario"]
        assert scenario["expected_cagr"] is not None
        assert "historical" in scenario["expected_cagr_basis"].lower()

    def test_max_holdings_truncation_is_disclosed(self) -> None:
        holdings = [{"symbol": "AAA", "weight": 0.5}, {"symbol": "BBB", "weight": 0.5}]
        result = evaluate_portfolio_intelligence_engine(
            {"holdings": holdings}, as_of="2023-01-11", max_holdings=1
        )
        assert result["holding_count"] == 1
        assert any("more than 1 holdings" in msg for msg in result["limitations"])


class TestNarrowEndpointsShareOrchestration:
    def test_health_endpoint_matches_full_result(self) -> None:
        full = evaluate_portfolio_intelligence_engine(_portfolio(), as_of="2023-01-11")
        narrow = evaluate_portfolio_health(_portfolio(), as_of="2023-01-11")
        assert narrow["health_score"] == full["health_score"]

    def test_recommendations_endpoint_matches_full_result(self) -> None:
        full = evaluate_portfolio_intelligence_engine(_portfolio(), as_of="2023-01-11")
        narrow = evaluate_portfolio_recommendations(_portfolio(), as_of="2023-01-11")
        assert narrow["recommendations"] == full["recommendations"]

    def test_opportunities_endpoint_matches_full_result(self) -> None:
        full = evaluate_portfolio_intelligence_engine(_portfolio(), as_of="2023-01-11")
        narrow = evaluate_portfolio_opportunities(_portfolio(), as_of="2023-01-11")
        assert narrow["opportunities"] == full["opportunities"]

    def test_scenario_endpoint_matches_full_result(self) -> None:
        full = evaluate_portfolio_intelligence_engine(_portfolio(), as_of="2023-01-11")
        narrow = evaluate_portfolio_scenario(_portfolio(), as_of="2023-01-11")
        assert narrow["scenario"] == full["scenario"]

    def test_narrow_endpoints_unavailable_without_holdings(self) -> None:
        assert evaluate_portfolio_health({"holdings": []})["available"] is False
        assert (
            evaluate_portfolio_recommendations({"holdings": []})["available"] is False
        )
        assert evaluate_portfolio_opportunities({"holdings": []})["available"] is False
        assert evaluate_portfolio_scenario({"holdings": []})["available"] is False


class TestHealthCheck:
    def test_health_reports_versions(self) -> None:
        health = portfolio_intelligence_engine_health()
        assert health["service_version"]
        assert health["engine_package_version"]
        assert "portfolio_analytics" in health


class TestDspPlatformDelegation:
    def test_platform_evaluate_portfolio_intelligence_engine(self, platform) -> None:
        result = platform.evaluate_portfolio_intelligence_engine(
            _portfolio(), as_of="2023-01-11"
        )
        assert result["available"] is True

    def test_platform_evaluate_portfolio_health(self, platform) -> None:
        result = platform.evaluate_portfolio_health(_portfolio(), as_of="2023-01-11")
        assert result["available"] is True

    def test_platform_evaluate_portfolio_recommendations(self, platform) -> None:
        result = platform.evaluate_portfolio_recommendations(
            _portfolio(), as_of="2023-01-11"
        )
        assert result["available"] is True

    def test_platform_evaluate_portfolio_opportunities(self, platform) -> None:
        result = platform.evaluate_portfolio_opportunities(
            _portfolio(), as_of="2023-01-11"
        )
        assert result["available"] is True

    def test_platform_evaluate_portfolio_scenario(self, platform) -> None:
        result = platform.evaluate_portfolio_scenario(_portfolio(), as_of="2023-01-11")
        assert result["available"] is True

    def test_platform_portfolio_intelligence_engine_health(self, platform) -> None:
        result = platform.portfolio_intelligence_engine_health()
        assert result["service_version"]
