"""Decision Assurance deterministic rule tests."""

from __future__ import annotations

from ai_committee import Decision
from contracts import Instrument, RecommendationAction
from decision_intelligence import (
    AssuranceLevel,
    DecisionIntelligenceService,
    GuidanceStance,
)

from .conftest import available_mos, make_recommendation, make_report


class TestDecisionAssurance:
    def test_unanimous_buy_with_mos_is_high(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.BUY,
                Decision.BUY,
                Decision.BUY,
                Decision.BUY,
            ),
            sources=("technical", "fundamental", "economic", "valuation"),
        )
        recommendation = make_recommendation(report, margin_of_safety=available_mos())
        assurance = DecisionIntelligenceService().build_assurance(
            report, recommendation
        )

        assert assurance.assurance_level is AssuranceLevel.HIGH
        assert assurance.agreement_quality.value == "unanimous"
        assert (
            assurance.investor_guidance.stance
            is GuidanceStance.INVEST_IMMEDIATELY
        )

    def test_conflict_is_low_and_stand_aside(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.NEUTRAL,
            member_decisions=(Decision.BUY, Decision.SELL, Decision.HOLD),
        )
        recommendation = make_recommendation(report)
        assurance = DecisionIntelligenceService().build_assurance(
            report, recommendation
        )

        assert recommendation.action is RecommendationAction.HOLD
        assert assurance.assurance_level is AssuranceLevel.LOW
        assert (
            assurance.investor_guidance.stance is GuidanceStance.STAND_ASIDE
        )

    def test_single_engine_dependence_is_guarded(
        self, instrument: Instrument
    ) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.HOLD, Decision.HOLD),
        )
        recommendation = make_recommendation(report)
        assurance = DecisionIntelligenceService().build_assurance(
            report, recommendation
        )

        assert assurance.single_engine_dependence is True
        assert assurance.dominant_supporting_source == "technical"
        assert assurance.assurance_level in {
            AssuranceLevel.GUARDED,
            AssuranceLevel.LOW,
            AssuranceLevel.MODERATE,
        }
        assert assurance.agreement_quality.value in {
            "narrow",
            "conflict",
            "majority",
        }
        assert assurance.investor_guidance.stance in {
            GuidanceStance.WAIT_FOR_CONFIRMATION,
            GuidanceStance.WATCH_VALUATION,
            GuidanceStance.STAND_ASIDE,
        }

    def test_guidance_stances_are_closed_set(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL, Decision.SELL, Decision.HOLD),
        )
        recommendation = make_recommendation(report)
        assurance = DecisionIntelligenceService().build_assurance(
            report, recommendation
        )
        assert assurance.investor_guidance.stance in set(GuidanceStance)

    def test_deterministic(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.SELL),
        )
        recommendation = make_recommendation(report)
        service = DecisionIntelligenceService()
        assert service.build_assurance(
            report, recommendation
        ) == service.build_assurance(report, recommendation)

    def test_review_triggers_present(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.HOLD),
        )
        recommendation = make_recommendation(report, margin_of_safety=available_mos())
        assurance = DecisionIntelligenceService().build_assurance(
            report, recommendation
        )
        assert assurance.review_triggers
        assert assurance.confidence_drivers
        assert assurance.key_strengths
        assert assurance.key_fragilities
