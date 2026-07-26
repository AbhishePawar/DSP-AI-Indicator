"""Model tests for Earnings Quality Intelligence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from earnings_quality import (
    EARNINGS_QUALITY_VERSION,
    EarningsQualityAnalysis,
    EarningsQualityComponentScore,
    EarningsQualityConfidence,
    EarningsQualityDimension,
    EarningsQualityEvidence,
    EarningsQualityExplainability,
    EarningsQualityMetadata,
    EarningsQualityRating,
    EarningsQualityScore,
    EarningsQualityValidationError,
    EarningsQualityValidationSummary,
)


def test_models_immutable_and_serialize() -> None:
    metadata = EarningsQualityMetadata(
        engine_version=EARNINGS_QUALITY_VERSION,
        company=" Acme ",
        ticker=" acm ",
    )
    evidence = EarningsQualityEvidence(
        source="FinancialAnalysis",
        reference="cash_flow",
        summary="Cash support",
        reasoning="Cash-backed earnings",
        confidence=0.7,
        supporting_metrics=("cash_conversion=1.0",),
        limitations=("No restatement feed",),
    )
    confidence = EarningsQualityConfidence(value=0.6, basis="unit-test")
    component = EarningsQualityComponentScore(
        dimension=EarningsQualityDimension.EARNINGS_QUALITY,
        score=EarningsQualityScore(value=75.0, status="assessed"),
        confidence=confidence,
        evidence=[evidence],
        reasoning="quality proxy",
        weight=0.2,
    )
    analysis = EarningsQualityAnalysis(
        metadata=metadata,
        validation=EarningsQualityValidationSummary(ok=True, checks=["ok"]),
        score=EarningsQualityScore(value=75.0, status="assessed"),
        evidence=[evidence],
        confidence=confidence,
        explainability=EarningsQualityExplainability(
            evidence=[evidence], confidence=confidence, reasoning="test"
        ),
        components=[component],
        overall_earnings_rating=EarningsQualityRating.GOOD,
        summary="good",
        strengths=("cash",),
        weaknesses=("none",),
        research_disclaimer="research only",
    )
    payload = analysis.to_dict()
    assert payload["overall_earnings_score"] == 75.0
    assert payload["overall_earnings_rating"] == "good"
    assert metadata.to_dict()["ticker"] == "ACM"
    with pytest.raises(FrozenInstanceError):
        analysis.summary = "x"  # type: ignore[misc]


def test_validation_edges() -> None:
    with pytest.raises(EarningsQualityValidationError, match="range"):
        EarningsQualityConfidence(value=1.2, basis="x")
    scored = EarningsQualityScore(value=40.0, status="not_assessed")
    assert scored.status == "assessed"
