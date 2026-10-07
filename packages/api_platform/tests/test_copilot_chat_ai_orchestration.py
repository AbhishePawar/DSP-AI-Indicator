"""Task 62B — Comprehensive AI Provider Selection, Fallback, and Persistence Hardening."""

from __future__ import annotations

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
from llm_adapters.config import load_llm_config
from llm_adapters.orchestrator import (
    OrchestratorResult,
    OrchestratorStatus,
    UserResearchRequest,
)
from llm_adapters.privacy_boundary import PublicDecisionPack
from llm_adapters.quality_gate import GateOutcome, GateVerdict
from llm_adapters.model_tiers import ModelTier
from llm_adapters.registry import ProviderRegistry
from persistence.research_session import (
    ResearchSessionService,
    compute_session_id,
    reset_research_session_service_for_tests,
)
from persistence.storage import InMemoryStorageProvider


class MockProviderAdapter:
    """Mock ProviderAdapter implementing the production provider contract."""

    def __init__(
        self,
        provider_id: str,
        model_label: str = "mock-model",
        canned_response: str = "MOCK_DEFAULT_AI_RESPONSE",
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


def _build_test_app(base_platform, gemini_adapter: MockProviderAdapter, openai_adapter: MockProviderAdapter):
    """Wire real ProviderRegistry with injected adapters into the application."""
    app = create_app(platform=base_platform)
    registry = ProviderRegistry(load_llm_config())
    registry._adapters["gemini"] = gemini_adapter
    registry._adapters["openai"] = openai_adapter

    app.state.api.copilot_service._registry = registry
    app.state.api.provider_registry = registry
    app.state.api.language_model = None
    return app


# ---------------------------------------------------------------------------
# TEST 1: Minimal Real HTTP Gemini Proof Test (Cost Control Proof)
# ---------------------------------------------------------------------------


def test_minimal_http_gemini_success_proves_provider_registry(session_service, base_platform):
    """TEST 1: Authenticated POST /copilot/chat exercises ProviderRegistry -> Gemini mock -> HTTP 200."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_GEMINI_COPILOT_RESPONSE_001")
    openai_mock = MockProviderAdapter("openai", canned_response="MOCK_OPENAI_COPILOT_RESPONSE_001")

    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    user_id = "usr_min_proof"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Tell me about Reliance", "symbol": "RELIANCE", "analysis_id": "an-min-proof"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "MOCK_GEMINI_COPILOT_RESPONSE_001" in data["result"]["answer"]
    assert gemini_mock.call_count == 1
    assert openai_mock.call_count == 0


# ---------------------------------------------------------------------------
# TEST 2 & 3: Cost Control & OpenAI Fallback Path
# ---------------------------------------------------------------------------


def test_gemini_success_does_not_call_openai(session_service, base_platform):
    """TEST 2: Gemini success strictly avoids unnecessary OpenAI invocation."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_GEMINI_COST_CTRL")
    openai_mock = MockProviderAdapter("openai", canned_response="MOCK_OPENAI_COST_CTRL")

    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_cost", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "What is INFY revenue?", "symbol": "INFY", "analysis_id": "an-cost"},
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert openai_mock.call_count == 0
    assert "MOCK_GEMINI_COST_CTRL" in res.json()["result"]["answer"]


def test_openai_fallback_when_gemini_fails(session_service, base_platform):
    """TEST 3: When Gemini fails, ProviderRegistry falls back to OpenAI and returns OpenAI answer."""
    gemini_mock = MockProviderAdapter("gemini", should_fail=True)
    openai_mock = MockProviderAdapter("openai", canned_response="MOCK_OPENAI_COPILOT_RESPONSE_001")

    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_fb", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze INFY", "symbol": "INFY", "analysis_id": "an-fb"},
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert openai_mock.call_count == 1
    assert "MOCK_OPENAI_COPILOT_RESPONSE_001" in res.json()["result"]["answer"]


