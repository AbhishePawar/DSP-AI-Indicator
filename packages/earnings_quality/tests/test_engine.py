"""Engine integration, determinism, and explainability tests."""

from __future__ import annotations

import pytest

from earnings_quality import (
    EarningsQualityDimension,
    EarningsQualityEngine,
    EarningsQualityRating,
    EarningsQualityValidationError,
)


def test_analyze_produces_six_components(
    financial_analysis, business_quality_analysis
) -> None:
    result = EarningsQualityEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    assert result.validation.ok is True
    assert result.score.value is not None
    assert 0.0 <= result.score.value <= 100.0
    assert result.overall_earnings_rating in set(EarningsQualityRating)
    assert len(result.components) == 6
    assert {c.dimension for c in result.components} == set(EarningsQualityDimension)
    assert result.evidence
    assert all(e.source and e.reference and e.reasoning for e in result.evidence)
    assert result.summary and result.recommendation
    payload = result.to_dict()
    assert len(payload["components"]) == 6


def test_analyze_is_deterministic(
    financial_analysis, business_quality_analysis
) -> None:
    engine = EarningsQualityEngine()
    a = engine.analyze(financial_analysis, business_quality_analysis)
    b = engine.analyze(financial_analysis, business_quality_analysis)
    assert a.to_dict() == b.to_dict()


def test_explain_and_validate(
    financial_analysis, business_quality_analysis
) -> None:
    engine = EarningsQualityEngine()
    analysis = engine.analyze(financial_analysis, business_quality_analysis)
    assert engine.explain(analysis) is analysis.explainability
    with pytest.raises(
        EarningsQualityValidationError, match="EarningsQualityAnalysis"
    ):
        engine.explain(object())  # type: ignore[arg-type]
    assert engine.validate(None, None).ok is False


def test_predictability_and_accounting_confidence_caps(
    financial_analysis, business_quality_analysis
) -> None:
    result = EarningsQualityEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    by_dim = {c.dimension: c for c in result.components}
    assert by_dim[EarningsQualityDimension.EARNINGS_PREDICTABILITY].confidence.value <= 0.70
    assert by_dim[EarningsQualityDimension.ACCOUNTING_QUALITY].confidence.value <= 0.65


def test_distinct_from_business_quality_module() -> None:
    """FEATURE-004 package engine is not the F3.2 BQ module class."""
    from business_quality import EarningsQualityEngine as BqEqEngine
    from earnings_quality import EarningsQualityEngine as EqEngine

    assert EqEngine is not BqEqEngine
    assert EqEngine.__module__.startswith("earnings_quality")
