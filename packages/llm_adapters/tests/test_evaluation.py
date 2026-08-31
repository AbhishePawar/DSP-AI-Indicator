"""Tests for AI provider/model evaluation foundation.

Focused unit tests:
- pricing identity resolution
- token cost calculation
- quality / cost / overall scoring (50/50)
- provider/model identity contract
- malformed evaluation result
- missing pricing
"""

from __future__ import annotations

import pytest

from llm_adapters.cost_scoring import (
    calculate_cost_score,
    calculate_estimated_cost,
    calculate_overall_score,
    calculate_quality_score,
    score_evaluations,
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
    ModelInfo,
    ModelPricing,
    get_model_info,
    list_identities,
)


# --- pricing + identity ----------------------------------------------------


def test_default_catalog_has_all_four_providers() -> None:
    identities = set(list_identities())
    for required in (
        "openai:gpt-4o-mini",
        "anthropic:claude-3-5-sonnet-20241022",
        "gemini:gemini-1.5-flash",
        "deepseek:deepseek-chat",
    ):
        assert required in identities


def test_get_model_info_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_model_info("openai:does-not-exist")


def test_model_identity_is_provider_colon_model() -> None:
    info = get_model_info("openai:gpt-4o-mini")
    assert info.identity == "openai:gpt-4o-mini"
    assert info.provider == "openai"
    assert info.model == "gpt-4o-mini"


def test_capabilities_flags_present() -> None:
    info = get_model_info("deepseek:deepseek-chat")
    assert info.capabilities.structured_output is True
    assert info.capabilities.tool_call is True
    assert info.capabilities.streaming is True


def test_pricing_is_configuration_not_hardcoded() -> None:
    """A custom catalog override must flow through pricing math."""
    custom_pricing = ModelPricing(input_usd_per_1m=10.0, output_usd_per_1m=20.0)
    info = ModelInfo(
        provider="openai",
        model="gpt-4o-mini",
        capabilities=DEFAULT_CATALOG["openai:gpt-4o-mini"].capabilities,
        limits=DEFAULT_CATALOG["openai:gpt-4o-mini"].limits,
        pricing=custom_pricing,
    )
    cost = calculate_estimated_cost(TokenUsage(input_tokens=1_000_000, output_tokens=500_000), info.pricing)
    assert cost == pytest.approx(20.0)  # 10*1 + 20*0.5


# --- cost calculator -------------------------------------------------------


def test_calculate_estimated_cost_basic() -> None:
    pricing = ModelPricing(input_usd_per_1m=0.15, output_usd_per_1m=0.60)
    # 1M input + 0 output = $0.15
    assert calculate_estimated_cost(TokenUsage(1_000_000, 0), pricing) == pytest.approx(0.15)
    # 0 input + 1M output = $0.60
    assert calculate_estimated_cost(TokenUsage(0, 1_000_000), pricing) == pytest.approx(0.60)
    # 100k in + 100k out = 0.015 + 0.06 = 0.075
    assert calculate_estimated_cost(TokenUsage(100_000, 100_000), pricing) == pytest.approx(0.075)


def test_calculate_estimated_cost_zero_tokens() -> None:
    pricing = ModelPricing(input_usd_per_1m=0.15, output_usd_per_1m=0.60)
    assert calculate_estimated_cost(TokenUsage(0, 0), pricing) == 0.0


def test_calculate_estimated_cost_rejects_negative() -> None:
    pricing = ModelPricing(input_usd_per_1m=0.15, output_usd_per_1m=0.60)
    with pytest.raises(ValueError):
        calculate_estimated_cost(TokenUsage(-1, 0), pricing)


def test_calculate_estimated_cost_missing_pricing_returns_zero() -> None:
    """Missing pricing must not crash — caller surfaces error separately."""
    assert calculate_estimated_cost(TokenUsage(1000, 1000), None) == 0.0  # type: ignore[arg-type]


# --- quality score ---------------------------------------------------------


def test_calculate_quality_score_empty_is_zero() -> None:
    assert calculate_quality_score(QualityEvaluation()) == 0.0


def test_calculate_quality_score_mean() -> None:
    q = QualityEvaluation(factual_accuracy=1.0, valuation_reasoning=0.5)
    assert calculate_quality_score(q) == pytest.approx(75.0)


def test_calculate_quality_score_rejects_out_of_range() -> None:
    q = QualityEvaluation(factual_accuracy=1.5)
    with pytest.raises(ValueError):
        calculate_quality_score(q)


