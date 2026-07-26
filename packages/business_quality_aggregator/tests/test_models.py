"""Model tests for Business Quality Aggregator."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from business_quality_aggregator import (
    AGGREGATOR_VERSION,
    AggregatorComponent,
    AggregatorComponentResult,
    BusinessQualityAggregation,
    BusinessQualityAggregatorConfidence,
    BusinessQualityAggregatorEvidence,
    BusinessQualityAggregatorExplainability,
    BusinessQualityAggregatorMetadata,
    BusinessQualityAggregatorRating,
    BusinessQualityAggregatorScore,
    BusinessQualityAggregatorValidationError,
    BusinessQualityAggregatorValidationSummary,
)


def test_models_immutable_and_serialize() -> None:
    metadata = BusinessQualityAggregatorMetadata(
        engine_version=AGGREGATOR_VERSION,
        company=" Acme ",
        ticker=" acm ",
    )
    evidence = BusinessQualityAggregatorEvidence(
        source="EconomicAnalysis",
        reference="moat",
        summary="Moat signal",
        reasoning="Durable advantage",
        confidence=0.7,
        supporting_metrics=("moat_score=80",),
        limitations=("Peer data deferred",),
        contributing_engines=("economic_moat",),
    )
    confidence = BusinessQualityAggregatorConfidence(value=0.6, basis="unit-test")
    component = AggregatorComponentResult(
        component=AggregatorComponent.ECONOMIC_MOAT,
        engine_score=BusinessQualityAggregatorScore(value=80.0, status="assessed"),
        engine_rating="strong",
        engine_confidence=confidence,
        weight=0.25,
        weighted_contribution=20.0,
        evidence=[evidence],
    )
    analysis = BusinessQualityAggregation(
        metadata=metadata,
        validation=BusinessQualityAggregatorValidationSummary(ok=True, checks=["ok"]),
        score=BusinessQualityAggregatorScore(value=75.0, status="assessed"),
        evidence=[evidence],
        confidence=confidence,
        explainability=BusinessQualityAggregatorExplainability(
            evidence=[evidence], confidence=confidence, reasoning="test"
        ),
        components=[component],
        overall_business_quality_rating=BusinessQualityAggregatorRating.GOOD,
        summary="good",
        strengths=("moat",),
        weaknesses=("none",),
        research_disclaimer="research only",
    )
    payload = analysis.to_dict()
    assert payload["overall_business_quality_score"] == 75.0
    assert payload["overall_business_quality_rating"] == "good"
    assert metadata.to_dict()["ticker"] == "ACM"
    with pytest.raises(FrozenInstanceError):
        analysis.summary = "x"  # type: ignore[misc]


def test_validation_edges() -> None:
    with pytest.raises(BusinessQualityAggregatorValidationError, match="range"):
        BusinessQualityAggregatorConfidence(value=1.2, basis="x")
    scored = BusinessQualityAggregatorScore(value=40.0, status="not_assessed")
    assert scored.status == "assessed"
