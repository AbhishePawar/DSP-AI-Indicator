import json
import pytest
from starlette.testclient import TestClient

from api_platform import create_app
from api_platform.api.dependencies import require_authenticated_actor
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.copilot_v2 import reset_copilot_memory_store_for_tests
from dsp_platform.copilot_v2.memory import CopilotMemoryStore
from llm_adapters.model_tiers import ModelTier
from llm_adapters.orchestrator import (
    AICompletion,
    OrchestratorResult,
    OrchestratorStatus,
    ResearchOrchestrator,
    UserResearchRequest,
)
from llm_adapters.privacy_boundary import PublicDecisionPack
from persistence.research_session import (
    ResearchSessionService,
    compute_session_id,
    reset_research_session_service_for_tests,
)
from persistence.storage import InMemoryStorageProvider


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
        from llm_adapters.model_tiers import ModelTier
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


def test_durable_copilot_calls_ai_orchestration(session_service, base_platform):
    """TEST 1: Durable Copilot reaches ResearchOrchestrator when AI research is requested."""
    fake_orch = FakeResearchOrchestrator()
    app = create_app(platform=base_platform)
    app.state.api.research_orchestrator = fake_orch
    client = TestClient(app)

    user_id = "usr_orch_1"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Conduct AI research on AAPL", "symbol": "AAPL", "analysis_id": "an-ai-1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    ans = data["result"]["answer"]
    assert "AI Research Analysis for AAPL" in ans
    assert "solid competitive position" in ans

    # Orchestrator was actually invoked with correct request parameters
    assert fake_orch.call_count == 1
    assert fake_orch.last_request is not None
    assert fake_orch.last_request.symbol == "AAPL"
    assert "AI research" in fake_orch.last_request.question

    # Sources record dual verification and evidence citations
    sources = data["result"]["sources"]
    source_names = [s.get("engine") for s in sources]
    assert "research_orchestrator" in source_names
    assert "dsp_evidence" in source_names


def test_deterministic_company_query_does_not_require_live_ai(session_service, base_platform):
    """TEST 2: Standard deterministic company Copilot request succeeds without AI."""
    fake_orch = FakeResearchOrchestrator()
    app = create_app(platform=base_platform)
    app.state.api.research_orchestrator = fake_orch
    client = TestClient(app)

    user_id = "usr_det_1"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Analyze AAPL", "symbol": "AAPL", "analysis_id": "an-det-1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    # Standard company query used deterministic handler, orchestrator not invoked
    assert fake_orch.call_count == 0


def test_ai_research_fails_closed_when_orchestrator_fails(session_service, base_platform):
    """TEST 3: When AI research is requested and orchestrator fails, fail closed safely."""
    fake_orch = FakeResearchOrchestrator(fail=True)
    app = create_app(platform=base_platform)
    app.state.api.research_orchestrator = fake_orch
    client = TestClient(app)

    user_id = "usr_fail_closed"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}
    sid = compute_session_id(user_id, "AAPL", "an-fail-closed")

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Conduct AI research on AAPL", "symbol": "AAPL", "analysis_id": "an-fail-closed"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["result"]["unavailable"] is True
    assert "Data unavailable" in data["result"]["answer"]

    # Durable turn persisted as unavailable
    turns = session_service.get_turns(sid, user_id=user_id)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"


def test_ai_cannot_override_dsp_authority(session_service, base_platform):
    """TEST 4: AI returned Sell and 50.0, but deterministic DSP returned Strong Buy, 185.0, and 35.5%."""
    conflicting_pack = PublicDecisionPack(
        recommendation="Sell",
        valuation="50.0",
        analysis="AI suggests selling.",
        risks=("Risk of loss",),
        evidence_citations=("dsp.valuation",),
        confidence=0.85,
        limitations=(),
        schema_version="public_decision_pack_v1",
    )
    fake_orch = FakeResearchOrchestrator(public_pack=conflicting_pack)
    app = create_app(platform=base_platform)
    app.state.api.research_orchestrator = fake_orch
    client = TestClient(app)

    user_id = "usr_dsp_auth"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    # DSP analyse_response with authoritative Strong Buy, 35.5% MoS, 185.0 IV
    dsp_analyse = {
        "recommendation_summary": {
            "label": "Strong Buy",
            "decision": "Strong Buy",
            "margin_of_safety": "35.5%",
            "intrinsic_value": "185.0",
            "confidence": "High",
        },
        "valuation": {
            "intrinsic_value": "185.0",
            "margin_of_safety": "35.5%",
        },
    }

    res = client.post(
        "/api/v1/copilot/chat",
        json={
            "message": "Conduct deep research on AAPL",
            "symbol": "AAPL",
            "analysis_id": "an-dsp-override",
            "analyse_response": dsp_analyse,
        },
    )
    assert res.status_code == 200
    data = res.json()
    ans = data["result"]["answer"]

    # DSP recommendation, valuation, and margin of safety override AI outputs
    assert "**Authoritative Recommendation:** Strong Buy" in ans
    assert "**Valuation:** 185.0" in ans
    assert "**Margin of Safety:** 35.5%" in ans
    assert "Sell" not in ans
    assert "50.0" not in ans


def test_secrets_and_raw_payloads_isolated(session_service, base_platform):
    """TEST 5: Confirm no API keys, internal prompts, or raw payloads reach client."""
    fake_orch = FakeResearchOrchestrator()
    app = create_app(platform=base_platform)
    app.state.api.research_orchestrator = fake_orch
    client = TestClient(app)

    user_id = "usr_secret_iso"
    app.dependency_overrides[require_authenticated_actor] = lambda: {"user_id": user_id, "user": {}}

    res = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Conduct AI research on AAPL", "symbol": "AAPL", "analysis_id": "an-sec-1"},
    )
    assert res.status_code == 200
    text_content = res.text

    assert "Authorization" not in text_content
    assert "Bearer" not in text_content
    assert "api_key" not in text_content
    assert "PRIVATE_PROMPT" not in text_content
    assert "internal_prompt" not in text_content
    assert "chain_of_thought" not in text_content
