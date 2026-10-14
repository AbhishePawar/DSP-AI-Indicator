"""AI Research Orchestrator — isolated, not wired to the live research HTTP endpoint.

USER REQUEST → ResearchSpecification → trusted DSP tools → routing →
AI provider → structured output → validation → PublicDecisionPack.

Provider HTTP stays in adapters. DSP engines stay behind ToolCallBoundary.
"""

from __future__ import annotations

import contextvars
import math
import os
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from llm_adapters.evaluation import (
    ErrorCategory,
    EvaluationResult,
    EvaluationStatus,
    QualityEvaluation,
    TokenUsage,
)
from llm_adapters.model_catalog import ModelInfo, get_model_info
from llm_adapters.model_tiers import (
    DEFAULT_TIERS,
    ModelTier,
    TierConfig,
    get_tier_config,
)
from llm_adapters.orchestrator.evidence import gather_specified_tools
from llm_adapters.orchestrator.loop import (
    DEFAULT_TOOL_LOOP_LIMITS,
    ToolLoopLimits,
    run_trusted_tool_loop,
)
from llm_adapters.orchestrator.provider import AICompletion, AIProvider
from llm_adapters.orchestrator.specification import (
    ResearchSpecification,
    UserResearchRequest,
)
from llm_adapters.orchestrator.validation import (
    ValidationFailure,
    ValidationSuccess,
    failed_closed_pack,
    validate_research_output,
)
from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)
from llm_adapters.quality_gate import GateOutcome, GateVerdict, run_with_escalation
from llm_adapters.routing import RoutingDecision, decide_routing
from llm_adapters.tools.contract import DSPToolBackend
from llm_adapters.tools.protocol.dispatcher import ToolCallBoundary
from llm_adapters.tools.protocol.models import ToolCallOutcome
from llm_adapters.tools.registry import ToolRegistry

_PROVENANCE = "dsp.research.orchestrator.v1"


class OrchestratorStatus(str, Enum):
    ACCEPTED = "accepted"
    FAILED_CLOSED = "failed_closed"


@dataclass(frozen=True, slots=True)
class OrchestratorResult:
    """Full orchestrator outcome. Browser may receive ``public`` only."""

    status: OrchestratorStatus
    public: PublicDecisionPack
    private: PrivateInternalResult
    gate: GateVerdict

    def to_public(self) -> PublicDecisionPack:
        pack = self.private.to_public()
        assert_no_private_leakage(pack.to_dict())
        return pack


@dataclass
class _AttemptMemory:
    completion: AICompletion | None = None
    prompt: tuple[str, ...] = ()
    outcomes: tuple[ToolCallOutcome, ...] = ()
    catalog: tuple[dict[str, Any], ...] = ()
    validation: ValidationSuccess | ValidationFailure | None = None
    identity: str = ""
    contributing_models: tuple[str, ...] = ()
    conflicting_sections: tuple[str, ...] = ()


_orchestrator_memory_var: contextvars.ContextVar[_AttemptMemory | None] = (
    contextvars.ContextVar("_orchestrator_memory", default=None)
)


