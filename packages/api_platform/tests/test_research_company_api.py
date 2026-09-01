"""STEP 4I — canonical POST /api/v1/research/company blocked stub."""

from __future__ import annotations

import json
from typing import Any

import pytest
from auth_test_helpers import bearer_headers, register_user
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api_platform import create_app
from api_platform.api.research_company_schemas import (
    AI_EXECUTION_BLOCKED_MESSAGE,
    AiExecutionState,
    PublicResearchReportHttp,
    ResearchCompanyOutcome,
    ResearchCompanyRequest,
    ResearchCompanyResponse,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_report.models import (
    PRIVATE_REPORT_FIELD_NAMES,
    PUBLIC_TOP_LEVEL_KEYS,
    assert_public_report_privacy,
)
from security_platform import Permission, Role, SecurityBundle, SecuritySettings

_PRIVATE_CANARIES = (
    "DSP_PRIVATE_METHODOLOGY_PROMPT_v1",
    "DSP_PRIVATE_RESEARCH_INSTRUCTION_v1",
)

_LEAK_NEEDLES = (
    "ResearchPackage",
    "research_package",
    "PrivateResearchPrompt",
    "DecisionPack",
    "PublicDecisionPack",
    "analyze_decision_pack",
    "ResearchOrchestrator",
    "openai",
    "anthropic",
    "gemini",
    "deepseek",
    "gpt-4",
    "claude",
)


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
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="research-company-user", username="researchcompany")
    return bearer_headers(client, username="researchcompany")


def _assert_blocked_envelope(body: dict[str, Any]) -> None:
    parsed = ResearchCompanyResponse.model_validate(body)
    assert parsed.ok is False
    assert parsed.api_version == "v1"
    assert parsed.ai_execution_state is AiExecutionState.AI_EXECUTION_BLOCKED
    assert parsed.outcome is ResearchCompanyOutcome.AI_EXECUTION_BLOCKED
    assert parsed.report is None
    assert parsed.analysis_id is None
    assert AI_EXECUTION_BLOCKED_MESSAGE in parsed.errors
    assert AI_EXECUTION_BLOCKED_MESSAGE in parsed.limitations
    assert_public_report_privacy(body)


def _blob(body: dict[str, Any]) -> str:
    return json.dumps(body, default=str)


