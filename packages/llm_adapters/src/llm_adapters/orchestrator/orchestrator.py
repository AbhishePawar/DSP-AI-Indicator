"""AI Research Orchestrator — isolated, not wired to the live research HTTP endpoint.

USER REQUEST → ResearchSpecification → trusted DSP tools → routing →
AI provider → structured output → validation → PublicDecisionPack.

Provider HTTP stays in adapters. DSP engines stay behind ToolCallBoundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from llm_adapters.evaluation import (
    ErrorCategory,
    EvaluationResult,
    EvaluationStatus,
    QualityEvaluation,
    TokenUsage,
)
from llm_adapters.model_catalog import ModelInfo, get_model_info
from llm_adapters.model_tiers import DEFAULT_TIERS, ModelTier, TierConfig, get_tier_config
from llm_adapters.orchestrator.evidence import (
    evidence_catalog,
    gather_specified_tools,
)
from llm_adapters.orchestrator.provider import AICompletion, AIProvider
from llm_adapters.orchestrator.research_prompt import build_research_prompt
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
from llm_adapters.tools.protocol.dispatcher import ToolCallBoundary, safe_provider_payload
from llm_adapters.tools.protocol.models import ToolCallOutcome
from llm_adapters.tools.registry import ToolRegistry

_MAX_TOOL_ROUNDS = 3
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


class ResearchOrchestrator:
    """Server-side research loop. Not connected to the live research HTTP endpoint."""

    def __init__(
        self,
        *,
        backend: DSPToolBackend,
        providers: Mapping[ModelTier, AIProvider],
        registry: ToolRegistry | None = None,
        tier_registry: Mapping[ModelTier, TierConfig] | None = None,
    ) -> None:
        self._registry = registry or ToolRegistry.default()
        self._boundary = ToolCallBoundary(self._registry, backend)
        self._providers = dict(providers)
        self._tier_registry = dict(tier_registry) if tier_registry is not None else dict(DEFAULT_TIERS)
        self._memory = _AttemptMemory()

    def run(self, request: UserResearchRequest) -> OrchestratorResult:
        spec = ResearchSpecification.from_user_request(
            request,
            allowed_tools=self._boundary.allowed_names(),
        )
        routing = decide_routing(spec.complexity_signals)
        prefetched = gather_specified_tools(spec, self._boundary)
        self._memory = _AttemptMemory(outcomes=prefetched)

        def run_at_tier(tier: ModelTier) -> EvaluationResult:
            return self._run_tier(tier, spec, routing)

        verdict, accepted = run_with_escalation(
            decision=routing,
            run_at_tier=run_at_tier,
            tier_registry=self._tier_registry,
        )
        return self._finalize(spec, routing, verdict, accepted)

    def _run_tier(
        self,
        tier: ModelTier,
        spec: ResearchSpecification,
        routing: RoutingDecision,
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
        outcomes = list(self._memory.outcomes)
        catalog = evidence_catalog(tuple(outcomes))
        prompt = build_research_prompt(
            spec,
            evidence_catalog=catalog,
            tool_manifest=self._boundary.public_manifest(),
        )
        completion = provider.complete(
            prompt_parts=prompt,
            evidence_catalog=catalog,
        )
        rounds = 0
        while completion.requested_calls and rounds < _MAX_TOOL_ROUNDS:
            executed = self._boundary.execute_many(completion.requested_calls)
            outcomes.extend(executed)
            catalog = evidence_catalog(tuple(outcomes))
            prompt = build_research_prompt(
                spec,
                evidence_catalog=catalog,
                tool_manifest=self._boundary.public_manifest(),
            )
            tool_payloads = tuple(safe_provider_payload(item) for item in executed)
            completion = provider.complete(
                prompt_parts=prompt,
                evidence_catalog=catalog,
                prior_tool_results=tool_payloads,
            )
            rounds += 1

        self._memory.completion = completion
        self._memory.prompt = prompt
        self._memory.outcomes = tuple(outcomes)
        self._memory.catalog = catalog
        self._memory.identity = f"{provider.provider_id}:{provider.model_label}"

        if completion.status != "complete" or not completion.text:
            category = (
                ErrorCategory.PROVIDER_UNAVAILABLE
                if completion.status == "unavailable"
                else ErrorCategory.UNKNOWN
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
            outcomes=tuple(outcomes),
            catalog=catalog,
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
        identity = self._memory.identity or get_tier_config(
            verdict.tier, self._tier_registry
        ).model_identity
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
            internal_validation = {"outcome": verdict.outcome.value, "reason": verdict.reason}
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
            estimated_cost_usd=accepted.estimated_cost_usd if accepted is not None else 0.0,
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
            audit={"spec_id": spec.spec_id, "spec_version": spec.spec_version},
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
