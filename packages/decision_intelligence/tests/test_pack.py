"""Decision Pack aggregate tests."""

from __future__ import annotations

import pytest

from ai_committee import Decision
from contracts import Instrument
from core.exceptions import ValidationError
from decision_intelligence import (
    DecisionIntelligenceError,
    DecisionIntelligenceService,
    DecisionPack,
)

from .conftest import make_recommendation, make_report


class TestDecisionPack:
    def test_pack_contains_three_parts(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.HOLD),
        )
        recommendation = make_recommendation(report)
        pack = DecisionIntelligenceService().build_pack(report, recommendation)

        assert isinstance(pack, DecisionPack)
        assert pack.recommendation is recommendation
        assert pack.brief.action is recommendation.action
        assert pack.assurance.action is recommendation.action
        assert pack.brief.instrument == instrument
        assert pack.assurance.instrument == instrument

    def test_mismatched_instruments_rejected(self, instrument: Instrument) -> None:
        from contracts import AssetClass, Instrument as Inst

        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.BUY),
        )
        recommendation = make_recommendation(report)
        other = Inst(symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD")
        bad = type(recommendation)(
            instrument=other,
            action=recommendation.action,
            conviction=recommendation.conviction,
            rationale=recommendation.rationale,
            generated_at=recommendation.generated_at,
            supporting_evidence=recommendation.supporting_evidence,
            dissenting_views=recommendation.dissenting_views,
        )
        with pytest.raises(DecisionIntelligenceError, match="instrument"):
            DecisionIntelligenceService().build_pack(report, bad)

    def test_pack_validation_on_action_mismatch(
        self, instrument: Instrument
    ) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.BUY),
        )
        recommendation = make_recommendation(report)
        brief = DecisionIntelligenceService().build_brief(report, recommendation)
        assurance = DecisionIntelligenceService().build_assurance(
            report, recommendation
        )
        from contracts import RecommendationAction

        hold_report = make_report(
            instrument,
            decision=Decision.HOLD,
            member_decisions=(Decision.HOLD, Decision.HOLD, Decision.HOLD),
        )
        hold_rec = make_recommendation(hold_report)
        with pytest.raises(ValidationError):
            DecisionPack(
                recommendation=hold_rec,
                brief=brief,
                assurance=assurance,
            )
        assert brief.action is RecommendationAction.BUY

    def test_deterministic(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL, Decision.SELL, Decision.HOLD),
        )
        recommendation = make_recommendation(report)
        service = DecisionIntelligenceService()
        assert service.build_pack(report, recommendation) == service.build_pack(
            report, recommendation
        )