# --- cost score (relative) -------------------------------------------------


def _result(model_id: str, cost: float, quality: QualityEvaluation) -> EvaluationResult:
    info = get_model_info(model_id)
    return EvaluationResult(
        model=info,
        research_case_id="case-1",
        status=EvaluationStatus.SUCCESS,
        latency_ms=100,
        usage=TokenUsage(1000, 1000),
        estimated_cost_usd=cost,
        structured_output_valid=True,
        quality=quality,
    )


def test_calculate_cost_score_cheapest_is_100() -> None:
    r1 = _result("openai:gpt-4o-mini", 0.01, QualityEvaluation(factual_accuracy=0.5))
    r2 = _result("anthropic:claude-3-5-sonnet-20241022", 0.10, QualityEvaluation(factual_accuracy=0.5))
    assert calculate_cost_score([r1, r2], r1) == pytest.approx(100.0)
    assert calculate_cost_score([r1, r2], r2) == pytest.approx(0.0)


def test_calculate_cost_score_equal_costs_is_100() -> None:
    r1 = _result("openai:gpt-4o-mini", 0.05, QualityEvaluation(factual_accuracy=0.5))
    r2 = _result("gemini:gemini-1.5-flash", 0.05, QualityEvaluation(factual_accuracy=0.5))
    assert calculate_cost_score([r1, r2], r1) == 100.0
    assert calculate_cost_score([r1, r2], r2) == 100.0


def test_calculate_cost_score_zero_target_is_zero() -> None:
    r1 = _result("openai:gpt-4o-mini", 0.0, QualityEvaluation(factual_accuracy=0.5))
    r2 = _result("gemini:gemini-1.5-flash", 0.05, QualityEvaluation(factual_accuracy=0.5))
    assert calculate_cost_score([r1, r2], r1) == 0.0


# --- overall (50/50) -------------------------------------------------------


def test_calculate_overall_score_equal_weighting() -> None:
    assert calculate_overall_score(80.0, 20.0) == pytest.approx(50.0)
    assert calculate_overall_score(100.0, 100.0) == 100.0
    assert calculate_overall_score(0.0, 0.0) == 0.0


def test_calculate_overall_score_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        calculate_overall_score(120.0, 50.0)


# --- composite ranking -----------------------------------------------------


def test_score_evaluations_sorts_descending() -> None:
    # Cheap+low-quality vs expensive+high-quality vs mid
    r1 = _result("gemini:gemini-1.5-flash", 0.001, QualityEvaluation(factual_accuracy=0.3))
    r2 = _result(
        "anthropic:claude-3-5-sonnet-20241022",
        0.10,
        QualityEvaluation(factual_accuracy=0.9, valuation_reasoning=0.9),
    )
    r3 = _result(
        "openai:gpt-4o-mini",
        0.02,
        QualityEvaluation(factual_accuracy=0.6, valuation_reasoning=0.6),
    )
    scored = score_evaluations([r1, r2, r3])
    assert len(scored) == 3
    # All scores 0-100
    for s in scored:
        assert 0.0 <= s.quality_score <= 100.0
        assert 0.0 <= s.cost_score <= 100.0
        assert 0.0 <= s.overall_score <= 100.0
    # Descending by overall
    for a, b in zip(scored, scored[1:]):
        assert a.overall_score >= b.overall_score


def test_score_evaluations_empty() -> None:
    assert score_evaluations([]) == []


# --- malformed result handling --------------------------------------------


def test_evaluation_result_with_failed_status_and_error() -> None:
    info = get_model_info("openai:gpt-4o-mini")
    r = EvaluationResult(
        model=info,
        research_case_id="case-x",
        status=EvaluationStatus.FAILED,
        latency_ms=30_000,
        usage=TokenUsage(1000, 0),
        estimated_cost_usd=0.0,
        structured_output_valid=False,
        quality=QualityEvaluation(),
        error_category=ErrorCategory.TIMEOUT,
        error_detail="upstream timeout",
    )
    assert r.is_success() is False
    assert r.error_category is ErrorCategory.TIMEOUT
    # Failed result can still be scored (cost=0 -> cost_score=0)
    scored = score_evaluations([r])
    assert scored[0].overall_score == 0.0


def test_token_usage_total() -> None:
    u = TokenUsage(input_tokens=700, output_tokens=300)
    assert u.total == 1000
