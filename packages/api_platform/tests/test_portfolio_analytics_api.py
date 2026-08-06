"""Portfolio Intelligence Analytics API tests — endpoint contracts + honesty."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
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
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.historical_series import reset_historical_series_service_for_tests

AS_OF = "2023-01-11"


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


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


def _portfolio() -> dict[str, object]:
    return {
        "holdings": [
            {"symbol": "AAA", "weight": 0.6, "sector": "Technology", "exchange": "NASDAQ"},
            {"symbol": "BBB", "weight": 0.4, "sector": "Energy", "exchange": "NSE"},
        ]
    }


class TestPerformanceEndpoint:
    def test_returns_ratios_with_seeded_history(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/analytics/performance",
            json={
                "portfolio": _portfolio(),
                "benchmark_symbol": "SPY",
                "as_of": AS_OF,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["available"] is True
        assert body["result"]["max_drawdown"] is not None
        assert body["result"]["beta"] is not None

    def test_data_unavailable_without_holdings(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/analytics/performance", json={"portfolio": {"holdings": []}}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is False
        assert body["message"] == "Data unavailable."


class TestRiskEndpoint:
    def test_returns_attribution_and_factors(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/analytics/risk",
            json={"portfolio": _portfolio(), "as_of": AS_OF},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["risk_attribution"]["status"] == "complete"
        assert "factor_exposure" in body


class TestAllocationEndpoint:
    def test_returns_sector_and_country_breakdowns(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/analytics/allocation", json={"portfolio": _portfolio()}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sector_allocation"]["status"] == "complete"
        assert body["country_allocation"]["status"] == "complete"


class TestSimulationEndpoint:
    def test_returns_monte_carlo_and_frontier(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/analytics/simulation",
            json={
                "portfolio": _portfolio(),
                "monte_carlo_paths": 50,
                "frontier_samples": 20,
                "seed": 3,
                "as_of": AS_OF,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["monte_carlo"]["status"] == "complete"
        assert body["efficient_frontier"]["status"] == "complete"


class TestStressEndpoint:
    def test_scenario_and_stress_window(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/analytics/stress",
            json={
                "portfolio": _portfolio(),
                "scenarios": [{"name": "market -10%", "shock_pct": -0.10}],
                "stress_window_ids": ["covid_2020", "bogus_window"],
                "benchmark_symbol": "SPY",
                "as_of": AS_OF,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["scenarios"][0]["portfolio_impact_pct"] is not None
        by_id = {s["scenario_id"]: s for s in body["stress_tests"]}
        assert by_id["bogus_window"]["available"] is False


class TestConstraintsEndpoint:
    def test_position_limit_breach_and_rebalancing(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/analytics/constraints",
            json={
                "portfolio": _portfolio(),
                "max_position_weight": 0.5,
                "target_weights": {"AAA": 0.5, "BBB": 0.5},
            },
        )
        assert response.status_code == 200
        body = response.json()
        breached = {b["label"] for b in body["position_limits"]["breaches"]}
        assert "AAA" in breached
        assert len(body["rebalancing"]["trades"]) == 2


class TestTaxEndpoint:
    def test_partial_without_full_cost_basis(self, client: TestClient) -> None:
        portfolio = _portfolio()
        portfolio["holdings"][0]["cost_basis_per_unit"] = 80.0
        portfolio["holdings"][0]["purchase_date"] = "2022-01-01"
        response = client.post(
            "/api/v1/portfolio/analytics/tax",
            json={"portfolio": portfolio, "as_of": "2024-06-01"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result"]["status"] == "partial"


class TestHealthEndpoint:
    def test_health_reports_price_history_source(self, client: TestClient) -> None:
        response = client.get("/api/v1/portfolio/analytics/health")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "price_history_source" in body["health"]
