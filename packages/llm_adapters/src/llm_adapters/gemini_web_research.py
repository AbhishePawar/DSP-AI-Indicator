"""Activation-gated Gemini web research. Production remains blocked.

Wraps the existing GeminiAdapter. Does not read environment flags, does
not construct ShareCountSnapshot, and is not wired to /api/v1/analyse.
"""

from __future__ import annotations

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.gemini_adapter import GeminiAdapter
from llm_adapters.gemini_grounding import (
    GroundedWebResearchResult,
    parse_grounded_web_research,
    untrusted_extraction_from_grounded_web_research,
)

__all__ = [
    "ActivationGatedGeminiWebResearch",
    "untrusted_extraction_from_grounded_web_research",
]

_BLOCKED = "AI_PRODUCTION_BLOCKED"


class ActivationGatedGeminiWebResearch:
    """Refuse Gemini web research unless activation_ready is injected True.

    ``activation_ready`` is supplied by the composition root after
    ``evaluate_activation``. It is never read from the environment.
    """

    def __init__(
        self,
        adapter: GeminiAdapter,
        *,
        activation_ready: bool,
    ) -> None:
        self._adapter = adapter
        self._activation_ready = bool(activation_ready)

    @property
    def provider_id(self) -> str:
        return self._adapter.provider_id

    @property
    def model_label(self) -> str:
        return self._adapter.model_label

    def invoke_web_research(
        self,
        request: LanguageModelRequest,
    ) -> tuple[LanguageModelResult, GroundedWebResearchResult]:
        if not self._activation_ready:
            blocked = LanguageModelResult(
                result_id="activation-blocked",
                status=LanguageModelStatus.PROVIDER_UNAVAILABLE,
                provenance=("llm_adapters.gemini_web_research", "dsp.llm.gemini.v1"),
                limitations=(_BLOCKED,),
                model_label=self.model_label,
            )
            grounded = parse_grounded_web_research(
                {},
                narrative_text=None,
                status="unavailable",
                limitations=(_BLOCKED,),
            )
            return blocked, grounded
        return self._adapter.invoke_web_research(request)
