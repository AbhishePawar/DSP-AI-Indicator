"""Provider-neutral AI completion port.

The orchestrator talks only to this port. Provider HTTP, API keys, and
vendor SDKs stay inside existing provider adapters (or test doubles).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.interfaces import ProviderAdapter
from llm_adapters.tools.protocol.models import ToolCall, ToolCallOutcome


@dataclass(frozen=True, slots=True)
class AICompletion:
    """Normalized provider result. No raw HTTP body, no credentials."""

    status: str  # complete | failed | unavailable
    text: str | None
    requested_calls: tuple[ToolCall | ToolCallOutcome, ...]
    provider_id: str
    model_label: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


@runtime_checkable
class AIProvider(Protocol):
    """Reasoning-brain port. Implementations must not live in DSP engines."""

    provider_id: str
    model_label: str

    def complete(
        self,
        *,
        prompt_parts: tuple[str, ...],
        evidence_catalog: tuple[dict[str, Any], ...],
        prior_tool_results: tuple[dict[str, Any], ...] = (),
    ) -> AICompletion:
        """Return structured text and/or already-normalized tool calls."""
        ...


class AdapterBackedAIProvider:
    """Wraps an existing ProviderAdapter without adding HTTP here.

    Tool-calling is not sent on the live ``invoke`` path (STEP 3H left
    ``invoke`` unwired). Prefetched tool evidence is in the prompt.
    """

    def __init__(self, adapter: ProviderAdapter) -> None:
        self._adapter = adapter

    @property
    def provider_id(self) -> str:
        return self._adapter.provider_id

    @property
    def model_label(self) -> str:
        return self._adapter.model_label

    def complete(
        self,
        *,
        prompt_parts: tuple[str, ...],
        evidence_catalog: tuple[dict[str, Any], ...],
        prior_tool_results: tuple[dict[str, Any], ...] = (),
    ) -> AICompletion:
        del evidence_catalog, prior_tool_results
        if not self._adapter.is_configured():
            return AICompletion(
                status="unavailable",
                text=None,
                requested_calls=(),
                provider_id=self.provider_id,
                model_label=self.model_label,
            )
        request = LanguageModelRequest(
            request_id=str(uuid.uuid4()),
            intent_class=UserIntentType.EXPLAIN_REPORT,
            prompt_parts=prompt_parts,
            context_digest_ids=("Recommendation",),
            provenance=("llm_adapters.orchestrator", "dsp.research.orchestrator.v1"),
            constraints=("Return JSON only. Do not invent numbers.",),
        )
        result: LanguageModelResult = self._adapter.invoke(request)
        if result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE:
            status = "unavailable"
        elif result.status is LanguageModelStatus.COMPLETE:
            status = "complete"
        else:
            status = "failed"
        return AICompletion(
            status=status,
            text=result.narrative_text,
            requested_calls=(),
            provider_id=self.provider_id,
            model_label=result.model_label or self.model_label,
        )


__all__ = [
    "AICompletion",
    "AIProvider",
    "AdapterBackedAIProvider",
]
