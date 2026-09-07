"""Google Gemini adapter — generateContent REST API.

Uses ``generativelanguage.googleapis.com/v1beta/models/{model}:generateContent``
with the ``x-goog-api-key`` header. No vendor SDK (httpx only). Returns
a provider-neutral ``LanguageModelResult``; raw provider output never
leaves this module.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Iterator
from typing import Any

import httpx

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.gemini_grounding import (
    GroundedWebResearchResult,
    google_search_tool_for_model,
    parse_grounded_web_research,
)
from llm_adapters.tools.protocol.gemini import (
    GeminiToolCalling,
    gemini_payload_contains_function_calls,
)

_PROVENANCE = ("llm_adapters.gemini", "dsp.llm.gemini.v1")
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_LOG = logging.getLogger("dsp.llm.gemini")


def _response_bytes(response: object) -> int:
    content = getattr(response, "content", None)
    if isinstance(content, (bytes, bytearray)):
        return len(content)
    if isinstance(content, str):
        return len(content.encode("utf-8"))
    return -1


def _google_error_status(response: object) -> str:
    """Copy Google error.status only. Never returns bodies or credentials."""
    json_fn = getattr(response, "json", None)
    if not callable(json_fn):
        return ""
    try:
        payload = json_fn()
    except (ValueError, TypeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if not isinstance(error, dict):
        return ""
    status = str(error.get("status") or "").strip()
    if status and all(ch.isalnum() or ch == "_" for ch in status):
        message = str(error.get("message") or "").casefold()
        if "aiza" in message:
            return status
        if "api key" in message:
            return f"{status}:API_KEY"
        if "not found" in message or "not supported for generatecontent" in message:
            return f"{status}:MODEL_UNAVAILABLE"
        if (
            "mime type" in message
            or "controlled generation" in message
            or "google_search tool" in message
        ):
            return f"{status}:STRUCTURED_OUTPUT_WITH_TOOLS"
        return status
    return ""


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

    def invoke_web_research(
        self,
        request: LanguageModelRequest,
    ) -> tuple[LanguageModelResult, GroundedWebResearchResult]:
        """generateContent with official Google Search grounding.

        Copilot ``invoke`` is unchanged and still does not send tools.
        This path is not wired to ``/api/v1/analyse``.
        """
        tool = google_search_tool_for_model(self.model_label)
        # gemini-2.5-flash rejects googleSearch + responseMimeType=application/json
        # with HTTP 400 INVALID_ARGUMENT. JSON is required by the prompt instead.
        result, raw = self._generate(
            request,
            tools=tool,
            allow_tool_only=False,
            response_json=False,
        )
        status = "complete"
        if result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE:
            status = "unavailable"
        elif result.status is not LanguageModelStatus.COMPLETE:
            status = "failed"
        grounded = parse_grounded_web_research(
            raw if isinstance(raw, dict) else {},
            narrative_text=result.narrative_text,
            status=status,
            limitations=result.limitations,
        )
        if grounded.malformed and result.status is LanguageModelStatus.COMPLETE:
            failed = self._failed("malformed_response: JSON")
            grounded = parse_grounded_web_research(
                raw if isinstance(raw, dict) else {},
                narrative_text=result.narrative_text,
                status="malformed",
                limitations=failed.limitations,
            )
            return failed, grounded
        return result, grounded

    def _generate(
        self,
        request: LanguageModelRequest,
        *,
        tools: Any,
        allow_tool_only: bool,
        response_json: bool = False,
    ) -> tuple[LanguageModelResult, dict[str, Any] | None]:
        if not self.is_configured():
            return self._unavailable("GEMINI_API_KEY not configured"), None

        if not request.prompt_parts:
            return self._failed("empty prompt parts"), None

        system_content, *user_parts = request.prompt_parts
        user_text = "\n\n".join(user_parts)
        url = f"{_BASE_URL}/{self.model_label}:generateContent"
        generation_config: dict[str, Any] = {"temperature": 0.2}
        if response_json:
            generation_config["responseMimeType"] = "application/json"
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_text}],
                }
            ],
            "generationConfig": generation_config,
        }
        if system_content:
            payload["systemInstruction"] = {
                "role": "system",
                "parts": [{"text": system_content}],
            }
        if tools:
            payload["tools"] = [tools] if isinstance(tools, dict) else tools

        _LOG.warning(
            "gemini_http stage=request model=%s timeout_s=%s json_mime=%s tools=%s",
            self.model_label,
            self._config.request_timeout_seconds,
            int(response_json),
            int(bool(tools)),
        )
        started = time.perf_counter()
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
                latency_ms = int((time.perf_counter() - started) * 1000)
                _LOG.warning(
                    "gemini_http stage=response model=%s status=%s latency_ms=%s "
                    "response_bytes=%s",
                    self.model_label,
                    response.status_code,
                    latency_ms,
                    _response_bytes(response),
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            detail = exc.__class__.__name__
            response = getattr(exc, "response", None)
            code = getattr(response, "status_code", None)
            _LOG.warning(
                "gemini_http stage=error model=%s status=%s latency_ms=%s "
                "exception_class=%s",
                self.model_label,
                code if isinstance(code, int) else 0,
                int((time.perf_counter() - started) * 1000),
                type(exc).__name__,
            )
            if isinstance(code, int):
                detail = f"{detail}:{code}"
                error_status = _google_error_status(response)
                if error_status:
                    detail = f"{detail}:{error_status}"
            return self._failed(f"http_error: {detail}"), None
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
            with (
                httpx.Client(timeout=self._config.request_timeout_seconds) as client,
                client.stream(
                    "POST",
                    url,
                    params={"alt": "sse"},
                    headers={
                        "x-goog-api-key": self._config.gemini_api_key or "",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response,
            ):
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
