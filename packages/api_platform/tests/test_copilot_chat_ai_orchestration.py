"""Task 61 — Comprehensive AI-mandatory Copilot tests."""

from __future__ import annotations

import json
import uuid
import pytest
from starlette.testclient import TestClient

from api_platform import create_app
from api_platform.api.dependencies import require_authenticated_actor
from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.copilot_v2 import reset_copilot_memory_store_for_tests
from dsp_platform.copilot_v2.memory import CopilotMemoryStore
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.model_tiers import ModelTier
from llm_adapters.orchestrator import (
    OrchestratorResult,
    OrchestratorStatus,
    UserResearchRequest,
)
from llm_adapters.privacy_boundary import PublicDecisionPack
from persistence.research_session import (
    ResearchSessionService,
    compute_session_id,
    reset_research_session_service_for_tests,
)
from persistence.storage import InMemoryStorageProvider


class MockProviderAdapter:
    """Mock ProviderAdapter implementing the provider contract."""

    def __init__(
        self,
        provider_id: str,
        model_label: str = "mock-model",
        canned_response: str = "MOCK_AI_COPILOT_RESPONSE_123",
        should_fail: bool = False,
    ):
        self.provider_id = provider_id
        self.model_label = model_label
        self.canned_response = canned_response
        self.should_fail = should_fail
        self.call_count = 0
        self.invoked_requests: list[LanguageModelRequest] = []

    def is_configured(self) -> bool:
        return True

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        self.call_count += 1
        self.invoked_requests.append(request)
        if self.should_fail:
            return LanguageModelResult(
                result_id=str(uuid.uuid4()),
                status=LanguageModelStatus.FAILED,
                provenance=("mock", "failure"),
                narrative_text=None,
                limitations=("Mock provider failed",),
            )
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.COMPLETE,
            provenance=("mock", self.provider_id),
            narrative_text=self.canned_response,
            limitations=(),
        )


class MockProviderRegistry:
    """Mock ProviderRegistry with configurable providers and direct fallback."""

    def __init__(
        self,
        adapters: dict[str, MockProviderAdapter] | None = None,
        default_provider: str = "gemini",
    ):
        self._adapters = adapters or {}
        self._config = LLMPlatformConfig(
            default_provider=default_provider,  # type: ignore[arg-type]
            openai_api_key="mock",
            anthropic_api_key=None,
            gemini_api_key="mock",
            deepseek_api_key=None,
            ai_gateway_api_key=None,
            ai_gateway_base_url="https://ai-gateway.example/v1",
            openai_model="gpt-4.1-mini",
            anthropic_model="claude-3-5-sonnet-20241022",
            gemini_model="gemini-3.1-flash-lite",
            deepseek_model="deepseek-chat",
            request_timeout_seconds=30.0,
            max_retries=1,
        )

    @property
    def config(self) -> LLMPlatformConfig:
        return self._config

    def get(self, provider_id: str):
        return self._adapters.get(provider_id)

    def direct_fallback(self, provider_id: str):
        return None


class FakeResearchOrchestrator:
    """Deterministic fake for testing Copilot -> ResearchOrchestrator boundary."""

    def __init__(
        self,
        *,
        status: OrchestratorStatus = OrchestratorStatus.ACCEPTED,
        fail: bool = False,
        public_pack: PublicDecisionPack | None = None,
    ):
        self.status = status
        self.fail = fail
        self.public_pack = public_pack or PublicDecisionPack(
            recommendation="AI Buy",
            valuation="150.0",
            analysis="AI research analysis confirms solid competitive position.",
            risks=("Supply chain concentration",),
            evidence_citations=("dsp.valuation", "dsp.financial_statements"),
            confidence=0.88,
            limitations=("No forward guidance",),
            schema_version="public_decision_pack_v1",
        )
        self.call_count = 0
        self.last_request: UserResearchRequest | None = None

    def run(self, request: UserResearchRequest) -> OrchestratorResult:
        self.call_count += 1
        self.last_request = request
        if self.fail:
            raise RuntimeError("Provider dual verification failed closed")
        from llm_adapters.quality_gate import GateOutcome, GateVerdict

        verdict = GateVerdict(
            outcome=GateOutcome.ACCEPTED if self.status == OrchestratorStatus.ACCEPTED else GateOutcome.FAILED_CLOSED,
            tier=ModelTier.PREMIUM,
            reason="verified",
            quality_score=100.0,
            meets_floor=True,
            requires_escalation=False,
        )
        return OrchestratorResult(
            status=self.status,
            public=self.public_pack if self.status == OrchestratorStatus.ACCEPTED else None,
            private=None,
            gate=verdict,
        )


