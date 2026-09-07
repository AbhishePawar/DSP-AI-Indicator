"""Gemini port for share research. Provider faults stay off the share-count breaker."""

from __future__ import annotations

import logging
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
    "GeminiShareResearchAdapter",
    "ShareResearchGeminiError",
    "ShareResearchGeminiPort",
    "ShareResearchGeminiResult",
    "classify_share_research_gemini_failure",
]

_PROVIDER_HTTP_5XX = ("500", "502", "503", "504")


def classify_share_research_gemini_failure(
    status: LanguageModelStatus,
    limitations: Sequence[str] | str,
) -> str | None:
    """Map adapter status/limitations to ShareResearchGeminiError.kind.

    ``None`` means COMPLETE — the caller must parse narrative JSON next.
    HTTP 4xx is a provider fault, not a malformed research payload.
    """
    blob = limitations if isinstance(limitations, str) else " ".join(limitations)
    if status is LanguageModelStatus.PROVIDER_UNAVAILABLE:
        return "unavailable"
    if "429" in blob:
        return "rate_limited"
    if "Timeout" in blob or "timeout" in blob.casefold():
        return "timeout"
    if any(code in blob for code in _PROVIDER_HTTP_5XX):
        return "http_5xx"
    if "MODEL_UNAVAILABLE" in blob or "API_KEY" in blob:
        return "unavailable"
    if "http_error" in blob:
        return "http_4xx"
    if "empty Gemini" in blob:
        return "empty"
    if status is not LanguageModelStatus.COMPLETE:
        return "malformed"
    return None


_LOG = logging.getLogger("dsp.share_research.gemini")


class ShareResearchGeminiError(Exception):
    """Provider or parse failure. Not a share-count circuit event."""

    def __init__(self, kind: str, message: str) -> None:
        self.kind = kind
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
    ) -> ShareResearchGeminiResult:
        del identity, stored, horizon_iso, user_prompt
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
            request_id=str(uuid.uuid4()),
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
        kind = classify_share_research_gemini_failure(
            result.status, result.limitations or ()
        )
        if kind == "unavailable":
            raise ShareResearchGeminiError("unavailable", "Gemini provider unavailable")
        if kind == "rate_limited":
            raise ShareResearchGeminiError("rate_limited", "Gemini HTTP 429")
        if kind == "timeout":
            raise ShareResearchGeminiError("timeout", "Gemini timeout")
        if kind == "http_5xx":
            raise ShareResearchGeminiError("http_5xx", "Gemini HTTP 5xx")
        if kind == "http_4xx":
            raise ShareResearchGeminiError("http_4xx", "Gemini HTTP 4xx")
        if kind == "empty":
            raise ShareResearchGeminiError("empty", "Gemini response was empty")
        if kind == "malformed":
            raise ShareResearchGeminiError("malformed", "Gemini research did not complete")
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
