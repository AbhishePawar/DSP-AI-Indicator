"""Model tests for Growth Quality Intelligence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from growth_quality import (
    GROWTH_QUALITY_VERSION,
    GrowthQualityAnalysis,
    GrowthQualityComponentScore,
    GrowthQualityConfidence,
    GrowthQualityDimension,
    GrowthQualityEvidence,
    GrowthQualityExplainability,
    GrowthQualityMetadata,
    GrowthQualityRating,
    GrowthQualityScore,
    GrowthQualityValidationError,
    GrowthQualityValidationSummary,
)


def test_models_immutable_and_serialize() -> None:
    metadata = GrowthQualityMetadata(
        engine_version=GROWTH_QUALITY_VERSION,
        company=" Acme ",
        ticker=" acm ",
    )
    evidence = GrowthQualityEvidence(
        source="FinancialAnalysis",
        reference="growth",
        summary="Revenue growth",
        reasoning="Durable organic growth",
        confidence=0.7,
        supporting_metrics=("revenue_cagr=0.12",),
        limitations=("Acquisition attribution deferred",),
    )
    confidence = GrowthQualityConfidence(value=0.6, basis="unit-test")
    component = GrowthQualityComponentScore(
        dimension=GrowthQualityDimension.REVENUE_GROWTH_QUALITY,
        score=GrowthQualityScore(value=75.0, status="assessed"),
        confidence=confidence,
        evidence=[evidence],
        reasoning="growth proxy",
        weight=0.18,
    )
    analysis = GrowthQualityAnalysis(
        metadata=metadata,
        validation=GrowthQualityValidationSummary(ok=True, checks=["ok"]),
        score=GrowthQualityScore(value=75.0, status="assessed"),
        evidence=[evidence],
        confidence=confidence,
        explainability=GrowthQualityExplainability(
            evidence=[evidence], confidence=confidence, reasoning="test"
        ),
        components=[component],
        overall_growth_rating=GrowthQualityRating.STRONG,
        summary="strong",
        strengths=("organic",),
        weaknesses=("none",),
        research_disclaimer="research only",
    )
    payload = analysis.to_dict()
    assert payload["overall_growth_score"] == 75.0
    assert payload["overall_growth_rating"] == "strong"
    assert metadata.to_dict()["ticker"] == "ACM"
    with pytest.raises(FrozenInstanceError):
        analysis.summary = "x"  # type: ignore[misc]


def test_validation_edges() -> None:
    with pytest.raises(GrowthQualityValidationError, match="range"):
        GrowthQualityConfidence(value=1.2, basis="x")
    scored = GrowthQualityScore(value=40.0, status="not_assessed")
    assert scored.status == "assessed"
