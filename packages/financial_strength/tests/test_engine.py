"""Engine integration, determinism, and explainability tests."""

from __future__ import annotations

import pytest

from financial_strength import (
    FinancialStrengthDimension,
    FinancialStrengthEngine,
    FinancialStrengthRating,
    FinancialStrengthValidationError,
)


def test_analyze_produces_six_components(
    financial_analysis, business_quality_analysis
) -> None:
    result = FinancialStrengthEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    assert result.validation.ok is True
    assert result.score.value is not None
    assert 0.0 <= result.score.value <= 100.0
    assert result.overall_strength_rating in set(FinancialStrengthRating)
    assert len(result.components) == 6
    assert {c.dimension for c in result.components} == set(FinancialStrengthDimension)
    assert result.evidence
    assert all(e.source and e.reference and e.reasoning for e in result.evidence)
    assert result.summary and result.recommendation
    assert result.key_metrics
    payload = result.to_dict()
    assert len(payload["components"]) == 6
    assert "strengths" in payload and "weaknesses" in payload


def test_analyze_is_deterministic(
    financial_analysis, business_quality_analysis
) -> None:
    engine = FinancialStrengthEngine()
    a = engine.analyze(financial_analysis, business_quality_analysis)
    b = engine.analyze(financial_analysis, business_quality_analysis)
    assert a.to_dict() == b.to_dict()


def test_explain_and_validate(
    financial_analysis, business_quality_analysis
) -> None:
    engine = FinancialStrengthEngine()
    analysis = engine.analyze(financial_analysis, business_quality_analysis)
    assert engine.explain(analysis) is analysis.explainability
    with pytest.raises(
        FinancialStrengthValidationError, match="FinancialStrengthAnalysis"
    ):
        engine.explain(object())  # type: ignore[arg-type]
    assert engine.validate(None, None).ok is False


def test_balance_sheet_maturity_confidence_soft_cap(
    financial_analysis, business_quality_analysis
) -> None:
    result = FinancialStrengthEngine().analyze(
        financial_analysis, business_quality_analysis
    )
    by_dim = {c.dimension: c for c in result.components}
    assert by_dim[FinancialStrengthDimension.BALANCE_SHEET_STRENGTH].confidence.value <= 0.75
    assert by_dim[FinancialStrengthDimension.FINANCIAL_RESILIENCE].confidence.value <= 0.70
