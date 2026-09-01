"""Provider-neutral AI completion port.

The orchestrator talks only to this port. Provider HTTP, API keys, and
vendor SDKs stay inside existing provider adapters (or test doubles).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
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
        tool_manifest: Sequence[Mapping[str, Any]] = (),
        prior_outcomes: tuple[ToolCallOutcome, ...] = (),
    ) -> AICompletion:
        """Return structured text and/or already-normalized tool calls."""
        ...


class AdapterBackedAIProvider:
    """Wraps an existing ProviderAdapter without adding HTTP here.

    Research completions use ``invoke_research`` when the adapter exposes
    it so the public DSP tool manifest can be translated by the existing
    protocol mixins. Copilot ``invoke`` is unchanged and still does not
    send tools. This class never performs HTTP.
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
        tool_manifest: Sequence[Mapping[str, Any]] = (),
        prior_outcomes: tuple[ToolCallOutcome, ...] = (),
    ) -> AICompletion:
        del evidence_catalog
        if not self._adapter.is_configured():
            return AICompletion(
                status="unavailable",
                text=None,
                requested_calls=(),
                provider_id=self.provider_id,
                model_label=self.model_label,
            )
        parts = list(prompt_parts)
        if prior_tool_results:
            parts.append(
                "Latest DSP tool results: "
                + json.dumps(
                    list(prior_tool_results),
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
        formatter = getattr(self._adapter, "format_tool_results", None)
        if prior_outcomes and callable(formatter):
            formatted = formatter(prior_outcomes)
            parts.append(
                "Provider tool result messages: "
                + json.dumps(formatted, separators=(",", ":"), sort_keys=True)
            )
        request = LanguageModelRequest(
            request_id=str(uuid.uuid4()),
            intent_class=UserIntentType.EXPLAIN_REPORT,
            prompt_parts=tuple(parts),
            context_digest_ids=("Recommendation",),
            provenance=("llm_adapters.orchestrator", "dsp.research.orchestrator.v1"),
            constraints=("Return JSON only. Do not invent numbers.",),
        )
        tools = None
        declarations = getattr(self._adapter, "tool_declarations", None)
        if tool_manifest and callable(declarations):
            tools = declarations(tool_manifest)

        raw: Any = None
        invoke_research = getattr(self._adapter, "invoke_research", None)
        if callable(invoke_research):
            result, raw = invoke_research(
                request,
                tools=tools,
                tool_result_messages=None,
            )
        else:
            result = self._adapter.invoke(request)
        if not isinstance(result, LanguageModelResult):
            return AICompletion(
                status="failed",
                text=None,
                requested_calls=(),
                provider_id=self.provider_id,
                model_label=self.model_label,
            )

        requested: tuple[ToolCall | ToolCallOutcome, ...] = ()
        contains = getattr(self._adapter, "payload_contains_tool_calls", None)
        parser = getattr(self._adapter, "parse_tool_calls", None)
        allowed_fn = getattr(self._adapter, "allowed_names_from_manifest", None)
        if (
            raw is not None
            and callable(contains)
            and callable(parser)
            and contains(raw)
        ):
            allowed = allowed_fn(tool_manifest) if callable(allowed_fn) else frozenset()
            try:
                parsed = parser(raw, allowed_internal=allowed)
            except Exception:  # noqa: BLE001 — fail-closed
                return AICompletion(
                    status="failed",
                    text=None,
                    requested_calls=(),
                    provider_id=self.provider_id,
                    model_label=self.model_label,
                )
            requested = tuple(parsed)

        if result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE:
            status = "unavailable"
        elif result.status is LanguageModelStatus.COMPLETE:
            status = "complete"
        else:
            status = "failed"
        text = None if requested else result.narrative_text
        return AICompletion(
            status=status,
            text=text,
            requested_calls=requested,
            provider_id=self.provider_id,
            model_label=result.model_label or self.model_label,
        )


__all__ = [
    "AICompletion",
    "AIProvider",
    "AdapterBackedAIProvider",
]
