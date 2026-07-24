"""Tests for RecommendationMapper."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_committee.enums import Decision
from ai_committee.models import (
    CommitteeReport,
    InvestmentDecision,
    MemberVote,
    Opinion,
)
from contracts.domain.evidence import Evidence
from contracts.domain.instrument import Instrument
from contracts.domain.recommendation import Recommendation
from contracts.enums import AssetClass, EngineSource, RecommendationAction
from recommendation import RecommendationMapper, RecommendationMappingError

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


def _evidence(claim: str) -> Evidence:
    return Evidence(
        source_engine=EngineSource.AI_COMMITTEE,
        claim=claim,
        value=1.0,
        reference="test",
        weight=0.5,
    )


def _opinion(
    source: str,
    recommendation: Decision,
    *,
    evidence: tuple[Evidence, ...] = (),
) -> Opinion:
    return Opinion(
        source=source,
        recommendation=recommendation,
        reasoning=f"{source} reasons for {recommendation.value}",
        evidence=evidence,
        engine=EngineSource.AI_COMMITTEE,
    )


def _report(
    instrument: Instrument,
    *,
    decision: Decision,
    member_decisions: tuple[Decision, ...],
) -> CommitteeReport:
    sources = ("technical", "fundamental", "economic")
    opinions: list[Opinion] = []
    votes: list[MemberVote] = []
    paired = list(zip(sources[: len(member_decisions)], member_decisions, strict=True))
    for source, member_decision in paired:
        opinion = _opinion(
            source,
            member_decision,
            evidence=(_evidence(f"{source} evidence"),),
        )
        opinions.append(opinion)
        votes.append(
            MemberVote(
                source=source,
                recommendation=member_decision,
                opinion=opinion,
            )
        )

    investment = InvestmentDecision(
        instrument=instrument,
        decision=decision,
        rationale=f"Committee decides {decision.value}.",
        decided_at=FIXED_NOW,
    )
    return CommitteeReport(
        instrument=instrument,
        opinions=tuple(opinions),
        votes=tuple(votes),
        decision=investment,
        voting_summary=f"votes={[d.value for d in member_decisions]}",
        explanation="Full deliberation narrative.",
    )


class TestPublicApi:
    def test_exports(self) -> None:
        assert RecommendationMapper is not None
        assert issubclass(RecommendationMappingError, Exception)


class TestActionMapping:
    def test_buy(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.HOLD),
        )
        result = RecommendationMapper.map(report)
        assert isinstance(result, Recommendation)
        assert result.action is RecommendationAction.BUY
        assert result.instrument == instrument
        assert result.generated_at == FIXED_NOW

    def test_sell(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL, Decision.SELL, Decision.HOLD),
        )
        assert RecommendationMapper.map(report).action is RecommendationAction.SELL

    def test_hold(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.HOLD,
            member_decisions=(Decision.HOLD, Decision.HOLD, Decision.BUY),
        )
        assert RecommendationMapper.map(report).action is RecommendationAction.HOLD

    def test_neutral_maps_to_hold(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.NEUTRAL,
            member_decisions=(Decision.BUY, Decision.SELL),
        )
        result = RecommendationMapper.map(report)
        assert result.action is RecommendationAction.HOLD
        assert result.conviction == pytest.approx(0.5)


class TestConviction:
    def test_unanimous_is_one(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.BUY),
        )
        assert RecommendationMapper.map(report).conviction == pytest.approx(1.0)

    def test_two_of_three_is_two_thirds(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.SELL),
        )
        assert RecommendationMapper.map(report).conviction == pytest.approx(2 / 3)


class TestEvidenceAndDissent:
    def test_supporting_evidence_from_agreeing_members(
        self, instrument: Instrument
    ) -> None:
        report = _report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.SELL),
        )
        result = RecommendationMapper.map(report)
        claims = {item.claim for item in result.supporting_evidence}
        assert "technical evidence" in claims
        assert "fundamental evidence" in claims
        assert "economic evidence" not in claims

    def test_dissenting_views_capture_minority(
        self, instrument: Instrument
    ) -> None:
        report = _report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.SELL),
        )
        result = RecommendationMapper.map(report)
        assert len(result.dissenting_views) == 1
        assert result.dissenting_views[0].startswith("economic: sell")

    def test_neutral_puts_all_opinions_in_dissent(
        self, instrument: Instrument
    ) -> None:
        report = _report(
            instrument,
            decision=Decision.NEUTRAL,
            member_decisions=(Decision.BUY, Decision.SELL),
        )
        result = RecommendationMapper.map(report)
        assert len(result.dissenting_views) == 2
        assert len(result.supporting_evidence) == 2


class TestRationaleAndDecisionMapper:
    def test_rationale_includes_voting_summary(
        self, instrument: Instrument
    ) -> None:
        report = _report(
            instrument,
            decision=Decision.HOLD,
            member_decisions=(Decision.HOLD, Decision.HOLD),
        )
        result = RecommendationMapper.map(report)
        assert "Committee decides hold" in result.rationale
        assert "votes=" in result.rationale

    def test_map_decision_standalone(self, instrument: Instrument) -> None:
        decision = InvestmentDecision(
            instrument=instrument,
            decision=Decision.SELL,
            rationale="Standalone sell.",
            decided_at=FIXED_NOW,
        )
        result = RecommendationMapper.map_decision(decision, conviction=0.8)
        assert result.action is RecommendationAction.SELL
        assert result.conviction == pytest.approx(0.8)
        assert result.supporting_evidence == ()
        assert result.dissenting_views == ()

    def test_deterministic(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.HOLD),
        )
        assert RecommendationMapper.map(report) == RecommendationMapper.map(report)

    def test_immutable_output(self, instrument: Instrument) -> None:
        report = _report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY),
        )
        result = RecommendationMapper.map(report)
        with pytest.raises(AttributeError):
            result.conviction = 0.1  # type: ignore[misc]

    def test_propagates_mos_from_valuation_opinion(
        self, instrument: Instrument
    ) -> None:
        from contracts.domain.margin_of_safety import MarginOfSafety
        from contracts.domain.valuation_summary import ValuationSummary
        from datetime import date

        mos = MarginOfSafety(
            ratio=0.30,
            intrinsic_value=1000.0,
            market_value=700.0,
            available=True,
        )
        summary = ValuationSummary(
            intrinsic_low=900.0,
            intrinsic_mid=1000.0,
            intrinsic_high=1100.0,
            margin_of_safety=mos,
            confidence="high",
            currency="USD",
            as_of=date(2023, 12, 31),
        )
        valuation_opinion = Opinion(
            source="valuation",
            recommendation=Decision.BUY,
            reasoning="Undervalued with MoS cushion.",
            evidence=(_evidence("mos evidence"),),
            engine=EngineSource.VALUATION_ENGINE,
            margin_of_safety=mos,
            valuation_summary=summary,
        )
        technical = _opinion("technical", Decision.BUY, evidence=(_evidence("t"),))
        report = CommitteeReport(
            instrument=instrument,
            opinions=(technical, valuation_opinion),
            votes=(
                MemberVote(
                    source="technical",
                    recommendation=Decision.BUY,
                    opinion=technical,
                ),
                MemberVote(
                    source="valuation",
                    recommendation=Decision.BUY,
                    opinion=valuation_opinion,
                ),
            ),
            decision=InvestmentDecision(
                instrument=instrument,
                decision=Decision.BUY,
                rationale="Buy.",
                decided_at=FIXED_NOW,
            ),
            voting_summary="unanimous BUY",
            explanation="Full deliberation.",
        )
        result = RecommendationMapper.map(report)
        assert result.margin_of_safety is mos
        assert result.valuation_summary is summary
        assert result.margin_of_safety.ratio == pytest.approx(0.30)
