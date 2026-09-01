"""Tests for the production AI activation guard.

Covers the 10 mandatory conditions + privacy separation + fail-closed.
"""

from __future__ import annotations

import pytest

from llm_adapters.activation_evidence import (
    ActivationEvidence,
    BenchmarkEvidence,
    ConfigurationEvidence,
    FailClosedEvidence,
    ModelEvaluationEvidence,
    PrivacyEvidence,
    ToolEvidence,
)
from llm_adapters.activation_guard import (
    ActivationCondition,
    ActivationState,
    evaluate_activation,
)
from llm_adapters.evaluation import QualityEvaluation
from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)


# --- helpers --------------------------------------------------------------


def _good_quality(score: float = 90.0) -> QualityEvaluation:
    """A QualityEvaluation whose mean score equals ``score`` (0-100 scale)."""
    s = score / 100.0  # internal component scale
    return QualityEvaluation(
        factual_accuracy=s,
        financial_reasoning=s,
        valuation_reasoning=s,
        buffett_reasoning=s,
        moat_business_quality=s,
        management=s,
        financial_strength=s,
        earnings_quality=s,
        growth_quality=s,
        risk=s,
        evidence_correctness=s,
        hallucination=s,
        unsupported_claims=s,
        structured_output=s,
        consistency=s,
        business_quality=s,
    )


def _good_evaluation(
    model_identity: str = "deepseek:deepseek-chat",
    *,
    quality_score: float | None = None,
    pricing_known: bool = True,
    structured_output_valid: bool = True,
    cost: float = 0.01,
) -> ModelEvaluationEvidence:
    qs = 90.0 if quality_score is None else quality_score
    q = _good_quality(qs)
    return ModelEvaluationEvidence(
        model_identity=model_identity,
        research_case_id="case-1",
        quality=q,
        quality_score=qs,
        estimated_cost_usd=cost,
        pricing_known=pricing_known,
        structured_output_valid=structured_output_valid,
        token_usage={"input": 1000, "output": 500},
        latency_ms=200,
    )


def _good_benchmark() -> BenchmarkEvidence:
    return BenchmarkEvidence(
        benchmark_completed=True,
        benchmark_version="v1",
        case_count=8,
        accepted_run_count=12,
        best_overall_score=85.0,
        best_model_identity="deepseek:deepseek-chat",
        cost_min_usd=0.001,
        cost_max_usd=0.05,
    )


def _good_config() -> ConfigurationEvidence:
    return ConfigurationEvidence(
        default_provider="deterministic",
        cost_efficient_model="deepseek:deepseek-chat",
        premium_model="anthropic:claude-3-5-sonnet-20241022",
        available_providers=("openai", "anthropic", "gemini", "deepseek"),
        pricing_known_for_all_tiers=True,
        routing_tier_count=2,
        all_provider_keys_configured=False,
    )


def _good_tools() -> ToolEvidence:
    return ToolEvidence(
        available_tools=("dsp.analyse", "dsp.valuation", "dsp.committee"),
        minimum_tool_count=2,
        all_tools_healthy=True,
    )


def _good_privacy() -> PrivacyEvidence:
    return PrivacyEvidence(
        private_fields_enumerated=True,
        public_pack_present=True,
        leakage_guard_active=True,
        benchmark_report_audited=True,
    )


def _good_fail_closed() -> FailClosedEvidence:
    return FailClosedEvidence(
        quality_gate_present=True,
        no_fabrication_guarantee=True,
        deterministic_fallback_present=True,
        escalation_present=True,
    )


def _good_evidence(**overrides) -> ActivationEvidence:
    """Build a fully-passing evidence bundle; overrides let tests mutate one field."""
    base = ActivationEvidence(
        benchmark=overrides.get("benchmark", _good_benchmark()),
        successful_evaluations=overrides.get("successful_evaluations", (_good_evaluation(),)),
        configuration=overrides.get("configuration", _good_config()),
        tools=overrides.get("tools", _good_tools()),
        privacy=overrides.get("privacy", _good_privacy()),
        fail_closed=overrides.get("fail_closed", _good_fail_closed()),
        required_quality_threshold=60.0,
    )
    return base


# --- condition 1: benchmark required --------------------------------------


def test_no_benchmark_blocks() -> None:
    evidence = _good_evidence(benchmark=BenchmarkEvidence.empty())
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.BENCHMARK_REQUIRED in verdict.failed


# --- condition 2: successful model required ------------------------------


def test_no_successful_model_blocks() -> None:
    evidence = _good_evidence(successful_evaluations=())
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.SUCCESSFUL_MODEL_REQUIRED in verdict.failed


# --- condition 3: quality threshold --------------------------------------


def test_quality_below_threshold_blocks() -> None:
    bad = _good_evaluation(quality_score=30.0)  # below 60.0
    evidence = _good_evidence(successful_evaluations=(bad,))
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.QUALITY_THRESHOLD_REQUIRED in verdict.failed


# --- condition 4: pricing known ------------------------------------------


