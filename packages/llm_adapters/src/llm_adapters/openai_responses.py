"""OpenAI Responses API client — httpx only, no vendor SDK.

Chat Completions remain in openai_adapter.py. This module is additive:
research agents may attach remote MCP servers to POST /v1/responses.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from llm_adapters.config import LLMPlatformConfig

__all__ = [
    "OPENAI_RESPONSES_URL",
    "OpenAIResponsesClient",
    "OpenAIResponsesResult",
    "build_remote_mcp_tool",
    "build_responses_payload",
    "parse_responses_output",
    "redact_secrets",
]

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

_SECRET_RE = re.compile(
    r"(Bearer\s+)[A-Za-z0-9._\-]+|(sk-[A-Za-z0-9\-._]+)|"
    r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s]+",
    re.I,
)


def redact_secrets(text: str) -> str:
    """Strip credentials from errors/logs. Never persist raw secrets."""
    return _SECRET_RE.sub(lambda m: (m.group(1) or "") + "[REDACTED]", str(text or ""))


def build_remote_mcp_tool(
    *,
    server_label: str,
    server_url: str,
    server_description: str | None = None,
    require_approval: str = "never",
    allowed_tools: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Native Responses API remote-MCP tool object. No Chat Completions functions."""
    tool: dict[str, Any] = {
        "type": "mcp",
        "server_label": server_label,
        "server_url": server_url,
        "require_approval": require_approval,
    }
    if server_description:
        tool["server_description"] = server_description
    if allowed_tools:
        tool["allowed_tools"] = list(allowed_tools)
    return tool


def build_responses_payload(
    *,
    model: str,
    input_text: str,
    mcp_tools: tuple[dict[str, Any], ...] = (),
    max_output_tokens: int = 800,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": input_text,
        "max_output_tokens": max_output_tokens,
    }
    if mcp_tools:
        payload["tools"] = list(mcp_tools)
    return payload


@dataclass(frozen=True, slots=True)
class OpenAIResponsesResult:
    status: str
    output_text: str | None
    mcp_list_tools: tuple[dict[str, Any], ...]
    mcp_calls: tuple[dict[str, Any], ...]
    usage: dict[str, Any] | None
    raw: dict[str, Any]
    error: str | None = None


def parse_responses_output(data: dict[str, Any]) -> OpenAIResponsesResult:
    output = data.get("output") or []
    listed: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    texts: list[str] = []
    if not isinstance(output, list):
        return OpenAIResponsesResult(
            status="failed",
            output_text=None,
            mcp_list_tools=(),
            mcp_calls=(),
            usage=data.get("usage") if isinstance(data.get("usage"), dict) else None,
            raw=data,
            error="malformed Responses output",
        )
    for item in output:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "mcp_list_tools":
            listed.append(item)
        elif kind == "mcp_call":
            calls.append(item)
        elif kind == "message":
            content = item.get("content") or []
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("text"):
                        texts.append(str(part["text"]))
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
    return OpenAIResponsesResult(
        status="complete",
        output_text="\n".join(texts) or None,
        mcp_list_tools=tuple(listed),
        mcp_calls=tuple(calls),
        usage=usage,
        raw=data,
    )


class OpenAIResponsesClient:
    """POST /v1/responses. Domain packages must not import OpenAI SDK types."""

    def __init__(self, config: LLMPlatformConfig) -> None:
        self._config = config
        self.model_label = config.openai_model

    def is_configured(self) -> bool:
        return bool(self._config.openai_api_key)

    def invoke(self, payload: dict[str, Any]) -> OpenAIResponsesResult:
        if not self.is_configured():
            return OpenAIResponsesResult(
                status="unavailable",
                output_text=None,
                mcp_list_tools=(),
                mcp_calls=(),
                usage=None,
                raw={},
                error="OPENAI_API_KEY not configured",
            )
        headers = {
            "Authorization": f"Bearer {self._config.openai_api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                response = client.post(
                    OPENAI_RESPONSES_URL, headers=headers, json=payload
                )
        except httpx.TimeoutException as exc:
            return OpenAIResponsesResult(
                status="timeout",
                output_text=None,
                mcp_list_tools=(),
                mcp_calls=(),
                usage=None,
                raw={},
                error=redact_secrets(f"MCP_TIMEOUT: {exc}"),
            )
        except httpx.HTTPError as exc:
            return OpenAIResponsesResult(
                status="unavailable",
                output_text=None,
                mcp_list_tools=(),
                mcp_calls=(),
                usage=None,
                raw={},
                error=redact_secrets(str(exc)),
            )
        if response.status_code == 429:
            return OpenAIResponsesResult(
                status="rate_limited",
                output_text=None,
                mcp_list_tools=(),
                mcp_calls=(),
                usage=None,
                raw={},
                error="rate limited",
            )
        if response.status_code >= 400:
            return OpenAIResponsesResult(
                status="failed",
                output_text=None,
                mcp_list_tools=(),
                mcp_calls=(),
                usage=None,
                raw={},
                error=redact_secrets(f"HTTP {response.status_code} {response.text[:300]}"),
            )
        try:
            data = response.json()
        except json.JSONDecodeError:
            return OpenAIResponsesResult(
                status="failed",
                output_text=None,
                mcp_list_tools=(),
                mcp_calls=(),
                usage=None,
                raw={},
                error="malformed JSON from Responses API",
            )
        if not isinstance(data, dict):
            return OpenAIResponsesResult(
                status="failed",
                output_text=None,
                mcp_list_tools=(),
                mcp_calls=(),
                usage=None,
                raw={},
                error="Responses API JSON must be an object",
            )
        return parse_responses_output(data)
