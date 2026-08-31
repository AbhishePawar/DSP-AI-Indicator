"""DeepSeek adapter — OpenAI-compatible Chat Completions API.

DeepSeek exposes ``https://api.deepseek.com/v1/chat/completions`` with
the same request/response shape as OpenAI. We use httpx (no vendor SDK)
to keep the dependency surface consistent with the other adapters.
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

_PROVENANCE = ("llm_adapters.deepseek", "dsp.llm.deepseek.v1")
_BASE_URL = "https://api.deepseek.com"


class DeepSeekAdapter:
    """DeepSeek chat adapter implementing the provider-neutral port."""

    provider_id = "deepseek"

    def __init__(self, config: LLMPlatformConfig) -> None:
        self._config = config
        self.model_label = config.deepseek_model

    def is_configured(self) -> bool:
        return bool(self._config.deepseek_api_key)

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        if not self.is_configured():
            return self._unavailable("DEEPSEEK_API_KEY not configured")

        if not request.prompt_parts:
            return self._failed("empty prompt parts")

        system_content, *user_parts = request.prompt_parts
        payload = {
            "model": self.model_label,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            "temperature": 0.2,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                response = client.post(
                    f"{_BASE_URL}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._config.deepseek_api_key}",
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
            return self._failed("empty DeepSeek response")

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
        payload = {
            "model": self.model_label,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            "temperature": 0.2,
        }
        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                with client.stream(
                    "POST",
                    f"{_BASE_URL}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._config.deepseek_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
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
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
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
