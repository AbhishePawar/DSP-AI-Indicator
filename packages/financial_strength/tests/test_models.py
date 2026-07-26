"""Model tests for Financial Strength Intelligence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from financial_strength import (
    FINANCIAL_STRENGTH_VERSION,
    FinancialStrengthAnalysis,
    FinancialStrengthComponentScore,
    FinancialStrengthConfidence,
    FinancialStrengthDimension,
    FinancialStrengthEvidence,
    FinancialStrengthExplainability,
    FinancialStrengthMetadata,
    FinancialStrengthRating,
    FinancialStrengthScore,
    FinancialStrengthValidationError,
    FinancialStrengthValidationSummary,
)


def test_models_immutable_and_serialize() -> None:
    metadata = FinancialStrengthMetadata(
        engine_version=FINANCIAL_STRENGTH_VERSION,
        company=" Acme ",
        ticker=" acm ",
    )
    evidence = FinancialStrengthEvidence(
        source="FinancialAnalysis",
        reference="balance_sheet.leverage",
        summary="D/E proxy",
        reasoning="Conservative leverage",
        confidence=0.7,
        supporting_metrics=("debt_to_equity=0.4",),
        limitations=("No maturity schedule",),
    )
    confidence = FinancialStrengthConfidence(value=0.6, basis="unit-test")
    component = FinancialStrengthComponentScore(
        dimension=FinancialStrengthDimension.LIQUIDITY,
        score=FinancialStrengthScore(value=72.0, status="assessed"),
        confidence=confidence,
        evidence=[evidence],
        reasoning="liquidity proxy",
        key_metrics=("current_ratio=2.0",),
        weight=0.15,
    )
    analysis = FinancialStrengthAnalysis(
        metadata=metadata,
        validation=FinancialStrengthValidationSummary(ok=True, checks=["ok"]),
        score=FinancialStrengthScore(value=72.0, status="assessed"),
        evidence=[evidence],
        confidence=confidence,
        explainability=FinancialStrengthExplainability(
            evidence=[evidence], confidence=confidence, reasoning="test"
        ),
        components=[component],
        overall_strength_rating=FinancialStrengthRating.STRONG,
        summary="strong",
        strengths=("cash",),
        weaknesses=("none",),
        key_metrics=("current_ratio=2.0",),
        research_disclaimer="research only",
    )
    payload = analysis.to_dict()
    assert payload["overall_strength_score"] == 72.0
    assert payload["overall_strength_rating"] == "strong"
    assert metadata.to_dict()["ticker"] == "ACM"
    with pytest.raises(FrozenInstanceError):
        analysis.summary = "x"  # type: ignore[misc]


def test_validation_edges() -> None:
    with pytest.raises(FinancialStrengthValidationError, match="range"):
        FinancialStrengthConfidence(value=-0.1, basis="x")
    scored = FinancialStrengthScore(value=40.0, status="not_assessed")
    assert scored.status == "assessed"