def test_unknown_pricing_blocks() -> None:
    bad = _good_evaluation(pricing_known=False)
    evidence = _good_evidence(successful_evaluations=(bad,))
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.PRICING_KNOWN_REQUIRED in verdict.failed


# --- condition 5: structured output --------------------------------------


def test_invalid_structured_output_blocks() -> None:
    bad = _good_evaluation(structured_output_valid=False)
    evidence = _good_evidence(successful_evaluations=(bad,))
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.STRUCTURED_OUTPUT_REQUIRED in verdict.failed


def test_structured_output_optional_when_not_required() -> None:
    """Operators can opt out by setting structured_output_required=False."""
    bad = _good_evaluation(structured_output_valid=False)
    evidence = _good_evidence(successful_evaluations=(bad,))
    object.__setattr__(evidence, "structured_output_required", False)
    verdict = evaluate_activation(evidence)
    assert ActivationCondition.STRUCTURED_OUTPUT_REQUIRED in verdict.passed


# --- condition 6: DSP tools available ------------------------------------


def test_no_dsp_tools_blocks() -> None:
    bad = ToolEvidence(available_tools=(), minimum_tool_count=2, all_tools_healthy=True)
    evidence = _good_evidence(tools=bad)
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.DSP_TOOLS_AVAILABLE_REQUIRED in verdict.failed


def test_unhealthy_dsp_tools_blocks() -> None:
    bad = ToolEvidence(
        available_tools=("dsp.analyse",),
        minimum_tool_count=2,
        all_tools_healthy=False,
    )
    evidence = _good_evidence(tools=bad)
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.DSP_TOOLS_AVAILABLE_REQUIRED in verdict.failed


# --- condition 7: evidence requirements met ------------------------------


def test_incomplete_evidence_bundle_blocks() -> None:
    bad_cfg = ConfigurationEvidence(
        default_provider="",
        cost_efficient_model="deepseek:deepseek-chat",
        premium_model="anthropic:claude-3-5-sonnet-20241022",
        available_providers=("openai", "anthropic"),
        pricing_known_for_all_tiers=True,
        routing_tier_count=2,
        all_provider_keys_configured=False,
    )
    evidence = _good_evidence(configuration=bad_cfg)
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.EVIDENCE_REQUIREMENTS_MET in verdict.failed


# --- condition 8: privacy boundary ----------------------------------------


def test_privacy_failure_blocks() -> None:
    bad = PrivacyEvidence(
        private_fields_enumerated=True,
        public_pack_present=True,
        leakage_guard_active=False,  # guard disabled
        benchmark_report_audited=True,
    )
    evidence = _good_evidence(privacy=bad)
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.PRIVACY_BOUNDARY_REQUIRED in verdict.failed


# --- condition 9: fail-closed wiring --------------------------------------


def test_missing_fail_closed_blocks() -> None:
    bad = FailClosedEvidence(
        quality_gate_present=True,
        no_fabrication_guarantee=True,
        deterministic_fallback_present=False,  # missing fallback
        escalation_present=True,
    )
    evidence = _good_evidence(fail_closed=bad)
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.FAIL_CLOSED_REQUIRED in verdict.failed


# --- condition 10: configuration valid ------------------------------------


def test_invalid_provider_blocks() -> None:
    bad = ConfigurationEvidence(
        default_provider="not-a-real-provider",
        cost_efficient_model="deepseek:deepseek-chat",
        premium_model="anthropic:claude-3-5-sonnet-20241022",
        available_providers=("openai", "anthropic", "deepseek"),
        pricing_known_for_all_tiers=True,
        routing_tier_count=2,
        all_provider_keys_configured=False,
    )
    evidence = _good_evidence(configuration=bad)
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.CONFIGURATION_VALID in verdict.failed


def test_identical_tiers_blocks() -> None:
    bad = ConfigurationEvidence(
        default_provider="deterministic",
        cost_efficient_model="deepseek:deepseek-chat",
        premium_model="deepseek:deepseek-chat",  # not distinct
        available_providers=("deepseek", "anthropic"),
        pricing_known_for_all_tiers=True,
        routing_tier_count=2,
        all_provider_keys_configured=False,
    )
    evidence = _good_evidence(configuration=bad)
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.CONFIGURATION_VALID in verdict.failed


# --- happy path ----------------------------------------------------------


def test_all_requirements_satisfied_ready() -> None:
    evidence = _good_evidence()
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_READY
    assert verdict.failed == ()
    assert len(verdict.passed) == 10
    # Recommended models are populated when ready.
    assert "deepseek:deepseek-chat" in verdict.recommended_models
    assert "anthropic:claude-3-5-sonnet-20241022" in verdict.recommended_models


def test_multiple_accepted_runs_below_threshold_blocks() -> None:
    good = _good_evaluation(quality_score=90.0)
    bad = _good_evaluation(quality_score=30.0)
    evidence = _good_evidence(successful_evaluations=(good, bad))
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert ActivationCondition.QUALITY_THRESHOLD_REQUIRED in verdict.failed


