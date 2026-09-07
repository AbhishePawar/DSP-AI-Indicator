"""Gemini port for share research. Provider faults stay off the share-count breaker."""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from dsp_platform.share_count_refresh import InstrumentIdentity
from dsp_platform.share_research.policy import SHARE_RESEARCH_MASTER_POLICY

__all__ = [
    "FixedShareResearchGemini",
    "GeminiFailureClass",
    "GeminiShareResearchAdapter",
    "ShareResearchGeminiError",
    "ShareResearchGeminiPort",
    "ShareResearchGeminiResult",
    "classify_share_research_gemini_failure",
    "classify_share_research_gemini_failure_detail",
]

_PROVIDER_HTTP_5XX = ("500", "502", "503", "504")
_HTTP_STATUS = re.compile(r"HTTPStatusError:(\d{3})")
_PROVIDER_CODE = re.compile(r"HTTPStatusError:\d{3}:([A-Z0-9_]+(?::[A-Z0-9_]+)?)")


@dataclass(frozen=True, slots=True)
class GeminiFailureClass:
    kind: str
    status_code: int = 0
    provider_code: str = ""


def classify_share_research_gemini_failure(
    status: LanguageModelStatus,
    limitations: Sequence[str] | str,
) -> str | None:
    """Return ShareResearchGeminiError.kind, or None when COMPLETE (parse next)."""
    detail = classify_share_research_gemini_failure_detail(status, limitations)
    return None if detail is None else detail.kind


def classify_share_research_gemini_failure_detail(
    status: LanguageModelStatus,
    limitations: Sequence[str] | str,
) -> GeminiFailureClass | None:
    """Typed provider/parse class. HTTP 4xx is never malformed."""
    blob = limitations if isinstance(limitations, str) else " ".join(limitations)
    match = _HTTP_STATUS.search(blob)
    code = int(match.group(1)) if match else 0
    provider_match = _PROVIDER_CODE.search(blob)
    provider_code = provider_match.group(1) if provider_match else ""
    if status is LanguageModelStatus.PROVIDER_UNAVAILABLE:
        return GeminiFailureClass("unavailable")
    if "Timeout" in blob or "timeout" in blob.casefold():
        return GeminiFailureClass("timeout", status_code=code, provider_code=provider_code)
    if code == 429 or "429" in blob:
        return GeminiFailureClass("rate_limited", status_code=429, provider_code=provider_code)
    if code >= 500 or any(token in blob for token in _PROVIDER_HTTP_5XX):
        return GeminiFailureClass(
            "http_5xx", status_code=code or 500, provider_code=provider_code
        )
    if "MODEL_UNAVAILABLE" in blob:
        return GeminiFailureClass("http_404", status_code=code or 404, provider_code=provider_code)
    if "API_KEY" in blob:
        if code == 403:
            return GeminiFailureClass("http_403", status_code=403, provider_code=provider_code)
        if code == 400:
            return GeminiFailureClass("http_4xx", status_code=400, provider_code=provider_code)
        return GeminiFailureClass("http_401", status_code=code or 401, provider_code=provider_code)
    if code == 401:
        return GeminiFailureClass("http_401", status_code=401, provider_code=provider_code)
    if code == 403:
        return GeminiFailureClass("http_403", status_code=403, provider_code=provider_code)
    if code == 404:
        return GeminiFailureClass("http_404", status_code=404, provider_code=provider_code)
    if code == 400:
        return GeminiFailureClass("http_4xx", status_code=400, provider_code=provider_code)
    if code >= 400:
        return GeminiFailureClass("http_4xx", status_code=code, provider_code=provider_code)
    if "ConnectError" in blob or "NetworkError" in blob or "TLS" in blob:
        return GeminiFailureClass("transport", provider_code=provider_code)
    if "http_error" in blob:
        return GeminiFailureClass("transport", provider_code=provider_code)
    if "tool_only" in blob:
        return GeminiFailureClass("tool_only")
    if "empty Gemini" in blob:
        return GeminiFailureClass("empty")
    if status is not LanguageModelStatus.COMPLETE:
        return GeminiFailureClass("malformed")
    return None


_LOG = logging.getLogger("dsp.share_research.gemini")