@pytest.fixture
def session_service():
    storage = InMemoryStorageProvider()
    service = ResearchSessionService(storage)
    reset_research_session_service_for_tests(service)
    reset_copilot_memory_store_for_tests(CopilotMemoryStore())
    return service


@pytest.fixture
def base_platform():
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


# ---------------------------------------------------------------------------
# TESTS 1-10: Every Copilot request invokes AI & returns AI-generated content
# ---------------------------------------------------------------------------


def test_standard_company_query_invokes_ai_and_returns_content(session_service, base_platform):
    """TEST 1 & 2 & 10: Standard company query reaches AI provider and returns AI content."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="MOCK_AI_COPILOT_RESPONSE_123")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    user_id = "usr_ai_std"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Tell me about Reliance", "symbol": "RELIANCE", "analysis_id": "an-ai-std"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert mock_adapter.call_count == 1
    assert "MOCK_AI_COPILOT_RESPONSE_123" in data["result"]["answer"]
    assert any(s.get("engine") == "ai_provider" for s in data["result"]["sources"])


def test_company_overview_invokes_ai(session_service, base_platform):
    """TEST 3: Company overview query invokes AI."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="AI Overview of TCS")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_tcs", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Give me an overview of TCS", "symbol": "TCS", "analysis_id": "an-tcs"},
    )
    assert res.status_code == 200
    assert mock_adapter.call_count == 1
    assert "AI Overview of TCS" in res.json()["result"]["answer"]


def test_financial_metric_query_invokes_ai(session_service, base_platform):
    """TEST 4: Financial metrics query invokes AI to explain evidence."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="AI explains revenue metrics")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_fin", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "What is the revenue of Reliance?", "symbol": "RELIANCE", "analysis_id": "an-fin"},
    )
    assert res.status_code == 200
    assert mock_adapter.call_count == 1
    assert "AI explains revenue metrics" in res.json()["result"]["answer"]


def test_valuation_query_invokes_ai(session_service, base_platform):
    """TEST 5: Valuation query invokes AI."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="AI explains intrinsic valuation calculation")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_val", "user": {}}

    dsp_analyse = {
        "valuation": {"intrinsic_value": "1842", "margin_of_safety": "18%"},
        "recommendation_summary": {"decision": "BUY", "label": "BUY"},
    }

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "What is the intrinsic value of Reliance?",
            "symbol": "RELIANCE",
            "analysis_id": "an-val",
            "analyse_response": dsp_analyse,
        },
    )
    assert res.status_code == 200
    assert mock_adapter.call_count == 1
    assert "AI explains intrinsic valuation" in res.json()["result"]["answer"]


def test_recommendation_query_invokes_ai(session_service, base_platform):
    """TEST 6: Recommendation query invokes AI."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="AI explains recommendation reasoning")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_rec", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Should I buy Reliance?", "symbol": "RELIANCE", "analysis_id": "an-rec"},
    )
    assert res.status_code == 200
    assert mock_adapter.call_count == 1
    assert "AI explains recommendation reasoning" in res.json()["result"]["answer"]


def test_portfolio_query_invokes_ai(session_service, base_platform):
    """TEST 7: Portfolio query invokes AI."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="AI analyzes portfolio holdings")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_port", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Review my portfolio",
            "symbol": "AAPL",
            "analysis_id": "an-port",
            "portfolio": {"holdings": [{"symbol": "AAPL", "weight": 1.0}]},
        },
    )
    assert res.status_code == 200
    assert mock_adapter.call_count == 1
    assert "AI analyzes portfolio holdings" in res.json()["result"]["answer"]


