"""Engine integration and determinism tests for Economic Moat Intelligence."""

from __future__ import annotations

import pytest

from economic_moat import (
    EconomicEngine,
    EconomicMoatValidationError,
    MoatDimension,
    MoatRating,
)


def test_analyze_produces_six_components_with_evidence(
    financial_analysis, business_quality_analysis
) -> None:
    engine = EconomicEngine()
    result = engine.analyze(financial_analysis, business_quality_analysis)

    assert result.validation.ok is True
    assert result.score.value is not None
    assert 0.0 <= result.score.value <= 100.0
    assert result.overall_moat_rating in set(MoatRating)
    assert len(result.components) == 6
    dims = {c.dimension for c in result.components}
    assert dims == set(MoatDimension)
    assert result.evidence
    assert all(e.source and e.reference and e.reasoning for e in result.evidence)
    assert result.summary
    assert result.recommendation
    assert result.weights_used is not None
    assert "research-only" in result.research_disclaimer.lower() or "not investment" in result.research_disclaimer.lower()
    payload = result.to_dict()
    assert payload["overall_moat_score"] == result.score.value
    assert len(payload["components"]) == 6


def test_analyze_is_deterministic(
    financial_analysis, business_quality_analysis
) -> None:
    engine = EconomicEngine()
    a = engine.analyze(financial_analysis, business_quality_analysis)
    b = engine.analyze(financial_analysis, business_quality_analysis)
    assert a.to_dict() == b.to_dict()


def test_explain_returns_analysis_explainability(
    financial_analysis, business_quality_analysis
) -> None:
    engine = EconomicEngine()
    analysis = engine.analyze(financial_analysis, business_quality_analysis)
    assert engine.explain(analysis) is analysis.explainability
    with pytest.raises(EconomicMoatValidationError, match="EconomicAnalysis"):
        engine.explain(object())  # type: ignore[arg-type]


def test_validate_rejects_missing_inputs() -> None:
    engine = EconomicEngine()
    summary = engine.validate(None, None)
    assert summary.ok is False
    assert "FinancialAnalysis" in summary.missing_inputs
    assert "BusinessQualityAnalysis" in summary.missing_inputs


def test_network_and_efficient_scale_are_confidence_capped(
    financial_analysis, business_quality_analysis
) -> None:
    result = EconomicEngine().analyze(financial_analysis, business_quality_analysis)
    by_dim = {c.dimension: c for c in result.components}
    assert by_dim[MoatDimension.NETWORK_EFFECTS].confidence.value <= 0.55
    assert by_dim[MoatDimension.EFFICIENT_SCALE].confidence.value <= 0.50
