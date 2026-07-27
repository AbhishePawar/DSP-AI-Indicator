"""OpenAI adapter tests — no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.openai_adapter import OpenAIAdapter


def _config() -> LLMPlatformConfig:
    return LLMPlatformConfig(
        default_provider="openai",
        openai_api_key="test-key",
        anthropic_api_key=None,
        gemini_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude",
        gemini_model="gemini",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def test_openai_adapter_not_configured_without_key() -> None:
    config = _config()
    config = LLMPlatformConfig(
        default_provider="openai",
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        openai_model=config.openai_model,
        anthropic_model=config.anthropic_model,
        gemini_model=config.gemini_model,
        request_timeout_seconds=5.0,
        max_retries=0,
    )
    adapter = OpenAIAdapter(config)
    request = LanguageModelRequest(
        request_id="req-1",
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=("system", "user question"),
        context_digest_ids=("Recommendation",),
        provenance=("test",),
    )
    result = adapter.invoke(request)
    assert result.status == LanguageModelStatus.PROVIDER_UNAVAILABLE


def test_openai_adapter_parses_response() -> None:
    adapter = OpenAIAdapter(_config())
    request = LanguageModelRequest(
        request_id="req-2",
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=("system", "user question"),
        context_digest_ids=("Recommendation",),
        provenance=("test",),
    )
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Explanation text."}}]
    }
    with patch("llm_adapters.openai_adapter.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = mock_response
        result = adapter.invoke(request)
    assert result.status == LanguageModelStatus.COMPLETE
    assert result.narrative_text == "Explanation text."
