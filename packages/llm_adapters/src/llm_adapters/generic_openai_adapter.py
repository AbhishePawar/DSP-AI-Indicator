"""Universal OpenAI-compatible chat adapter.

Supports Groq, OpenRouter, Mistral, xAI Grok, Together, Fireworks, Perplexity,
Cohere, and self-hosted Ollama endpoints using httpx with OpenAI-compatible wire formats.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import httpx

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.tools.protocol.openai_compatible import (
    OpenAICompatibleToolCalling,
    openai_payload_contains_tool_calls,
)


class GenericOpenAIAdapter(OpenAICompatibleToolCalling):
    """Configurable OpenAI-compatible provider adapter."""

    def __init__(
        self,
        provider_id: str,
        *,
        base_url: str,
        api_key: str | None = None,
        model_label: str = "",
        timeout_seconds: float = 30.0,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.provider_id = provider_id.lower()
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip() if api_key else None
        self.model_label = model_label
        self.timeout_seconds = timeout_seconds
        self.extra_headers = extra_headers or {}
        self._provenance = (f"llm_adapters.{self.provider_id}", f"dsp.llm.{self.provider_id}.v1")

    def is_configured(self) -> bool:
        if self.provider_id == "ollama":
            return bool(self.base_url)
        return bool(self.api_key)

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        result, _ = self._chat(request, tools=None, allow_tool_only=False)
        return result

    def invoke_research(
        self,
        request: LanguageModelRequest,
        *,
        tools: Any = None,
        tool_result_messages: Any = None,
    ) -> tuple[LanguageModelResult, dict[str, Any] | None]:
        del tool_result_messages
        return self._chat(request, tools=tools, allow_tool_only=True)

    def _chat(
        self,
        request: LanguageModelRequest,
        *,
        tools: Any,
        allow_tool_only: bool,
    ) -> tuple[LanguageModelResult, dict[str, Any] | None]:
        if not self.is_configured():
            return self._unavailable(f"{self.provider_id.upper()} credentials not configured"), None

        if not request.prompt_parts:
            return self._failed("empty prompt parts"), None

        system_content, *user_parts = request.prompt_parts
        payload: dict[str, Any] = {
            "model": self.model_label,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "dsp-ai-indicator/1.0",
            **self.extra_headers,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/chat/completions"
        if not self.base_url.endswith("/v1") and not self.base_url.endswith("/v2") and "api" not in self.base_url:
            url = f"{self.base_url}/v1/chat/completions"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            return self._failed(f"http_error: {exc.__class__.__name__}"), None
        except (ValueError, KeyError) as exc:
            return self._failed(f"malformed_response: {exc.__class__.__name__}"), None

        if not isinstance(data, dict):
            return self._failed("malformed_response: TypeError"), None
        text = self._extract_text(data)
        has_tools = openai_payload_contains_tool_calls(data)
        if not text and not (allow_tool_only and has_tools):
            return self._failed(f"empty {self.provider_id} response"), data
        return (
            LanguageModelResult(
                result_id=str(uuid.uuid4()),
                status=LanguageModelStatus.COMPLETE,
                provenance=self._provenance,
                narrative_text=text,
                structured_sections=() if text else ("tool_call",),
                model_label=self.model_label,
            ),
            data,
        )

    def stream_invoke(self, request: LanguageModelRequest) -> Iterator[str]:
        if not self.is_configured():
            return
        if not request.prompt_parts:
            return
        system_content, *user_parts = request.prompt_parts
        payload = {
            "model": self.model_label,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.extra_headers,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/chat/completions"
        if not self.base_url.endswith("/v1") and not self.base_url.endswith("/v2") and "api" not in self.base_url:
            url = f"{self.base_url}/v1/chat/completions"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        chunk_raw = line[6:].strip()
                        if chunk_raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(chunk_raw)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if delta:
                            yield str(delta)
        except httpx.HTTPError:
            return

    def _extract_text(self, data: dict[str, Any]) -> str | None:
        choices = data.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = message.get("content")
        return str(content).strip() if content else None

    def _unavailable(self, reason: str) -> LanguageModelResult:
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.PROVIDER_UNAVAILABLE,
            provenance=self._provenance,
            limitations=(reason,),
            model_label=self.model_label,
        )

    def _failed(self, reason: str) -> LanguageModelResult:
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.FAILED,
            provenance=self._provenance,
            limitations=(reason,),
            model_label=self.model_label,
        )
