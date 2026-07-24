"""End-to-end tests for InvestmentCommittee (2-, 3-, and 4-member)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contracts.enums import SignalDirection
from contracts import AnalyticalStance, ValuationConfidence

from ai_committee.committee import InvestmentCommittee
from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members import (
    EconomicMember,
    FundamentalMember,
    TechnicalMember,
    ValuationMember,
)
from ai_committee.models import CommitteeReport

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _two_member_committee() -> InvestmentCommittee:
    """Backward-compatible Technical + Fundamental roster."""
    return InvestmentCommittee(
        members=[TechnicalMember(), FundamentalMember()],
        clock=lambda: FIXED_NOW,
    )


def _three_member_committee() -> InvestmentCommittee:
    """Sprint 6.1 Technical + Fundamental + Economic roster."""
    return InvestmentCommittee(
        members=[TechnicalMember(), FundamentalMember(), EconomicMember()],
        clock=lambda: FIXED_NOW,
    )


class TestInvestmentCommitteeDefaults:
    """Default roster and registration."""

    def test_default_members_include_valuation(self) -> None:
        committee = InvestmentCommittee(clock=lambda: FIXED_NOW)
        assert tuple(m.name for m in committee.members) == (
            "technical",
            "fundamental",
            "economic",
            "valuation",
        )

    def test_register_duplicate_raises(self) -> None:
        committee = InvestmentCommittee(members=[], clock=lambda: FIXED_NOW)
        committee.register(TechnicalMember())
        with pytest.raises(CommitteeError, match="already registered"):
            committee.register(TechnicalMember())

    def test_empty_roster_raises(self, context_factory) -> None:
        committee = InvestmentCommittee(members=[], clock=lambda: FIXED_NOW)
        with pytest.raises(CommitteeError, match="empty"):
            committee.deliberate(context_factory())


class TestTwoMemberBackwardCompatibility:
    """Sprint 5.0 two-member behavior must remain intact."""

    def test_buy_consensus(self, context_factory) -> None:
        report = _two_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BULLISH,),
                include_economic=False,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.BUY
        assert report.members_participated == ("technical", "fundamental")

    def test_sell_consensus(self, context_factory) -> None:
        report = _two_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BEARISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                include_economic=False,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.SELL

    def test_hold_consensus(self, context_factory) -> None:
        report = _two_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.NEUTRAL,),
                fundamental_dirs=(SignalDirection.NEUTRAL,),
                include_economic=False,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.HOLD

    def test_buy_sell_is_neutral(self, context_factory) -> None:
        report = _two_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                include_economic=False,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.NEUTRAL

    def test_buy_hold_is_hold(self, context_factory) -> None:
        report = _two_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.NEUTRAL,),
                include_economic=False,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.HOLD

    def test_sell_hold_is_hold(self, context_factory) -> None:
        report = _two_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BEARISH,),
                fundamental_dirs=(SignalDirection.NEUTRAL,),
                include_economic=False,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.HOLD


class TestThreeMemberVoting:
    """Sprint 6.1 three-member plurality voting (explicit roster)."""

    def test_buy_buy_buy(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BULLISH,),
                economic_recommendation=AnalyticalStance.BUY,
                include_valuation=False,
            )
        )
        assert isinstance(report, CommitteeReport)
        assert report.decision.decision is Decision.BUY
        assert report.members_participated == (
            "technical",
            "fundamental",
            "economic",
        )
        assert "economic" in report.explanation

    def test_sell_sell_sell(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BEARISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                economic_recommendation=AnalyticalStance.SELL,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.SELL

    def test_buy_buy_hold_is_buy(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BULLISH,),
                economic_recommendation=AnalyticalStance.HOLD,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.BUY

    def test_sell_sell_hold_is_sell(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BEARISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                economic_recommendation=AnalyticalStance.HOLD,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.SELL

    def test_buy_hold_hold_is_hold(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.NEUTRAL,),
                economic_recommendation=AnalyticalStance.HOLD,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.HOLD

    def test_sell_hold_hold_is_hold(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BEARISH,),
                fundamental_dirs=(SignalDirection.NEUTRAL,),
                economic_recommendation=AnalyticalStance.HOLD,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.HOLD

    def test_buy_buy_sell_is_buy(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BULLISH,),
                economic_recommendation=AnalyticalStance.SELL,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.BUY

    def test_sell_sell_buy_is_sell(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BEARISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                economic_recommendation=AnalyticalStance.BUY,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.SELL

    def test_buy_sell_hold_is_neutral(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                economic_recommendation=AnalyticalStance.HOLD,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.NEUTRAL
        assert "conflict" in report.decision.rationale.lower()

    def test_buy_sell_sell_is_sell(self, context_factory) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                economic_recommendation=AnalyticalStance.SELL,
                include_valuation=False,
            )
        )
        assert report.decision.decision is Decision.SELL

    def test_registration_order_independence(self, context_factory) -> None:
        context = context_factory(
            technical_dirs=(SignalDirection.BULLISH,),
            fundamental_dirs=(SignalDirection.BULLISH,),
            economic_recommendation=AnalyticalStance.SELL,
            include_valuation=False,
        )
        forward = InvestmentCommittee(
            members=[
                TechnicalMember(),
                FundamentalMember(),
                EconomicMember(),
            ],
            clock=lambda: FIXED_NOW,
        ).deliberate(context)
        reverse = InvestmentCommittee(
            members=[
                EconomicMember(),
                FundamentalMember(),
                TechnicalMember(),
            ],
            clock=lambda: FIXED_NOW,
        ).deliberate(context)
        assert forward.decision.decision is Decision.BUY
        assert reverse.decision.decision is Decision.BUY
        assert set(forward.members_participated) == set(
            reverse.members_participated
        )

    def test_report_includes_all_opinions_and_evidence(
        self, context_factory
    ) -> None:
        report = _three_member_committee().deliberate(
            context_factory(
                technical_dirs=(
                    SignalDirection.BULLISH,
                    SignalDirection.BULLISH,
                ),
                fundamental_dirs=(SignalDirection.BULLISH,),
                economic_recommendation=AnalyticalStance.BUY,
                include_valuation=False,
            )
        )
        assert len(report.opinions) == 3
        assert len(report.votes) == 3
        assert len(report.evidence_used) == 4  # 2 tech + 1 fund + 1 eco
        assert "Evidence items used: 4" in report.explanation

    def test_determinism(self, context_factory) -> None:
        committee = _three_member_committee()
        context = context_factory(include_valuation=False)
        assert committee.deliberate(context) == committee.deliberate(context)

    def test_missing_economic_raises_when_member_registered(
        self, context_factory
    ) -> None:
        committee = _three_member_committee()
        with pytest.raises(CommitteeError, match="economic"):
            committee.deliberate(
                context_factory(
                    include_economic=False, include_valuation=False
                )
            )


class TestFourMemberVoting:
    """Sprint 8.1 four-member plurality including Valuation."""

    def test_all_buy(self, context_factory) -> None:
        committee = InvestmentCommittee(clock=lambda: FIXED_NOW)
        report = committee.deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BULLISH,),
                economic_recommendation=AnalyticalStance.BUY,
                valuation_mos=0.25,
            )
        )
        assert report.decision.decision is Decision.BUY
        assert report.members_participated == (
            "technical",
            "fundamental",
            "economic",
            "valuation",
        )
        assert "valuation" in report.explanation
        assert any(
            e.source_engine.value == "valuation_engine"
            for e in report.evidence_used
        )

    def test_valuation_buy_swings_plurality(self, context_factory) -> None:
        # T BUY, F SELL, E HOLD, V BUY → BUY plurality
        committee = InvestmentCommittee(clock=lambda: FIXED_NOW)
        report = committee.deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BEARISH,),
                economic_recommendation=AnalyticalStance.HOLD,
                valuation_mos=0.30,
                valuation_confidence=ValuationConfidence.HIGH,
            )
        )
        assert report.decision.decision is Decision.BUY

    def test_valuation_hold_when_mos_unavailable(self, context_factory) -> None:
        committee = InvestmentCommittee(clock=lambda: FIXED_NOW)
        report = committee.deliberate(
            context_factory(
                technical_dirs=(SignalDirection.BULLISH,),
                fundamental_dirs=(SignalDirection.BULLISH,),
                economic_recommendation=AnalyticalStance.BUY,
                valuation_mos=None,
                valuation_confidence=ValuationConfidence.HIGH,
            )
        )
        assert report.decision.decision is Decision.BUY
        valuation_vote = next(
            v for v in report.votes if v.source == "valuation"
        )
        assert valuation_vote.recommendation is Decision.HOLD

    def test_missing_valuation_raises_when_member_registered(
        self, context_factory
    ) -> None:
        committee = InvestmentCommittee(clock=lambda: FIXED_NOW)
        with pytest.raises(CommitteeError, match="valuation"):
            committee.deliberate(context_factory(include_valuation=False))

    def test_determinism(self, context_factory) -> None:
        committee = InvestmentCommittee(clock=lambda: FIXED_NOW)
        context = context_factory()
        assert committee.deliberate(context) == committee.deliberate(context)