class ShareResearchGeminiError(Exception):
    """Provider or parse failure. Not a share-count circuit event."""

    def __init__(
        self, kind: str, message: str, *, status_code: int = 0, provider_code: str = ""
    ) -> None:
        self.kind = kind
        self.status_code = status_code
        self.provider_code = provider_code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ShareResearchGeminiResult:
    payload: dict[str, Any]
    duration_ms: int
    model_label: str
    reference: str


class ShareResearchGeminiPort(Protocol):
    def research(
        self,
        *,
        identity: InstrumentIdentity,
        stored: Mapping[str, Any] | None,
        horizon_iso: str,
        user_prompt: str,
        correlation_id: str = "",
    ) -> ShareResearchGeminiResult:
        ...


class FixedShareResearchGemini:
    """Test double. Raises ShareResearchGeminiError when kind is set."""

    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        kind: str | None = None,
        message: str = "gemini failure",
        duration_ms: int = 5,
    ) -> None:
        self._payload = dict(payload or {})
        self._kind = kind
        self._message = message
        self._duration_ms = duration_ms
        self.calls = 0

    def research(
        self,
        *,
        identity: InstrumentIdentity,
        stored: Mapping[str, Any] | None,
        horizon_iso: str,
        user_prompt: str,
        correlation_id: str = "",
    ) -> ShareResearchGeminiResult:
        del identity, stored, horizon_iso, user_prompt, correlation_id
        self.calls += 1
        if self._kind:
            raise ShareResearchGeminiError(self._kind, self._message)
        return ShareResearchGeminiResult(
            payload=dict(self._payload),
            duration_ms=self._duration_ms,
            model_label="test-double",
            reference="test-gemini",
        )


class GeminiShareResearchAdapter:
    """Live Gemini web research. DSP still validates the JSON."""

    def __init__(self, adapter: Any | None = None) -> None:
        self._adapter = adapter

    def research(
        self,
        *,
        identity: InstrumentIdentity,
        stored: Mapping[str, Any] | None,
        horizon_iso: str,
        user_prompt: str,
        correlation_id: str = "",
    ) -> ShareResearchGeminiResult:
        adapter = self._adapter
        if adapter is None:
            from llm_adapters.config import load_llm_config
            from llm_adapters.gemini_adapter import GeminiAdapter

            adapter = GeminiAdapter(load_llm_config())
        if not adapter.is_configured():
            _LOG.warning(
                "share_research_gemini stage=unavailable model=%s isin=%s key_present=0",
                getattr(adapter, "model_label", ""),
                identity.isin,
            )
            raise ShareResearchGeminiError("unavailable", "GEMINI_API_KEY not configured")
        _LOG.warning(
            "share_research_gemini stage=invoke model=%s isin=%s key_present=1",
            getattr(adapter, "model_label", ""),
            identity.isin,
        )
        request = LanguageModelRequest(
            request_id=(correlation_id or "").strip() or str(uuid.uuid4()),
            intent_class=UserIntentType.TRACE_EVIDENCE,
            prompt_parts=(SHARE_RESEARCH_MASTER_POLICY, user_prompt),
            context_digest_ids=("share-research",),
            provenance=("dsp.share_research", "dsp.llm.gemini.web_research.v1"),
        )
        started = time.perf_counter()
        result, grounded = adapter.invoke_web_research(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        _LOG.warning(
            "share_research_gemini stage=adapter_result model=%s isin=%s "
            "status=%s latency_ms=%s",
            getattr(adapter, "model_label", ""),
            identity.isin,
            getattr(result.status, "name", str(result.status)),
            duration_ms,
        )
        detail = classify_share_research_gemini_failure_detail(
            result.status, result.limitations or ()
        )
        if detail is not None:
            raise ShareResearchGeminiError(
                detail.kind,
                f"Gemini research failed ({detail.kind})",
                status_code=detail.status_code,
                provider_code=detail.provider_code,
            )
        from llm_adapters.gemini_grounding import parse_json_object

        payload_map = parse_json_object(result.narrative_text)
        if payload_map is None:
            raise ShareResearchGeminiError("malformed", "Gemini JSON is malformed")
        payload = dict(payload_map)
        reference = str(getattr(grounded, "model_label", "") or adapter.model_label)
        return ShareResearchGeminiResult(
            payload=payload,
            duration_ms=duration_ms,
            model_label=str(adapter.model_label),
            reference=reference or "gemini-web-research",
        )
