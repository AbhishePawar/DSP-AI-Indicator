"""Copilot complete service — LLM with deterministic fallback."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from llm_adapters.deterministic_composer import (
    DeterministicAnswer,
    compose_deterministic_answer,
    extract_research_payload,
)
from llm_adapters.openai_adapter import map_intent_to_user_intent
from llm_adapters.prompts import build_prompt_parts
from llm_adapters.registry import ProviderRegistry, build_default_registry
from llm_adapters.safety import validate_llm_narrative

_PROVENANCE = ("llm_adapters.service", "dsp.copilot.complete.v1")


@dataclass(frozen=True, slots=True)
class CopilotCompleteResult:
    content: str
    citations: list[str]
    intent: str
    unavailable: bool
    provider_id: str
    limitations: tuple[str, ...] = ()
    streamed: bool = False


class CopilotCompleteService:
    """Orchestrates provider selection, prompts, safety, and fallback."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or build_default_registry()

    def complete(
        self,
        *,
        question_id: str,
        freeform: str | None,
        request: dict[str, Any] | None,
        response: dict[str, Any] | None,
        secondary_request: dict[str, Any] | None = None,
        secondary_response: dict[str, Any] | None = None,
        last_intent: str | None = None,
        market_context: dict[str, Any] | None = None,
    ) -> CopilotCompleteResult:
        research = extract_research_payload(request, response)
        deterministic = compose_deterministic_answer(
            question_id=question_id,
            freeform=freeform,
            research=research,
            last_intent=last_intent,
        )

        provider_name, adapter = self._registry.resolve_active()
        if adapter is None:
            return self._from_deterministic(deterministic, "deterministic")

        question = freeform or question_id
        prompt_parts = build_prompt_parts(
            question=question,
            intent=deterministic.intent,
            research=research,
            market_context=market_context,
        )
        lm_request = LanguageModelRequest(
            request_id=str(uuid.uuid4()),
            intent_class=map_intent_to_user_intent(deterministic.intent),
            prompt_parts=prompt_parts,
            context_digest_ids=tuple(deterministic.citations),
            provenance=_PROVENANCE,
            constraints=(
                "Do not modify recommendations, scores, intrinsic values, "
                "or committee decisions.",
            ),
        )

        dual_result = self._complete_with_cross_verification(
            lm_request=lm_request,
            research=research,
            deterministic=deterministic,
        )
        if dual_result is not None:
            return dual_result

        lm_result = self._invoke_provider_with_fallback(provider_name, adapter, lm_request)
        if lm_result.status not in (
            LanguageModelStatus.COMPLETE,
            LanguageModelStatus.PARTIAL,
        ):
            limitations = tuple(lm_result.limitations or ("LLM unavailable",))
            result = self._from_deterministic(deterministic, "deterministic")
            return CopilotCompleteResult(
                content=result.content,
                citations=result.citations,
                intent=result.intent,
                unavailable=result.unavailable,
                provider_id="deterministic",
                limitations=limitations + result.limitations,
            )

        narrative = lm_result.narrative_text or ""
        safe_text, safety_warnings = validate_llm_narrative(narrative, research)
        return CopilotCompleteResult(
            content=safe_text,
            citations=list(deterministic.citations),
            intent=deterministic.intent,
            unavailable=False,
            provider_id=provider_name,
            limitations=tuple(lm_result.limitations or ()) + safety_warnings,
        )

    def stream(
        self,
        *,
        question_id: str,
        freeform: str | None,
        request: dict[str, Any] | None,
        response: dict[str, Any] | None,
        last_intent: str | None = None,
        market_context: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Yield SSE-ready text deltas."""
        result = self.complete(
            question_id=question_id,
            freeform=freeform,
            request=request,
            response=response,
            last_intent=last_intent,
            market_context=market_context,
        )
        words = result.content.split(" ")
        for index, word in enumerate(words):
            prefix = "" if index == 0 else " "
            yield f"{prefix}{word}"

    def list_providers(self) -> list[dict[str, object]]:
        return self._registry.list_providers()

    def active_provider_id(self) -> str:
        provider_name, _ = self._registry.resolve_active()
        return provider_name

    def _complete_with_cross_verification(
        self,
        *,
        lm_request: LanguageModelRequest,
        research: dict[str, Any],
        deterministic: DeterministicAnswer,
    ) -> CopilotCompleteResult | None:
        """Run independent Gemini/OpenAI analyses and reconcile privately.

        This path is intentionally internal: only the reconciled narrative is
        returned. Validated DSP data and deterministic calculations outrank
        either model, and an unavailable model never blocks the final result.
        """
        gemini = self._registry.get("gemini")
        openai = self._registry.get("openai")
        if not gemini or not openai or not gemini.is_configured() or not openai.is_configured():
            return None

        gemini_result = self._invoke_provider_with_fallback("gemini", gemini, lm_request)
        openai_result = self._invoke_provider_with_fallback("openai", openai, lm_request)
        successful = [
            result
            for result in (gemini_result, openai_result)
            if result.status in (LanguageModelStatus.COMPLETE, LanguageModelStatus.PARTIAL)
            and result.narrative_text
        ]
        if not successful:
            return None
        if len(successful) == 1:
            narrative = successful[0].narrative_text or ""
            safe_text, warnings = validate_llm_narrative(narrative, research)
            return CopilotCompleteResult(
                content=safe_text,
                citations=list(deterministic.citations),
                intent=deterministic.intent,
                unavailable=False,
                provider_id="cross-verified",
                limitations=("One independent analysis was unavailable.",) + warnings,
            )

        reconciliation_prompt = LanguageModelRequest(
            request_id=str(uuid.uuid4()),
            intent_class=lm_request.intent_class,
            prompt_parts=(
                "Reconcile two independent research analyses into one concise final explanation.",
                "Use this evidence hierarchy: approved financial data, DSP-validated data, deterministic DSP calculations, DSP valuation methodology, supporting evidence, then model interpretations.",
                "Never change or invent numerical facts. Do not choose a model by score or fluency. If interpretation remains uncertain, use the conservative evidence-supported interpretation.",
                f"Validated DSP context: {research}",
                f"Independent analysis A: {successful[0].narrative_text}",
                f"Independent analysis B: {successful[1].narrative_text}",
            ),
            context_digest_ids=lm_request.context_digest_ids,
            provenance=("llm_adapters.service", "dsp.cross_verification.v1"),
            constraints=(
                "Return only the final client-safe explanation.",
                "Do not mention models, disagreement, prompts, reconciliation, or internal confidence.",
            ),
        )
        resolver = openai if self._registry.config.default_provider == "gemini" else gemini
        resolved = self._invoke_with_retry(resolver, reconciliation_prompt)
        if resolved.status not in (LanguageModelStatus.COMPLETE, LanguageModelStatus.PARTIAL):
            resolved = successful[0]
        narrative = resolved.narrative_text or ""
        safe_text, warnings = validate_llm_narrative(narrative, research)
        return CopilotCompleteResult(
            content=safe_text,
            citations=list(deterministic.citations),
            intent=deterministic.intent,
            unavailable=False,
            provider_id="cross-verified",
            limitations=tuple(warnings),
        )

    def _invoke_provider_with_fallback(
        self,
        provider_name: str,
        adapter,
        request: LanguageModelRequest,
    ) -> LanguageModelResult:
        result = self._invoke_with_retry(adapter, request)
        if result.status in (LanguageModelStatus.COMPLETE, LanguageModelStatus.PARTIAL):
            return result
        direct_adapter = self._registry.direct_fallback(provider_name)
        if direct_adapter is not None and direct_adapter is not adapter:
            fallback = self._invoke_with_retry(direct_adapter, request)
            if fallback.status in (LanguageModelStatus.COMPLETE, LanguageModelStatus.PARTIAL):
                return fallback
        return result

    def _invoke_with_retry(
        self,
        adapter,
        request: LanguageModelRequest,
    ) -> LanguageModelResult:
        attempts = max(1, self._registry.config.max_retries + 1)
        last: LanguageModelResult | None = None
        for _ in range(attempts):
            last = adapter.invoke(request)
            if last.status in (
                LanguageModelStatus.COMPLETE,
                LanguageModelStatus.PARTIAL,
            ):
                return last
        return last or LanguageModelResult(
            result_id=str(uuid.uuid4()),
            status=LanguageModelStatus.FAILED,
            provenance=_PROVENANCE,
            limitations=("LLM invocation failed",),
        )

    def _from_deterministic(
        self,
        answer: DeterministicAnswer,
        provider_id: str,
    ) -> CopilotCompleteResult:
        return CopilotCompleteResult(
            content=answer.content,
            citations=list(answer.citations),
            intent=answer.intent,
            unavailable=answer.unavailable,
            provider_id=provider_id,
            limitations=(),
        )
