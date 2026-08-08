"""EPIC-A001 AI Research Copilot unit tests."""

from __future__ import annotations

import pytest

from dsp_platform.research_copilot import (
    COPILOT_SCHEMA_VERSION,
    UNAVAILABLE_MESSAGE,
    ask_research_copilot,
    build_prompt,
    build_research_context,
    copilot_response_from_dict,
    process_question,
    reset_conversation_store_for_tests,
    ConversationStore,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict
from dsp_platform.institutional_report import (
    generate_institutional_report,
    institutional_report_to_dict,
)

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_conversation_store_for_tests(ConversationStore())
    yield
    reset_conversation_store_for_tests(None)


def _ro() -> dict:
    return research_object_to_dict(
        build_research_object(
            symbol="AAPL",
            object_id="ro-copilot-1",
            created_at=FIXED,
            data_bundle={
                "identity": {
                    "symbol": "AAPL",
                    "ticker": "AAPL",
                    "company_name": "Apple Inc",
                },
                "market_quote": {
                    "status": {
                        "available": True,
                        "status": "ok",
                        "retrieved_at": FIXED,
                    },
                    "payload": {"fields": {"current_price": 190.5}},
                    "provenance": {"provider_id": "mq"},
                },
                "financial_statements": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "corporate_actions": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "historical_series": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
            },
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.25,
                },
                "stage_summaries": [
                    {"stage": "valuation", "has_result": True, "summary": "v"}
                ],
            },
        )
    )


def test_context_builder() -> None:
    ro = _ro()
    report = institutional_report_to_dict(
        generate_institutional_report(ro, report_id="rpt-c1", generated_at=FIXED)
    )
    ctx = build_research_context(
        research_object=ro, report=report, assembled_at=FIXED
    )
    assert ctx.research_object is not None
    assert ctx.report is not None
    assert ctx.source_refs["research_object_id"] == "ro-copilot-1"
    assert ctx.source_refs["report_id"] == "rpt-c1"


def test_prompt_builder() -> None:
    q = process_question("What is the current market price?")
    ctx = build_research_context(research_object=_ro(), assembled_at=FIXED)
    prompt = build_prompt(q, ctx)
    assert prompt["context_attached"] is True
    assert "research_object" in prompt["available_sources"]
    assert any("Data unavailable." in r for r in prompt["system_rules"])


def test_citation_mapping_and_answer() -> None:
    response = ask_research_copilot(
        "What is the current market price?",
        research_object=_ro(),
        response_id="resp-1",
        created_at=FIXED,
        conversation_id="conv-1",
    )
    assert response["schema_version"] == COPILOT_SCHEMA_VERSION
    assert response["unavailable"] is False
    assert any(c["section"] == "market_data" for c in response["citations"])
    assert "190.5" in response["answer"]
    assert response["provenance"]["providers_called"] is False


def test_missing_data() -> None:
    response = ask_research_copilot(
        "Show financial statements",
        research_object=_ro(),
        response_id="resp-2",
        created_at=FIXED,
    )
    assert UNAVAILABLE_MESSAGE in response["answer"]
    assert any(
        c["section"] == "financial_statements" and c["available"] is False
        for c in response["citations"]
    )


def test_no_context_unavailable() -> None:
    response = ask_research_copilot(
        "What is the price?",
        response_id="resp-3",
        created_at=FIXED,
    )
    assert response["unavailable"] is True
    assert response["answer"] == UNAVAILABLE_MESSAGE
    assert response["citations"] == []


def test_determinism() -> None:
    ro = _ro()
    a = ask_research_copilot(
        "margin of safety?",
        research_object=ro,
        response_id="resp-d",
        created_at=FIXED,
        conversation_id="conv-d",
    )
    reset_conversation_store_for_tests(ConversationStore())
    b = ask_research_copilot(
        "margin of safety?",
        research_object=ro,
        response_id="resp-d",
        created_at=FIXED,
        conversation_id="conv-d",
    )
    # Drop audit history_turns dependence by comparing core fields
    for key in ("answer", "citations", "prompt", "provenance", "question"):
        assert a[key] == b[key]


def test_serialization_roundtrip() -> None:
    response = ask_research_copilot(
        "company overview",
        research_object=_ro(),
        response_id="resp-s",
        created_at=FIXED,
    )
    from dsp_platform.research_copilot import copilot_response_to_dict

    restored = copilot_response_from_dict(response)
    assert copilot_response_to_dict(restored) == response


def test_provenance_audit() -> None:
    response = ask_research_copilot(
        "recommendation?",
        research_object=_ro(),
        response_id="resp-p",
        created_at=FIXED,
        conversation_id="conv-p",
    )
    assert response["audit"]["response_id"] == "resp-p"
    assert response["audit"]["conversation_id"] == "conv-p"
    assert response["provenance"]["engines_called"] is False