# ---------------------------------------------------------------------------
# TEST 4: Total AI Failure Path (Fail Closed Without Deterministic Bypass)
# ---------------------------------------------------------------------------


def test_total_ai_failure_fails_closed_no_deterministic_bypass(session_service, base_platform):
    """TEST 4: When all AI providers fail, returns sanitized AI-unavailable with no deterministic bypass."""
    failing_gemini = MockProviderAdapter("gemini", should_fail=True)
    failing_openai = MockProviderAdapter("openai", should_fail=True)

    app = _build_test_app(base_platform, failing_gemini, failing_openai)
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
    assert failing_gemini.call_count == 1
    assert failing_openai.call_count == 1
    # Ensure no deterministic company analysis bypassed AI
    assert "Company analysis for TCS" not in data["result"]["answer"]

    # Assistant turn persisted safely as unavailable failure event
    turns = session_service.get_turns(sid, user_id=user_id)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"
    assert "temporarily unavailable" in turns[1]["content"]
    assert turns[1].get("metadata", {}).get("failure_event") is True


# ---------------------------------------------------------------------------
# TESTS 5-12: Distinctive Mock AI Output Reaches User For Every Copilot Path
# ---------------------------------------------------------------------------


def test_company_overview_path_returns_ai_output(session_service, base_platform):
    """TEST 5: Company overview query invokes AI and returns distinctive output."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_AI_COMPANY_OVERVIEW_001")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_overview", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Give me an overview of TCS", "symbol": "TCS", "analysis_id": "an-overview"},
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert "MOCK_AI_COMPANY_OVERVIEW_001" in res.json()["result"]["answer"]


def test_financial_metrics_path_returns_ai_output(session_service, base_platform):
    """TEST 6: Financial metrics query invokes AI and returns distinctive output."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_AI_FINANCIAL_METRICS_001")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_metrics", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "What is the revenue and margin of Reliance?", "symbol": "RELIANCE", "analysis_id": "an-metrics"},
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert "MOCK_AI_FINANCIAL_METRICS_001" in res.json()["result"]["answer"]


def test_valuation_path_returns_ai_output(session_service, base_platform):
    """TEST 7: Valuation query invokes AI and returns distinctive output."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_AI_VALUATION_EXPLANATION_001")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
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
    assert gemini_mock.call_count == 1
    assert "MOCK_AI_VALUATION_EXPLANATION_001" in res.json()["result"]["answer"]


def test_recommendation_path_returns_ai_output(session_service, base_platform):
    """TEST 8: Recommendation query invokes AI and returns distinctive output."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_AI_RECOMMENDATION_001")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_rec", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Should I buy Reliance?", "symbol": "RELIANCE", "analysis_id": "an-rec"},
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert "MOCK_AI_RECOMMENDATION_001" in res.json()["result"]["answer"]


def test_portfolio_path_returns_ai_output(session_service, base_platform):
    """TEST 9: Portfolio query invokes AI and returns distinctive output."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_AI_PORTFOLIO_REVIEW_001")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_port", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Review my portfolio holdings",
            "symbol": "AAPL",
            "analysis_id": "an-port",
            "portfolio": {"holdings": [{"symbol": "AAPL", "weight": 1.0}]},
        },
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert "MOCK_AI_PORTFOLIO_REVIEW_001" in res.json()["result"]["answer"]


def test_buffett_path_returns_ai_output(session_service, base_platform):
    """TEST 10: Buffett query invokes AI and returns distinctive output."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_AI_BUFFETT_ANALYSIS_001")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
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
    assert gemini_mock.call_count == 1
    assert "MOCK_AI_BUFFETT_ANALYSIS_001" in res.json()["result"]["answer"]


