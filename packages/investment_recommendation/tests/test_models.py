"""Model tests for Investment Recommendation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from investment_recommendation import (
    RECOMMENDATION_VERSION,
    InvestmentRecommendation,
    InvestmentRecommendationAction,
    InvestmentRecommendationConfidence,
    InvestmentRecommendationEvidence,
    InvestmentRecommendationExplainability,
    InvestmentRecommendationMetadata,
    InvestmentRecommendationScore,
    InvestmentRecommendationValidationError,
    InvestmentRecommendationValidationSummary,
)


def test_models_immutable_and_serialize() -> None:
    metadata = InvestmentRecommendationMetadata(
        engine_version=RECOMMENDATION_VERSION,
        company=" Acme ",
        ticker=" acm ",
    )
    evidence = InvestmentRecommendationEvidence(
        source="valuation",
        reference="mos",
        summary="undervalued",
        reasoning="MoS positive",
        confidence=0.7,
        supporting_metrics=("mos=0.3",),
        contributing_engines=("valuation",),
    )
    confidence = InvestmentRecommendationConfidence(value=0.6, basis="unit-test")
    analysis = InvestmentRecommendation(
        metadata=metadata,
        validation=InvestmentRecommendationValidationSummary(ok=True, checks=["ok"]),
        score=InvestmentRecommendationScore(value=75.0, status="assessed"),
        recommendation=InvestmentRecommendationAction.BUY,
        confidence=confidence,
        evidence=[evidence],
        explainability=InvestmentRecommendationExplainability(
            evidence=[evidence], confidence=confidence, reasoning="test"
        ),
        investment_thesis="thesis",
        decision_summary="summary",
        research_disclaimer="research only",
    )
    payload = analysis.to_dict()
    assert payload["overall_investment_score"] == 75.0
    assert payload["recommendation"] == "buy"
    assert metadata.to_dict()["ticker"] == "ACM"
    with pytest.raises(FrozenInstanceError):
        analysis.decision_summary = "x"  # type: ignore[misc]


def test_validation_edges() -> None:
    with pytest.raises(InvestmentRecommendationValidationError, match="range"):
        InvestmentRecommendationConfidence(value=1.2, basis="x")
    scored = InvestmentRecommendationScore(value=40.0, status="not_assessed")
    assert scored.status == "assessed"
