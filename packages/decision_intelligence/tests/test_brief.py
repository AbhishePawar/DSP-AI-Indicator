"""Decision Brief tests."""

from __future__ import annotations

from ai_committee import Decision
from contracts import Instrument, RecommendationAction
from decision_intelligence import DecisionBrief, DecisionIntelligenceService

from .conftest import available_mos, make_recommendation, make_report


class TestDecisionBrief:
    def test_contains_required_sections(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.HOLD),
        )
        recommendation = make_recommendation(report)
        brief = DecisionIntelligenceService().build_brief(report, recommendation)

        assert isinstance(brief, DecisionBrief)
        assert brief.instrument == instrument
        assert brief.action is RecommendationAction.BUY
        assert brief.headline
        assert brief.executive_summary
        assert brief.attribution
        assert brief.key_assumptions
        assert brief.invalidators
        assert brief.monitoring_watchlist

    def test_attribution_roles(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.SELL),
        )
        recommendation = make_recommendation(report)
        brief = DecisionIntelligenceService().build_brief(report, recommendation)

        roles = {a.source: a.role for a in brief.attribution}
        assert roles["technical"] == "supporting"
        assert roles["fundamental"] == "supporting"
        assert roles["economic"] == "dissenting"

    def test_mos_assumption_when_available(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.BUY),
        )
        recommendation = make_recommendation(report, margin_of_safety=available_mos())
        brief = DecisionIntelligenceService().build_brief(report, recommendation)

        assert any("Margin of Safety" in a for a in brief.key_assumptions)
        assert any("Margin of Safety" in item for item in brief.monitoring_watchlist)

    def test_deterministic(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.HOLD,
            member_decisions=(Decision.BUY, Decision.SELL, Decision.HOLD),
        )
        recommendation = make_recommendation(report)
        service = DecisionIntelligenceService()
        first = service.build_brief(report, recommendation)
        second = service.build_brief(report, recommendation)
        assert first == second
