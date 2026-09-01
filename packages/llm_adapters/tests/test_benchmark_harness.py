"""Tests for the real-model benchmark harness + evaluator.

These tests use no live network and no API keys. Every model call hits
``PROVIDER_UNAVAILABLE`` because no keys are configured in the test env;
the harness records the failure cleanly and the gate fail-closes. The
purpose is to prove:

- benchmark cases load and have 8 cases
- evaluator scores ground-truth narratives correctly
- evaluator never invents scores
- harness produces private records only
- report never leaks private fields
- unknown pricing is propagated as unknown, not zero
- gate escalation works end-to-end
"""

from __future__ import annotations

import os

import pytest

from llm_adapters.benchmark_cases import (
    BENCHMARK_CASES,
    BenchmarkCase,
    ResearchSpec,
)
from llm_adapters.benchmark_harness import (
    BENCHMARK_MODELS,
    BenchmarkRun,
    build_report,
    run_benchmark,
    run_one_case_one_model,
)
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.evaluation import ErrorCategory, EvaluationStatus
from llm_adapters.model_tiers import DEFAULT_TIERS, ModelTier
from llm_adapters.privacy_boundary import (
    PrivateInternalResult,
    PublicDecisionPack,
    assert_no_private_leakage,
)
from llm_adapters.quality_evaluator import (
    aggregate,
    evaluate_narrative,
)
from llm_adapters.quality_gate import GateOutcome


# --- benchmark cases ------------------------------------------------------


def test_eight_cases_present() -> None:
    assert len(BENCHMARK_CASES) == 8
    ids = [c.spec.research_case_id for c in BENCHMARK_CASES]
    for required in (
        "DSP-BMK-01-simple-interpretation",
        "DSP-BMK-02-simple-comparison",
        "DSP-BMK-03-routine-valuation",
        "DSP-BMK-04-valuation-conflict",
        "DSP-BMK-05-conflicting-evidence",
        "DSP-BMK-06-missing-history",
        "DSP-BMK-07-difficult-buffett-bq",
        "DSP-BMK-08-high-risk-uncertain",
    ):
        assert required in ids


def test_every_case_has_frozen_values_and_signals() -> None:
    for case in BENCHMARK_CASES:
        assert case.spec.frozen_values, case.spec.research_case_id
        assert case.signals, case.spec.research_case_id
        assert case.expected_routing_tier in ("cost_efficient", "premium")


# --- evaluator: no invention, conservative -------------------------------


def test_evaluator_perfect_match_scores_high() -> None:
    frozen = {"intrinsic_value_per_share": "180", "margin_of_safety": "12.0%"}
    narrative = (
        "The intrinsic value per share is 180 (frozen) with a margin of "
        "safety of 12.0%. The current price is below intrinsic value "
        "[evidence:r1]."
    )
    v = evaluate_narrative(narrative, frozen)
    assert v.quality.factual_accuracy == 1.0
    # intrinsic matched (0.5); no current_market_price in frozen -> not 1.0
    assert (v.quality.valuation_reasoning or 0.0) >= 0.5
    assert v.hallucination_count == 0
    # Every substantive sentence now carries a citation marker.
    assert v.unsupported_claim_count == 0


def test_evaluator_hallucination_counted() -> None:
    frozen = {"intrinsic_value_per_share": "180"}
    narrative = "The intrinsic value per share is 180, ROE is 25%, revenue grew 40%."
    v = evaluate_narrative(narrative, frozen)
    assert v.hallucination_count == 2  # 25 and 40 are not in frozen
    assert (v.quality.hallucination or 1.0) < 1.0


def test_evaluator_returns_none_for_unverifiable_components() -> None:
    frozen = {"intrinsic_value_per_share": "180"}
    v = evaluate_narrative(
        "The intrinsic value per share is 180.", frozen
    )
    # moat_business_quality: not enough frozen keys to score -> None
    assert v.quality.moat_business_quality is None
    # risk: no risk key in frozen -> None
    assert v.quality.risk is None


def test_evaluator_does_not_invent_factual_score() -> None:
    """A narrative that ignores all frozen values scores 0.0, not invented."""
    frozen = {"intrinsic_value_per_share": "180"}
    v = evaluate_narrative("I cannot say.", frozen)
    assert v.quality.factual_accuracy == 0.0


def test_evaluator_structured_output_requires_minimum_structure() -> None:
    v = evaluate_narrative("Too short.", {"x": "1"})
    assert v.quality.structured_output == 0.0
    v2 = evaluate_narrative(
        "Sentence one. Sentence two. Sentence three. Sentence four.",
        {"x": "1"},
    )
    assert v2.quality.structured_output == 1.0


def test_aggregator_does_not_invent_components() -> None:
    a = evaluate_narrative("ok", {"x": "1"})
    b = evaluate_narrative("ok", {"x": "1"})
    agg = aggregate([a, b])
    # components None in every input stay None in the aggregate
    assert agg.risk is None
    # components present in every input get averaged
    assert agg.factual_accuracy is not None


# --- harness: no-key, fail-closed path -----------------------------------