def test_buffett_query_invokes_ai(session_service, base_platform):
    """TEST 8: Buffett query invokes AI with Buffett principles."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="Buffett AI: Rule No. 1 is never lose money.")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_buf", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Analyse Reliance using Buffett principles",
            "symbol": "RELIANCE",
            "analysis_id": "an-buf",
            "buffett_mode": True,
        },
    )
    assert res.status_code == 200
    assert mock_adapter.call_count == 1
    assert "Buffett AI" in res.json()["result"]["answer"]


def test_research_query_invokes_orchestrator(session_service, base_platform):
    """TEST 9: Research query invokes existing ResearchOrchestrator."""
    fake_orch = FakeResearchOrchestrator()
    app = create_app(platform=base_platform)
    app.state.api.research_orchestrator = fake_orch
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_res", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Do deep research on Reliance",
            "symbol": "RELIANCE",
            "analysis_id": "an-res",
        },
    )
    assert res.status_code == 200
    assert fake_orch.call_count == 1
    assert "AI Research Analysis for RELIANCE" in res.json()["result"]["answer"]


# ---------------------------------------------------------------------------
# TESTS 11-14: Provider selection (Gemini preferred), Fallback, Fail Closed
# ---------------------------------------------------------------------------


def test_gemini_preferred_and_selected(session_service, base_platform):
    """TEST 11: Gemini lowest-cost provider is preferred by default registry."""
    gemini_mock = MockProviderAdapter("gemini", model_label="gemini-3.1-flash-lite", canned_response="Response from Gemini")
    openai_mock = MockProviderAdapter("openai", model_label="gpt-4.1-mini", canned_response="Response from OpenAI")

    registry = MockProviderRegistry(
        adapters={"gemini": gemini_mock, "openai": openai_mock},
        default_provider="gemini",
    )

    app = create_app(platform=base_platform)
    app.state.api.copilot_service._registry = registry
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_pref", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze INFY", "symbol": "INFY", "analysis_id": "an-pref"},
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert openai_mock.call_count == 0
    assert "Response from Gemini" in res.json()["result"]["answer"]


def test_openai_fallback_when_gemini_fails(session_service, base_platform):
    """TEST 12: OpenAI fallback works when Gemini fails."""
    failing_gemini = MockProviderAdapter("gemini", should_fail=True)
    working_openai = MockProviderAdapter("openai", canned_response="Response from OpenAI Fallback")

    registry = MockProviderRegistry(
        adapters={"gemini": failing_gemini, "openai": working_openai},
        default_provider="gemini",
    )

    app = create_app(platform=base_platform)
    app.state.api.copilot_service._registry = registry
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_fb", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze INFY", "symbol": "INFY", "analysis_id": "an-fb"},
    )
    assert res.status_code == 200
    assert failing_gemini.call_count == 1
    assert working_openai.call_count == 1
    assert "Response from OpenAI Fallback" in res.json()["result"]["answer"]


def test_total_ai_failure_fails_closed_no_deterministic_bypass(session_service, base_platform):
    """TEST 13 & 14: When all AI providers fail, Copilot fails closed without deterministic bypass."""
    failing_gemini = MockProviderAdapter("gemini", should_fail=True)
    failing_openai = MockProviderAdapter("openai", should_fail=True)

    registry = MockProviderRegistry(
        adapters={"gemini": failing_gemini, "openai": failing_openai},
        default_provider="gemini",
    )

    app = create_app(platform=base_platform)
    app.state.api.copilot_service._registry = registry
    client = TestClient(app)

    user_id = "usr_fail_closed"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}
    sid = compute_session_id(user_id, "TCS", "an-fc")

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze TCS", "symbol": "TCS", "analysis_id": "an-fc"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["result"]["unavailable"] is True
    assert "AI Copilot is temporarily unavailable" in data["result"]["answer"]
    # Ensure no deterministic company analysis bypassed AI
    assert "Company analysis for TCS" not in data["result"]["answer"]

    # Assistant turn persisted safely as unavailable
    turns = session_service.get_turns(sid, user_id=user_id)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"
    assert "temporarily unavailable" in turns[1]["content"]


# ---------------------------------------------------------------------------
# TESTS 15-19: DSP Authority preservation & missing evidence handling
# ---------------------------------------------------------------------------


def test_ai_cannot_override_intrinsic_value_mos_or_recommendation(session_service, base_platform):
    """TEST 15 & 16 & 17 & 18: DSP intrinsic value, margin of safety, and recommendation cannot be overridden."""
    hallucinating_ai = MockProviderAdapter(
        "gemini",
        canned_response=(
            "AI Model claims: Intrinsic Value is 2100, Margin of Safety is 25%, and my Recommendation is HOLD."
        ),
    )
    app = create_app(platform=base_platform)
    app.state.api.language_model = hallucinating_ai
    client = TestClient(app)

    user_id = "usr_auth_check"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    dsp_analyse = {
        "recommendation_summary": {
            "decision": "BUY",
            "label": "BUY",
            "margin_of_safety": "18%",
            "intrinsic_value": "1842",
        },
        "valuation": {
            "intrinsic_value": "1842",
            "margin_of_safety": "18%",
        },
    }

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "What is the valuation?",
            "symbol": "RELIANCE",
            "analysis_id": "an-auth-check",
            "analyse_response": dsp_analyse,
        },
    )
    assert res.status_code == 200
    ans = res.json()["result"]["answer"]

    # Authoritative DSP numbers MUST be preserved
    assert "**Authoritative Recommendation:** BUY" in ans
    assert "**Valuation:** 1842" in ans
    assert "**Margin of Safety:** 18%" in ans

    # Conflicting recommendation was sanitized
    assert "Recommendation is BUY" in ans or "**Authoritative Recommendation:** BUY" in ans


def test_missing_dsp_evidence_remains_unavailable_not_hallucinated(session_service, base_platform):
    """TEST 19: Missing DSP evidence remains 'Data unavailable' and is not invented."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="I invented some numbers")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_missing", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Compare TCS vs INFY", "symbol": "TCS", "analysis_id": "an-comp"},
    )
    assert res.status_code == 200
    data = res.json()
    # Comparison without comparison payloads produces unavailable
    assert data["result"]["unavailable"] is True
    assert "Data unavailable" in data["result"]["answer"]


