"""Tests for adaptive model benchmark + routing + privacy boundary."""

from __future__ import annotations

import math

import pytest

from llm_adapters.benchmark import (
    build_benchmark_table,
    run_case_against_model,
)
from llm_adapters.evaluation import (
    ErrorCategory,
    EvaluationResult,
    EvaluationStatus,
    QualityEvaluation,
    TokenUsage,
)
from llm_adapters.model_catalog import (
    DEFAULT_CATALOG,
    ModelCapabilities,
    ModelInfo,
    ModelLimits,
    ModelPricing,
    get_model_info,
)
from llm_adapters.model_tiers import (
    DEFAULT_TIERS,
    ModelTier,
    TierConfig,
)
from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)
from llm_adapters.quality_gate import (
    GateOutcome,
    evaluate_gate,
    run_with_escalation,
)
from llm_adapters.routing import (
    ComplexitySignal,
    decide_routing,
)


# ---- helpers --------------------------------------------------------------


def _result(
    model_identity: str,
    *,
    quality: QualityEvaluation | None = None,
    cost: float | None = 0.01,
    status: EvaluationStatus = EvaluationStatus.SUCCESS,
    error: ErrorCategory = ErrorCategory.NONE,
) -> EvaluationResult:
    info = get_model_info(model_identity)
    q = quality if quality is not None else QualityEvaluation(factual_accuracy=0.9)
    if cost is None:
        # Mimic unknown-pricing -> NaN
        cost = float("nan")
    return EvaluationResult(
        model=info,
        research_case_id="case-1",
        status=status,
        latency_ms=100,
        usage=TokenUsage(1000, 500),
        estimated_cost_usd=cost if not math.isnan(cost) else 0.0,
        structured_output_valid=True,
        quality=q,
        error_category=error,
    )


# ---- routing: simple vs complex -------------------------------------------


def test_simple_case_routes_to_cost_efficient() -> None:
    decision = decide_routing([ComplexitySignal.MISSING_DATA])
    assert decision.routing_tier is ModelTier.COST_EFFICIENT
    assert decision.routing_reasons == ()
    assert decision.confidence_requirement == 0.6


def test_complex_case_routes_to_premium() -> None:
    decision = decide_routing(
        [ComplexitySignal.CONFLICTING_EVIDENCE, ComplexitySignal.MISSING_DATA]
    )
    assert decision.routing_tier is ModelTier.PREMIUM
    assert "conflicting_evidence" in decision.routing_reasons
    # MISSING_DATA is not a premium trigger, so not in reasons.
    assert "missing_data" not in decision.routing_reasons
    assert decision.confidence_requirement == 0.8


def test_all_premium_triggers_escalate() -> None:
    for sig in (
        ComplexitySignal.CONFLICTING_EVIDENCE,
        ComplexitySignal.VALUATION_DISAGREEMENT,
        ComplexitySignal.UNUSUAL_FINANCIAL_STRUCTURE,
        ComplexitySignal.MATERIAL_RISK,
        ComplexitySignal.DIFFICULT_BUFFETT_ANALYSIS,
        ComplexitySignal.HIGH_IMPACT_DECISION,
    ):
        assert decide_routing([sig]).routing_tier is ModelTier.PREMIUM


def test_routing_is_deterministic_and_deduped() -> None:
    d1 = decide_routing(
        [ComplexitySignal.CONFLICTING_EVIDENCE, ComplexitySignal.CONFLICTING_EVIDENCE]
    )
    d2 = decide_routing([ComplexitySignal.CONFLICTING_EVIDENCE])
    assert d1.routing_reasons == d2.routing_reasons == ("conflicting_evidence",)


# ---- quality gate ---------------------------------------------------------


def test_high_quality_at_cost_efficient_passes() -> None:
    decision = decide_routing([])
    result = _result(
        "deepseek:deepseek-chat",
        quality=QualityEvaluation(factual_accuracy=0.9, valuation_reasoning=0.8),
    )
    verdict = evaluate_gate(result, decision)
    assert verdict.outcome is GateOutcome.ACCEPTED
    assert verdict.requires_escalation is False