def test_research_path_returns_orchestrator_output(session_service, base_platform):
    """TEST 11: Specialized research query routes to ResearchOrchestrator and returns AI output."""
    fake_orch = FakeResearchOrchestrator()
    gemini_mock = MockProviderAdapter("gemini")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    app.state.api.research_orchestrator = fake_orch
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_res", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Do deep research on Reliance", "symbol": "RELIANCE", "analysis_id": "an-res"},
    )
    assert res.status_code == 200
    assert fake_orch.call_count == 1
    assert "AI Research Analysis for RELIANCE" in res.json()["result"]["answer"]


def test_general_question_path_returns_ai_output(session_service, base_platform):
    """TEST 12: General question query invokes AI and returns distinctive output."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="MOCK_AI_GENERAL_QUESTION_001")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_gen", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "How does Reliance compete in retail?", "symbol": "RELIANCE", "analysis_id": "an-gen"},
    )
    assert res.status_code == 200
    assert gemini_mock.call_count == 1
    assert "MOCK_AI_GENERAL_QUESTION_001" in res.json()["result"]["answer"]


# ---------------------------------------------------------------------------
# TESTS 13-15: DSP Authority, Word Boundary, and Missing Values
# ---------------------------------------------------------------------------


def test_dsp_authority_overrides_conflicting_ai_values(session_service, base_platform):
    """TEST 13: Deliberately conflicting AI figures cannot override DSP authority."""
    conflicting_ai = MockProviderAdapter(
        "gemini",
        canned_response=(
            "AI Model Assessment: Intrinsic Value is 2500, Margin of Safety is 35%, and Recommendation is SELL."
        ),
    )
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, conflicting_ai, openai_mock)
    client = TestClient(app)

    user_id = "usr_auth_override"
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
            "analysis_id": "an-auth-override",
            "analyse_response": dsp_analyse,
        },
    )
    assert res.status_code == 200
    ans = res.json()["result"]["answer"]

    # Deterministic DSP authority preserved
    assert "**Authoritative Recommendation:** BUY" in ans
    assert "**Valuation:** 1842" in ans
    assert "**Margin of Safety:** 18%" in ans
    # AI conflicting recommendation SELL was replaced with authoritative BUY
    assert "SELL" not in ans


def test_regex_word_boundary_does_not_corrupt_subwords(session_service, base_platform):
    """TEST 14: Proper regex word boundary \b prevents matching inside words like BUYBACK."""
    ai_with_subword = MockProviderAdapter(
        "gemini",
        canned_response="The company announced a major share BUYBACK program for FY26.",
    )
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, ai_with_subword, openai_mock)
    client = TestClient(app)

    user_id = "usr_subword"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    dsp_analyse = {
        "recommendation_summary": {"decision": "HOLD", "label": "HOLD"},
        "valuation": {"intrinsic_value": "1000", "margin_of_safety": "5%"},
    }

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "What about buybacks?",
            "symbol": "TCS",
            "analysis_id": "an-subword",
            "analyse_response": dsp_analyse,
        },
    )
    assert res.status_code == 200
    ans = res.json()["result"]["answer"]

    # BUYBACK must NOT be corrupted to HOLDBACK
    assert "BUYBACK" in ans
    assert "HOLDBACK" not in ans


def test_missing_dsp_evidence_remains_unavailable_not_hallucinated(session_service, base_platform):
    """TEST 15: Missing DSP evidence remains 'Data unavailable' and is not invented."""
    mock_gemini = MockProviderAdapter("gemini", canned_response="I invented some comparison numbers")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, mock_gemini, openai_mock)
    client = TestClient(app)

    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": "usr_missing", "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Compare TCS vs INFY", "symbol": "TCS", "analysis_id": "an-comp"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["result"]["unavailable"] is True
    assert "Data unavailable" in data["result"]["answer"]


# ---------------------------------------------------------------------------
# TEST 16: Failure + Idempotency (Failure Does Not Poison Idempotency)
# ---------------------------------------------------------------------------


def test_failed_ai_does_not_poison_idempotency_and_retry_succeeds(session_service, base_platform):
    """TEST 16: Failed AI request does not replay as failure; fixed retry succeeds and binds idempotency."""
    failing_gemini = MockProviderAdapter("gemini", should_fail=True)
    failing_openai = MockProviderAdapter("openai", should_fail=True)

    app = _build_test_app(base_platform, failing_gemini, failing_openai)
    client = TestClient(app)

    user_id = "usr_idem_recovery"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}
    sid = compute_session_id(user_id, "AAPL", "an-recovery")

    # Attempt 1: Total AI failure
    res1 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-recovery"},
        headers={"Idempotency-Key": "key-fail-recover"},
    )
    assert res1.status_code == 200
    assert res1.json()["result"]["unavailable"] is True
    assert "temporarily unavailable" in res1.json()["result"]["answer"]

    # Check persistence: failure event recorded, not successful assistant answer
    turns1 = session_service.get_turns(sid, user_id=user_id)
    assert len(turns1) == 2
    assert turns1[1].get("metadata", {}).get("failure_event") is True
    assert turns1[1].get("metadata", {}).get("idempotency_key") is None

    # Now restore working AI provider
    working_gemini = MockProviderAdapter("gemini", canned_response="SUCCESSFUL_AI_RECOVERY_RESPONSE")
    app.state.api.provider_registry._adapters["gemini"] = working_gemini
    app.state.api.provider_registry._adapters["openai"] = MockProviderAdapter("openai")

    # Attempt 2: Retry with SAME idempotency key must NOT replay the failure
    res2 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-recovery"},
        headers={"Idempotency-Key": "key-fail-recover"},
    )
    assert res2.status_code == 200
    assert res2.json()["result"]["unavailable"] is False
    assert "SUCCESSFUL_AI_RECOVERY_RESPONSE" in res2.json()["result"]["answer"]
    assert working_gemini.call_count == 1

    # Attempt 3: Subsequent retry with same idempotency key now REPLAYS the successful answer
    res3 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-recovery"},
        headers={"Idempotency-Key": "key-fail-recover"},
    )
    assert res3.status_code == 200
    assert res3.json()["result"]["answer"] == res2.json()["result"]["answer"]
    # Working gemini was NOT invoked again
    assert working_gemini.call_count == 1
    assert res3.json()["result"]["provenance"]["replayed_from_idempotency"] is True


# ---------------------------------------------------------------------------
# TESTS 17-19: Authentication, Isolation, Secrets, and FIFO
# ---------------------------------------------------------------------------


def test_authentication_mandatory_and_session_isolated(session_service, base_platform):
    """TEST 17: Authentication is mandatory and cross-user sessions are strictly isolated."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="User isolated AI answer")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
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


