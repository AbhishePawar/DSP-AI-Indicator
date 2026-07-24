"""Tests for ai_committee internal models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, EngineSource
from core.exceptions import ValidationError

from ai_committee.enums import Decision
from ai_committee.models import (
    CommitteeReport,
    InvestmentDecision,
    MemberVote,
    Opinion,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(
        symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
    )


def _opinion(
    *,
    source: str = "technical",
    recommendation: Decision = Decision.BUY,
) -> Opinion:
    return Opinion(
        source=source,
        recommendation=recommendation,
        confidence=None,
        reasoning="Test reasoning.",
        engine=EngineSource.INDICATOR_ENGINE,
    )


class TestOpinion:
    """Tests for Opinion validation."""

    def test_normalizes_source(self) -> None:
        opinion = _opinion(source="  Technical  ")
        assert opinion.source == "technical"

    def test_confidence_reserved_defaults_none(self) -> None:
        assert _opinion().confidence is None

    def test_empty_source_raises(self) -> None:
        with pytest.raises(ValidationError, match="source"):
            _opinion(source="   ")

    def test_empty_reasoning_raises(self) -> None:
        with pytest.raises(ValidationError, match="reasoning"):
            Opinion(
                source="technical",
                recommendation=Decision.BUY,
                reasoning="   ",
            )

    def test_neutral_recommendation_raises(self) -> None:
        with pytest.raises(ValidationError, match="BUY, HOLD, or SELL"):
            Opinion(
                source="technical",
                recommendation=Decision.NEUTRAL,
                reasoning="Conflict.",
            )

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValidationError, match="confidence"):
            Opinion(
                source="technical",
                recommendation=Decision.BUY,
                reasoning="Ok.",
                confidence=1.5,
            )


class TestMemberVote:
    """Tests for MemberVote consistency checks."""

    def test_valid_vote(self) -> None:
        opinion = _opinion()
        vote = MemberVote(
            source="technical",
            recommendation=Decision.BUY,
            opinion=opinion,
        )
        assert vote.source == "technical"

    def test_mismatched_source_raises(self) -> None:
        opinion = _opinion(source="technical")
        with pytest.raises(ValidationError, match="source"):
            MemberVote(
                source="fundamental",
                recommendation=Decision.BUY,
                opinion=opinion,
            )

    def test_mismatched_recommendation_raises(self) -> None:
        opinion = _opinion(recommendation=Decision.BUY)
        with pytest.raises(ValidationError, match="recommendation"):
            MemberVote(
                source="technical",
                recommendation=Decision.SELL,
                opinion=opinion,
            )


class TestInvestmentDecision:
    """Tests for InvestmentDecision validation."""

    def test_accepts_neutral(self, instrument: Instrument) -> None:
        decision = InvestmentDecision(
            instrument=instrument,
            decision=Decision.NEUTRAL,
            rationale="Conflict.",
            decided_at=FIXED_NOW,
        )
        assert decision.decision is Decision.NEUTRAL

    def test_empty_rationale_raises(self, instrument: Instrument) -> None:
        with pytest.raises(ValidationError, match="rationale"):
            InvestmentDecision(
                instrument=instrument,
                decision=Decision.HOLD,
                rationale="  ",
                decided_at=FIXED_NOW,
            )


class TestCommitteeReport:
    """Tests for CommitteeReport validation and properties."""

    def test_properties(self, instrument: Instrument) -> None:
        opinion = _opinion()
        vote = MemberVote(
            source="technical",
            recommendation=Decision.BUY,
            opinion=opinion,
        )
        decision = InvestmentDecision(
            instrument=instrument,
            decision=Decision.BUY,
            rationale="Agree.",
            decided_at=FIXED_NOW,
        )
        report = CommitteeReport(
            instrument=instrument,
            opinions=(opinion,),
            votes=(vote,),
            decision=decision,
            voting_summary="votes=1 buy=1 hold=0 sell=0 → buy",
            explanation="Explanation text.",
        )
        assert report.members_participated == ("technical",)
        assert report.evidence_used == ()

    def test_empty_opinions_raises(self, instrument: Instrument) -> None:
        decision = InvestmentDecision(
            instrument=instrument,
            decision=Decision.HOLD,
            rationale="None.",
            decided_at=FIXED_NOW,
        )
        with pytest.raises(ValidationError, match="opinions"):
            CommitteeReport(
                instrument=instrument,
                opinions=(),
                votes=(),
                decision=decision,
                voting_summary="none",
                explanation="Explanation.",
            )

    def test_length_mismatch_raises(self, instrument: Instrument) -> None:
        opinion = _opinion()
        vote = MemberVote(
            source="technical",
            recommendation=Decision.BUY,
            opinion=opinion,
        )
        decision = InvestmentDecision(
            instrument=instrument,
            decision=Decision.BUY,
            rationale="Agree.",
            decided_at=FIXED_NOW,
        )
        with pytest.raises(ValidationError, match="same length"):
            CommitteeReport(
                instrument=instrument,
                opinions=(opinion, opinion),
                votes=(vote,),
                decision=decision,
                voting_summary="bad",
                explanation="Explanation.",
            )

    def test_instrument_mismatch_raises(self, instrument: Instrument) -> None:
        other = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        opinion = _opinion()
        vote = MemberVote(
            source="technical",
            recommendation=Decision.BUY,
            opinion=opinion,
        )
        decision = InvestmentDecision(
            instrument=other,
            decision=Decision.BUY,
            rationale="Agree.",
            decided_at=FIXED_NOW,
        )
        with pytest.raises(ValidationError, match="instrument"):
            CommitteeReport(
                instrument=instrument,
                opinions=(opinion,),
                votes=(vote,),
                decision=decision,
                voting_summary="votes=1 buy=1 hold=0 sell=0 → buy",
                explanation="Explanation.",
            )

    def test_empty_vote_source_raises(self) -> None:
        opinion = _opinion()
        with pytest.raises(ValidationError, match="source"):
            MemberVote(
                source="   ",
                recommendation=Decision.BUY,
                opinion=opinion,
            )

    def test_empty_voting_summary_raises(self, instrument: Instrument) -> None:
        opinion = _opinion()
        vote = MemberVote(
            source="technical",
            recommendation=Decision.BUY,
            opinion=opinion,
        )
        decision = InvestmentDecision(
            instrument=instrument,
            decision=Decision.BUY,
            rationale="Agree.",
            decided_at=FIXED_NOW,
        )
        with pytest.raises(ValidationError, match="voting_summary"):
            CommitteeReport(
                instrument=instrument,
                opinions=(opinion,),
                votes=(vote,),
                decision=decision,
                voting_summary="   ",
                explanation="Explanation.",
            )

    def test_empty_explanation_raises(self, instrument: Instrument) -> None:
        opinion = _opinion()
        vote = MemberVote(
            source="technical",
            recommendation=Decision.BUY,
            opinion=opinion,
        )
        decision = InvestmentDecision(
            instrument=instrument,
            decision=Decision.BUY,
            rationale="Agree.",
            decided_at=FIXED_NOW,
        )
        with pytest.raises(ValidationError, match="explanation"):
            CommitteeReport(
                instrument=instrument,
                opinions=(opinion,),
                votes=(vote,),
                decision=decision,
                voting_summary="votes=1 buy=1 hold=0 sell=0 → buy",
                explanation="   ",
            )
