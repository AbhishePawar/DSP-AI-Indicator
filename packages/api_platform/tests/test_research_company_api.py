"""Canonical POST /api/v1/research/company HTTP contract tests."""

from __future__ import annotations

import json
from typing import Any

import pytest
from auth_test_helpers import bearer_headers, register_user
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api_platform import create_app
from api_platform.api.research_company_schemas import (
    AI_EXECUTION_UNAVAILABLE_MESSAGE,
    AI_VALIDATION_FAILED_MESSAGE,
    AiExecutionState,
    PublicResearchReportHttp,
    ResearchCompanyOutcome,
    ResearchCompanyRequest,
    ResearchCompanyResponse,
)
from api_platform.api.research_company_service import ResearchExecution
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


def _blob(body: dict[str, Any]) -> str:
    return json.dumps(body, default=str)


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


def _public_report_fixture() -> dict[str, object]:
    return {
        "schema_version": "dsp.public_research_report.test",
        "methodology_version": "test",
        "source_pipeline": "compose_intelligence",
        "research_status": "complete",
        "identity": {},
        "executive_summary": {},
        "business_quality": {},
        "economic_moat": {},
        "management_quality": {},
        "financial_strength": {},
        "earnings_quality": {},
        "growth_quality": {},
        "factor_scorecard": [],
        "buffett_analysis": {},
        "financials": {},
        "valuation": {},
        "recommendation": {},
        "risk": {},
        "entry_exit": {},
        "scenarios": {},
        "expected_returns": {},
        "industry": {},
        "evidence": [],
        "limitations": [],
    }


class TestResearchCompanyApi:
    def test_valid_request_without_openai_is_explicitly_unavailable(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("DEFAULT_AI_PROVIDER", "deterministic")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        response = client.post(
            "/api/v1/research/company",
            headers={**auth_headers, "X-Request-Id": "corr-research-unavailable"},
            json={"ticker": "TCS", "exchange": "NSE", "company": "TCS"},
        )
        assert response.status_code == 200
        body = response.json()
        parsed = ResearchCompanyResponse.model_validate(body)
        assert parsed.ok is False
        assert parsed.ai_execution_state is AiExecutionState.AI_UNAVAILABLE
        assert parsed.outcome is ResearchCompanyOutcome.AI_UNAVAILABLE
        assert parsed.report is None
        assert parsed.correlation_id == "corr-research-unavailable"
        assert_public_report_privacy(body)

    def test_success_returns_only_validated_public_report(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "api_platform.api.routers.research_company.execute_research_company",
            lambda **_kwargs: ResearchExecution(
                ok=True,
                state="ai_executed",
                outcome="success",
                report=_public_report_fixture(),
            ),
        )
        response = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "TCS", "exchange": "NSE"},
        )
        assert response.status_code == 200
        body = response.json()
        parsed = ResearchCompanyResponse.model_validate(body)
        assert parsed.ok is True
        assert parsed.ai_execution_state is AiExecutionState.AI_EXECUTED
        assert parsed.outcome is ResearchCompanyOutcome.SUCCESS
        assert parsed.report is not None
        assert parsed.report.source_pipeline == "compose_intelligence"
        assert_public_report_privacy(body)
        assert "provider" not in _collect_keys(body)
        assert "model" not in _collect_keys(body)
        assert "routing" not in _collect_keys(body)
        blob = _blob(body)
        for canary in _PRIVATE_CANARIES:
            assert canary not in blob
        assert "ResearchPackage" not in blob
        assert "research_package" not in blob

    def test_validation_failure_is_fail_closed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "api_platform.api.routers.research_company.execute_research_company",
            lambda **_kwargs: ResearchExecution(
                ok=False,
                state="ai_validation_failed",
                outcome="ai_validation_failed",
                report=None,
                limitations=("AI output was rejected by DSP validation.",),
                errors=("AI recommendation mismatch",),
            ),
        )
        response = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "TCS"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["ai_execution_state"] == "ai_validation_failed"
        assert body["outcome"] == "ai_validation_failed"
        assert body["report"] is None
        assert "AI recommendation mismatch" in body["errors"]
        assert AI_VALIDATION_FAILED_MESSAGE not in body["errors"]

    def test_unversioned_alias_works(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("DEFAULT_AI_PROVIDER", "deterministic")
        response = client.post(
            "/research/company",
            headers=auth_headers,
            json={"ticker": "TCS"},
        )
        assert response.status_code == 200
        assert response.json()["ai_execution_state"] == "ai_unavailable"

    def test_missing_ticker_422(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"exchange": "NSE"},
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
            json={"ticker": "TCS", "provider": "openai"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "REQUEST_VALIDATION_ERROR"

    def test_unauthorized_without_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/research/company",
            json={"ticker": "TCS"},
        )
        assert response.status_code == 401

    def test_forbidden_without_analyze_company_permission(
        self, platform: DSPPlatform
    ) -> None:
        bundle = SecurityBundle.create(
            SecuritySettings(
                jwt_secret="research-company-secret",
                allow_guest=False,
                require_auth=True,
            )
        )
        token = bundle.jwt.issue(subject="usr_client", role=Role.CLIENT)
        secured = TestClient(create_app(platform=platform, security=bundle))
        response = secured.post(
            "/api/v1/research/company",
            headers={"Authorization": f"Bearer {token}"},
            json={"ticker": "TCS"},
        )
        assert response.status_code == 403
        assert response.json()["error"] == "AuthorizationError"
        assert not bundle.roles.has_permission(Role.CLIENT, Permission.ANALYZE_COMPANY)

    def test_response_schema_is_strict(self) -> None:
        with pytest.raises(ValidationError):
            ResearchCompanyResponse(
                ok=False,
                ai_execution_state=AiExecutionState.AI_UNAVAILABLE,
                outcome=ResearchCompanyOutcome.AI_UNAVAILABLE,
                provider="openai",  # type: ignore[call-arg]
            )
        with pytest.raises(ValidationError):
            ResearchCompanyRequest(ticker="TCS", model="gpt-4")  # type: ignore[call-arg]
        assert frozenset(PublicResearchReportHttp.model_fields) == PUBLIC_TOP_LEVEL_KEYS

    def test_report_contract_has_no_private_fields(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "api_platform.api.routers.research_company.execute_research_company",
            lambda **_kwargs: ResearchExecution(
                ok=True,
                state="ai_executed",
                outcome="success",
                report=_public_report_fixture(),
            ),
        )
        body = client.post(
            "/api/v1/research/company",
            headers=auth_headers,
            json={"ticker": "TCS"},
        ).json()
        keys = set(_collect_keys(body))
        assert keys & set(PRIVATE_REPORT_FIELD_NAMES) == set()
        assert_public_report_privacy(body)

    def test_analyse_route_remains_available(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/analyse",
            json={"ticker": "TCS", "exchange": "NSE"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["capability"] == "compose_intelligence"

    def test_openapi_includes_research_company(self, client: TestClient) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v1/research/company" in paths or "/research/company" in paths


# Keep this message referenced so the API contract does not silently remove
# the explicit unavailable-state copy used by clients.
def test_unavailable_message_is_stable() -> None:
    assert "OpenAI" in AI_EXECUTION_UNAVAILABLE_MESSAGE
