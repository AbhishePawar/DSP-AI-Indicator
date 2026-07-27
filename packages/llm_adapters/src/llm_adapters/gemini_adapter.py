"""Gemini adapter stub — configured interface without network in EPIC-012."""

from __future__ import annotations

import uuid

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.config import LLMPlatformConfig

_PROVENANCE = ("llm_adapters.gemini", "dsp.llm.gemini.stub.v1")


class GeminiAdapter:
    """Stub adapter — returns unavailable until a future epic wires the SDK."""

    provider_id = "gemini"

    def __init__(self, config: LLMPlatformConfig) -> None:
        self._config = config
        self.model_label = config.gemini_model

    def is_configured(self) -> bool:
        return bool(self._config.gemini_api_key)

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        if not self.is_configured():
            return LanguageModelResult(
                result_id=str(uuid.uuid4()),
                status=LanguageModelStatus.PROVIDER_UNAVAILABLE,
                provenance=_PROVENANCE,
                limitations=("GEMINI_API_KEY not configured",),
                model_label=self.model_label,
            )
        return LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.PROVIDER_UNAVAILABLE,
            provenance=_PROVENANCE,
            limitations=("Gemini adapter stub — not implemented in EPIC-012",),
            model_label=self.model_label,
        )

    def stream_invoke(self, request: LanguageModelRequest):
        yield ""
