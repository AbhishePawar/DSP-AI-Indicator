"""Benchmark harness — runs benchmark cases through the STEP 3B gate.

Cost-efficient first; escalate to premium on gate failure; fail closed
if both fail. The harness records everything privately — no public
serialization. Output is consumed only by the offline reporter.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest

from llm_adapters.benchmark_cases import (
    BENCHMARK_CASES,
    BenchmarkCase,
    ResearchSpec,
)
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.cost_scoring import (
    calculate_cost_score,
    calculate_estimated_cost,
    calculate_overall_score,
    calculate_quality_score,
)
from llm_adapters.deepseek_adapter import DeepSeekAdapter
from llm_adapters.evaluation import (
    ErrorCategory,
    EvaluationResult,
    EvaluationStatus,
    QualityEvaluation,
    TokenUsage,
)
from llm_adapters.gemini_adapter import GeminiAdapter
from llm_adapters.anthropic_adapter import AnthropicAdapter
from llm_adapters.model_catalog import (
    DEFAULT_CATALOG,
    ModelInfo,
    ModelPricing,
    get_model_info,
)
from llm_adapters.model_tiers import (
    DEFAULT_TIERS,
    ModelTier,
    TierConfig,
    get_tier_config,
)
from llm_adapters.openai_adapter import OpenAIAdapter
from llm_adapters.privacy_boundary import assert_no_private_leakage
from llm_adapters.quality_evaluator import EvaluatorVerdict, evaluate_narrative
from llm_adapters.quality_gate import (
    GateOutcome,
    GateVerdict,
    evaluate_gate,
)
from llm_adapters.routing import (
    ComplexitySignal,
    RoutingDecision,
    decide_routing,
)


# --- model identity catalog for benchmark targets -------------------------


BENCHMARK_MODELS: tuple[str, ...] = (
    "deepseek:deepseek-chat",
    "gemini:gemini-1.5-flash",
    "openai:gpt-4o-mini",
    "anthropic:claude-3-5-sonnet-20241022",
)


# --- prompt construction --------------------------------------------------


def _build_prompt(spec: ResearchSpec) -> tuple[str, ...]:
    """Provider-neutral prompt: system rules + user context + question."""
    system = (
        "You are a research assistant for an investment terminal. "
        "Use ONLY the supplied DSP evidence. Never invent numbers. "
        "If information is missing, say it is unavailable. "
        "Every factual claim must reference the supplied evidence."
    )
    evidence_lines = [f"  {k}: {v}" for k, v in spec.evidence.items()]
    evidence_block = "Evidence:\n" + "\n".join(evidence_lines)
    return (system, f"{evidence_block}\n\nQuestion: {spec.question}")


def _build_request(spec: ResearchSpec) -> LanguageModelRequest:
    return LanguageModelRequest(
        request_id=str(uuid.uuid4()),
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=_build_prompt(spec),
        context_digest_ids=tuple(spec.frozen_values.keys()),
        provenance=("llm_adapters.benchmark_harness", spec.research_spec_version),
    )


# --- adapter resolution ---------------------------------------------------


def _resolve_adapter(model_identity: str, config: LLMPlatformConfig):
    provider, _model = model_identity.split(":", 1)
    if provider == "openai":
        return OpenAIAdapter(config)
    if provider == "anthropic":
        return AnthropicAdapter(config)
    if provider == "gemini":
        return GeminiAdapter(config)
    if provider == "deepseek":
        return DeepSeekAdapter(config)
    raise ValueError(f"Unknown provider: {provider}")


# --- benchmark run record -------------------------------------------------


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    """One (case, model) private record. NEVER serialized to clients."""

    research_case_id: str
    research_spec_version: str
    provider: str
    model: str
    tier: str
    routing_decision: RoutingDecision
    status: EvaluationStatus
    error_category: ErrorCategory
    error_detail: str | None
    latency_ms: int
    usage: TokenUsage
    pricing: ModelPricing
    estimated_cost_usd: float
    pricing_unknown: bool
    quality: QualityEvaluation
    quality_score: float
    evaluator: EvaluatorVerdict
    gate: GateVerdict
    was_escalated: bool
    raw_narrative: str = ""

    def public_summary(self) -> dict[str, Any]:
        """Return a PRINTER-FRIENDLY dict (not for API). No private data leaks.

        Private fields: provider, model, latency_ms, tokens, raw_narrative,
        internal_prompt, chain_of-thought, routing_reasons, etc. None of
        those may appear here. The assert at the report builder level
        enforces this.
        """
        return {
            "case": self.research_case_id,
            "tier": self.tier,
            "status": self.status.value,
            "error": self.error_category.value if self.error_category is not ErrorCategory.NONE else None,
            "quality_score": round(self.quality_score, 2),
            "cost_usd": round(self.estimated_cost_usd, 6) if not self.pricing_unknown else None,
            "gate": self.gate.outcome.value,
            "escalated": self.was_escalated,
        }


# --- harness --------------------------------------------------------------


def _estimate_tokens(prompt_parts: Sequence[str], narrative: str) -> TokenUsage:
    """Approximate token count: 1 token ≈ 4 chars (rough but consistent)."""
    in_chars = sum(len(p) for p in prompt_parts)
    out_chars = len(narrative)
    return TokenUsage(
        input_tokens=max(1, in_chars // 4),
        output_tokens=max(1, out_chars // 4) if narrative else 0,
    )


def run_one_case_one_model(
    case: BenchmarkCase,
    model_identity: str,
    config: LLMPlatformConfig,
    tier_registry: Mapping[ModelTier, TierConfig] | None = None,
) -> tuple[BenchmarkRun | None, BenchmarkRun | None]:
    """Run a case at COST_EFFICIENT first; escalate to PREMIUM on gate failure.

    Returns ``(cost_efficient_run, premium_run_or_None)``. Exactly one of
    the two carries ``status=SUCCESS`` if the gate accepted at any tier.
    """
    catalog_info = get_model_info(model_identity)
    routing = decide_routing(case.signals)
    request = _build_request(case.spec)
    adapter = _resolve_adapter(model_identity, config)

    # --- tier 1 ---
    start = time.perf_counter()
    result = adapter.invoke(request)
    latency_ms = int((time.perf_counter() - start) * 1000)
    narrative = result.narrative_text or ""
    usage = _estimate_tokens(request.prompt_parts, narrative)
    cost = calculate_estimated_cost(usage, catalog_info.pricing)
    pricing_unknown = (
        catalog_info.pricing.input_usd_per_1m <= 0
        and catalog_info.pricing.output_usd_per_1m <= 0
    )
    quality_verdict = evaluate_narrative(narrative, dict(case.spec.frozen_values))
    quality_score = calculate_quality_score(quality_verdict.quality)
    ev_result = EvaluationResult(
        model=catalog_info,
        research_case_id=case.spec.research_case_id,
        status=EvaluationStatus.SUCCESS
        if result.status is LanguageModelStatus.COMPLETE
        else EvaluationStatus.FAILED,
        latency_ms=latency_ms,
        usage=usage,
        estimated_cost_usd=cost,
        structured_output_valid=False,  # benchmark uses free text
        quality=quality_verdict.quality,
        error_category=ErrorCategory.NONE
        if result.status is LanguageModelStatus.COMPLETE
        else _classify_error(result),
        error_detail=result.limitations[0] if result.limitations else None,
    )
    gate = evaluate_gate(ev_result, routing, tier_registry)
    run_t1 = BenchmarkRun(
        research_case_id=case.spec.research_case_id,
        research_spec_version=case.spec.research_spec_version,
        provider=catalog_info.provider,
        model=catalog_info.model,
        tier=routing.routing_tier.value,
        routing_decision=routing,
        status=ev_result.status,
        error_category=ev_result.error_category,
        error_detail=ev_result.error_detail,
        latency_ms=latency_ms,
        usage=usage,
        pricing=catalog_info.pricing,
        estimated_cost_usd=cost,
        pricing_unknown=pricing_unknown,
        quality=quality_verdict.quality,
        quality_score=quality_score,
        evaluator=quality_verdict,
        gate=gate,
        was_escalated=False,
        raw_narrative=narrative,
    )

    if gate.outcome is GateOutcome.ACCEPTED:
        return run_t1, None

    if gate.outcome is GateOutcome.FAILED_CLOSED:
        return run_t1, None

    # --- escalate to premium on the same model family? No — premium is a
    # DIFFERENT model per STEP 3B tiers. Resolve the premium-tier model
    # and run it.
    premium_cfg = get_tier_config(ModelTier.PREMIUM, tier_registry)
    if premium_cfg.model_identity == model_identity:
        # Same model — no real escalation possible.
        return run_t1, None
    premium_info = get_model_info(premium_cfg.model_identity)
    premium_adapter = _resolve_adapter(premium_cfg.model_identity, config)
    premium_routing = RoutingDecision(
        routing_tier=ModelTier.PREMIUM,
        routing_reasons=routing.routing_reasons,
        confidence_requirement=0.8,
    )

    start = time.perf_counter()
    p_result = premium_adapter.invoke(request)
    p_latency_ms = int((time.perf_counter() - start) * 1000)
    p_narrative = p_result.narrative_text or ""
    p_usage = _estimate_tokens(request.prompt_parts, p_narrative)
    p_cost = calculate_estimated_cost(p_usage, premium_info.pricing)
    p_pricing_unknown = (
        premium_info.pricing.input_usd_per_1m <= 0
        and premium_info.pricing.output_usd_per_1m <= 0
    )
    p_quality = evaluate_narrative(p_narrative, dict(case.spec.frozen_values))
    p_quality_score = calculate_quality_score(p_quality.quality)
    p_ev = EvaluationResult(
        model=premium_info,
        research_case_id=case.spec.research_case_id,
        status=EvaluationStatus.SUCCESS
        if p_result.status is LanguageModelStatus.COMPLETE
        else EvaluationStatus.FAILED,
        latency_ms=p_latency_ms,
        usage=p_usage,
        estimated_cost_usd=p_cost,
        structured_output_valid=False,
        quality=p_quality.quality,
        error_category=ErrorCategory.NONE
        if p_result.status is LanguageModelStatus.COMPLETE
        else _classify_error(p_result),
        error_detail=p_result.limitations[0] if p_result.limitations else None,
    )
    p_gate = evaluate_gate(p_ev, premium_routing, tier_registry)
    run_t2 = BenchmarkRun(
        research_case_id=case.spec.research_case_id,
        research_spec_version=case.spec.research_spec_version,
        provider=premium_info.provider,
        model=premium_info.model,
        tier=ModelTier.PREMIUM.value,
        routing_decision=premium_routing,
        status=p_ev.status,
        error_category=p_ev.error_category,
        error_detail=p_ev.error_detail,
        latency_ms=p_latency_ms,
        usage=p_usage,
        pricing=premium_info.pricing,
        estimated_cost_usd=p_cost,
        pricing_unknown=p_pricing_unknown,
        quality=p_quality.quality,
        quality_score=p_quality_score,
        evaluator=p_quality,
        gate=p_gate,
        was_escalated=True,
        raw_narrative=p_narrative,
    )
    return run_t1, run_t2


def _classify_error(result) -> ErrorCategory:
    if result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE:
        return ErrorCategory.PROVIDER_UNAVAILABLE
    text = " ".join(result.limitations or ()).lower()
    if "timeout" in text or "http_error" in text:
        return ErrorCategory.TIMEOUT
    if "malformed" in text or "empty" in text:
        return ErrorCategory.MALFORMED_OUTPUT
    return ErrorCategory.UNKNOWN


def run_benchmark(
    config: LLMPlatformConfig,
    cases: Sequence[BenchmarkCase] = BENCHMARK_CASES,
    models: Sequence[str] = BENCHMARK_MODELS,
    tier_registry: Mapping[ModelTier, TierConfig] | None = None,
) -> list[BenchmarkRun]:
    """Run the full benchmark. Returns private BenchmarkRun records."""
    runs: list[BenchmarkRun] = []
    for case in cases:
        for model_identity in models:
            t1, t2 = run_one_case_one_model(
                case, model_identity, config, tier_registry
            )
            if t1 is not None:
                runs.append(t1)
            if t2 is not None:
                runs.append(t2)
    return runs


def build_report(runs: Sequence[BenchmarkRun]) -> dict[str, Any]:
    """Compose the offline benchmark report (private, never sent to clients).

    Cost efficiency for each accepted run is computed against the
    accepted-only cost range (cheapest accepted = 100, most expensive = 0).
    Overall score = 0.5*quality + 0.5*cost_efficiency.
    """
    accepted: list[BenchmarkRun] = [r for r in runs if r.gate.outcome is GateOutcome.ACCEPTED]
    failed: list[BenchmarkRun] = [r for r in runs if r.gate.outcome is GateOutcome.FAILED_CLOSED]
    escalated: list[BenchmarkRun] = [r for r in runs if r.was_escalated]
    accepted_costs = [r.estimated_cost_usd for r in accepted if not r.pricing_unknown]

    overall_by_run: dict[int, float] = {}
    cost_score_by_run: dict[int, float] = {}
    if accepted_costs:
        cmin, cmax = min(accepted_costs), max(accepted_costs)
        for r in accepted:
            if r.pricing_unknown:
                cost_score = 0.0
            elif cmax == cmin:
                cost_score = 100.0
            else:
                cost_score = max(
                    0.0,
                    min(
                        100.0,
                        100.0 * (1.0 - (r.estimated_cost_usd - cmin) / (cmax - cmin)),
                    ),
                )
            cost_score_by_run[id(r)] = cost_score
            overall_by_run[id(r)] = round(0.5 * r.quality_score + 0.5 * cost_score, 2)
        cost_min_usd: float | None = round(cmin, 6)
        cost_max_usd: float | None = round(cmax, 6)
    else:
        cost_min_usd = None
        cost_max_usd = None

    rows: list[dict[str, Any]] = []
    for r in runs:
        summary = r.public_summary()
        summary["cost_score"] = round(cost_score_by_run.get(id(r), 0.0), 2)
        summary["overall_score"] = overall_by_run.get(id(r), 0.0)
        # Defence-in-depth: confirm the public summary never carries
        # private fields. Raises immediately if anyone adds one.
        assert_no_private_leakage(summary)
        rows.append(summary)

    return {
        "summary": {
            "total_runs": len(runs),
            "accepted": len(accepted),
            "failed_closed": len(failed),
            "escalated": len(escalated),
            "cost_min_usd": cost_min_usd,
            "cost_max_usd": cost_max_usd,
        },
        "rows": rows,
    }


__all__ = [
    "BENCHMARK_CASES",
    "BENCHMARK_MODELS",
    "BenchmarkCase",
    "BenchmarkRun",
    "ResearchSpec",
    "build_report",
    "run_benchmark",
    "run_one_case_one_model",
]
