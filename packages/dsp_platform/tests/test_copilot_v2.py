"""Unit + memory tests — RC1 Milestone 7 Copilot 2.0."""

from __future__ import annotations

import pytest

from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.copilot_v2 import (
    UNAVAILABLE_MESSAGE,
    get_copilot_memory_store,
    reset_copilot_memory_store_for_tests,
    run_copilot_v2,
)
from dsp_platform.copilot_v2.intent import classify_intent, extract_symbols
from dsp_platform.copilot_v2.memory import CopilotMemoryStore


@pytest.fixture
def platform() -> DSPPlatform:
    reset_copilot_memory_store_for_tests(CopilotMemoryStore())
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


def test_classify_intent_rules() -> None:
    assert classify_intent("Compare TCS vs Infosys") == "comparison"
    assert classify_intent("Explain DCF assumptions") == "valuation"
    assert classify_intent("What is the bull case?") == "committee"
    assert classify_intent("Where is concentration risk?") == "risk"
    assert classify_intent("Analyze my portfolio") == "portfolio"
    assert classify_intent("Summarize the annual report") == "document"
    assert classify_intent("Generate an investment memo") == "memo"
    assert classify_intent("Explain like Buffett") == "buffett"
    assert classify_intent("Analyze TCS", mode="company") == "company"


def test_extract_symbols() -> None:
    assert "TCS" in extract_symbols("Analyze TCS")
    assert extract_symbols("compare A vs B", hinted=["INFY"])[0] == "INFY"


def test_memory_persists_context_and_delete() -> None:
    store = CopilotMemoryStore()
    reset_copilot_memory_store_for_tests(store)
    cid = store.ensure(None)
    store.update_context(cid, {"current_company": "TCS", "previous_questions": ["q1"]})
    store.append(cid, {"role": "user", "message": "q1", "created_at": "t1"})
    assert store.get_context(cid)["current_company"] == "TCS"
    assert len(store.history(cid)) == 1
    assert store.list_conversations()
    assert store.delete(cid) is True
    assert store.delete(cid) is False


def test_valuation_unavailable_without_payload(platform: DSPPlatform) -> None:
    result = run_copilot_v2(
        platform=platform,
        message="Explain margin of safety",
        mode="valuation",
    )
    assert result["unavailable"] is True
    assert result["answer"] == UNAVAILABLE_MESSAGE


def test_valuation_explains_analyse_payload(platform: DSPPlatform) -> None:
    result = run_copilot_v2(
        platform=platform,
        message="Explain valuation",
        mode="valuation",
        analyse_response={
            "recommendation_summary": {"margin_of_safety": 0.22, "confidence": 0.7},
            "valuation": {"intrinsic_value": 100, "buffett_score": 72},
        },
    )
    assert result["unavailable"] is False
    assert "0.22" in result["answer"] or "22" in result["answer"]
    assert "100" in result["answer"]
    assert result["provenance"]["calculations_performed"] is False


def test_portfolio_reuses_pi(platform: DSPPlatform) -> None:
    result = run_copilot_v2(
        platform=platform,
        message="Analyze my portfolio",
        mode="portfolio",
        symbols=["AAPL", "MSFT"],
    )
    assert result["unavailable"] is False
    assert "Portfolio Intelligence" in result["answer"] or "Linked research" in result["answer"]
    assert any(s["engine"] == "portfolio_intelligence" for s in result["sources"])


def test_conversation_memory_retained(platform: DSPPlatform) -> None:
    first = run_copilot_v2(
        platform=platform,
        message="Analyze TCS",
        mode="company",
        symbols=["TCS"],
    )
    cid = first["conversation_id"]
    second = run_copilot_v2(
        platform=platform,
        message="Explain valuation",
        mode="valuation",
        conversation_id=cid,
        analyse_response={"recommendation_summary": {"margin_of_safety": 0.1}},
    )
    assert second["conversation_id"] == cid
    assert second["context"]["current_company"] == "TCS"
    assert len(get_copilot_memory_store().history(cid)) >= 4


def test_platform_history_api(platform: DSPPlatform) -> None:
    platform.run_copilot_v2(message="hi", mode="chat")
    rows = platform.list_copilot_history()
    assert rows
    cid = rows[0]["conversation_id"]
    detail = platform.get_copilot_history(cid)
    assert detail["turns"]
    assert platform.delete_copilot_history(cid) is True
