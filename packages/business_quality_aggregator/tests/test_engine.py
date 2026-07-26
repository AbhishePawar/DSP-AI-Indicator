"""Engine integration, determinism, and explainability tests."""

from __future__ import annotations

import pytest

from business_quality_aggregator import (
    AggregatorComponent,
    BusinessQualityAggregatorEngine,
    BusinessQualityAggregatorRating,
    BusinessQualityAggregatorValidationError,
)


def test_analyze_produces_five_components(domain_analyses) -> None:
    result = BusinessQualityAggregatorEngine().analyze(**domain_analyses)
    assert result.validation.ok is True
    assert result.score.value is not None
    assert 0.0 <= result.score.value <= 100.0
    assert result.overall_business_quality_rating in set(
        BusinessQualityAggregatorRating
    )
    assert len(result.components) == 5
    assert {c.component for c in result.components} == set(AggregatorComponent)
    assert result.evidence
    assert result.summary and result.recommendation
    assert result.investment_observations
    assert result.explainability.engine_weights is not None
    assert result.raw_weighted_score is not None
    payload = result.to_dict()
    assert len(payload["components"]) == 5


def test_analyze_is_deterministic(domain_analyses) -> None:
    engine = BusinessQualityAggregatorEngine()
    a = engine.analyze(**domain_analyses)
    b = engine.analyze(**domain_analyses)
    assert a.to_dict() == b.to_dict()


def test_analyze_from_inputs(
    financial_analysis, business_quality_analysis
) -> None:
    result = BusinessQualityAggregatorEngine().analyze_from_inputs(
        financial_analysis, business_quality_analysis
    )
    assert result.validation.ok is True
    assert result.score.value is not None


def test_explain_and_validate(domain_analyses) -> None:
    engine = BusinessQualityAggregatorEngine()
    analysis = engine.analyze(**domain_analyses)
    assert engine.explain(analysis) is analysis.explainability
    with pytest.raises(
        BusinessQualityAggregatorValidationError, match="BusinessQualityAggregation"
    ):
        engine.explain(object())  # type: ignore[arg-type]
    assert engine.validate().ok is False


def test_explainability_includes_weights_and_availability(domain_analyses) -> None:
    result = BusinessQualityAggregatorEngine().analyze(**domain_analyses)
    assert result.explainability.engine_weights["economic_moat"] == pytest.approx(0.25)
    assert any("economic_moat:available" in x for x in result.explainability.data_availability)