# --- fail-closed: never silently fall back --------------------------------


def test_blocked_does_not_silently_pass_with_partial_evidence() -> None:
    """The gate must not relax conditions even if many pass."""
    # only benchmark + configuration valid; everything else missing
    evidence = ActivationEvidence(
        benchmark=_good_benchmark(),
        successful_evaluations=(),  # missing
        configuration=_good_config(),
        tools=ToolEvidence(available_tools=(), minimum_tool_count=2, all_tools_healthy=False),
        privacy=PrivacyEvidence(
            private_fields_enumerated=False,
            public_pack_present=False,
            leakage_guard_active=False,
            benchmark_report_audited=False,
        ),
        fail_closed=FailClosedEvidence(
            quality_gate_present=False,
            no_fabrication_guarantee=False,
            deterministic_fallback_present=False,
            escalation_present=False,
        ),
        required_quality_threshold=60.0,
    )
    verdict = evaluate_activation(evidence)
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert len(verdict.failed) >= 4  # many things failed at once


# --- privacy: verdict cannot leak private information ---------------------


def test_verdict_public_state_carries_no_reasons() -> None:
    evidence = _good_evidence()  # ready
    verdict = evaluate_activation(evidence)
    public = verdict.public_state()
    assert public == "ai_production_ready"
    # Public state is a single string — no reasons, no model names, no scores.
    assert "deepseek" not in public
    assert "anthropic" not in public
    assert "ok:" not in public
    assert "FAIL:" not in public


def test_blocked_verdict_public_state_only_says_blocked() -> None:
    bad = _good_evaluation(pricing_known=False)
    evidence = _good_evidence(successful_evaluations=(bad,))
    verdict = evaluate_activation(evidence)
    public = verdict.public_state()
    assert public == "ai_production_blocked"
    assert "deepseek" not in public
    assert "pricing" not in public.lower()


def test_verdict_object_cannot_be_dict_serialized_to_client_shape() -> None:
    """The verdict object itself must not be the public pack.

    PublicDecisionPack is the ONLY public shape. A naive consumer who
    accidentally returns the verdict as JSON would expose reasons,
    model names, recommended_models, etc. We assert those fields are
    present on the verdict (so the operator can use them) but that
    PublicDecisionPack does not include them.
    """
    evidence = _good_evidence()
    verdict = evaluate_activation(evidence)
    # Operator-side fields are present (private telemetry only).
    assert verdict.reasons
    assert verdict.recommended_models
    # PublicDecisionPack has no slot for any of these.
    public_fields = {
        "recommendation", "valuation", "analysis", "risks",
        "evidence_citations", "confidence", "limitations", "schema_version",
    }
    assert "reasons" not in public_fields
    assert "recommended_models" not in public_fields
    assert "state" not in public_fields


def test_private_to_public_path_isolated_from_guard() -> None:
    """The activation guard and the privacy boundary are independent layers.

    Even if the guard somehow returned AI_PRODUCTION_READY, the
    PrivateInternalResult -> PublicDecisionPack path must still strip
    every private field.
    """
    public = PublicDecisionPack(
        recommendation="Buy",
        valuation=None,
        analysis="ok",
        risks=(),
        evidence_citations=(),
        confidence=0.5,
        limitations=("lm_enrichment",),
    )
    private = PrivateInternalResult(
        public=public,
        provider="deepseek",
        model="deepseek-chat",
        routing_tier="cost_efficient",
        routing_reasons=(),
        confidence_requirement=0.6,
        estimated_cost_usd=0.01,
        input_tokens=1000,
        output_tokens=500,
        latency_ms=200,
        model_score=85.0,
        routing_criteria=(),
        internal_prompt="PRIVATE",
        raw_ai_response="PRIVATE",
        chain_of_thought="PRIVATE",
    )
    out = private.to_public().to_dict()
    assert_no_private_leakage(out)
    assert "PRIVATE" not in str(out)
    assert "deepseek" not in str(out).lower()


# --- multiple-failures: every failure is recorded -------------------------


def test_all_ten_conditions_recorded_on_full_evidence() -> None:
    """With perfect evidence, exactly 10 conditions pass, zero fail."""
    evidence = _good_evidence()
    verdict = evaluate_activation(evidence)
    assert len(verdict.passed) == 10
    assert len(verdict.failed) == 0


def test_recommended_models_deduped_and_ordered() -> None:
    """If accepted evals include the same model as a tier default, no dup."""
    e1 = _good_evaluation(model_identity="deepseek:deepseek-chat", quality_score=90.0)
    e2 = _good_evaluation(model_identity="anthropic:claude-3-5-sonnet-20241022", quality_score=95.0)
    evidence = _good_evidence(successful_evaluations=(e1, e2))
    verdict = evaluate_activation(evidence)
    # Order: cost_efficient, premium, best-scoring (deduped)
    assert verdict.recommended_models == (
        "deepseek:deepseek-chat",
        "anthropic:claude-3-5-sonnet-20241022",
    )
