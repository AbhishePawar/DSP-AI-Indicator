"""Engine integration, determinism, and explainability tests."""

from __future__ import annotations

import pytest

from growth_quality import (
    GrowthQualityDimension,
    GrowthQualityEngine,
    GrowthQualityRating,
    GrowthQualityValidationError,
)


def test_analyze_produces_six_components(
    financial_analysis, business_quality_analysis
) -> None:
    result = GrowthQualityEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    assert result.validation.ok is True
    assert result.score.value is not None
    assert 0.0 <= result.score.value <= 100.0
    assert result.overall_growth_rating in set(GrowthQualityRating)
    assert len(result.components) == 6
    assert {c.dimension for c in result.components} == set(GrowthQualityDimension)
    assert result.evidence
    assert all(e.source and e.reference and e.reasoning for e in result.evidence)
    assert result.summary and result.recommendation
    assert result.strengths is not None
    assert result.weaknesses is not None
    assert result.risks is not None
    payload = result.to_dict()
    assert len(payload["components"]) == 6


def test_analyze_is_deterministic(
    financial_analysis, business_quality_analysis
) -> None:
    engine = GrowthQualityEngine()
    a = engine.analyze(financial_analysis, business_quality_analysis)
    b = engine.analyze(financial_analysis, business_quality_analysis)
    assert a.to_dict() == b.to_dict()


def test_explain_and_validate(
    financial_analysis, business_quality_analysis
) -> None:
    engine = GrowthQualityEngine()
    analysis = engine.analyze(financial_analysis, business_quality_analysis)
    assert engine.explain(analysis) is analysis.explainability
    with pytest.raises(
        GrowthQualityValidationError, match="GrowthQualityAnalysis"
    ):
        engine.explain(object())  # type: ignore[arg-type]
    assert engine.validate(None, None).ok is False


def test_growth_risk_confidence_cap(
    financial_analysis, business_quality_analysis
) -> None:
    result = GrowthQualityEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    by_dim = {c.dimension: c for c in result.components}
    assert by_dim[GrowthQualityDimension.GROWTH_RISK].confidence.value <= 0.55
