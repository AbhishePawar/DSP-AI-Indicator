"""Engine integration, determinism, and explainability tests."""

from __future__ import annotations

import pytest

from investment_committee import (
    CommitteeDecision,
    InvestmentCommitteeEngine,
    InvestmentCommitteeValidationError,
    ReviewerRole,
)


def test_analyze_produces_committee_result(committee_inputs) -> None:
    result = InvestmentCommitteeEngine().analyze(**committee_inputs)
    assert result.validation.ok is True
    assert len(result.reviewers) == 5
    assert {r.role for r in result.reviewers} == set(ReviewerRole)
    assert result.decision in set(CommitteeDecision)
    assert result.consensus.agreement_score >= 0.0
    assert result.evidence
    assert result.final_investment_thesis and result.decision_summary
    assert result.explainability.consensus_method
    assert result.explainability.reviewer_contributions
    payload = result.to_dict()
    assert len(payload["reviewers"]) == 5


def test_analyze_is_deterministic(committee_inputs) -> None:
    engine = InvestmentCommitteeEngine()
    a = engine.analyze(**committee_inputs)
    b = engine.analyze(**committee_inputs)
    assert a.to_dict() == b.to_dict()


def test_overvalued_escalation(overvalued_committee_inputs) -> None:
    result = InvestmentCommitteeEngine().analyze(**overvalued_committee_inputs)
    assert (
        "great_business_expensive_valuation" in result.consensus.escalation_flags
        or any(
            "premium" in c.lower() or "margin of safety" in c.lower()
            for r in result.reviewers
            for c in r.concerns
        )
    )


def test_explain_and_validate(committee_inputs) -> None:
    engine = InvestmentCommitteeEngine()
    result = engine.analyze(**committee_inputs)
    assert engine.explain(result) is result.explainability
    with pytest.raises(
        InvestmentCommitteeValidationError, match="InvestmentCommitteeResult"
    ):
        engine.explain(object())  # type: ignore[arg-type]
    assert engine.validate().ok is False
