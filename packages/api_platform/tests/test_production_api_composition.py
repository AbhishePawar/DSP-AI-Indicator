"""Production API composition regression tests.

Proves ``POST /api/v1/analyse`` is served by the canonical DSP AI Indicator
composition path — ``DSPPlatform.compose_intelligence`` → ``PlatformOrchestrator``
→ ``run_execution_pipeline`` → authenticated valuation bundle → Upstox
production adapters — and never by the legacy Yahoo/FRED
``InvestmentAnalysisService``.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from api_platform.api.dependencies import (
    build_default_platform,
    resolve_platform_environment,
)
from dsp_platform import (
    CompositionRequest,
    Environment,
    PlatformError,
)

_SECRET = "upstox-analytics-secret-token"


def _analyse_body() -> dict[str, Any]:
    return {
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
        "current_market_price": 70.0,
    }


@pytest.fixture
def client() -> TestClient:
    """Client over the real production composition root (no test platform)."""
    return TestClient(create_app())


class TestProductionCompositionRoot:
    """The composition root must yield a canonically analysable platform."""

    def test_default_platform_is_composition_capable(self) -> None:
        platform = build_default_platform()
        assert platform.configuration.has_capability("compose_intelligence")
        assert callable(platform.compose_intelligence)

    def test_default_platform_omits_legacy_analysis_service(self) -> None:
        """The Yahoo/FRED InvestmentAnalysisService is not the production path."""
        platform = build_default_platform()
        assert platform.configuration.require_analysis_service is False
        with pytest.raises(PlatformError):
            _ = platform.analysis_service

    def test_default_platform_reports_ready(self) -> None:
        platform = build_default_platform()
        result = platform.health_check()
        assert result.ok is True
        by_name = {c.name: c.status.value for c in result.payload.checks}
        assert by_name["composition_pipeline"] == "pass"
        assert by_name["dependency_wiring"] == "skip"

    def test_environment_projected_from_dsp_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DSP_ENVIRONMENT stays the single source of truth — no new variable."""
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        assert resolve_platform_environment() is Environment.PRODUCTION
        monkeypatch.setenv("DSP_ENVIRONMENT", "")
        assert resolve_platform_environment() is Environment.DEVELOPMENT
        monkeypatch.setenv("DSP_ENVIRONMENT", "not-a-real-environment")
        assert resolve_platform_environment() is Environment.DEVELOPMENT

    def test_legacy_dsp_ai_variables_are_not_required(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The canonical path needs no DSP_AI_* PlatformConfig loader values."""
        for name in (
            "DSP_AI_ENVIRONMENT",
            "DSP_AI_MARKET_PROVIDER_ID",
            "DSP_AI_FUNDAMENTALS_PROVIDER_ID",
            "DSP_AI_ECONOMIC_PROVIDER_ID",
        ):
            monkeypatch.delenv(name, raising=False)
        assert build_default_platform().health_check().ok is True


class TestAnalyseUsesCanonicalOrchestrator:
    """/analyse must delegate to compose_intelligence, not analysis_service."""

    def test_analyse_succeeds_without_analysis_service(
        self, client: TestClient
    ) -> None:
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        body = response.json()
        assert "analysis service is not wired" not in str(body)

    def test_analyse_delegates_to_compose_intelligence(
        self, monkeypatch: pytest.MonkeyPatch, client: TestClient
    ) -> None:
        state = client.app.state.api
        calls: list[CompositionRequest] = []
        original = state.platform.compose_intelligence

        def _spy(request: CompositionRequest):  # type: ignore[no-untyped-def]
            calls.append(request)
            return original(request)

        monkeypatch.setattr(state.platform, "compose_intelligence", _spy)
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        assert len(calls) == 1
        assert isinstance(calls[0], CompositionRequest)
        assert calls[0].ticker == "ACM"

    def test_analyse_never_calls_legacy_analysis_paths(
        self, monkeypatch: pytest.MonkeyPatch, client: TestClient
    ) -> None:
        """Yahoo/FRED orchestration must not run for investment analysis."""
        state = client.app.state.api

        def _forbidden(*_args: Any, **_kwargs: Any):  # type: ignore[no-untyped-def]
            raise AssertionError("legacy InvestmentAnalysisService path invoked")

        monkeypatch.setattr(state.platform, "analyze", _forbidden)
        monkeypatch.setattr(state.platform, "analyze_company", _forbidden)
        monkeypatch.setattr(state.platform, "analyze_decision_pack", _forbidden)
        assert client.post("/api/v1/analyse", json=_analyse_body()).status_code == 200

    def test_response_reports_canonical_pipeline_stages(
        self, client: TestClient
    ) -> None:
        from dsp_platform.composition.pipeline import EXECUTION_ORDER

        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        payload = response.json()["payload"] or {}
        order = ((payload.get("metadata") or {}).get("execution_order")) or []
        assert order == [stage.value for stage in EXECUTION_ORDER]

    def test_provenance_behaviour_preserved(self, client: TestClient) -> None:
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        body = response.json()
        assert "provenance_persisted" in body
        if body.get("analysis_id"):
            # Unowned provenance stays non-world-readable (P0-05 / P1-07):
            # an anonymous read must not escalate into the export trust chain.
            lookup = client.get(f"/api/v1/analyse/provenance/{body['analysis_id']}")
            assert lookup.status_code == 403


class TestHealthReflectsCanonicalComposition:
    def test_dependencies_reports_platform_pass(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/dependencies")
        assert response.status_code == 200
        result = response.json().get("result") or {}
        components = {c["name"]: c for c in result.get("components", [])}
        assert components["platform"]["status"] == "pass"

    def test_database_component_status_preserved(self, client: TestClient) -> None:
        """Database readiness is still sourced from infrastructure probes."""
        response = client.get("/api/v1/health/dependencies")
        result = response.json().get("result") or {}
        components = {c["name"]: c for c in result.get("components", [])}
        assert components["database"]["status"] in {"pass", "fail", "skip"}

    def test_health_composition_check_is_probed_not_assumed(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        checks = response.json()["checks"]
        names = [c["name"] for c in checks]
        assert names.count("composition_pipeline") == 1
        composition = next(c for c in checks if c["name"] == "composition_pipeline")
        assert composition["status"] == "pass"
        assert "stages=" in composition["message"]

    def test_ready_probe_accepts_traffic(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["platform_ready"] is True
        assert body["ready"] is True


class TestProductionFailClosed:
    """Production must fail closed rather than silently degrade."""

    def test_missing_upstox_token_reports_investment_fail_without_blocking_ready(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        platform = build_default_platform()
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
        monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
        result = platform.health_check()
        assert result.ok is True
        by_name = {c.name: c.status.value for c in result.payload.checks}
        assert by_name["investment_data_provider"] == "fail"
        assert result.payload.ready is True
        assert "investment_data_provider" in " ".join(result.limitations)

    def test_upstox_provider_selection_intact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
        monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", _SECRET)
        from data_engine.connector_framework.production_profile import (
            assert_production_investment_connectors_configured,
        )

        selected = assert_production_investment_connectors_configured()
        assert selected["market_quote"] == "UpstoxQuoteAdapter"
        assert selected["financial_statement"] == "UpstoxStatementAdapter"

    def test_no_in_memory_analysis_fallback_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
        monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", _SECRET)
        platform = build_default_platform()
        result = platform.health_check()
        message = " ".join(c.message for c in result.payload.checks)
        for token in ("InMemory", "Null", "memory", "demo", "fixture"):
            assert token not in message

    def test_health_messages_never_leak_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
        monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", _SECRET)
        platform = build_default_platform()
        result = platform.health_check()
        rendered = " ".join(
            [*(c.message for c in result.payload.checks), *result.limitations]
        )
        assert _SECRET not in rendered

    def test_analyse_response_never_leaks_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", _SECRET)
        client = TestClient(create_app())
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert _SECRET not in response.text


class TestDevelopmentBehaviourIntact:
    def test_injected_platform_still_honoured(self) -> None:
        """create_app(platform=...) overrides remain the test/dev seam."""
        platform = build_default_platform()
        app = create_app(platform=platform)
        assert app.state.api.platform is platform

    def test_platform_factory_still_honoured(self) -> None:
        built: list[str] = []

        def _factory():  # type: ignore[no-untyped-def]
            built.append("called")
            return build_default_platform()

        app = create_app(platform_factory=_factory)
        assert built == ["called"]
        assert app.state.api.platform is not None

    def test_validate_route_unchanged(self, client: TestClient) -> None:
        response = client.post("/api/v1/validate", json=_analyse_body())
        assert response.status_code == 200
        assert response.json()["valid"] is True


class TestLegacyAnalyzeCompanyUnchanged:
    """The legacy route keeps its own semantics; readiness no longer depends on it.

    Relaxing ``dependency_wiring`` to SKIP must not silently reroute
    ``/analyze/company`` onto the canonical pipeline, nor loosen its auth.
    """

    def test_legacy_route_still_requires_authentication(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/analyze/company",
            json={
                "symbol": "AAPL",
                "asset_class": "equity",
                "currency": "USD",
                "start": "2024-01-01",
                "end": "2024-06-01",
            },
        )
        assert response.status_code == 401

    def test_legacy_platform_path_remains_fail_closed(self) -> None:
        """Without the legacy service the legacy capability still refuses to answer."""
        from contracts import Instrument
        from contracts.enums import AssetClass

        platform = build_default_platform()
        request = platform.make_request(
            Instrument(
                symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
            ),
            date(2024, 1, 1),
            date(2024, 6, 1),
        )
        result = platform.analyze_company(request)
        assert result.ok is False
        assert result.errors
        assert "analysis service" in " ".join(result.errors).lower()
