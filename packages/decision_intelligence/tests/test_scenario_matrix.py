"""B3 decision-quality scenario matrix.

Semantic assertions only — not fragile prose.
"""

from __future__ import annotations

import pytest

from ai_committee import Decision
from contracts import Instrument, RecommendationAction
from decision_intelligence import (
    AssuranceLevel,
    GuidanceStance,
)

from .conftest import available_mos, build_pack, unavailable_mos


class TestScenarioMatrix:
    def test_01_strong_buy_consensus(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 4,
            mos=available_mos(),
            with_valuation_summary=True,
        )
        assert pack.recommendation.action is RecommendationAction.BUY
        assert pack.assurance.assurance_level is AssuranceLevel.HIGH
        assert (
            pack.assurance.investor_guidance.stance
            is GuidanceStance.INVEST_IMMEDIATELY
        )
        assert pack.assurance.key_strengths
        assert pack.brief.invalidators
        assert pack.brief.monitoring_watchlist

    def test_02_strong_sell_consensus(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL,) * 4,
            mos=unavailable_mos(),
        )
        assert pack.recommendation.action is RecommendationAction.SELL
        assert pack.assurance.assurance_level in {
            AssuranceLevel.MODERATE,
            AssuranceLevel.GUARDED,
            AssuranceLevel.LOW,
        }
        assert (
            pack.assurance.investor_guidance.stance
            is GuidanceStance.WAIT_FOR_CONFIRMATION
        )
        assert "accumulat" not in pack.assurance.investor_guidance.rationale.lower()

    def test_03_hold_consensus(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.HOLD,
            member_decisions=(Decision.HOLD,) * 3,
            sources=("technical", "fundamental", "economic"),
        )
        assert pack.recommendation.action is RecommendationAction.HOLD
        assert (
            pack.assurance.investor_guidance.stance is GuidanceStance.STAND_ASIDE
        )
        assert "buy" not in pack.assurance.investor_guidance.rationale.lower()

    def test_04_technical_bullish_fundamental_bearish(
        self, instrument: Instrument
    ) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.NEUTRAL,
            member_decisions=(Decision.BUY, Decision.SELL, Decision.HOLD),
            sources=("technical", "fundamental", "economic"),
        )
        assert pack.recommendation.action is RecommendationAction.HOLD
        assert pack.assurance.assurance_level is AssuranceLevel.LOW
        assert (
            pack.assurance.investor_guidance.stance is GuidanceStance.STAND_ASIDE
        )

    def test_05_fundamentals_strong_valuation_expensive(
        self, instrument: Instrument
    ) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.HOLD,
                Decision.BUY,
                Decision.HOLD,
                Decision.SELL,
            ),
            mos=available_mos(ratio=-0.15),
            with_valuation_summary=True,
        )
        assert pack.recommendation.action is RecommendationAction.BUY
        assert any(
            a.source == "valuation" and a.role == "dissenting"
            for a in pack.brief.attribution
        )
        assert pack.assurance.assurance_level in {
            AssuranceLevel.GUARDED,
            AssuranceLevel.LOW,
            AssuranceLevel.MODERATE,
        }
        assert (
            pack.assurance.investor_guidance.stance
            is not GuidanceStance.INVEST_IMMEDIATELY
        )

    def test_06_fundamentals_weak_valuation_apparently_cheap(
        self, instrument: Instrument
    ) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.HOLD,
                Decision.SELL,
                Decision.HOLD,
                Decision.BUY,
            ),
            mos=available_mos(ratio=0.35),
            with_valuation_summary=True,
        )
        assert pack.recommendation.action is RecommendationAction.BUY
        assert any(
            a.source == "fundamental" and a.role == "dissenting"
            for a in pack.brief.attribution
        )
        assert pack.assurance.assurance_level is not AssuranceLevel.HIGH
        assert (
            pack.assurance.investor_guidance.stance
            is not GuidanceStance.INVEST_IMMEDIATELY
        )

    def test_07_macro_disagreement(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.SELL),
            sources=("technical", "fundamental", "economic"),
        )
        assert any(
            a.source == "economic" and a.role == "dissenting"
            for a in pack.brief.attribution
        )
        assert pack.assurance.key_fragilities
        joined = " ".join(
            pack.brief.monitoring_watchlist + pack.brief.invalidators
        ).lower()
        assert "macro" in joined or "economic" in joined or "dissent" in joined

    def test_08_high_mos_weak_evidence(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.HOLD,
                Decision.HOLD,
                Decision.HOLD,
                Decision.BUY,
            ),
            mos=available_mos(ratio=0.40),
            with_valuation_summary=True,
        )
        assert pack.recommendation.margin_of_safety is not None
        assert pack.recommendation.margin_of_safety.available is True
        assert pack.assurance.single_engine_dependence is True
        assert pack.assurance.assurance_level in {
            AssuranceLevel.GUARDED,
            AssuranceLevel.LOW,
        }
        assert (
            pack.assurance.investor_guidance.stance
            is not GuidanceStance.INVEST_IMMEDIATELY
        )

    def test_09_low_mos_strong_fundamentals(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.BUY,
                Decision.BUY,
                Decision.BUY,
                Decision.SELL,
            ),
            mos=available_mos(ratio=-0.20),
            with_valuation_summary=True,
        )
        assert pack.recommendation.action is RecommendationAction.BUY
        assert any(
            a.source == "valuation" and a.role == "dissenting"
            for a in pack.brief.attribution
        )
        assert (
            pack.assurance.investor_guidance.stance
            is not GuidanceStance.INVEST_IMMEDIATELY
        )

    def test_10_missing_valuation_data(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.BUY),
            sources=("technical", "fundamental", "economic"),
        )
        assert pack.recommendation.margin_of_safety is None
        assert pack.recommendation.valuation_summary is None
        assert pack.brief.key_assumptions

    def test_11_missing_economic_data(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.BUY),
            sources=("technical", "fundamental", "valuation"),
            mos=available_mos(),
            with_valuation_summary=True,
        )
        assert all(a.source != "economic" for a in pack.brief.attribution)
        assert pack.recommendation.action is RecommendationAction.BUY

    def test_12_partial_member_set(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.HOLD),
            sources=("technical", "fundamental"),
        )
        assert len(pack.brief.attribution) == 2
        assert pack.assurance.assurance_level in {
            AssuranceLevel.GUARDED,
            AssuranceLevel.LOW,
            AssuranceLevel.MODERATE,
        }

    def test_13_strong_committee_disagreement(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.NEUTRAL,
            member_decisions=(
                Decision.BUY,
                Decision.SELL,
                Decision.BUY,
                Decision.SELL,
            ),
        )
        assert pack.recommendation.action is RecommendationAction.HOLD
        assert pack.assurance.assurance_level is AssuranceLevel.LOW
        assert (
            pack.assurance.investor_guidance.stance is GuidanceStance.STAND_ASIDE
        )

    def test_14_single_domain_dependence(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.HOLD, Decision.HOLD),
            sources=("technical", "fundamental", "economic"),
        )
        assert pack.assurance.single_engine_dependence is True
        assert pack.assurance.dominant_supporting_source == "technical"
        assert pack.assurance.investor_guidance.stance in {
            GuidanceStance.WAIT_FOR_CONFIRMATION,
            GuidanceStance.STAND_ASIDE,
            GuidanceStance.WATCH_VALUATION,
        }

    def test_15_conflicting_evidence_high_vote_agreement(
        self, instrument: Instrument
    ) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY),
            sources=("technical", "fundamental"),
        )
        assert pack.recommendation.action is RecommendationAction.BUY
        assert pack.assurance.agreement_quality.value in {
            "unanimous",
            "strong_majority",
            "majority",
        }
        assert (
            pack.assurance.investor_guidance.stance
            is not GuidanceStance.INVEST_IMMEDIATELY
        )


@pytest.mark.parametrize(
    ("decision", "members", "sources"),
    [
        (
            Decision.BUY,
            (Decision.BUY,) * 4,
            ("technical", "fundamental", "economic", "valuation"),
        ),
        (
            Decision.SELL,
            (Decision.SELL,) * 3,
            ("technical", "fundamental", "economic"),
        ),
        (
            Decision.HOLD,
            (Decision.HOLD,) * 3,
            ("technical", "fundamental", "economic"),
        ),
    ],
)
def test_recommendation_echoed_exactly(
    instrument: Instrument,
    decision: Decision,
    members: tuple[Decision, ...],
    sources: tuple[str, ...],
) -> None:
    pack = build_pack(
        instrument,
        decision=decision,
        member_decisions=members,
        sources=sources,
    )
    assert pack.brief.action is pack.recommendation.action
    assert pack.assurance.action is pack.recommendation.action
    assert pack.brief.conviction == pack.recommendation.conviction
    assert pack.assurance.conviction == pack.recommendation.conviction
