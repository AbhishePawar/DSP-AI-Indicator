"""Tests for dsp_platform.portfolio_analytics — façade wiring, missing-data honesty."""

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
from dsp_platform.historical_series import reset_historical_series_service_for_tests
from dsp_platform.portfolio_analytics import (
    evaluate_portfolio_allocation_analytics,
    evaluate_portfolio_constraints,
    evaluate_portfolio_performance,
    evaluate_portfolio_risk_analytics,
    evaluate_portfolio_simulation,
    evaluate_portfolio_stress_analytics,
    evaluate_portfolio_tax_analytics,
    portfolio_analytics_health,
)


def _bundle(symbol: str, closes: list[tuple[date, float]]) -> AuthenticatedHistoricalBundle:
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
                base, 100.0, [0.01, -0.02, 0.03, 0.005, -0.01, 0.02, 0.015, -0.005, 0.01, 0.02]
            ),
        )
    )
    adapter.put(
        _bundle(
            "BBB",
            _closes_from_returns(
                base, 50.0, [0.02, 0.01, -0.01, 0.0, 0.015, -0.02, 0.01, 0.02, -0.015, 0.01]
            ),
        )
    )
    adapter.put(
        _bundle(
            "SPY",
            _closes_from_returns(
                base, 400.0, [0.015, 0.0, 0.01, 0.005, 0.0, 0.01, 0.02, 0.0, 0.005, 0.015]
            ),
        )
    )
    reset_historical_series_service_for_tests(HistoricalSeriesService(adapter))
    yield
    reset_historical_series_service_for_tests(None)


def _portfolio() -> dict[str, object]:
    return {
        "holdings": [
            {
                "symbol": "AAA",
                "weight": 0.6,
                "sector": "Technology",
                "exchange": "NASDAQ",
                "value_score": 0.2,
                "cost_basis_per_unit": 80.0,
                "purchase_date": "2022-01-01",
            },
            {
                "symbol": "BBB",
                "weight": 0.4,
                "sector": "Energy",
                "exchange": "NSE",
                "value_score": 0.4,
            },
        ]
    }


class TestEvaluatePortfolioPerformance:
    def test_available_with_seeded_history(self) -> None:
        result = evaluate_portfolio_performance(_portfolio(), benchmark_symbol="SPY", as_of="2023-01-11")
        assert result["available"] is True
        assert result["result"]["max_drawdown"] is not None
        assert result["result"]["beta"] is not None

    def test_unavailable_without_holdings(self) -> None:
        result = evaluate_portfolio_performance({"holdings": []})
        assert result["available"] is False
        assert result["message"] == "Data unavailable."

    def test_partial_without_benchmark(self) -> None:
        result = evaluate_portfolio_performance(_portfolio(), as_of="2023-01-11")
        assert result["available"] is True
        assert result["result"]["beta"] is None

    def test_unavailable_for_unknown_symbol(self) -> None:
        result = evaluate_portfolio_performance(
            {"holdings": [{"symbol": "UNKNOWNX", "weight": 1.0}]}, as_of="2023-01-11"
        )
        assert result["available"] is False


class TestEvaluatePortfolioRiskAnalytics:
    def test_available_with_seeded_history(self) -> None:
        result = evaluate_portfolio_risk_analytics(_portfolio(), as_of="2023-01-11")
        assert result["available"] is True
        assert result["risk_attribution"]["status"] == "complete"
        assert result["factor_exposure"]["status"] in {"complete", "partial"}


class TestEvaluatePortfolioAllocationAnalytics:
    def test_sector_and_country(self) -> None:
        result = evaluate_portfolio_allocation_analytics(_portfolio())
        assert result["sector_allocation"]["status"] == "complete"
        assert result["country_allocation"]["status"] == "complete"
        country_labels = {b["label"] for b in result["country_allocation"]["buckets"]}
        assert "United States" in country_labels
        assert "India" in country_labels


class TestEvaluatePortfolioSimulation:
    def test_monte_carlo_and_frontier_available(self) -> None:
        result = evaluate_portfolio_simulation(
            _portfolio(), monte_carlo_paths=50, frontier_samples=20, seed=7, as_of="2023-01-11"
        )
        assert result["monte_carlo"]["status"] == "complete"
        assert result["efficient_frontier"]["status"] == "complete"

    def test_deterministic_with_seed(self) -> None:
        first = evaluate_portfolio_simulation(
            _portfolio(), monte_carlo_paths=50, frontier_samples=20, seed=7, as_of="2023-01-11"
        )
        second = evaluate_portfolio_simulation(
            _portfolio(), monte_carlo_paths=50, frontier_samples=20, seed=7, as_of="2023-01-11"
        )
        assert first["monte_carlo"]["percentiles"] == second["monte_carlo"]["percentiles"]


class TestEvaluatePortfolioStressAnalytics:
    def test_scenario_impact_computed(self) -> None:
        result = evaluate_portfolio_stress_analytics(
            _portfolio(),
            scenarios=[{"name": "market -10%", "shock_pct": -0.10}],
            benchmark_symbol="SPY",
            as_of="2023-01-11",
        )
        assert result["scenarios"][0]["portfolio_impact_pct"] is not None

    def test_unknown_stress_window_is_honest(self) -> None:
        result = evaluate_portfolio_stress_analytics(
            _portfolio(), stress_window_ids=["not_a_real_window"]
        )
        entry = result["stress_tests"][0]
        assert entry["available"] is False
        assert "Unknown stress window" in entry["message"]

    def test_stress_window_catalog_exposed(self) -> None:
        result = evaluate_portfolio_stress_analytics(_portfolio())
        assert "gfc_2008" in result["stress_window_catalog"]
        assert "covid_2020" in result["stress_window_catalog"]


class TestEvaluatePortfolioConstraints:
    def test_position_limit_breach_detected(self) -> None:
        result = evaluate_portfolio_constraints(
            _portfolio(), max_position_weight=0.5
        )
        breached = {b["label"] for b in result["position_limits"]["breaches"]}
        assert "AAA" in breached

    def test_rebalancing_trades_computed(self) -> None:
        result = evaluate_portfolio_constraints(
            _portfolio(), target_weights={"AAA": 0.5, "BBB": 0.5}
        )
        assert len(result["rebalancing"]["trades"]) == 2


class TestEvaluatePortfolioTaxAnalytics:
    def test_partial_when_one_position_missing_cost_basis(self) -> None:
        result = evaluate_portfolio_tax_analytics(_portfolio(), as_of="2024-06-01")
        assert result["available"] is True
        assert result["result"]["status"] == "partial"

    def test_unavailable_without_holdings(self) -> None:
        result = evaluate_portfolio_tax_analytics({"holdings": []})
        assert result["available"] is False


class TestPortfolioAnalyticsHealth:
    def test_health_reports_price_history_source(self) -> None:
        health = portfolio_analytics_health()
        assert "price_history_source" in health
        assert health["price_history_source"]["healthy"] is True