class TestResearchCompanyBlockedStub:
    def test_valid_request_ai_blocked(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/research/company",
            headers={**auth_headers, "X-Request-Id": "corr-4i-blocked"},
            json={"ticker": "ACM", "exchange": "NYSE", "company": "Acme"},
        )
        assert response.status_code == 503
        body = response.json()
        _assert_blocked_envelope(body)
        assert body["correlation_id"] == "corr-4i-blocked"
        assert body["report"] is None
        assert response.headers.get("X-API-Version") == "v1"

    def test_unversioned_alias_also_blocked(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/research/company",
            headers=auth_headers,
            json={"ticker": "ACM"},
        )
        assert response.status_code == 503
        _assert_blocked_envelope(response.json())

    def test_missing_ticker_422(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"exchange": "NYSE"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["ok"] is False
        assert body["error_code"] == "REQUEST_VALIDATION_ERROR"

    def test_extra_unknown_field_422(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "ACM", "provider": "openai"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "REQUEST_VALIDATION_ERROR"

    def test_malformed_ticker_422(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "BAD TICKER!"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "REQUEST_VALIDATION_ERROR"

    def test_unauthorized_without_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/research/company",
            json={"ticker": "ACM"},
        )
        assert response.status_code == 401

    def test_unauthorized_when_security_enabled(self, platform: DSPPlatform) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(
                jwt_secret="4i-research-company-secret",
                allow_guest=False,
                require_auth=True,
            )
        )
        secured = TestClient(create_app(platform=platform, security=bundle))
        response = secured.post(
            "/api/v1/research/company",
            json={"ticker": "ACM"},
        )
        assert response.status_code == 401
        body = response.json()
        assert body["ok"] is False
        assert body["error"] == "AuthenticationError"

    def test_forbidden_without_analyze_company_permission(
        self, platform: DSPPlatform
    ) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(
                jwt_secret="4i-research-company-secret",
                allow_guest=False,
                require_auth=True,
            )
        )
        token = bundle.jwt.issue(subject="usr_client", role=Role.CLIENT)
        secured = TestClient(create_app(platform=platform, security=bundle))
        response = secured.post(
            "/api/v1/research/company",
            headers={"Authorization": f"Bearer {token}"},
            json={"ticker": "ACM"},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["ok"] is False
        assert body["error"] == "AuthorizationError"
        assert not bundle.roles.has_permission(Role.CLIENT, Permission.ANALYZE_COMPANY)

    def test_response_schema_is_strict(self) -> None:
        with pytest.raises(ValidationError):
            ResearchCompanyResponse(
                ok=False,
                ai_execution_state=AiExecutionState.AI_EXECUTION_BLOCKED,
                outcome=ResearchCompanyOutcome.AI_EXECUTION_BLOCKED,
                provider="openai",  # type: ignore[call-arg]
            )
        with pytest.raises(ValidationError):
            ResearchCompanyRequest(ticker="ACM", model="gpt-4")  # type: ignore[call-arg]
        assert frozenset(PublicResearchReportHttp.model_fields) == PUBLIC_TOP_LEVEL_KEYS

    def test_response_cannot_contain_private_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        body = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "ACM"},
        ).json()
        keys = set(_collect_keys(body))
        leaked = keys & set(PRIVATE_REPORT_FIELD_NAMES)
        assert leaked == set()
        assert_public_report_privacy(body)

    def test_response_cannot_contain_private_methodology_canary(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        blob = _blob(
            client.post(
                "/api/v1/research/company",
                headers=auth_headers,
                json={"ticker": "ACM"},
            ).json()
        )
        for canary in _PRIVATE_CANARIES:
            assert canary not in blob

    def test_response_cannot_contain_research_package(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        blob = _blob(
            client.post(
                "/api/v1/research/company",
                headers=auth_headers,
                json={"ticker": "ACM"},
            ).json()
        )
        assert "ResearchPackage" not in blob
        assert "research_package" not in blob

    def test_response_cannot_contain_provider_model_routing(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        body = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "ACM"},
        ).json()
        keys = set(_collect_keys(body))
        assert "provider" not in keys
        assert "model" not in keys
        assert "routing" not in keys
        blob = _blob(body).lower()
        for needle in ("openai", "anthropic", "gemini", "deepseek"):
            assert needle not in blob

    def test_analyse_regression_unchanged(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        del auth_headers
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["capability"] == "compose_intelligence"
        assert isinstance(body["payload"], dict)
        assert "stage_summaries" in body["payload"]

    def test_legacy_research_routes_unchanged(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        schema = client.get("/api/v1/research/object/schema")
        assert schema.status_code == 200
        assert schema.json()["ok"] is True
        report_schema = client.get("/api/v1/research/report/schema")
        assert report_schema.status_code == 200
        assert report_schema.json()["ok"] is True
        built = client.post(
            "/api/v1/research/object",
            headers=auth_headers,
            json={
                "symbol": "MSFT",
                "fetch_data_bundle": False,
                "data_bundle": None,
                "analysis_payload": None,
            },
        )
        assert built.status_code == 200
        assert built.json()["ok"] is True

    def test_zero_provider_calls(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[str] = []

        def _forbid(*_args: object, **_kwargs: object) -> None:
            calls.append("provider")
            raise AssertionError("provider must not be called")

        monkeypatch.setattr(
            "llm_adapters.openai_adapter.OpenAIAdapter.complete",
            _forbid,
            raising=False,
        )
        response = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "ACM"},
        )
        assert response.status_code == 503
        assert calls == []

    def test_no_ai_fixture_in_response(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        body = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "ACM"},
        ).json()
        blob = _blob(body)
        assert "AI_OUTPUT_FIXTURE" not in blob
        assert "build_test_only_ai_output_fixture" not in blob
        assert body["ai_execution_state"] != "ai_output_fixture"

    def test_openapi_includes_research_company(self, client: TestClient) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v1/research/company" in paths or "/research/company" in paths

    def test_blocked_response_is_not_successful_research(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        body = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "ACM"},
        ).json()
        assert body["ok"] is False
        assert body["report"] is None
        blob = _blob(body).lower()
        for needle in _LEAK_NEEDLES:
            assert needle.lower() not in blob


def _collect_keys(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.append(str(key))
            found.extend(_collect_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_keys(item))
    return found
