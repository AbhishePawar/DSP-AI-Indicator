"""Model and scoring tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from investment_committee import (
    COMMITTEE_VERSION,
    CommitteeDecision,
    CommitteeEvidence,
    CommitteeExplainability,
    CommitteeScore,
    CommitteeValidationSummary,
    InvestmentCommitteeConfidence,
    InvestmentCommitteeMetadata,
    InvestmentCommitteeResult,
    InvestmentCommitteeValidationError,
    ReviewerRole,
)
from investment_committee.models import CommitteeConsensus
from investment_committee.scoring import decision_from_score, rank_of


def test_models_immutable_and_serialize() -> None:
    metadata = InvestmentCommitteeMetadata(
        engine_version=COMMITTEE_VERSION, company=" Acme ", ticker=" acm "
    )
    evidence = CommitteeEvidence(
        source="buffett_analyst",
        reference="moat",
        summary="moat",
        reasoning="durable",
        confidence=0.7,
    )
    confidence = InvestmentCommitteeConfidence(value=0.6, basis="unit-test")
    consensus = CommitteeConsensus(
        decision=CommitteeDecision.HOLD,
        agreement_score=0.8,
        disagreement_summary="aligned",
        minority_opinions=(),
        consensus_confidence=confidence,
        consensus_method="test",
        escalation_flags=(),
        weighted_rank=3.0,
    )
    result = InvestmentCommitteeResult(
        metadata=metadata,
        validation=CommitteeValidationSummary(ok=True, checks=["ok"]),
        reviewers=(),
        consensus=consensus,
        score=CommitteeScore(value=60.0, status="assessed"),
        decision=CommitteeDecision.HOLD,
        confidence=confidence,
        evidence=[evidence],
        explainability=CommitteeExplainability(
            evidence=[evidence], confidence=confidence, reasoning="test"
        ),
        research_disclaimer="research only",
    )
    payload = result.to_dict()
    assert payload["decision"] == "hold"
    assert metadata.to_dict()["ticker"] == "ACM"
    with pytest.raises(FrozenInstanceError):
        result.decision_summary = "x"  # type: ignore[misc]


def test_scoring_helpers() -> None:
    assert decision_from_score(90) is CommitteeDecision.STRONG_BUY
    assert decision_from_score(10) is CommitteeDecision.STRONG_SELL
    assert rank_of(CommitteeDecision.BUY) == 5
    assert ReviewerRole.BUFFETT_ANALYST.value == "buffett_analyst"
    with pytest.raises(InvestmentCommitteeValidationError, match="0.0, 1.0"):
        InvestmentCommitteeConfidence(value=1.2, basis="x")
