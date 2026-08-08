"""EPIC-002 API composition integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import __version__, create_app
from dsp_platform import (
    COMPOSITION_PIPELINE_VERSION,
    DSPPlatform,
    PlatformBuilder,
    PlatformConfiguration,
)


@pytest.fixture
def client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


def _analyse_body(**overrides: object) -> dict:
    body: dict = {
        "ticker": "ACM",
        "exchange": "NYSE",
        "company": "Acme",
        "financial_statements": {
            "period": {
                "period_type": "annual",
                "period_end": "2024-12-31",
                "fiscal_year": 2024,
                "currency": "USD",
            },
            "income_statement": {
                "revenue": 1000.0,
                "cogs": 400.0,
                "gross_profit": 600.0,
                "ebit": 300.0,
                "ebitda": 350.0,
                "interest_expense": 20.0,
                "pretax_income": 280.0,
                "tax": 70.0,
                "net_income": 210.0,
                "weighted_shares": 100.0,
                "eps": 2.1,
            },
            "balance_sheet": {
                "cash": 150.0,
                "short_term_investments": 50.0,
                "accounts_receivable": 120.0,
                "inventory": 80.0,
                "current_assets": 450.0,
                "ppe": 400.0,
                "goodwill": 50.0,
                "intangibles": 50.0,
                "total_assets": 1000.0,
                "accounts_payable": 60.0,
                "short_term_debt": 50.0,
                "current_liabilities": 200.0,
                "long_term_debt": 200.0,
                "total_liabilities": 400.0,
                "retained_earnings": 300.0,
                "equity": 600.0,
                "total_equity": 600.0,
            },
            "cash_flow": {
                "operating_cash_flow": 250.0,
                "capex": -80.0,
                "free_cash_flow": 170.0,
                "dividends_paid": -50.0,
                "share_buybacks": -30.0,
                "debt_issued": 10.0,
                "debt_repaid": -40.0,
            },
            "statement_metadata": {"unit_scale": "millions"},
        },
        # P0-02 — market price input only; never client IV/MoS conclusions.
        "current_market_price": 70.0,
    }
    body.update(overrides)
    return body


class TestVersionHealthCapabilities:
    def test_package_version(self) -> None:
        assert __version__ == "0.3.0"

    def test_health_includes_pipeline(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["pipeline_version"] == COMPOSITION_PIPELINE_VERSION
        assert body["platform_version"] == "1.0.0"
        assert any(c["name"] == "composition_pipeline" for c in body["checks"])

    def test_version_endpoint(self, client: TestClient) -> None:
        response = client.get("/api/v1/version")
        assert response.status_code == 200
        body = response.json()
        assert body["api_version"] == "v1"
        assert body["api_package_version"] == "0.3.0"
        assert body["platform_version"] == "1.0.0"
        assert body["pipeline_version"] == COMPOSITION_PIPELINE_VERSION
        assert body["docs_version"] == "1.3.32"
        assert "financial" in body["package_versions"]

    def test_capabilities_endpoint(self, client: TestClient) -> None:
        response = client.get("/api/v1/capabilities")
        assert response.status_code == 200
        body = response.json()
        assert "investment_committee" in body["pipeline_stages"]
        assert "pipeline_result" in body["supported_reports"]
        assert "compose_intelligence" in body["platform_capabilities"]


class TestValidate:
    def test_validate_ok(self, client: TestClient) -> None:
        response = client.post("/api/v1/validate", json=_analyse_body())
        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is True
        assert body["errors"] == []

    def test_validate_missing_valuation(self, client: TestClient) -> None:
        payload = _analyse_body()
        payload.pop("current_market_price")
        response = client.post("/api/v1/validate", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        assert any("valuation" in e or "current_market_price" in e for e in body["errors"])

    def test_validate_rejects_client_intrinsic_value(self, client: TestClient) -> None:
        payload = _analyse_body(
            valuation_signals={
                "intrinsic_value_per_share": 999.0,
                "current_market_price": 70.0,
            }
        )
        response = client.post("/api/v1/validate", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        assert any("P0-02" in e for e in body["errors"])

    def test_validate_bad_ticker(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/validate", json=_analyse_body(ticker="BAD TICKER!")
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False


class TestAnalyse:
    def test_analyse_end_to_end(self, client: TestClient) -> None:
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["capability"] == "compose_intelligence"
        assert body["pipeline_version"] == COMPOSITION_PIPELINE_VERSION
        payload = body["payload"]
        assert payload["ok"] is True
        assert payload["has_investment_committee"] is True
        assert payload["committee_summary"] is not None
        assert len(payload["stage_summaries"]) == 11
        assert payload["risk"] is not None
        assert payload["risk"]["financial_risk"]["available"] is True
        assert "X-Request-Id" in response.headers

    def test_analyse_validation_error(self, client: TestClient) -> None:
        payload = _analyse_body()
        payload.pop("current_market_price")
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["ok"] is False
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["correlation_id"]
        assert body["timestamp"]
        assert any(
            "valuation" in e or "current_market_price" in e
            for e in body["validation_errors"]
        )

    def test_analyse_rejects_forged_client_iv(self, client: TestClient) -> None:
        """P0-02 — forged client IV must fail closed at the HTTP boundary."""
        payload = _analyse_body(
            valuation_signals={
                "intrinsic_value_per_share": 999.0,
                "current_market_price": 70.0,
                "confidence": 0.99,
            }
        )
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["ok"] is False
        assert body["error_code"] == "VALIDATION_ERROR"
        assert any("intrinsic_value_per_share" in e for e in body["validation_errors"])

    def test_analyse_accepts_price_only_without_client_iv(
        self, client: TestClient
    ) -> None:
        """P0-02 — analyse proceeds with market price; no client IV required."""
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        payload = body["payload"]
        assert payload["ok"] is True
        valuation_stage = next(
            s for s in payload["stage_summaries"] if s["stage"] == "valuation"
        )
        assert valuation_stage["status"] in {"succeeded", "degraded"}

    def test_analyse_schema_rejects_extra(self, client: TestClient) -> None:
        payload = _analyse_body()
        payload["unexpected"] = True
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "REQUEST_VALIDATION_ERROR"


class TestOpenAPIComposition:
    def test_openapi_includes_composition_routes(self, client: TestClient) -> None:
        data = client.get("/openapi.json").json()
        paths = data["paths"]
        assert "/api/v1/analyse" in paths or "/analyse" in paths
        assert "/api/v1/validate" in paths or "/validate" in paths
        assert "/api/v1/version" in paths or "/version" in paths
        assert "/api/v1/capabilities" in paths or "/capabilities" in paths
        assert data["info"]["version"] == "0.3.0"
