"""Model tests for Management Quality Intelligence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from management_quality import (
    MANAGEMENT_QUALITY_VERSION,
    ManagementAnalysis,
    ManagementComponentScore,
    ManagementConfidence,
    ManagementDimension,
    ManagementEvidence,
    ManagementExplainability,
    ManagementMetadata,
    ManagementQualityValidationError,
    ManagementRating,
    ManagementScore,
    ManagementValidationSummary,
)


def test_models_immutable_and_serialize() -> None:
    metadata = ManagementMetadata(
        engine_version=MANAGEMENT_QUALITY_VERSION,
        company=" Acme ",
        ticker=" acm ",
    )
    evidence = ManagementEvidence(
        source="FinancialAnalysis",
        reference="cash_flow",
        summary="FCF proxy",
        reasoning="Owner cash generation",
        confidence=0.6,
        supporting_metrics=("fcf=170",),
        limitations=("No proxy statement",),
    )
    confidence = ManagementConfidence(value=0.5, basis="unit-test")
    component = ManagementComponentScore(
        dimension=ManagementDimension.CAPITAL_ALLOCATION,
        score=ManagementScore(value=70.0, status="assessed"),
        confidence=confidence,
        evidence=[evidence],
        reasoning="ca proxy",
        weight=0.22,
    )
    analysis = ManagementAnalysis(
        metadata=metadata,
        validation=ManagementValidationSummary(ok=True, checks=["ok"]),
        score=ManagementScore(value=70.0, status="assessed"),
        evidence=[evidence],
        confidence=confidence,
        explainability=ManagementExplainability(
            evidence=[evidence], confidence=confidence, reasoning="test"
        ),
        components=[component],
        overall_management_rating=ManagementRating.GOOD,
        summary="good management",
        strengths=("strong CA",),
        weaknesses=("weak gov data",),
        research_disclaimer="research only",
    )
    payload = analysis.to_dict()
    assert payload["overall_management_score"] == 70.0
    assert payload["overall_management_rating"] == "good"
    assert metadata.to_dict()["ticker"] == "ACM"
    with pytest.raises(FrozenInstanceError):
        analysis.summary = "x"  # type: ignore[misc]


def test_score_and_confidence_validation() -> None:
    with pytest.raises(ManagementQualityValidationError, match="range"):
        ManagementConfidence(value=1.5, basis="x")
    with pytest.raises(ManagementQualityValidationError, match="score.value"):
        ManagementScore(value=150.0, status="assessed")
    scored = ManagementScore(value=40.0, status="not_assessed")
    assert scored.status == "assessed"
