"""OpenAI-compatible AI Gateway adapter with provider-neutral results."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.config import LLMPlatformConfig


class AIGatewayAdapter:
    """Routes Gemini/OpenAI model IDs through AI Gateway.

    The Gateway credential is only read on the server and never included in
    result payloads or exception text.
    """

    def __init__(self, config: LLMPlatformConfig, *, provider_id: str, model: str) -> None:
        self._config = config
        self.provider_id = provider_id
        self.model_label = model

    def is_configured(self) -> bool:
        return bool(self._config.ai_gateway_api_key)

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        if not self.is_configured():
            return self._unavailable("AI Gateway is not configured")
        if not request.prompt_parts:
            return self._failed("empty prompt")
        prompt = "\n\n".join(request.prompt_parts)
        payload: dict[str, Any] = {
            "model": self.model_label,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Analyze only the validated DSP evidence supplied by the user. "
                        "Do not fetch external financial data or override deterministic DSP values. "
                        "Return a concise evidence-backed conclusion."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        endpoint = _chat_completions_url(self._config.ai_gateway_base_url)
        try:
            with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
                response = client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {self._config.ai_gateway_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            return self._failed(
                f"gateway_http_error:{_classify_status(exc.response.status_code)}"
            )
        except httpx.TimeoutException:
            return self._failed("gateway_http_error:timeout")
        except httpx.RequestError:
            return self._failed("gateway_http_error:network")
        except (ValueError, TypeError):
            return self._failed("gateway_malformed_response")
        if not isinstance(data, dict):
            return self._failed("gateway_malformed_response")
        choices = data.get("choices") or []
        content = ((choices[0].get("message") or {}).get("content") if choices else None)
        if not content:
            return self._failed("gateway_empty_response")
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.COMPLETE,
            provenance=("llm_adapters.gateway", "dsp.llm.gateway.v1"),
            narrative_text=str(content).strip(),
            model_label=self.model_label,
        )

    def stream_invoke(self, request: LanguageModelRequest) -> Iterator[str]:
        result = self.invoke(request)
        if result.narrative_text:
            yield result.narrative_text

    def _unavailable(self, reason: str) -> LanguageModelResult:
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.PROVIDER_UNAVAILABLE,
            provenance=("llm_adapters.gateway", "dsp.llm.gateway.v1"),
            limitations=(reason,),
            model_label=self.model_label,
        )

    def _failed(self, reason: str) -> LanguageModelResult:
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.FAILED,
            provenance=("llm_adapters.gateway", "dsp.llm.gateway.v1"),
            limitations=(reason,),
            model_label=self.model_label,
        )

    
def _chat_completions_url(base_url: str) -> str:
    """Normalize supported Gateway base URL forms to one endpoint."""
    parsed = urlsplit(base_url.strip())
    path = parsed.path.rstrip("/")
    while path.endswith("/chat/completions") or path.endswith("/v1"):
        if path.endswith("/chat/completions"):
            path = path[: -len("/chat/completions")].rstrip("/")
        else:
            path = path[: -len("/v1")].rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}/v1/chat/completions", "", ""))


def _classify_status(status_code: int) -> str:
    if status_code in {401, 403}:
        return "authentication"
    if status_code == 404:
        return "endpoint_or_model"
    if status_code == 400:
        return "request"
    if status_code == 429:
        return "rate_limit"
    if 500 <= status_code <= 599:
        return "upstream"
    return f"http_{status_code}"


__all__ = ["AIGatewayAdapter"]


def gateway_provider(config: LLMPlatformConfig, provider_id: str) -> AIGatewayAdapter:
    model = config.gemini_model if provider_id == "gemini" else config.openai_model
    if "/" not in model:
        model = f"{provider_id}/{model}"
    return AIGatewayAdapter(config, provider_id=provider_id, model=model)
