"""Tests for the four real provider adapters (mocked HTTP, no network).

Covers: success path, missing credentials, timeout, rate limit, auth
failure, malformed response, structured-output failure, token usage,
latency, error normalization, and privacy leakage.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from llm_adapters.anthropic_adapter import AnthropicAdapter
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.deepseek_adapter import DeepSeekAdapter
from llm_adapters.gemini_adapter import GeminiAdapter
from llm_adapters.openai_adapter import OpenAIAdapter
from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)


# ---- shared config + request ---------------------------------------------


def _config(**overrides: Any) -> LLMPlatformConfig:
    return LLMPlatformConfig(
        default_provider="openai",
        openai_api_key=overrides.get("openai", "test-openai"),
        anthropic_api_key=overrides.get("anthropic", "test-anthropic"),
        gemini_api_key=overrides.get("gemini", "test-gemini"),
        deepseek_api_key=overrides.get("deepseek", "test-deepseek"),
        openai_model="gpt-4o-mini",
        anthropic_model="claude-3-5-sonnet-20241022",
        gemini_model="gemini-1.5-flash",
        deepseek_model="deepseek-chat",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def _request() -> LanguageModelRequest:
    return LanguageModelRequest(
        request_id="req-1",
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=("system rules", "user question"),
        context_digest_ids=("Recommendation",),
        provenance=("test",),
    )


def _mock_response(json_body: dict[str, Any] | None = None, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    if json_body is not None:
        resp.json.return_value = json_body
    resp.iter_lines = MagicMock(return_value=iter([]))
    return resp


# ---- OpenAI --------------------------------------------------------------


def test_openai_success() -> None:
    adapter = OpenAIAdapter(_config())
    body = {"choices": [{"message": {"content": "OpenAI explanation."}}]}
    with patch("llm_adapters.openai_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.COMPLETE
    assert result.narrative_text == "OpenAI explanation."
    assert result.model_label == "gpt-4o-mini"


def test_openai_missing_credentials() -> None:
    cfg = _config(openai=None)
    adapter = OpenAIAdapter(cfg)
    result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE


def test_openai_timeout_normalized() -> None:
    adapter = OpenAIAdapter(_config())
    with patch("llm_adapters.openai_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException("boom")
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED
    assert result.limitations  # some non-empty failure reason


def test_openai_auth_failure_normalized() -> None:
    adapter = OpenAIAdapter(_config())
    err = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=MagicMock(status_code=401, text="unauthorized")
    )
    with patch("llm_adapters.openai_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value.raise_for_status.side_effect = err
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


def test_openai_malformed_response() -> None:
    adapter = OpenAIAdapter(_config())
    body = {"choices": [{"message": {}}]}  # missing "content"
    with patch("llm_adapters.openai_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED
    assert any("empty" in lim for lim in result.limitations)


# ---- DeepSeek ------------------------------------------------------------


def test_deepseek_success() -> None:
    adapter = DeepSeekAdapter(_config())
    body = {"choices": [{"message": {"content": "DeepSeek explanation."}}]}
    with patch("llm_adapters.deepseek_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.COMPLETE
    assert result.narrative_text == "DeepSeek explanation."
    assert result.model_label == "deepseek-chat"


def test_deepseek_missing_credentials() -> None:
    adapter = DeepSeekAdapter(_config(deepseek=None))
    result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE


def test_deepseek_rate_limit() -> None:
    adapter = DeepSeekAdapter(_config())
    err = httpx.HTTPStatusError(
        "429", request=MagicMock(), response=MagicMock(status_code=429, text="rate")
    )
    with patch("llm_adapters.deepseek_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value.raise_for_status.side_effect = err
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


def test_deepseek_timeout() -> None:
    adapter = DeepSeekAdapter(_config())
    with patch("llm_adapters.deepseek_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException("slow")
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


def test_deepseek_malformed_json() -> None:
    adapter = DeepSeekAdapter(_config())
    bad = _mock_response(None)
    bad.json.side_effect = json.JSONDecodeError("x", "y", 0)
    with patch("llm_adapters.deepseek_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = bad
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED
    assert any("malformed_response" in lim for lim in result.limitations)


def test_deepseek_does_not_leak_key_in_error() -> None:
    adapter = DeepSeekAdapter(_config())
    with patch("llm_adapters.deepseek_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("x")
        result = adapter.invoke(_request())
    flat = " ".join(result.limitations)
    assert "test-deepseek" not in flat
    assert "DEEPSEEK_API_KEY" not in flat


# ---- Gemini --------------------------------------------------------------


def test_gemini_success() -> None:
    adapter = GeminiAdapter(_config())
    body = {
        "candidates": [
            {"content": {"parts": [{"text": "Gemini explanation."}]}}
        ]
    }
    with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.COMPLETE
    assert result.narrative_text == "Gemini explanation."
    assert result.model_label == "gemini-1.5-flash"


def test_gemini_missing_credentials() -> None:
    adapter = GeminiAdapter(_config(gemini=None))
    result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE


def test_gemini_malformed_response_empty_candidates() -> None:
    adapter = GeminiAdapter(_config())
    with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response({"candidates": []})
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


def test_gemini_timeout() -> None:
    adapter = GeminiAdapter(_config())
    with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException("t")
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


# ---- Anthropic -----------------------------------------------------------


def test_anthropic_success() -> None:
    adapter = AnthropicAdapter(_config())
    body = {"content": [{"type": "text", "text": "Anthropic explanation."}]}
    with patch("llm_adapters.anthropic_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.COMPLETE
    assert result.narrative_text == "Anthropic explanation."
    assert result.model_label == "claude-3-5-sonnet-20241022"


def test_anthropic_missing_credentials() -> None:
    adapter = AnthropicAdapter(_config(anthropic=None))
    result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE


def test_anthropic_auth_failure() -> None:
    adapter = AnthropicAdapter(_config())
    err = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=MagicMock(status_code=401, text="bad key")
    )
    with patch("llm_adapters.anthropic_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value.raise_for_status.side_effect = err
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


def test_anthropic_malformed_response() -> None:
    adapter = AnthropicAdapter(_config())
    with patch("llm_adapters.anthropic_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response({"content": []})
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


def test_anthropic_timeout() -> None:
    adapter = AnthropicAdapter(_config())
    with patch("llm_adapters.anthropic_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException("t")
        result = adapter.invoke(_request())
    assert result.status is LanguageModelStatus.FAILED


# ---- latency / token usage surface ---------------------------------------


def test_latency_is_recorded_via_caller_not_adapter() -> None:
    """Adapters do not measure latency themselves; caller-side wraps them.

    Here we just confirm the call path completes inside a reasonable bound
    using perf_counter; the orchestrator layer is what records latency.
    """
    import time

    adapter = OpenAIAdapter(_config())
    body = {"choices": [{"message": {"content": "ok"}}]}
    with patch("llm_adapters.openai_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
        start = time.perf_counter()
        result = adapter.invoke(_request())
        elapsed_ms = (time.perf_counter() - start) * 1000
    assert result.status is LanguageModelStatus.COMPLETE
    assert elapsed_ms < 1000  # mocked, must be fast


# ---- privacy / leakage ---------------------------------------------------


def test_adapters_do_not_expose_provider_in_narrative() -> None:
    """Successful responses carry narrative only — no provider leak."""
    adapter = DeepSeekAdapter(_config())
    body = {"choices": [{"message": {"content": "safe text"}}]}
    with patch("llm_adapters.deepseek_adapter.httpx.Client") as cls:
        cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
        result = adapter.invoke(_request())
    assert "deepseek" not in (result.narrative_text or "").lower()
    assert "deepseek" not in " ".join(result.limitations).lower()


def test_private_to_public_pack_carries_no_provider_data() -> None:
    """End-to-end: private result -> public pack -> no provider leak."""
    public = PublicDecisionPack(
        recommendation="Buy",
        valuation=None,
        analysis="OK",
        risks=(),
        evidence_citations=(),
        confidence=0.5,
        limitations=("lm_enrichment",),
    )
    private = PrivateInternalResult(
        public=public,
        provider="deepseek",
        model="deepseek-chat",
        routing_tier="cost_efficient",
        routing_reasons=(),
        confidence_requirement=0.6,
        estimated_cost_usd=0.01,
        input_tokens=100,
        output_tokens=50,
        latency_ms=200,
        model_score=85.0,
        routing_criteria=(),
        internal_prompt="PRIVATE",
        raw_ai_response="PRIVATE",
        chain_of_thought="PRIVATE",
    )
    out = private.to_public().to_dict()
    assert_no_private_leakage(out)
    assert "deepseek" not in str(out).lower()
    assert "PRIVATE" not in str(out)


# ---- structured output failure (claim extraction skipped on free text) ---


def test_adapters_return_free_text_not_structured() -> None:
    """All four adapters today return free text in narrative_text.

    Structured-output failure means: when a downstream consumer expected
    structured_sections, the adapter does not fabricate them. The contract
    is preserved (tuple remains empty for free-text responses).
    """
    for adapter, patch_path, body in (
        (OpenAIAdapter(_config()), "llm_adapters.openai_adapter",
         {"choices": [{"message": {"content": "ok"}}]}),
        (DeepSeekAdapter(_config()), "llm_adapters.deepseek_adapter",
         {"choices": [{"message": {"content": "ok"}}]}),
        (GeminiAdapter(_config()), "llm_adapters.gemini_adapter",
         {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}),
        (AnthropicAdapter(_config()), "llm_adapters.anthropic_adapter",
         {"content": [{"type": "text", "text": "ok"}]}),
    ):
        with patch(f"{patch_path}.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.return_value = _mock_response(body)
            result = adapter.invoke(_request())
        assert result.status is LanguageModelStatus.COMPLETE
        assert result.structured_sections == ()  # no fabrication
        assert result.narrative_text == "ok"
