"""Model and serialization tests for Economic Moat Intelligence."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from economic_moat import (
    ECONOMIC_MOAT_VERSION,
    EconomicAnalysis,
    EconomicConfidence,
    EconomicEvidence,
    EconomicExplainability,
    EconomicMetadata,
    EconomicMoatValidationError,
    EconomicScore,
    EconomicValidationSummary,
    MoatComponentScore,
    MoatDimension,
    MoatRating,
)


def test_models_are_immutable_and_serialize() -> None:
    metadata = EconomicMetadata(
        engine_version=ECONOMIC_MOAT_VERSION,
        company=" Acme ",
        ticker=" acm ",
        input_types=["FinancialAnalysis", "BusinessQualityAnalysis"],
    )
    evidence = EconomicEvidence(
        source="FinancialAnalysis",
        reference="financial:summary",
        summary="Margin proxy",
        reasoning="Pricing power proxy",
        confidence=0.6,
        supporting_metrics=("gross_margin=0.6",),
        limitations=("No brand survey",),
    )
    confidence = EconomicConfidence(value=0.25, basis="unit-test")
    explainability = EconomicExplainability(
        evidence=[evidence],
        confidence=confidence,
        assumptions=["input accepted"],
        limitations=["proxy only"],
        reasoning="test",
    )
    validation = EconomicValidationSummary(ok=True, checks=["types_valid=True"])
    component = MoatComponentScore(
        dimension=MoatDimension.BRAND,
        score=EconomicScore(value=55.0, status="assessed"),
        confidence=confidence,
        evidence=[evidence],
        reasoning="brand proxy",
        weight=0.2,
    )
    analysis = EconomicAnalysis(
        metadata=metadata,
        validation=validation,
        score=EconomicScore(value=55.0, status="assessed"),
        evidence=[evidence],
        confidence=confidence,
        explainability=explainability,
        components=[component],
        overall_moat_rating=MoatRating.NARROW,
        summary="narrow moat",
        research_disclaimer="research only",
    )

    assert metadata.to_dict()["ticker"] == "ACM"
    assert evidence.to_dict()["confidence"] == 0.6
    assert analysis.to_dict()["overall_moat_score"] == 55.0
    assert analysis.to_dict()["overall_moat_rating"] == "narrow"
    assert analysis.to_dict()["components"][0]["dimension"] == "brand"
    with pytest.raises(FrozenInstanceError):
        analysis.research_disclaimer = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"engine_version": ""}, "engine_version"),
        ({"engine_version": "v", "framework_version": ""}, "framework_version"),
        ({"engine_version": "v", "schema_version": ""}, "schema_version"),
    ],
)
def test_metadata_rejects_missing_contract_values(
    kwargs: dict[str, str], message: str
) -> None:
    with pytest.raises(EconomicMoatValidationError, match=message):
        EconomicMetadata(**kwargs)


@pytest.mark.parametrize(
    ("value", "basis", "message"),
    [
        ("bad", "basis", "numeric"),
        (-0.1, "basis", "range"),
        (1.1, "basis", "range"),
        (0.2, "", "basis"),
    ],
)
def test_confidence_rejects_invalid_values(
    value: object, basis: str, message: str
) -> None:
    with pytest.raises(EconomicMoatValidationError, match=message):
        EconomicConfidence(value=value, basis=basis)  # type: ignore[arg-type]


def test_score_and_evidence_validation() -> None:
    with pytest.raises(EconomicMoatValidationError, match="score.status"):
        EconomicScore(status=" ")
    with pytest.raises(EconomicMoatValidationError, match="score.value"):
        EconomicScore(value=150.0, status="assessed")
    with pytest.raises(EconomicMoatValidationError, match="evidence.source"):
        EconomicEvidence(source="", reference="r")
    with pytest.raises(EconomicMoatValidationError, match="evidence.reference"):
        EconomicEvidence(source="s", reference="")
    scored = EconomicScore(value=42.0, status="not_assessed")
    assert scored.status == "assessed"
