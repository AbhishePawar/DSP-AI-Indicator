"""Google Gemini adapter — generateContent REST API.

Uses ``generativelanguage.googleapis.com/v1beta/models/{model}:generateContent``
with the ``x-goog-api-key`` header. No vendor SDK (httpx only). Returns
a provider-neutral ``LanguageModelResult``; raw provider output never
leaves this module.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import httpx

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.tools.protocol.gemini import (
    GeminiToolCalling,
    gemini_payload_contains_function_calls,
)

_PROVENANCE = ("llm_adapters.gemini", "dsp.llm.gemini.v1")
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAdapter(GeminiToolCalling):
    """Google Gemini chat adapter implementing the provider-neutral port.

    Function-calling wire format is inherited from ``GeminiToolCalling``.
    ``invoke`` does not send tools and is not wired to ``/api/v1/analyse``.
    """

    provider_id = "gemini"

    def __init__(self, config: LLMPlatformConfig) -> None:
        self._config = config
        self.model_label = config.gemini_model

    def is_configured(self) -> bool:
        return bool(self._config.gemini_api_key)

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        result, _ = self._generate(request, tools=None, allow_tool_only=False)
        return result

    def invoke_research(
        self,
        request: LanguageModelRequest,
        *,
        tools: Any = None,
        tool_result_messages: Any = None,
    ) -> tuple[LanguageModelResult, dict[str, Any] | None]:
        del tool_result_messages
        return self._generate(request, tools=tools, allow_tool_only=True)

    def _generate(
        self,
        request: LanguageModelRequest,
        *,
        tools: Any,
        allow_tool_only: bool,
    ) -> tuple[LanguageModelResult, dict[str, Any] | None]:
        if not self.is_configured():
            return self._unavailable("GEMINI_API_KEY not configured"), None

        if not request.prompt_parts:
            return self._failed("empty prompt parts"), None

        system_content, *user_parts = request.prompt_parts
        user_text = "\n\n".join(user_parts)
        url = f"{_BASE_URL}/{self.model_label}:generateContent"
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_text}],
                }
            ],
            "generationConfig": {"temperature": 0.2},
        }
        if system_content:
            payload["systemInstruction"] = {
                "role": "system",
                "parts": [{"text": system_content}],
            }
        if tools:
            payload["tools"] = [tools] if isinstance(tools, dict) else tools

        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                response = client.post(
                    url,
                    headers={
                        "x-goog-api-key": self._config.gemini_api_key or "",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            return self._failed(f"http_error: {exc.__class__.__name__}"), None
        except (ValueError, KeyError) as exc:
            return self._failed(f"malformed_response: {exc.__class__.__name__}"), None

        if not isinstance(data, dict):
            return self._failed("malformed_response: TypeError"), None
        text = self._extract_text(data)
        has_tools = gemini_payload_contains_function_calls(data)
        if not text and not (allow_tool_only and has_tools):
            return self._failed("empty Gemini response"), data
        return (
            LanguageModelResult(
                result_id=str(uuid.uuid4()),
                status=LanguageModelStatus.COMPLETE,
                provenance=_PROVENANCE,
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
        user_text = "\n\n".join(user_parts)
        url = f"{_BASE_URL}/{self.model_label}:streamGenerateContent"
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {"temperature": 0.2},
        }
        if system_content:
            payload["systemInstruction"] = {
                "role": "system",
                "parts": [{"text": system_content}],
            }
        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                with client.stream(
                    "POST",
                    url,
                    params={"alt": "sse"},
                    headers={
                        "x-goog-api-key": self._config.gemini_api_key or "",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        chunk_raw = line[6:].strip()
                        if not chunk_raw or chunk_raw == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(chunk_raw)
                        except json.JSONDecodeError:
                            continue
                        text = self._extract_text(chunk)
                        if text:
                            yield text
        except httpx.HTTPError:
            return

    def _extract_text(self, data: dict[str, Any]) -> str | None:
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        chunks: list[str] = []
        for part in parts:
            text = part.get("text")
            if text:
                chunks.append(str(text))
        joined = "".join(chunks).strip()
        return joined or None

    def _unavailable(self, reason: str) -> LanguageModelResult:
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.PROVIDER_UNAVAILABLE,
            provenance=_PROVENANCE,
            limitations=(reason,),
            model_label=self.model_label,
        )

    def _failed(self, reason: str) -> LanguageModelResult:
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.FAILED,
            provenance=_PROVENANCE,
            limitations=(reason,),
            model_label=self.model_label,
        )
