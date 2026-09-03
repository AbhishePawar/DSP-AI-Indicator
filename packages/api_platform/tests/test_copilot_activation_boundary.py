"""Copilot live-LLM HTTP must pass evaluate_activation before any provider call."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
from uuid import uuid4

from auth_test_helpers import bearer_headers, register_user
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from api_platform.api.dependencies import AI_PRODUCTION_BLOCKED_DETAIL
from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from dsp_platform import PlatformBuilder, PlatformConfiguration
from llm_adapters.activation_evidence import (
    ActivationEvidence,
    BenchmarkEvidence,
    ConfigurationEvidence,
    FailClosedEvidence,
    ModelEvaluationEvidence,
    PrivacyEvidence,
    ToolEvidence,
)
from llm_adapters.activation_guard import evaluate_activation
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.evaluation import QualityEvaluation
from llm_adapters.service import CopilotCompleteService

_SRC = Path(__file__).resolve().parents[1] / "src" / "api_platform" / "api"
_COPILOT_ROUTER = _SRC / "routers" / "copilot.py"
_DEPENDENCIES = _SRC / "dependencies.py"


def _platform():
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


def _app_client():
    return TestClient(create_app(platform=_platform()))


def _auth(client: TestClient, username: str = "copilotgate") -> dict[str, str]:
    register_user(client, user_id=f"u-{username}", username=username)
    return bearer_headers(client, username=username)


def _body() -> dict[str, Any]:
    return {
        "question_id": "why_buy",
        "request": {"ticker": "AAPL", "company": "Apple", "exchange": "NASDAQ"},
        "response": {
            "ok": True,
            "payload": {
                "ok": True,
                "recommendation_summary": {
                    "decision": "Buy",
                    "confidence": 0.8,
                    "margin_of_safety": 0.2,
                },
                "committee_summary": {"decision": "Approve", "confidence": 0.7},
                "stage_summaries": [],
            },
        },
    }


class _BoomService:
    """Fails the test if complete/stream/resolve would run while blocked."""

    complete_calls = 0
    stream_calls = 0
    active_calls = 0

    def complete(self, **kwargs: Any) -> None:
        type(self).complete_calls += 1
        raise AssertionError(
            "CopilotCompleteService.complete must not run when blocked"
        )

    def stream(self, **kwargs: Any):
        type(self).stream_calls += 1
        raise AssertionError(
            "CopilotCompleteService.stream must not run when blocked"
        )
        yield from ()

    def active_provider_id(self) -> str:
        type(self).active_calls += 1
        raise AssertionError("active_provider_id must not run when blocked")


class _RecordingAdapter:
    provider_id = "openai"
    model_label = "test-fake"

    def __init__(self) -> None:
        self.invoke_calls = 0
        self.requests: list[LanguageModelRequest] = []

    def is_configured(self) -> bool:
        return True

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        self.invoke_calls += 1
        self.requests.append(request)
        return LanguageModelResult(
            result_id=str(uuid4()),
            status=LanguageModelStatus.COMPLETE,
            provenance=("test.recording.adapter",),
            narrative_text="Frozen-session narrative from the fake provider.",
        )


class _FailingAdapter(_RecordingAdapter):
    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        self.invoke_calls += 1
        self.requests.append(request)
        return LanguageModelResult(
            result_id=str(uuid4()),
            status=LanguageModelStatus.FAILED,
            provenance=("test.failing.adapter",),
            limitations=("LLM invocation failed",),
        )


class _AdapterRegistry:
    def __init__(self, adapter: _RecordingAdapter) -> None:
        self._adapter = adapter
        self.config = LLMPlatformConfig(
            default_provider="openai",
            openai_api_key="test-not-used",
            anthropic_api_key=None,
            gemini_api_key=None,
            deepseek_api_key=None,
            openai_model="gpt-4o-mini",
            anthropic_model="claude",
            gemini_model="gemini",
            deepseek_model="deepseek-chat",
            request_timeout_seconds=5.0,
            max_retries=0,
        )

    def resolve_active(self) -> tuple[str, _RecordingAdapter]:
        return "openai", self._adapter

    def list_providers(self) -> list[dict[str, object]]:
        return [{"id": "openai", "configured": True}]


def _quality(score: float = 90.0) -> QualityEvaluation:
    s = score / 100.0
    return QualityEvaluation(
        factual_accuracy=s,
        financial_reasoning=s,
        valuation_reasoning=s,
        buffett_reasoning=s,
        moat_business_quality=s,
        management=s,
        financial_strength=s,
        earnings_quality=s,
        growth_quality=s,
        risk=s,
        evidence_correctness=s,
        hallucination=s,
        unsupported_claims=s,
        structured_output=s,
        consistency=s,
        business_quality=s,
    )


def _ready_evidence() -> ActivationEvidence:
    return ActivationEvidence(
        benchmark=BenchmarkEvidence(
            benchmark_completed=True,
            benchmark_version="v1",
            case_count=8,
            accepted_run_count=12,
            best_overall_score=85.0,
            best_model_identity="deepseek:deepseek-chat",
            cost_min_usd=0.001,
            cost_max_usd=0.05,
        ),
        successful_evaluations=(
            ModelEvaluationEvidence(
                model_identity="deepseek:deepseek-chat",
                research_case_id="case-1",
                quality=_quality(),
                quality_score=90.0,
                estimated_cost_usd=0.01,
                pricing_known=True,
                structured_output_valid=True,
                token_usage={"input": 1000, "output": 500},
                latency_ms=200,
            ),
        ),
        configuration=ConfigurationEvidence(
            default_provider="deterministic",
            cost_efficient_model="deepseek:deepseek-chat",
            premium_model="anthropic:claude-3-5-sonnet-20241022",
            available_providers=("openai", "anthropic", "gemini", "deepseek"),
            pricing_known_for_all_tiers=True,
            routing_tier_count=2,
            all_provider_keys_configured=False,
        ),
        tools=ToolEvidence(
            available_tools=("dsp.analyse", "dsp.valuation", "dsp.committee"),
            minimum_tool_count=2,
            all_tools_healthy=True,
        ),
        privacy=PrivacyEvidence(
            private_fields_enumerated=True,
            public_pack_present=True,
            leakage_guard_active=True,
            benchmark_report_audited=True,
        ),
        fail_closed=FailClosedEvidence(
            quality_gate_present=True,
            no_fabrication_guarantee=True,
            deterministic_fallback_present=True,
            escalation_present=True,
        ),
        required_quality_threshold=60.0,
    )


def test_missing_evidence_is_blocked_by_existing_guard() -> None:
    verdict = evaluate_activation(ActivationEvidence.missing())
    assert verdict.is_ready() is False


def test_complete_blocked_does_not_call_provider() -> None:
    _BoomService.complete_calls = 0
    client = _app_client()
    client.app.state.api.copilot_service = _BoomService()
    headers = _auth(client, username="blockedcomplete")
    response = client.post(
        "/api/v1/copilot/complete", headers=headers, json=_body()
    )
    assert response.status_code == 503
    assert response.json()["detail"] == AI_PRODUCTION_BLOCKED_DETAIL
    assert _BoomService.complete_calls == 0


def test_stream_blocked_does_not_call_provider() -> None:
    _BoomService.stream_calls = 0
    _BoomService.active_calls = 0
    client = _app_client()
    client.app.state.api.copilot_service = _BoomService()
    headers = _auth(client, username="blockedstream")
    response = client.post(
        "/api/v1/copilot/stream", headers=headers, json=_body()
    )
    assert response.status_code == 503
    assert "text/event-stream" not in response.headers.get("content-type", "")
    assert response.json()["detail"] == AI_PRODUCTION_BLOCKED_DETAIL
    assert _BoomService.stream_calls == 0
    assert _BoomService.active_calls == 0


def test_unauthenticated_does_not_call_provider() -> None:
    _BoomService.complete_calls = 0
    client = _app_client()
    client.app.state.api.copilot_service = _BoomService()
    response = client.post("/api/v1/copilot/complete", json=_body())
    assert response.status_code == 401
    assert _BoomService.complete_calls == 0


def test_ready_complete_invokes_provider_once() -> None:
    adapter = _RecordingAdapter()
    client = _app_client()
    client.app.state.api.activation_evidence = _ready_evidence()
    client.app.state.api.copilot_service = CopilotCompleteService(
        _AdapterRegistry(adapter)
    )
    headers = _auth(client, username="readycomplete")
    response = client.post(
        "/api/v1/copilot/complete", headers=headers, json=_body()
    )
    assert response.status_code == 200
    body = response.json()
    assert adapter.invoke_calls == 1
    assert body["provider_id"] == "openai"
    assert body["unavailable"] is False
    assert "fake provider" in body["content"]


def test_ready_stream_invokes_provider_once() -> None:
    adapter = _RecordingAdapter()
    client = _app_client()
    client.app.state.api.activation_evidence = _ready_evidence()
    client.app.state.api.copilot_service = CopilotCompleteService(
        _AdapterRegistry(adapter)
    )
    headers = _auth(client, username="readystream")
    response = client.post(
        "/api/v1/copilot/stream", headers=headers, json=_body()
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "data:" in response.text
    assert adapter.invoke_calls == 1


def test_ready_provider_failure_keeps_existing_deterministic_fallback() -> None:
    adapter = _FailingAdapter()
    client = _app_client()
    client.app.state.api.activation_evidence = _ready_evidence()
    client.app.state.api.copilot_service = CopilotCompleteService(
        _AdapterRegistry(adapter)
    )
    headers = _auth(client, username="readyfail")
    response = client.post(
        "/api/v1/copilot/complete", headers=headers, json=_body()
    )
    assert response.status_code == 200
    body = response.json()
    assert adapter.invoke_calls == 1
    assert body["provider_id"] == "deterministic"
    assert "Buy" in body["content"]
    assert any(
        item in body["limitations"]
        for item in ("LLM unavailable", "LLM invocation failed")
    )


def test_evaluate_activation_called_once_per_complete(
    monkeypatch: Any,
) -> None:
    calls: list[ActivationEvidence] = []
    real = evaluate_activation

    def _wrapped(evidence: ActivationEvidence) -> Any:
        calls.append(evidence)
        return real(evidence)

    monkeypatch.setattr(
        "api_platform.api.dependencies.evaluate_activation", _wrapped
    )
    client = _app_client()
    headers = _auth(client, username="guardonce")
    response = client.post(
        "/api/v1/copilot/complete", headers=headers, json=_body()
    )
    assert response.status_code == 503
    assert len(calls) == 1


def test_research_company_remains_blocked() -> None:
    client = _app_client()
    headers = _auth(client, username="researchstillblocked")
    response = client.post(
        "/api/v1/research/company",
        headers=headers,
        json={"ticker": "ACM", "exchange": "NYSE", "company": "Acme"},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["ai_execution_state"] == "ai_execution_blocked"
    assert body["report"] is None


def _depends_names(fn: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for default in fn.args.defaults:
        if (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id == "Depends"
            and default.args
            and isinstance(default.args[0], ast.Name)
        ):
            names.add(default.args[0].id)
    return names


def test_architecture_complete_and_stream_share_single_activation_dependency() -> None:
    tree = ast.parse(_COPILOT_ROUTER.read_text(encoding="utf-8-sig"))
    by_name = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    complete = by_name["copilot_complete"]
    stream = by_name["copilot_stream"]
    assert "require_live_ai_activation" in _depends_names(complete)
    assert "require_live_ai_activation" in _depends_names(stream)
    source = _COPILOT_ROUTER.read_text(encoding="utf-8-sig")
    assert "evaluate_activation(" not in source
    dep_source = _DEPENDENCIES.read_text(encoding="utf-8-sig")
    assert dep_source.count("evaluate_activation(") == 1
    assert "require_authenticated_actor" in _depends_names(
        next(
            node
            for node in ast.walk(ast.parse(dep_source))
            if isinstance(node, ast.FunctionDef)
            and node.name == "require_live_ai_activation"
        )
    )
