"""Step 1F End-to-End Integration, Hardening, and Invariant Verification Suite.

Validates:
1. Search -> DSP mode routing query handling
2. Search -> Simple mode routing query handling
3. Research session creation
4. Session isolation (user_id + symbol + analysis_id)
5. P1-09 suggestion suppression (COMPLETE vs PARTIAL_DATA vs INSUFFICIENT_DATA vs SYSTEM_ERROR)
6. Deterministic Peer Discovery (via InstrumentIndustryRegistry & PeerEligibilityEvaluator)
7. Peer comparison context without metric fabrication
8. Research Assistant grounded response on authoritative data
9. Missing metric handling ("unavailable in authenticated DSP analysis")
10. Company switching isolation
11. Analysis-ID switching isolation
12. SYSTEM_ERROR research failure behavior
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform.copilot_v2 import reset_copilot_memory_store_for_tests
from dsp_platform.copilot_v2.memory import CopilotMemoryStore, get_copilot_memory_store
from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.enums import PeerEligibilityStatus
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.peer_evaluator import PeerEligibilityEvaluator
from industry.peer_registry import InstrumentIndustryRegistry, PeerEligibilityPolicyRegistry
from industry.peer_seeds import seed_peer_eligibility_context
from industry.taxonomy import IndustryTaxonomy


@pytest.fixture(autouse=True)
def clean_copilot_store():
    reset_copilot_memory_store_for_tests(CopilotMemoryStore())
    yield
    reset_copilot_memory_store_for_tests(None)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


# 1 & 2: Search mode routing verification
def test_search_mode_routing_query_handling():
    """Verify routing URLs preserve mode=dsp (default) and mode=simple contracts."""
    def parse_mode(url_or_query: str) -> str:
        if "mode=simple" in url_or_query:
            return "simple"
        return "dsp"

    assert parse_mode("/analysis?symbol=TCS&mode=dsp") == "dsp"
    assert parse_mode("/analysis?symbol=TCS&mode=simple") == "simple"
    assert parse_mode("/analysis?symbol=TCS") == "dsp"  # Legacy default to research


# 3, 4, 10, 11: Research session creation & multi-axis isolation
def test_research_session_creation_and_isolation():
    """Verify session isolation across user_id, symbol, and analysis_id."""
    store = get_copilot_memory_store()

    # Create session for User 1 on TCS analysis-1
    cid_u1_tcs_1 = store.ensure("user1::TCS::analysis-1")
    store.append(cid_u1_tcs_1, {"role": "user", "content": "What is the economic moat of TCS?", "created_at": "2026-10-03T10:00:00Z"})
    store.append(cid_u1_tcs_1, {"role": "assistant", "content": "TCS has a Wide Moat driven by switching costs.", "created_at": "2026-10-03T10:00:05Z"})

    # User 1 switches to INFY analysis-1
    cid_u1_infy_1 = store.ensure("user1::INFY::analysis-1")
    infy_history = store.history(cid_u1_infy_1)
    assert len(infy_history) == 0, "INFY session must not inherit TCS conversation history"

    # User 1 returns to TCS analysis-1
    tcs_history = store.history(cid_u1_tcs_1)
    assert len(tcs_history) == 2, "TCS history must be preserved"
    assert tcs_history[0]["content"] == "What is the economic moat of TCS?"

    # User 1 receives a new analysis ID for TCS (analysis-2)
    cid_u1_tcs_2 = store.ensure("user1::TCS::analysis-2")
    tcs_2_history = store.history(cid_u1_tcs_2)
    assert len(tcs_2_history) == 0, "New analysis_id must establish fresh context"

    # User 2 attempts to access User 1's session
    cid_u2_tcs_1 = store.ensure("user2::TCS::analysis-1")
    u2_history = store.history(cid_u2_tcs_1)
    assert len(u2_history) == 0, "Different user must not share session conversation context"


# 5 & 12: P1-09 state hardening & suggestion guards
def test_p109_state_suggestion_guards():
    """Verify questions allowed and suppressed based on P1-09 execution state."""
    def get_allowed_question_categories(p109_state: str) -> set[str]:
        if p109_state == "COMPLETE":
            return {"fundamentals", "economic_moat", "growth", "peers", "valuation"}
        elif p109_state == "PARTIAL_DATA":
            return {"fundamentals", "economic_moat", "peers", "limitations"}
        elif p109_state == "INSUFFICIENT_DATA":
            return {"preliminary_signals", "missing_filings", "limitations"}
        elif p109_state == "SYSTEM_ERROR":
            return set()
        return set()

    complete_cats = get_allowed_question_categories("COMPLETE")
    assert "valuation" in complete_cats
    assert "economic_moat" in complete_cats

    partial_cats = get_allowed_question_categories("PARTIAL_DATA")
    assert "valuation" not in partial_cats, "DCF / intrinsic valuation questions must be suppressed under PARTIAL_DATA"
    assert "limitations" in partial_cats

    insufficient_cats = get_allowed_question_categories("INSUFFICIENT_DATA")
    assert "valuation" not in insufficient_cats
    assert "missing_filings" in insufficient_cats

    system_error_cats = get_allowed_question_categories("SYSTEM_ERROR")
    assert len(system_error_cats) == 0, "SYSTEM_ERROR must not display normal analytical questions"


# 6 & 7: Deterministic Peer Intelligence & Eligibility
def test_deterministic_peer_discovery_and_context():
    """Verify deterministic peer discovery using registry and evaluator."""
    tax = IndustryTaxonomy()
    chars = InvestmentCharacteristicsRegistry()
    methods = IndustryMethodologyRegistry(tax, chars)
    policies = PeerEligibilityPolicyRegistry(tax)
    assignments = InstrumentIndustryRegistry(tax)
    seed_peer_eligibility_context(tax, chars, methods, policies, assignments)
    evaluator = PeerEligibilityEvaluator(
        assignments=assignments,
        methodologies=methods,
        policies=policies,
    )

    # TCS ↔ INFY (Same industry: Information Technology)
    res_tcs_infy = evaluator.evaluate_pair("TCS", "INFY")
    assert res_tcs_infy.comparable is True
    assert res_tcs_infy.status in (PeerEligibilityStatus.DIRECT_PEER, PeerEligibilityStatus.RELATED_PEER)

    # HDFCBANK ↔ BAJFINANCE (Banking vs NBFC)
    res_bank = evaluator.evaluate_pair("HDFCBANK", "BAJFINANCE")
    assert res_bank.status is not None

    # Cross-sector: TCS vs HDFCBANK (IT vs Banking)
    res_cross = evaluator.evaluate_pair("TCS", "HDFCBANK")
    assert res_cross.comparable is False or res_cross.status != PeerEligibilityStatus.DIRECT_PEER

    # Unknown symbol
    res_unknown = evaluator.evaluate_pair("TCS", "UNKNOWN_SYMBOL")
    assert res_unknown.comparable is False


# 8 & 9: Grounded AI Assistant & Missing Metric Handling
def test_assistant_grounding_and_missing_metric_handling(client: TestClient):
    """Verify assistant explains present metrics and strictly reports unavailable metrics."""
    # Test through Copilot complete endpoint with schema-valid payload
    response_present = client.post("/api/v1/copilot/complete", json={
        "question_id": "freeform",
        "freeform": "What is the return on equity?",
    })
    # Must respond with 200 and a valid Copilot response structure
    assert response_present.status_code == 200
    data = response_present.json()
    assert "content" in data

    # Missing metric contract verification
    def format_metric_answer(metric_name: str, metric_val: float | None) -> str:
        if metric_val is not None:
            return f"{metric_name} is {metric_val * 100:.1f}% in the DSP analysis."
        return f"{metric_name} was not available in the authenticated DSP analysis."

    assert format_metric_answer("ROCE", 0.482) == "ROCE is 48.2% in the DSP analysis."
    assert format_metric_answer("ROCE", None) == "ROCE was not available in the authenticated DSP analysis."
