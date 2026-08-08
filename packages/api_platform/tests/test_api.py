"""API Platform tests (K1.1) — HTTP surface only."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from ai_committee import (
    CommitteeReport,
    Decision,
    InvestmentDecision,
    MemberVote,
    Opinion,
)
from contracts import EngineSource, Evidence
from decision_intelligence import DecisionIntelligenceService, DecisionPack
from fastapi.testclient import TestClient
from recommendation import RecommendationMapper

from api_platform import __version__, create_app
from auth_test_helpers import bearer_headers, register_user
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


def _peer_instrument(symbol: str) -> Instrument:
    return Instrument(
        symbol=symbol, asset_class=AssetClass.EQUITY, currency="INR", name=symbol
    )


def _peer_opinion(source: str, decision: Decision) -> Opinion:
    return Opinion(
        source=source,
        recommendation=decision,
        reasoning=f"{source} for {decision.value}",
        evidence=(
            Evidence(
                source_engine=EngineSource.AI_COMMITTEE,
                claim=f"{source} evidence",
                value=1.0,
                reference="t",
                weight=0.5,
            ),
        ),
        engine=EngineSource.AI_COMMITTEE,
    )


def make_decision_pack(
    symbol: str, *, decision: Decision = Decision.BUY
) -> DecisionPack:
    """Build a real ``DecisionPack`` for compare-endpoint tests.

    Mirrors ``packages/comparison/tests/test_comparison.py::make_pack`` —
    the same construction sequence ``DSPPlatform.analyze_decision_pack``
    uses in production once wired to a live analysis service.
    """
    instrument = _peer_instrument(symbol)
    sources = ("technical", "fundamental", "economic")
    decisions = (decision, decision, Decision.HOLD)
    opinions = []
    votes = []
    for source, member in zip(sources, decisions, strict=True):
        op = _peer_opinion(source, member)
        opinions.append(op)
        votes.append(MemberVote(source=source, recommendation=member, opinion=op))
    report = CommitteeReport(
        instrument=instrument,
        opinions=tuple(opinions),
        votes=tuple(votes),
        decision=InvestmentDecision(
            instrument=instrument,
            decision=decision,
            rationale=f"Committee {decision.value}",
            decided_at=FIXED_NOW,
        ),
        voting_summary="synthetic",
        explanation="synthetic",
    )
    recommendation = RecommendationMapper.map(report)
    return DecisionIntelligenceService().build_pack(report, recommendation)


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
        assert __version__ == "0.3.0"

    def test_openapi_generated(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["version"] == "0.3.0"
        paths = data["paths"]
        assert "/health" in paths
        assert "/platform" in paths
        assert "/auth/login" in paths
        assert "/analyze/company" in paths
        assert "/analyse" in paths
        assert "/validate" in paths
        assert "/version" in paths
        assert "/capabilities" in paths
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
        assert body["version"] == "1.0.0"
        assert "analyze_company" in body["capabilities"]
        assert "compose_intelligence" in body["capabilities"]


class TestAnalyzeAndReport:
    def test_analyze_company(self, client: TestClient) -> None:
        register_user(client, user_id="analyze-owner", username="analyzeowner")
        headers = bearer_headers(client, username="analyzeowner")
        response = client.post(
            "/analyze/company",
            headers=headers,
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

        report = client.get(f"/report/{report_id}", headers=headers)
        assert report.status_code == 200
        assert report.json()["report_id"] == report_id

    def test_analyze_validation_error(self, client: TestClient) -> None:
        register_user(client, user_id="analyze-val", username="analyzeval")
        headers = bearer_headers(client, username="analyzeval")
        response = client.post(
            "/analyze/company",
            headers=headers,
            json={
                "symbol": "AAPL",
                "start": "2024-06-01",
                "end": "2024-01-01",
            },
        )
        assert response.status_code == 422

    def test_report_not_found(self, client: TestClient) -> None:
        register_user(client, user_id="analyze-miss", username="analyzemiss")
        headers = bearer_headers(client, username="analyzemiss")
        response = client.get("/report/missing", headers=headers)
        assert response.status_code == 404


class TestCompareWorkflowCopilot:
    def test_compare_requires_two_report_ids(self, client: TestClient) -> None:
        response = client.post("/compare", json={"report_ids": []})
        assert response.status_code == 422

        response = client.post("/compare", json={"report_ids": ["only-one"]})
        assert response.status_code == 422

    def test_compare_unknown_report_id(self, client: TestClient) -> None:
        response = client.post(
            "/compare", json={"report_ids": ["missing-a", "missing-b"]}
        )
        assert response.status_code == 422

    def test_compare_rejects_non_decision_pack_report(
        self, client: TestClient
    ) -> None:
        state = client.app.state.api  # type: ignore[attr-defined]
        state.reports.put("rpt-not-a-pack", {"payload": {"not": "a pack"}})
        state.reports.put("rpt-also-not", {"payload": None})
        response = client.post(
            "/compare",
            json={"report_ids": ["rpt-not-a-pack", "rpt-also-not"]},
        )
        assert response.status_code == 422

    def test_compare_end_to_end(self, client: TestClient) -> None:
        state = client.app.state.api  # type: ignore[attr-defined]
        state.reports.put(
            "rpt-hdfcbank", {"payload": make_decision_pack("HDFCBANK")}
        )
        state.reports.put(
            "rpt-icicibank", {"payload": make_decision_pack("ICICIBANK")}
        )
        response = client.post(
            "/compare",
            json={"report_ids": ["rpt-hdfcbank", "rpt-icicibank"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["capability"] == "compare_companies"
        payload = body["payload"]
        assert payload["status"] == "complete"
        assert payload["report"]["included_symbols"] == [
            "HDFCBANK",
            "ICICIBANK",
        ]
        assert payload["report"]["excluded_symbols"] == []
        assert payload["report"]["pair_observations"]

    def test_compare_refuses_incompatible_industries(
        self, client: TestClient
    ) -> None:
        state = client.app.state.api  # type: ignore[attr-defined]
        state.reports.put("rpt-bank2", {"payload": make_decision_pack("HDFCBANK")})
        state.reports.put("rpt-software2", {"payload": make_decision_pack("TCS")})
        response = client.post(
            "/compare",
            json={"report_ids": ["rpt-bank2", "rpt-software2"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["payload"]["status"] == "refused"
        assert body["payload"]["report"]["included_symbols"] == []

    def test_workflow_requires_context_ref(self, client: TestClient) -> None:
        response = client.post("/workflow/run", json={})
        assert response.status_code == 422

    def test_workflow_missing_context(self, client: TestClient) -> None:
        response = client.post(
            "/workflow/run", json={"context_ref": "missing"}
        )
        assert response.status_code == 404

    def test_copilot_chat_accepts_freeform_without_context_ref(
        self, client: TestClient
    ) -> None:
        """RC1 M7 — /copilot/chat orchestrates without J1 context_ref."""
        response = client.post("/copilot/chat", json={"user_text": "hi"})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["result"]["unavailable"] is True



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