def test_low_quality_at_cost_efficient_escalates() -> None:
    decision = decide_routing([])
    result = _result(
        "deepseek:deepseek-chat",
        quality=QualityEvaluation(factual_accuracy=0.3),
    )
    verdict = evaluate_gate(result, decision)
    assert verdict.outcome is GateOutcome.ESCALATED
    assert verdict.requires_escalation is True


def test_validation_failure_escalates() -> None:
    decision = decide_routing([])
    result = _result(
        "deepseek:deepseek-chat",
        quality=QualityEvaluation(factual_accuracy=0.9),
        error=ErrorCategory.SCHEMA_FAILURE,
    )
    verdict = evaluate_gate(result, decision)
    assert verdict.outcome is GateOutcome.ESCALATED


def test_premium_failure_fails_closed() -> None:
    decision = decide_routing([ComplexitySignal.CONFLICTING_EVIDENCE])
    result = _result(
        "anthropic:claude-3-5-sonnet-20241022",
        quality=QualityEvaluation(factual_accuracy=0.3),
    )
    verdict = evaluate_gate(result, decision)
    assert verdict.outcome is GateOutcome.FAILED_CLOSED


def test_premium_pass_accepted() -> None:
    decision = decide_routing([ComplexitySignal.CONFLICTING_EVIDENCE])
    result = _result(
        "anthropic:claude-3-5-sonnet-20241022",
        quality=QualityEvaluation(
            factual_accuracy=0.95, valuation_reasoning=0.9, evidence_correctness=0.9
        ),
    )
    verdict = evaluate_gate(result, decision)
    assert verdict.outcome is GateOutcome.ACCEPTED


def test_minimum_quality_gate_overrides_cost() -> None:
    # Below floor -> benchmark score forced to 0 even if cheap.
    decision = decide_routing([])
    result = _result(
        "deepseek:deepseek-chat",
        quality=QualityEvaluation(factual_accuracy=0.3),
    )
    row = run_case_against_model(
        research_case_id="case-q",
        research_spec_version="v1",
        model_identity="deepseek:deepseek-chat",
        signals=[ComplexitySignal.MISSING_DATA],
        run_model=lambda _m, _t: result,
    )
    table = build_benchmark_table([row])
    assert table[0].meets_floor is False
    assert table[0].benchmark_score == 0.0


# ---- escalation: end-to-end ----------------------------------------------


def test_run_with_escalation_cheap_pass() -> None:
    decision = decide_routing([])
    result = _result(
        "deepseek:deepseek-chat",
        quality=QualityEvaluation(factual_accuracy=0.9),
    )
    verdict, accepted = run_with_escalation(
        decision=decision, run_at_tier=lambda _t: result
    )
    assert verdict.outcome is GateOutcome.ACCEPTED
    assert accepted is not None


def test_run_with_escalation_premium_on_cheap_failure() -> None:
    decision = decide_routing([])

    def run_at_tier(tier: ModelTier) -> EvaluationResult:
        if tier is ModelTier.COST_EFFICIENT:
            return _result(
                "deepseek:deepseek-chat",
                quality=QualityEvaluation(factual_accuracy=0.2),
            )
        return _result(
            "anthropic:claude-3-5-sonnet-20241022",
            quality=QualityEvaluation(
                factual_accuracy=0.95, valuation_reasoning=0.9
            ),
        )

    verdict, accepted = run_with_escalation(
        decision=decision, run_at_tier=run_at_tier
    )
    assert verdict.outcome is GateOutcome.ACCEPTED
    assert accepted is not None
    assert verdict.tier is ModelTier.PREMIUM


def test_run_with_escalation_fail_closed() -> None:
    decision = decide_routing([])

    def run_at_tier(tier: ModelTier) -> EvaluationResult:
        # Both tiers fail
        return _result(
            "deepseek:deepseek-chat",
            quality=QualityEvaluation(factual_accuracy=0.1),
        )

    verdict, accepted = run_with_escalation(
        decision=decision, run_at_tier=run_at_tier
    )
    assert verdict.outcome is GateOutcome.FAILED_CLOSED
    assert accepted is None  # NO FABRICATION


# ---- benchmark scoring ----------------------------------------------------


