"""Tests for llm_adapters deterministic composer and service."""

from __future__ import annotations

from llm_adapters.config import LLMPlatformConfig
from llm_adapters.deterministic_composer import (
    compose_deterministic_answer,
    extract_research_payload,
)
from llm_adapters.registry import ProviderRegistry
from llm_adapters.service import CopilotCompleteService


def _sample_request() -> dict:
    return {
        "ticker": "AAPL",
        "company": "Apple",
        "exchange": "NASDAQ",
        "intrinsic_value_per_share": 180.0,
        "current_market_price": 150.0,
    }


def _sample_response() -> dict:
    return {
        "ok": True,
        "payload": {
            "ok": True,
            "recommendation_summary": {
                "decision": "Buy",
                "confidence": 0.8,
                "margin_of_safety": 0.2,
            },
            "committee_summary": {
                "decision": "Approve",
                "confidence": 0.7,
            },
            "stage_summaries": [
                {
                    "stage": "economic_moat",
                    "status": "succeeded",
                    "has_result": True,
                    "label": "Wide",
                }
            ],
        },
    }


def test_extract_research_payload() -> None:
    payload = extract_research_payload(_sample_request(), _sample_response())
    assert payload.has_session is True
    assert payload.recommendation == "Buy"
    assert payload.ticker == "AAPL"


def test_deterministic_fallback_without_session() -> None:
    answer = compose_deterministic_answer(
        question_id="why_buy",
        freeform=None,
        research=extract_research_payload(None, None),
    )
    assert answer.unavailable is True


def test_service_uses_deterministic_when_no_api_keys(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = LLMPlatformConfig(
        default_provider="openai",
        openai_api_key=None,
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
    service = CopilotCompleteService(ProviderRegistry(config))
    result = service.complete(
        question_id="why_buy",
        freeform=None,
        request=_sample_request(),
        response=_sample_response(),
    )
    assert result.provider_id == "deterministic"
    assert "Buy" in result.content


def test_registry_lists_providers() -> None:
    registry = ProviderRegistry()
    providers = registry.list_providers()
    assert {p["id"] for p in providers} == {"openai", "anthropic", "gemini", "deepseek"}
