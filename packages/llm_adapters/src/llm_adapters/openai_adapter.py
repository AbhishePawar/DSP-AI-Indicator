"""OpenAI adapter — httpx only, no vendor SDK in domain packages."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import httpx

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.tools.protocol.openai_compatible import OpenAICompatibleToolCalling

_PROVENANCE = ("llm_adapters.openai", "dsp.llm.openai.v1")


class OpenAIAdapter(OpenAICompatibleToolCalling):
    """OpenAI Chat Completions adapter implementing LanguageModelPort.

    Function-calling wire format is inherited from
    ``OpenAICompatibleToolCalling`` (shared with DeepSeek). ``invoke``
    does not send tools and is not wired to ``/api/v1/analyse``.
    """

    provider_id = "openai"

    def __init__(self, config: LLMPlatformConfig) -> None:
        self._config = config
        self.model_label = config.openai_model

    def is_configured(self) -> bool:
        return bool(self._config.openai_api_key)

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        if not self.is_configured():
            return self._unavailable("OPENAI_API_KEY not configured")

        prompt = "\n\n".join(request.prompt_parts)
        payload = {
            "model": self.model_label,
            "messages": [
                {"role": "system", "content": prompt.split("\n\n")[0]},
                {"role": "user", "content": "\n\n".join(request.prompt_parts[1:])},
            ],
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._config.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            return self._failed(str(exc))

        text = self._extract_text(data)
        if not text:
            return self._failed("empty OpenAI response")

        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.COMPLETE,
            provenance=_PROVENANCE,
            narrative_text=text,
            model_label=self.model_label,
        )

    def stream_invoke(self, request: LanguageModelRequest) -> Iterator[str]:
        if not self.is_configured():
            yield ""
            return

        prompt = "\n\n".join(request.prompt_parts)
        payload = {
            "model": self.model_label,
            "stream": True,
            "messages": [
                {"role": "system", "content": prompt.split("\n\n")[0]},
                {"role": "user", "content": "\n\n".join(request.prompt_parts[1:])},
            ],
            "temperature": 0.2,
        }

        with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
            with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._config.openai_api_key}",
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


def map_intent_to_user_intent(intent: str) -> UserIntentType:
    if intent == "compare_companies":
        return UserIntentType.COMPARE_OUTCOMES
    if intent in {"explain_recommendation", "explain_valuation", "explain_moat"}:
        return UserIntentType.EXPLAIN_REPORT
    return UserIntentType.SUMMARIZE_POSTURE