def test_benchmark_50_50_composite() -> None:
    rows = [
        run_case_against_model(
            research_case_id="c1",
            research_spec_version="v1",
            model_identity="gemini:gemini-1.5-flash",
            signals=[],
            run_model=lambda _m, _t: _result(
                "gemini:gemini-1.5-flash",
                quality=QualityEvaluation(factual_accuracy=0.9),
                cost=0.001,
            ),
        ),
        run_case_against_model(
            research_case_id="c1",
            research_spec_version="v1",
            model_identity="anthropic:claude-3-5-sonnet-20241022",
            signals=[],
            run_model=lambda _m, _t: _result(
                "anthropic:claude-3-5-sonnet-20241022",
                quality=QualityEvaluation(factual_accuracy=0.9),
                cost=0.10,
            ),
        ),
    ]
    table = build_benchmark_table(rows)
    assert len(table) == 2
    for r in table:
        assert 0.0 <= r.benchmark_score <= 100.0
    # Cheaper row should rank first when quality is equal
    assert table[0].model.identity == "gemini:gemini-1.5-flash"


def test_unknown_pricing_not_treated_as_zero() -> None:
    # Custom catalog with one model missing pricing
    custom_info = ModelInfo(
        provider="deepseek",
        model="deepseek-unknown",
        capabilities=ModelCapabilities(),
        limits=ModelLimits(context_window_tokens=8000, max_output_tokens=2000),
        pricing=ModelPricing(input_usd_per_1m=0.0, output_usd_per_1m=0.0),
    )
    catalog = {**DEFAULT_CATALOG, "deepseek:deepseek-unknown": custom_info}

    def run_model(mid: str, _tier: ModelTier) -> EvaluationResult:
        info = get_model_info(mid, catalog)
        return EvaluationResult(
            model=info,
            research_case_id="c1",
            status=EvaluationStatus.SUCCESS,
            latency_ms=100,
            usage=TokenUsage(1000, 500),
            estimated_cost_usd=0.01,
            structured_output_valid=True,
            quality=QualityEvaluation(factual_accuracy=0.9),
        )

    row = run_case_against_model(
        research_case_id="c1",
        research_spec_version="v1",
        model_identity="deepseek:deepseek-unknown",
        signals=[],
        run_model=run_model,
        catalog=catalog,
    )
    assert row.pricing_missing is True
    table = build_benchmark_table([row])
    assert table[0].benchmark_score == 0.0  # can't win with unknown pricing


# ---- privacy boundary -----------------------------------------------------


def test_public_pack_has_no_private_fields() -> None:
    pack = PublicDecisionPack(
        recommendation="Buy",
        valuation="180",
        analysis="DCF suggests upside.",
        risks=("FX", "Concentration"),
        evidence_citations=("section:r1", "section:r2"),
        confidence=0.85,
        limitations=("LLM enrichment only",),
    )
    d = pack.to_dict()
    assert_no_private_leakage(d)
    # Public fields are exactly the declared ones
    assert set(d.keys()) == {
        "recommendation",
        "valuation",
        "analysis",
        "risks",
        "evidence_citations",
        "confidence",
        "limitations",
        "schema_version",
    }


def test_private_result_exposes_only_public_to_client() -> None:
    pack = PublicDecisionPack(
        recommendation="Hold",
        valuation=None,
        analysis="Mixed signals.",
        risks=(),
        evidence_citations=(),
        confidence=0.5,
        limitations=("deterministic-only",),
    )
    private = PrivateInternalResult(
        public=pack,
        provider="openai",
        model="gpt-4o-mini",
        routing_tier="premium",
        routing_reasons=("conflicting_evidence",),
        confidence_requirement=0.8,
        estimated_cost_usd=0.0123,
        input_tokens=1000,
        output_tokens=400,
        latency_ms=2400,
        model_score=82.0,
        routing_criteria=("quality<floor",),
        internal_prompt="PRIVATE — never expose",
        raw_ai_response="PRIVATE — never expose",
        chain_of_thought="PRIVATE — never expose",
    )
    # Client call: must return only public.
    client_view = private.to_public().to_dict()
    assert_no_private_leakage(client_view)
    assert "openai" not in client_view
    assert "PRIVATE" not in str(client_view)


def test_assert_no_private_leakage_catches_violations() -> None:
    bad = {"recommendation": "Buy", "provider": "openai"}
    with pytest.raises(ValueError):
        assert_no_private_leakage(bad)
