"""Anthropic Claude adapter — Messages API.

Uses ``api.anthropic.com/v1/messages`` with the ``x-api-key`` header and
``anthropic-version`` header. The adapter is responsible for translating
between the provider-neutral ``LanguageModelRequest`` and Anthropic's
``system`` + ``messages`` shape. Raw provider output never leaves this
module.
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

_PROVENANCE = ("llm_adapters.anthropic", "dsp.llm.anthropic.v1")
_BASE_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter:
    """Anthropic Messages adapter implementing the provider-neutral port."""

    provider_id = "anthropic"

    def __init__(self, config: LLMPlatformConfig) -> None:
        self._config = config
        self.model_label = config.anthropic_model

    def is_configured(self) -> bool:
        return bool(self._config.anthropic_api_key)

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        if not self.is_configured():
            return self._unavailable("ANTHROPIC_API_KEY not configured")

        if not request.prompt_parts:
            return self._failed("empty prompt parts")

        system_content, *user_parts = request.prompt_parts
        messages = [{"role": "user", "content": "\n\n".join(user_parts)}]
        payload: dict[str, Any] = {
            "model": self.model_label,
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": messages,
        }
        if system_content:
            payload["system"] = system_content

        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                response = client.post(
                    _BASE_URL,
                    headers={
                        "x-api-key": self._config.anthropic_api_key or "",
                        "anthropic-version": _ANTHROPIC_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            return self._failed(f"http_error: {exc.__class__.__name__}")
        except (ValueError, KeyError) as exc:
            return self._failed(f"malformed_response: {exc.__class__.__name__}")

        text = self._extract_text(data)
        if not text:
            return self._failed("empty Anthropic response")

        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.COMPLETE,
            provenance=_PROVENANCE,
            narrative_text=text,
            model_label=self.model_label,
        )

    def stream_invoke(self, request: LanguageModelRequest) -> Iterator[str]:
        if not self.is_configured():
            return
        if not request.prompt_parts:
            return
        system_content, *user_parts = request.prompt_parts
        messages = [{"role": "user", "content": "\n\n".join(user_parts)}]
        payload: dict[str, Any] = {
            "model": self.model_label,
            "max_tokens": 1024,
            "temperature": 0.2,
            "stream": True,
            "messages": messages,
        }
        if system_content:
            payload["system"] = system_content
        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                with client.stream(
                    "POST",
                    _BASE_URL,
                    headers={
                        "x-api-key": self._config.anthropic_api_key or "",
                        "anthropic-version": _ANTHROPIC_VERSION,
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
                        # event-driven: content_block_delta -> delta.text
                        evt_type = chunk.get("type")
                        if evt_type == "content_block_delta":
                            delta = chunk.get("delta") or {}
                            text = delta.get("text")
                            if text:
                                yield str(text)
        except httpx.HTTPError:
            return

    def _extract_text(self, data: dict[str, Any]) -> str | None:
        content = data.get("content") or []
        chunks: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text")
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
