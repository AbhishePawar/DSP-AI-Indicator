"""OpenAI Responses API + remote MCP request construction. No live network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from llm_adapters.config import LLMPlatformConfig
from llm_adapters.openai_responses import (
    OPENAI_RESPONSES_URL,
    OpenAIResponsesClient,
    build_remote_mcp_tool,
    build_responses_payload,
    parse_responses_output,
    redact_secrets,
)


def _config(*, key: str | None = "sk-test-secret-key") -> LLMPlatformConfig:
    return LLMPlatformConfig(
        default_provider="openai",
        openai_api_key=key,
        anthropic_api_key=None,
        gemini_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude",
        gemini_model="gemini",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def test_responses_payload_and_remote_mcp_config() -> None:
    tool = build_remote_mcp_tool(
        server_label="nse_bhavcopy",
        server_url="https://mcp.nseindia.in/bhavcopy/cm/mcp",
        require_approval="never",
    )
    payload = build_responses_payload(
        model="gpt-4o-mini",
        input_text="research",
        mcp_tools=(tool,),
        max_output_tokens=200,
    )
    assert payload["model"] == "gpt-4o-mini"
    assert payload["tools"][0]["type"] == "mcp"
    assert payload["tools"][0]["server_url"].startswith("https://mcp.nseindia.in/")
    assert "chat/completions" not in str(payload)
    assert OPENAI_RESPONSES_URL.endswith("/v1/responses")


def test_parse_mcp_list_and_call_items() -> None:
    parsed = parse_responses_output(
        {
            "output": [
                {"type": "mcp_list_tools", "server_label": "nse_bhavcopy", "tools": [{"name": "nse_lookup_symbol"}]},
                {
                    "type": "mcp_call",
                    "name": "get_ltp_by_date",
                    "server_label": "nse_bhavcopy",
                    "output": "{\"close\": 1}",
                },
                {"type": "message", "content": [{"type": "output_text", "text": "not a valuation"}]},
            ],
            "usage": {"input_tokens": 11, "output_tokens": 4},
        }
    )
    assert parsed.status == "complete"
    assert parsed.mcp_list_tools
    assert parsed.mcp_calls[0]["name"] == "get_ltp_by_date"
    assert parsed.output_text == "not a valuation"
    assert parsed.usage["input_tokens"] == 11


def test_redact_provider_secrets() -> None:
    text = redact_secrets("Authorization: Bearer sk-test-secret-key failed")
    assert "sk-test-secret-key" not in text
    assert "[REDACTED]" in text


def test_client_posts_to_responses_not_chat_completions() -> None:
    client = OpenAIResponsesClient(_config())
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "output": [{"type": "message", "content": [{"text": "ok"}]}],
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    with patch("llm_adapters.openai_responses.httpx.Client") as client_cls:
        http = client_cls.return_value.__enter__.return_value
        http.post.return_value = mock_response
        result = client.invoke(
            build_responses_payload(model="gpt-4o-mini", input_text="x")
        )
        posted = http.post.call_args
    assert posted.args[0] == OPENAI_RESPONSES_URL
    headers = posted.kwargs["headers"]
    assert "Authorization" in headers
    assert result.status == "complete"


def test_client_rate_limit_and_timeout() -> None:
    client = OpenAIResponsesClient(_config())
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "slow down"
    with patch("llm_adapters.openai_responses.httpx.Client") as client_cls:
        http = client_cls.return_value.__enter__.return_value
        http.post.return_value = mock_response
        limited = client.invoke({"model": "gpt-4o-mini", "input": "x"})
    assert limited.status == "rate_limited"
    assert client.is_configured() is True
    missing = OpenAIResponsesClient(_config(key=None))
    assert missing.is_configured() is False
    assert missing.invoke({"model": "gpt-4o-mini", "input": "x"}).status == "unavailable"
