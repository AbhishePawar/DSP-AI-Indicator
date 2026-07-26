"""Engine integration, determinism, and explainability tests."""

from __future__ import annotations

import pytest

from management_quality import (
    ManagementDimension,
    ManagementEngine,
    ManagementQualityValidationError,
    ManagementRating,
)


def test_analyze_produces_six_components(
    financial_analysis, business_quality_analysis
) -> None:
    result = ManagementEngine().analyze(financial_analysis, business_quality_analysis)
    assert result.validation.ok is True
    assert result.score.value is not None
    assert 0.0 <= result.score.value <= 100.0
    assert result.overall_management_rating in set(ManagementRating)
    assert len(result.components) == 6
    assert {c.dimension for c in result.components} == set(ManagementDimension)
    assert result.evidence
    assert all(e.source and e.reference and e.reasoning for e in result.evidence)
    assert result.summary
    assert result.recommendation
    assert "research-only" in result.research_disclaimer.lower() or "not investment" in result.research_disclaimer.lower()
    payload = result.to_dict()
    assert len(payload["components"]) == 6
    assert "strengths" in payload and "weaknesses" in payload


def test_analyze_is_deterministic(
    financial_analysis, business_quality_analysis
) -> None:
    engine = ManagementEngine()
    a = engine.analyze(financial_analysis, business_quality_analysis)
    b = engine.analyze(financial_analysis, business_quality_analysis)
    assert a.to_dict() == b.to_dict()


def test_explain_and_validate(
    financial_analysis, business_quality_analysis
) -> None:
    engine = ManagementEngine()
    analysis = engine.analyze(financial_analysis, business_quality_analysis)
    assert engine.explain(analysis) is analysis.explainability
    with pytest.raises(ManagementQualityValidationError, match="ManagementAnalysis"):
        engine.explain(object())  # type: ignore[arg-type]
    summary = engine.validate(None, None)
    assert summary.ok is False


def test_governance_confidence_capped(
    financial_analysis, business_quality_analysis
) -> None:
    result = ManagementEngine().analyze(financial_analysis, business_quality_analysis)
    by_dim = {c.dimension: c for c in result.components}
    assert by_dim[ManagementDimension.GOVERNANCE].confidence.value <= 0.45
    gov_score = by_dim[ManagementDimension.GOVERNANCE].score.value
    if gov_score is not None:
        assert gov_score <= 60.0