def test_no_secrets_raw_payloads_prompts_leak(session_service, base_platform):
    """TEST 18: No API keys, tokens, Authorization headers, or internal prompts leak."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="Clean public answer with no secrets.")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
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
    assert "GEMINI_API_KEY" not in full_text
    assert "OPENAI_API_KEY" not in full_text
    assert "CRITICAL GOVERNANCE RULES" not in full_text
    assert "raw_provider_response" not in full_text


def test_fifo_turn_retention_preserved(session_service, base_platform):
    """TEST 19: 20-turn FIFO retention preserved across multiple AI queries."""
    gemini_mock = MockProviderAdapter("gemini", canned_response="Turn response")
    openai_mock = MockProviderAdapter("openai")
    app = _build_test_app(base_platform, gemini_mock, openai_mock)
    client = TestClient(app)

    user_id = "usr_fifo"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}
    sid = compute_session_id(user_id, "AAPL", "an-fifo")

    for i in range(12):
        res = client.post(
            "/api/v1/copilot/chat",
            json={"message": f"Query {i}", "symbol": "AAPL", "analysis_id": "an-fifo"},
        )
        assert res.status_code == 200

    # FIFO retention bounds turns to max 20
    turns = session_service.get_turns(sid, user_id=user_id)
    assert len(turns) <= 20