# ---------------------------------------------------------------------------
# TESTS 20-23: Secret and payload isolation
# ---------------------------------------------------------------------------


def test_no_secrets_raw_payloads_prompts_or_disagreement_leak(session_service, base_platform):
    """TEST 20 & 21 & 22 & 23: No API keys, raw provider payloads, internal prompts, or disagreement reach client."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="Clean public answer.")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_sec", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-sec"},
    )
    assert res.status_code == 200
    full_text = res.text

    assert "Authorization" not in full_text
    assert "Bearer" not in full_text
    assert "api_key" not in full_text
    assert "sk-" not in full_text
    assert "CRITICAL GOVERNANCE RULES" not in full_text
    assert "raw_provider_response" not in full_text
    assert "disagreement" not in full_text
    assert "cross_verification_dispute" not in full_text


# ---------------------------------------------------------------------------
# TESTS 24-28: Authentication, Isolation, Idempotency, Durability, FIFO
# ---------------------------------------------------------------------------


def test_authentication_mandatory_and_session_isolated(session_service, base_platform):
    """TEST 24 & 25 & 27: Authentication is mandatory and cross-user sessions isolated."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="Hello AI")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    # 1. Unauthenticated fails 401
    res_unauth = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-iso"},
    )
    assert res_unauth.status_code == 401

    # 2. User A
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "user_1", "user": {}}
    res_a = client.post(
        "/api/v1/copilot/chat",
        json={"message": "User 1 query", "symbol": "AAPL", "analysis_id": "an-iso"},
    )
    assert res_a.status_code == 200
    sid_a = res_a.json()["result"]["conversation_id"]

    # 3. User B
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "user_2", "user": {}}
    res_b = client.post(
        "/api/v1/copilot/chat",
        json={"message": "User 2 query", "symbol": "AAPL", "analysis_id": "an-iso"},
    )
    assert res_b.status_code == 200
    sid_b = res_b.json()["result"]["conversation_id"]

    assert sid_a != sid_b
    turns_a = session_service.get_turns(sid_a, user_id="user_1")
    turns_b = session_service.get_turns(sid_b, user_id="user_2")
    assert len(turns_a) == 2
    assert len(turns_b) == 2


def test_idempotency_replay_preserves_ai_answer(session_service, base_platform):
    """TEST 26: Idempotency replay returns exact same AI answer without re-invoking AI."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="Deterministic AI Answer")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    user_id = "usr_idem_ai"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    # Call 1
    res1 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-idem"},
        headers={"Idempotency-Key": "key-ai-100"},
    )
    assert res1.status_code == 200
    assert mock_adapter.call_count == 1
    ans1 = res1.json()["result"]["answer"]

    # Call 2 with replay
    res2 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-idem"},
        headers={"Idempotency-Key": "key-ai-100"},
    )
    assert res2.status_code == 200
    # Provider not invoked again
    assert mock_adapter.call_count == 1
    assert res2.json()["result"]["answer"] == ans1
    assert res2.json()["result"]["provenance"]["replayed_from_idempotency"] is True


def test_fifo_turn_retention_preserved(session_service, base_platform):
    """TEST 28: 20-turn FIFO retention preserved across multiple AI queries."""
    mock_adapter = MockProviderAdapter("gemini", canned_response="Turn response")
    app = create_app(platform=base_platform)
    app.state.api.language_model = mock_adapter
    client = TestClient(app)

    user_id = "usr_fifo"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}
    sid = compute_session_id(user_id, "AAPL", "an-fifo")

    # Perform 12 queries (24 turns total)
    for i in range(12):
        res = client.post(
            "/api/v1/copilot/chat",
            json={"message": f"Query {i}", "symbol": "AAPL", "analysis_id": "an-fifo"},
        )
        assert res.status_code == 200

    # FIFO retention bounds turns to max 20
    turns = session_service.get_turns(sid, user_id=user_id)
    assert len(turns) <= 20