class ResearchOrchestrator:
    """Server-side research loop. Not connected to the live research HTTP endpoint."""

    def __init__(
        self,
        *,
        backend: DSPToolBackend,
        providers: Mapping[ModelTier, AIProvider],
        registry: ToolRegistry | None = None,
        tier_registry: Mapping[ModelTier, TierConfig] | None = None,
        loop_limits: ToolLoopLimits | None = None,
        dual_verification: bool = False,
        timeout_seconds: float | None = None,
    ) -> None:
        self._registry = registry or ToolRegistry.default()
        self._boundary = ToolCallBoundary(self._registry, backend)
        self._providers = dict(providers)
        self._tier_registry = (
            dict(tier_registry) if tier_registry is not None else dict(DEFAULT_TIERS)
        )
        self._loop_limits = loop_limits or DEFAULT_TOOL_LOOP_LIMITS
        self._dual_verification = dual_verification
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else float(
                os.environ.get(
                    "DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS",
                    os.environ.get("DSP_AI_REQUEST_TIMEOUT_SECONDS", "20.0"),
                )
            )
        )
        self._memory = _AttemptMemory()

    @property
    def _memory(self) -> _AttemptMemory:
        mem = _orchestrator_memory_var.get()
        if mem is None:
            mem = _AttemptMemory()
            _orchestrator_memory_var.set(mem)
        return mem

    @_memory.setter
    def _memory(self, value: _AttemptMemory) -> None:
        _orchestrator_memory_var.set(value)

    def run(
        self,
        request: UserResearchRequest,
        *,
        timeout_seconds: float | None = None,
        cancellation_event: threading.Event | None = None,
    ) -> OrchestratorResult:
        start_time = time.monotonic()
        eff_timeout = (
            timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        )
        if eff_timeout is not None and not math.isfinite(eff_timeout):
            eff_timeout = self._timeout_seconds
        deadline = start_time + eff_timeout if eff_timeout is not None else None

        spec = ResearchSpecification.from_user_request(
            request,
            allowed_tools=self._boundary.allowed_names(),
        )
        routing = decide_routing(spec.complexity_signals)

        if cancellation_event is not None and cancellation_event.is_set():
            return self._fail_closed(
                spec, routing, ErrorCategory.TIMEOUT, "orchestration cancelled"
            )

        prefetched = gather_specified_tools(spec, self._boundary)
        self._memory = _AttemptMemory(outcomes=prefetched)

        if cancellation_event is not None and cancellation_event.is_set():
            return self._fail_closed(
                spec, routing, ErrorCategory.TIMEOUT, "orchestration cancelled"
            )

        if eff_timeout is not None and eff_timeout <= 0:
            return self._fail_closed(
                spec,
                routing,
                ErrorCategory.TIMEOUT,
                f"timeout before tier execution: {eff_timeout}s",
            )

        if deadline is not None and time.monotonic() >= deadline:
            return self._fail_closed(
                spec,
                routing,
                ErrorCategory.TIMEOUT,
                f"timeout before tier execution: {eff_timeout}s",
            )

        try:
            if self._dual_verification:
                return self._run_dual(
                    spec,
                    routing,
                    deadline=deadline,
                    cancellation_event=cancellation_event,
                )

            def run_at_tier(tier: ModelTier) -> EvaluationResult:
                rem_timeout = (
                    max(0.0, deadline - time.monotonic())
                    if deadline is not None
                    else None
                )
                return self._run_tier(
                    tier,
                    spec,
                    routing,
                    timeout_seconds=rem_timeout,
                    cancellation_event=cancellation_event,
                )

            verdict, accepted = run_with_escalation(
                decision=routing,
                run_at_tier=run_at_tier,
                tier_registry=self._tier_registry,
            )
            return self._finalize(spec, routing, verdict, accepted)
        finally:
            _orchestrator_memory_var.set(None)

    def _fail_closed(
        self,
        spec: ResearchSpecification,
        routing: RoutingDecision,
        category: ErrorCategory,
        reason: str,
    ) -> OrchestratorResult:
        verdict = GateVerdict(
            outcome=GateOutcome.FAILED_CLOSED,
            tier=routing.routing_tier,
            quality_score=0.0,
            meets_floor=False,
            reason=f"{category.value}: {reason}" if category else reason,
            requires_escalation=False,
        )
        return self._finalize(spec, routing, verdict, accepted=None)

    def _run_dual(
        self,
        spec: ResearchSpecification,
        routing: RoutingDecision,
        *,
        deadline: float | None = None,
        cancellation_event: threading.Event | None = None,
    ) -> OrchestratorResult:
        """Run both configured tiers independently over the same evidence snapshot."""
        tiers = (ModelTier.COST_EFFICIENT, ModelTier.PREMIUM)
        attempts: list[tuple[EvaluationResult, _AttemptMemory]] = []
        initial_outcomes = self._memory.outcomes
        for tier in tiers:
            if cancellation_event is not None and cancellation_event.is_set():
                break
            rem_timeout = (
                max(0.0, deadline - time.monotonic()) if deadline is not None else None
            )
            if rem_timeout is not None and rem_timeout <= 0.0:
                break
            self._memory = _AttemptMemory(outcomes=initial_outcomes)
            evaluation = self._run_tier(
                tier,
                spec,
                routing,
                timeout_seconds=rem_timeout,
                cancellation_event=cancellation_event,
            )
            attempts.append((evaluation, self._memory))

        successful = [
            item
            for item in attempts
            if item[0].status is EvaluationStatus.SUCCESS
            and isinstance(item[1].validation, ValidationSuccess)
        ]
        if len(successful) >= 2:
            selected = self._select_evidence_supported(successful)
            merged_evaluation, merged_memory = self._merge_successful_attempts(
                successful, selected
            )
            self._memory = merged_memory
            verdict = GateVerdict(
                outcome=GateOutcome.ACCEPTED,
                tier=self._tier_for_memory(selected[1], attempts),
                reason=(
                    "validated provider findings merged; unresolved narrative "
                    "differences retained as limitations"
                ),
                quality_score=(
                    min(item[0].quality.evidence_correctness for item in successful)
                    * 100.0
                ),
                meets_floor=True,
                requires_escalation=False,
            )
            return self._finalize(spec, routing, verdict, merged_evaluation)
        if successful:
            selected = successful[0]
            self._memory = selected[1]
            verdict = GateVerdict(
                outcome=GateOutcome.ACCEPTED,
                tier=self._tier_for_memory(selected[1], attempts),
                reason="one provider completed; deterministic DSP evidence preserved",
                quality_score=100.0,
                meets_floor=True,
                requires_escalation=False,
            )
            return self._finalize(spec, routing, verdict, selected[0])

        self._memory = (
            attempts[0][1] if attempts else _AttemptMemory(outcomes=initial_outcomes)
        )
        verdict = GateVerdict(
            outcome=GateOutcome.FAILED_CLOSED,
            tier=ModelTier.PREMIUM,
            reason=(
                "both independent providers failed; deterministic result "
                "remains authoritative"
            ),
            quality_score=0.0,
            meets_floor=False,
            requires_escalation=False,
        )
        return self._finalize(spec, routing, verdict, None)

    @staticmethod
    def _merge_texts(values: list[str]) -> str:
        """Merge unique, already-validated narrative text without choosing a winner."""
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            key = " ".join(text.casefold().split())
            if text and key not in seen:
                seen.add(key)
                unique.append(text)
        if not unique:
            return "Evidence unavailable."
        if len(unique) == 1:
            return unique[0]
        return "\n\n".join(f"- {item}" for item in unique)

    @classmethod
    def _merge_successful_attempts(
        cls,
        successful: list[tuple[EvaluationResult, _AttemptMemory]],
        selected: tuple[EvaluationResult, _AttemptMemory],
    ) -> tuple[EvaluationResult, _AttemptMemory]:
        """Union independently validated findings while preserving DSP authority.

        This method does not attempt to decide which conflicting narrative is
        true. Distinct model summaries are retained and explicitly disclosed
        as a limitation; deterministic recommendation and valuation fields
        remain those from the selected, independently validated result.
        """
        from dataclasses import replace

        from llm_adapters.orchestrator.validation import ValidationSuccess

        selected_eval, selected_memory = selected
        selected_validation = selected_memory.validation
        if not isinstance(selected_validation, ValidationSuccess):
            return selected

        validations = [
            memory.validation
            for _, memory in successful
            if isinstance(memory.validation, ValidationSuccess)
        ]
        outputs = [validation.output for validation in validations]
        packs = [validation.pack for validation in validations]
        if len(outputs) < 2 or len(packs) < 2:
            return selected

        section_names = (
            "business_quality",
            "moat",
            "management",
            "financial_strength",
            "earnings_quality",
            "growth_quality",
            "industry",
            "risk",
            "buffett_analysis",
        )
        output_updates: dict[str, Any] = {}
        divergent_sections: list[str] = []
        for name in section_names:
            sections = [getattr(output, name) for output in outputs]
            summaries = [section.summary for section in sections]
            if len({" ".join(s.casefold().split()) for s in summaries}) > 1:
                divergent_sections.append(name)
            ids = list(
                dict.fromkeys(
                    evidence_id
                    for section in sections
                    for evidence_id in section.evidence_ids
                )
            )
            output_updates[name] = sections[0].model_copy(
                update={
                    "summary": cls._merge_texts(summaries),
                    "evidence_ids": ids,
                    "unavailable": all(section.unavailable for section in sections),
                }
            )

        # Valuation is deliberately not merged: each model's figures must remain
        # bound to the deterministic DSP valuation tool, never AI-derived.
        all_evidence: list[Any] = []
        evidence_keys: set[tuple[str, str, str]] = set()
        for output in outputs:
            for evidence in output.evidence:
                key = (evidence.id, evidence.source, evidence.claim)
                if key not in evidence_keys:
                    evidence_keys.add(key)
                    all_evidence.append(evidence)

        limitations = list(
            dict.fromkeys(
                limitation for output in outputs for limitation in output.limitations
            )
        )
        if divergent_sections:
            limitations.append(
                "Unresolved differences between validated model narratives in: "
                + ", ".join(divergent_sections)
                + (
                    ". Both evidence-backed perspectives are retained; "
                    "review cited sources."
                )
            )

        base_output = selected_validation.output
        merged_output = base_output.model_copy(
            update={
                **output_updates,
                "decision_brief": cls._merge_texts(
                    [output.decision_brief for output in outputs]
                ),
                "evidence": all_evidence,
                "limitations": list(dict.fromkeys(limitations)),
                "confidence": min(output.confidence for output in outputs),
                "research_status": (
                    "partial"
                    if divergent_sections
                    or any(output.research_status != "complete" for output in outputs)
                    else "complete"
                ),
            }
        )

        base_pack = selected_validation.pack
        pack_limitations = list(
            dict.fromkeys(
                limitation for pack in packs for limitation in pack.limitations
            )
        )
        if divergent_sections:
            pack_limitations.append(
                "Unresolved differences between model narratives are "
                "retained for review."
            )
        merged_pack = replace(
            base_pack,
            analysis=cls._merge_texts([pack.analysis for pack in packs]),
            risks=tuple(dict.fromkeys(risk for pack in packs for risk in pack.risks)),
            evidence_citations=tuple(
                dict.fromkeys(
                    citation for pack in packs for citation in pack.evidence_citations
                )
            ),
            confidence=min(pack.confidence for pack in packs),
            limitations=tuple(pack_limitations),
        )

        merged_validation = ValidationSuccess(output=merged_output, pack=merged_pack)
        merged_outcome_rows: list[ToolCallOutcome] = []
        outcome_ids: set[str] = set()
        for _, memory in successful:
            for outcome in memory.outcomes:
                if outcome.call_id not in outcome_ids:
                    outcome_ids.add(outcome.call_id)
                    merged_outcome_rows.append(outcome)
        merged_outcomes = tuple(merged_outcome_rows)
        merged_catalog_rows: list[dict[str, Any]] = []
        catalog_keys: set[str] = set()
        for _, memory in successful:
            for row in memory.catalog:
                key = str(row.get("id", ""))
                if key and key not in catalog_keys:
                    catalog_keys.add(key)
                    merged_catalog_rows.append(row)
        merged_memory = _AttemptMemory(
            completion=selected_memory.completion,
            prompt=selected_memory.prompt,
            outcomes=merged_outcomes,
            catalog=tuple(merged_catalog_rows),
            validation=merged_validation,
            identity=selected_memory.identity,
            contributing_models=tuple(
                dict.fromkeys(
                    memory.identity for _, memory in successful if memory.identity
                )
            ),
            conflicting_sections=tuple(divergent_sections),
        )
        return selected_eval, merged_memory

    @staticmethod
    def _tier_for_memory(
        memory: _AttemptMemory,
        attempts: list[tuple[EvaluationResult, _AttemptMemory]],
    ) -> ModelTier:
        for index, (_, candidate) in enumerate(attempts):
            if candidate is memory:
                return (ModelTier.COST_EFFICIENT, ModelTier.PREMIUM)[index]
        return ModelTier.PREMIUM

    @staticmethod
    def _select_evidence_supported(
        attempts: list[tuple[EvaluationResult, _AttemptMemory]],
    ) -> tuple[EvaluationResult, _AttemptMemory]:
        """Resolve model disagreement without provider preference.

        Validation already binds recommendations, valuations, and citations to
        DSP tool outputs. When narratives differ, the result with the greater
        evidence-backed quality score wins; ties are resolved conservatively by
        the lower reported confidence in the validated output.
        """
        ranked = sorted(
            attempts,
            key=lambda item: (
                item[0].quality.evidence_correctness,
                item[0].quality.factual_accuracy,
                (
                    -item[1].validation.output.confidence
                    if isinstance(item[1].validation, ValidationSuccess)
                    else 0.0
                ),
            ),
            reverse=True,
        )
        return ranked[0]

    def _run_tier(
        self,
        tier: ModelTier,
        spec: ResearchSpecification,
        routing: RoutingDecision,
        *,
        timeout_seconds: float | None = None,
        cancellation_event: threading.Event | None = None,
    ) -> EvaluationResult:
        del routing
        provider = self._providers.get(tier)
        identity = get_tier_config(tier, self._tier_registry).model_identity
        if provider is None:
            return self._eval(
                identity,
                spec.spec_id,
                EvaluationStatus.FAILED,
                ErrorCategory.PROVIDER_UNAVAILABLE,
                structured=False,
            )
        loop = run_trusted_tool_loop(
            provider=provider,
            spec=spec,
            boundary=self._boundary,
            initial_outcomes=self._memory.outcomes,
            limits=self._loop_limits,
            timeout_seconds=timeout_seconds,
            cancellation_event=cancellation_event,
        )
        completion = loop.completion
        self._memory.completion = completion
        self._memory.prompt = loop.prompt
        self._memory.outcomes = loop.outcomes
        self._memory.catalog = loop.catalog
        self._memory.identity = f"{provider.provider_id}:{provider.model_label}"

        if loop.error_category is not ErrorCategory.NONE:
            return self._eval(
                identity,
                spec.spec_id,
                EvaluationStatus.FAILED,
                loop.error_category,
                structured=False,
                latency_ms=completion.latency_ms,
                usage=TokenUsage(completion.input_tokens, completion.output_tokens),
            )

        if completion.status != "complete" or not completion.text:
            category = (
                ErrorCategory.PROVIDER_UNAVAILABLE
                if completion.status == "unavailable"
                else ErrorCategory.PROVIDER_FAILED
            )
            return self._eval(
                identity,
                spec.spec_id,
                EvaluationStatus.FAILED,
                category,
                structured=False,
                latency_ms=completion.latency_ms,
                usage=TokenUsage(completion.input_tokens, completion.output_tokens),
            )

        validated = validate_research_output(
            completion.text,
            outcomes=loop.outcomes,
            catalog=loop.catalog,
        )
        self._memory.validation = validated
        if isinstance(validated, ValidationFailure):
            return self._eval(
                identity,
                spec.spec_id,
                EvaluationStatus.FAILED,
                validated.error_category,
                structured=False,
                latency_ms=completion.latency_ms,
                usage=TokenUsage(completion.input_tokens, completion.output_tokens),
            )
        return self._eval(
            identity,
            spec.spec_id,
            EvaluationStatus.SUCCESS,
            ErrorCategory.NONE,
            structured=True,
            latency_ms=completion.latency_ms,
            usage=TokenUsage(completion.input_tokens, completion.output_tokens),
            quality=QualityEvaluation(
                factual_accuracy=1.0,
                evidence_correctness=1.0,
                structured_output=1.0,
                unsupported_claims=1.0,
            ),
        )

    def _finalize(
        self,
        spec: ResearchSpecification,
        routing: RoutingDecision,
        verdict: GateVerdict,
        accepted: EvaluationResult | None,
    ) -> OrchestratorResult:
        completion = self._memory.completion
        prompt_text = "\n\n".join(self._memory.prompt)
        identity = (
            self._memory.identity
            or get_tier_config(verdict.tier, self._tier_registry).model_identity
        )
        provider_id, _, model = identity.partition(":")
        tool_calls = tuple(
            {"call_id": o.call_id, "tool_name": o.tool_name, "status": o.status.value}
            for o in self._memory.outcomes
        )
        tool_results = tuple(dict(o.audit) for o in self._memory.outcomes)
        raw = completion.text if completion is not None else ""
        usage_in = completion.input_tokens if completion is not None else 0
        usage_out = completion.output_tokens if completion is not None else 0
        latency = completion.latency_ms if completion is not None else 0

        if verdict.outcome is GateOutcome.ACCEPTED and isinstance(
            self._memory.validation, ValidationSuccess
        ):
            public = self._memory.validation.pack
            status = OrchestratorStatus.ACCEPTED
            internal_validation = {
                "outcome": verdict.outcome.value,
                "reason": verdict.reason,
            }
        else:
            public = failed_closed_pack()
            status = OrchestratorStatus.FAILED_CLOSED
            internal_validation = {
                "outcome": verdict.outcome.value,
                "reason": verdict.reason,
            }

        private = PrivateInternalResult(
            public=public,
            provider=provider_id or "unknown",
            model=model or identity,
            routing_tier=routing.routing_tier.value,
            routing_reasons=routing.routing_reasons,
            confidence_requirement=routing.confidence_requirement,
            estimated_cost_usd=(
                accepted.estimated_cost_usd if accepted is not None else 0.0
            ),
            input_tokens=usage_in,
            output_tokens=usage_out,
            latency_ms=latency,
            model_score=verdict.quality_score,
            routing_criteria=tuple(s.value for s in spec.complexity_signals),
            internal_prompt=prompt_text,
            tool_calls=tool_calls,
            tool_results=tool_results,
            raw_ai_response=raw or "",
            internal_validation=internal_validation,
            chain_of_thought="",
            audit={
                "spec_id": spec.spec_id,
                "spec_version": spec.spec_version,
                "contributing_models": self._memory.contributing_models
                or ((identity,) if identity else ()),
                "conflicting_sections": self._memory.conflicting_sections,
                "reconciliation_mode": (
                    "complementary_merge"
                    if len(self._memory.contributing_models) > 1
                    else "single_provider_or_deterministic"
                ),
            },
        )
        assert_no_private_leakage(public.to_dict())
        return OrchestratorResult(
            status=status,
            public=public,
            private=private,
            gate=verdict,
        )

    def _eval(
        self,
        identity: str,
        spec_id: str,
        status: EvaluationStatus,
        category: ErrorCategory,
        *,
        structured: bool,
        latency_ms: int = 0,
        usage: TokenUsage | None = None,
        quality: QualityEvaluation | None = None,
    ) -> EvaluationResult:
        try:
            model: ModelInfo = get_model_info(identity)
        except KeyError:
            # Test doubles may use catalog identities already; fall back to
            # the default cost-efficient identity for schema completeness.
            model = get_model_info("deepseek:deepseek-chat")
        return EvaluationResult(
            model=model,
            research_case_id=spec_id,
            status=status,
            latency_ms=latency_ms,
            usage=usage or TokenUsage(),
            estimated_cost_usd=0.0,
            structured_output_valid=structured,
            quality=quality or QualityEvaluation(),
            error_category=category,
        )


__all__ = [
    "OrchestratorResult",
    "OrchestratorStatus",
    "ResearchOrchestrator",
]
