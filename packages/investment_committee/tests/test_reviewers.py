"""Reviewer and consensus unit tests."""

from __future__ import annotations

from investment_committee.consensus import build_consensus
from investment_committee.reviewers import evaluate_all_reviewers
from investment_committee.scoring import CommitteeDecision, ReviewerRole, rank_of
from investment_committee.signals import CommitteeSignals


def _signals(**overrides: object) -> CommitteeSignals:
    base = dict(
        business_quality=75.0,
        economic_moat=80.0,
        management_quality=70.0,
        financial_strength=70.0,
        earnings_quality=70.0,
        growth_quality=65.0,
        investment_score=70.0,
        recommendation="buy",
        mos_ratio=0.30,
        premium_discount=-0.30,
        mos_classification="deep_value",
        ir_confidence=0.7,
        bq_confidence=0.7,
        valuation_confidence=0.7,
        conflict_count=0,
        ir_triggered_rules=(),
    )
    base.update(overrides)
    return CommitteeSignals(**base)  # type: ignore[arg-type]


def test_all_five_reviewers_present() -> None:
    opinions = evaluate_all_reviewers(_signals())
    assert len(opinions) == 5
    assert {o.role for o in opinions} == set(ReviewerRole)
    assert all(o.evidence and o.reasoning for o in opinions)


def test_value_penalises_material_premium() -> None:
    cheap = evaluate_all_reviewers(_signals(mos_ratio=0.3, premium_discount=-0.3))
    rich = evaluate_all_reviewers(_signals(mos_ratio=-0.3, premium_discount=0.3))
    cheap_value = next(o for o in cheap if o.role is ReviewerRole.VALUE_INVESTOR)
    rich_value = next(o for o in rich if o.role is ReviewerRole.VALUE_INVESTOR)
    assert (cheap_value.score.value or 0) > (rich_value.score.value or 0)


def test_risk_flags_growth_weak_balance_sheet() -> None:
    opinions = evaluate_all_reviewers(
        _signals(growth_quality=85.0, financial_strength=35.0)
    )
    growth = next(o for o in opinions if o.role is ReviewerRole.GROWTH_INVESTOR)
    assert any("weak balance sheet" in c.lower() for c in growth.concerns)


def test_consensus_agreement_and_escalation() -> None:
    reviewers = evaluate_all_reviewers(
        _signals(
            business_quality=85.0,
            mos_ratio=-0.20,
            premium_discount=0.20,
            recommendation="hold",
        )
    )
    consensus = build_consensus(
        reviewers,
        _signals(business_quality=85.0, mos_ratio=-0.20, premium_discount=0.20),
    )
    assert 0.0 <= consensus.agreement_score <= 1.0
    assert consensus.decision in set(CommitteeDecision)
    assert "great_business_expensive_valuation" in consensus.escalation_flags
    assert consensus.consensus_method


def test_risk_soft_veto_caps_buy() -> None:
    # Force risk officer very bearish via weak BS + conflicts + overvaluation
    reviewers = evaluate_all_reviewers(
        _signals(
            financial_strength=20.0,
            conflict_count=3,
            mos_ratio=-0.30,
            premium_discount=0.30,
            ir_confidence=0.2,
            bq_confidence=0.2,
            ir_triggered_rules=("a", "b", "c"),
            business_quality=90.0,
            economic_moat=90.0,
            management_quality=90.0,
            earnings_quality=90.0,
            growth_quality=90.0,
        )
    )
    risk = next(r for r in reviewers if r.role is ReviewerRole.RISK_OFFICER)
    assert rank_of(risk.opinion) <= rank_of(CommitteeDecision.REDUCE)
    consensus = build_consensus(reviewers, _signals(financial_strength=20.0))
    assert rank_of(consensus.decision) <= rank_of(CommitteeDecision.ACCUMULATE)