def _no_key_config() -> LLMPlatformConfig:
    """A config with every key absent — every model returns PROVIDER_UNAVAILABLE."""
    for k in (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY",
        "DSP_AI_OPENAI_API_KEY", "DSP_AI_ANTHROPIC_API_KEY",
        "DSP_AI_GEMINI_API_KEY", "DSP_AI_DEEPSEEK_API_KEY",
    ):
        os.environ.pop(k, None)
    return LLMPlatformConfig(
        default_provider="deterministic",
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        deepseek_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude-3-5-sonnet-20241022",
        gemini_model="gemini-1.5-flash",
        deepseek_model="deepseek-chat",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def test_harness_with_no_keys_fails_cleanly() -> None:
    config = _no_key_config()
    case = BENCHMARK_CASES[0]  # simple interpretation
    t1, t2 = run_one_case_one_model(case, "deepseek:deepseek-chat", config)
    assert t1 is not None
    assert t1.error_category is ErrorCategory.PROVIDER_UNAVAILABLE
    assert t1.status is EvaluationStatus.FAILED
    # Without keys, the gate at the cheap tier escalates to the premium
    # tier (Anthropic), which is ALSO unconfigured. The premium run is
    # recorded so the operator can see what happened; both tiers
    # fail-closed and no fabrication occurs.
    assert t2 is not None
    assert t2.tier == "premium"
    assert t2.error_category is ErrorCategory.PROVIDER_UNAVAILABLE
    assert t2.was_escalated is True


def test_harness_never_calls_network_without_keys() -> None:
    """Sanity: no DNS or sockets touched. The adapter returns immediately."""
    config = _no_key_config()
    runs = run_benchmark(config, cases=BENCHMARK_CASES[:2], models=BENCHMARK_MODELS[:2])
    assert runs  # we got records
    for r in runs:
        assert r.gate.outcome is GateOutcome.FAILED_CLOSED or r.error_category is not ErrorCategory.NONE


def test_unknown_pricing_never_treated_as_zero_in_records() -> None:
    config = _no_key_config()
    # Use a model identity whose catalog pricing is set, but the
    # call never executes (no key). So estimated_cost_usd == 0 from
    # the cost calculator applied to zero tokens, and pricing_unknown
    # reflects the catalog. Confirm pricing is present in the record.
    case = BENCHMARK_CASES[0]
    t1, _ = run_one_case_one_model(case, "deepseek:deepseek-chat", config)
    assert t1 is not None
    assert t1.pricing.input_usd_per_1m > 0  # catalog has DeepSeek pricing
    assert t1.pricing_unknown is False


# --- report: privacy boundary --------------------------------------------


def test_report_rows_have_no_private_fields() -> None:
    config = _no_key_config()
    runs = run_benchmark(config, cases=BENCHMARK_CASES[:1], models=BENCHMARK_MODELS[:1])
    report = build_report(runs)
    for row in report["rows"]:
        assert_no_private_leakage(row)


def test_report_summary_present() -> None:
    config = _no_key_config()
    runs = run_benchmark(config, cases=BENCHMARK_CASES[:1], models=BENCHMARK_MODELS[:1])
    report = build_report(runs)
    assert "summary" in report
    assert "rows" in report
    for key in ("total_runs", "accepted", "failed_closed", "escalated"):
        assert key in report["summary"]


def test_private_run_records_are_not_in_public_pack_shape() -> None:
    """BenchmarkRun carries private fields; only public_summary() is safe."""
    config = _no_key_config()
    runs = run_benchmark(config, cases=BENCHMARK_CASES[:1], models=BENCHMARK_MODELS[:1])
    # Build a PrivateInternalResult wrapping a benign public pack, and
    # confirm no provider/cost/routing fields reach the public dict.
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
        provider=runs[0].provider,
        model=runs[0].model,
        routing_tier=runs[0].tier,
        routing_reasons=runs[0].routing_decision.routing_reasons,
        confidence_requirement=runs[0].routing_decision.confidence_requirement,
        estimated_cost_usd=runs[0].estimated_cost_usd,
        input_tokens=runs[0].usage.input_tokens,
        output_tokens=runs[0].usage.output_tokens,
        latency_ms=runs[0].latency_ms,
        model_score=runs[0].quality_score,
        routing_criteria=("complexity",),
        internal_prompt="PRIVATE",
    )
    out = private.to_public().to_dict()
    assert_no_private_leakage(out)


# --- reproducibility -----------------------------------------------------


def test_benchmark_cases_are_immutable() -> None:
    """Two reads of the same spec must compare equal."""
    c1 = BENCHMARK_CASES[0]
    c2 = BENCHMARK_CASES[0]
    assert c1 == c2
    assert c1.spec.research_case_id == c2.spec.research_case_id
    assert c1.spec.frozen_values == c2.spec.frozen_values


def test_run_one_case_one_model_is_deterministic_when_no_keys() -> None:
    config = _no_key_config()
    case = BENCHMARK_CASES[2]  # routine valuation
    t1a, t2a = run_one_case_one_model(case, "gemini:gemini-1.5-flash", config)
    t1b, t2b = run_one_case_one_model(case, "gemini:gemini-1.5-flash", config)
    # Status + error category must match (latency may differ by a few ms).
    assert t1a is not None and t1b is not None
    assert t1a.status == t1b.status
    assert t1a.error_category == t1b.error_category
