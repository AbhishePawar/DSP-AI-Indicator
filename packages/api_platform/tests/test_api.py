"""API Platform tests (K1.1) — HTTP surface only."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api_platform import __version__, create_app
from contracts.domain.instrument import Instrument
from contracts.domain.recommendation import Recommendation
from contracts.enums import AssetClass, RecommendationAction
from dsp_platform import (
    AnalysisRequest,
    DSPPlatform,
    PlatformBuilder,
    PlatformConfiguration,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


class _FakeAnalysisService:
    def __init__(self, recommendation: Recommendation) -> None:
        self._recommendation = recommendation
        self.calls = 0

    def analyze(self, request: AnalysisRequest) -> Any:
        self.calls += 1
        raise AssertionError("not used")

    def analyze_recommendation(self, request: AnalysisRequest) -> Recommendation:
        self.calls += 1
        return self._recommendation


def _recommendation() -> Recommendation:
    instrument = Instrument(
        symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
    )
    return Recommendation(
        instrument=instrument,
        action=RecommendationAction.BUY,
        conviction=0.75,
        rationale="API platform test.",
        generated_at=FIXED_NOW,
    )


@pytest.fixture
def platform() -> DSPPlatform:
    fake = _FakeAnalysisService(_recommendation())
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=True))
        .with_analysis_service(fake)  # type: ignore[arg-type]
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


class TestVersionAndOpenAPI:
    def test_version(self) -> None:
        assert __version__ == "0.1.0"

    def test_openapi_generated(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["version"] == "0.1.0"
        paths = data["paths"]
        assert "/health" in paths
        assert "/platform" in paths
        assert "/auth/login" in paths
        assert "/analyze/company" in paths
        assert "/compare" in paths
        assert "/workflow/run" in paths
        assert "/copilot/chat" in paths
        assert "/report/{report_id}" in paths

    def test_swagger_docs(self, client: TestClient) -> None:
        response = client.get("/docs")
        assert response.status_code == 200

    def test_versioned_aliases(self, client: TestClient) -> None:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/platform").status_code == 200


class TestHealthAndPlatform:
    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "ready" in body
        assert body["api_version"] == "v1"
        assert response.headers.get("X-API-Version") == "v1"

    def test_platform_info(self, client: TestClient) -> None:
        response = client.get("/platform")
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == "0.6.0"
        assert "analyze_company" in body["capabilities"]


class TestAnalyzeAndReport:
    def test_analyze_company(self, client: TestClient) -> None:
        response = client.post(
            "/analyze/company",
            json={
                "symbol": "AAPL",
                "asset_class": "equity",
                "currency": "USD",
                "start": "2024-01-01",
                "end": "2024-06-01",
                "as_decision_pack": False,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["capability"] == "analyze_company"
        report_id = body["payload"]["report_id"]
        assert report_id.startswith("rpt-")

        report = client.get(f"/report/{report_id}")
        assert report.status_code == 200
        assert report.json()["report_id"] == report_id

    def test_analyze_validation_error(self, client: TestClient) -> None:
        response = client.post(
            "/analyze/company",
            json={
                "symbol": "AAPL",
                "start": "2024-06-01",
                "end": "2024-01-01",
            },
        )
        assert response.status_code == 422

    def test_report_not_found(self, client: TestClient) -> None:
        response = client.get("/report/missing")
        assert response.status_code == 404


class TestCompareWorkflowCopilot:
    def test_compare_requires_packs(self, client: TestClient) -> None:
        response = client.post("/compare", json={"packs": []})
        assert response.status_code == 422

    def test_compare_validates_packs(self, client: TestClient) -> None:
        response = client.post(
            "/compare", json={"packs": [{"id": "pack-1"}]}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["capability"] == "compare_companies"
        assert body["payload"]["pack_count"] == 1

    def test_workflow_requires_context_ref(self, client: TestClient) -> None:
        response = client.post("/workflow/run", json={})
        assert response.status_code == 422

    def test_workflow_missing_context(self, client: TestClient) -> None:
        response = client.post(
            "/workflow/run", json={"context_ref": "missing"}
        )
        assert response.status_code == 404

    def test_copilot_requires_context_ref(self, client: TestClient) -> None:
        response = client.post("/copilot/chat", json={"user_text": "hi"})
        assert response.status_code == 422


class TestAuthLogin:
    def test_login_requires_security(self, client: TestClient) -> None:
        response = client.post("/auth/login", json={"username": "admin"})
        assert response.status_code == 503

    def test_login_issues_jwt(self) -> None:
        from security_platform import SecurityBundle, SecuritySettings

        from api_platform import create_app

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="web-login-secret")
        )
        secured = TestClient(create_app(security=bundle))
        response = secured.post("/api/v1/auth/login", json={"username": "admin"})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["payload"]["token_type"] == "bearer"
        assert body["payload"]["access_token"]

    def test_package_depends_on_platform_only(self) -> None:
        import tomllib
        from pathlib import Path

        data = tomllib.loads(
            (
                Path(__file__).resolve().parents[1] / "pyproject.toml"
            ).read_text(encoding="utf-8")
        )
        deps = data["project"]["dependencies"]
        assert any(d.startswith("dsp_platform") for d in deps)
        assert any(d.startswith("fastapi") for d in deps)
        forbidden = {
            "valuation",
            "recommendation",
            "workflow",
            "knowledge_graph",
            "copilot",
            "orchestration",
        }
        top = {d.split(">=", 1)[0].split("==", 1)[0] for d in deps}
        assert top.isdisjoint(forbidden)

    def test_create_app_factory(self) -> None:
        app = create_app()
        assert app.title.startswith("DSP")
