"""Portfolio Intelligence Engine API tests — contracts + honesty (RC1 Milestone 4)."""

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
    }


class TestPortfolioInsightsEndpoint:
    def test_full_result_returns_every_capability(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/insights",
            json={"portfolio": _portfolio(), "as_of": AS_OF},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["available"] is True
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
            assert key in body

    def test_data_unavailable_without_holdings(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/insights", json={"portfolio": {"holdings": []}}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is False
        assert body["message"] == "Data unavailable."

    def test_valuation_flows_through_from_research_objects(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/portfolio/insights",
            json={
                "portfolio": _portfolio(),
                "research_objects": _research_objects(),
                "as_of": AS_OF,
            },
        )
        body = response.json()
        aaa_row = next(
            r for r in body["valuation_heatmap"]["rows"] if r["symbol"] == "AAA"
        )
        assert aaa_row["valuation_class"] == "undervalued"

    def test_available_on_both_unversioned_and_versioned_paths(
        self, client: TestClient
    ) -> None:
        for path in ("/portfolio/insights", "/api/v1/portfolio/insights"):
            response = client.post(
                path, json={"portfolio": _portfolio(), "as_of": AS_OF}
            )
            assert response.status_code == 200
            assert response.json()["ok"] is True

    def test_does_not_collide_with_epic_a002_portfolio_intelligence(
        self, client: TestClient
    ) -> None:
        insights = client.post(
            "/api/v1/portfolio/insights",
            json={"portfolio": _portfolio(), "as_of": AS_OF},
        )
        legacy = client.post(
            "/api/v1/portfolio/intelligence", json={"portfolio": _portfolio()}
        )
        assert insights.status_code == 200
        assert legacy.status_code == 200
        assert "health_score" in insights.json()
        assert "health_score" not in legacy.json().get("result", {})


class TestPortfolioInsightsHealthEndpoint:
    def test_returns_health_score_and_components(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/insights/health",
            json={
                "portfolio": _portfolio(),
                "research_objects": _research_objects(),
                "cash_weight": 0.05,
                "as_of": AS_OF,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is True
        assert 0.0 <= body["health_score"]["score"] <= 100.0


class TestPortfolioInsightsRecommendationsEndpoint:
    def test_returns_one_recommendation_per_holding(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/insights/recommendations",
            json={"portfolio": _portfolio(), "as_of": AS_OF},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["recommendations"]) == 2


class TestPortfolioInsightsOpportunitiesEndpoint:
    def test_returns_ranking_dimensions(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/insights/opportunities",
            json={
                "portfolio": _portfolio(),
                "research_objects": _research_objects(),
                "as_of": AS_OF,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["opportunities"]["highest_margin_of_safety"]
        assert body["opportunities"]["highest_expected_cagr"] == []


class TestPortfolioInsightsScenarioEndpoint:
    def test_returns_bull_base_bear(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/portfolio/insights/scenario",
            json={
                "portfolio": _portfolio(),
                "research_objects": _research_objects(),
                "as_of": AS_OF,
            },
        )
        assert response.status_code == 200
        body = response.json()
        cases = {c["case"] for c in body["scenario"]["cases"]}
        assert cases == {"bull", "base", "bear"}


class TestHealthCheckEndpoint:
    def test_returns_service_versions(self, client: TestClient) -> None:
        response = client.get("/api/v1/portfolio/insights/health-check")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["health"]["service_version"]
