"""Presentation view model tests."""

from __future__ import annotations

from ai_committee import Decision
from contracts import Instrument
from decision_intelligence import present_decision_pack

from .conftest import available_mos, build_pack


class TestPresentationView:
    def test_sections_present(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 4,
            mos=available_mos(),
            with_valuation_summary=True,
        )
        view = present_decision_pack(pack)
        assert view.symbol == "AAPL"
        assert view.decision.action is pack.recommendation.action
        assert view.robustness.level is pack.assurance.assurance_level
        assert view.valuation.mos_available is True
        assert view.valuation.intrinsic_mid == 100.0
        assert view.committee.supporting
        assert view.why.key_strengths
        assert view.caution.invalidators
        assert view.action.stance is pack.assurance.investor_guidance.stance
        assert view.watch.monitoring
        assert view.evidence.attached is False
        assert view.evidence.availability == "not_attached"

    def test_no_recalculation(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 4,
            mos=available_mos(ratio=0.25),
            with_valuation_summary=True,
        )
        view = present_decision_pack(pack)
        assert view.valuation.mos_ratio == pack.recommendation.margin_of_safety.ratio
        assert (
            view.valuation.intrinsic_mid
            == pack.recommendation.valuation_summary.intrinsic_mid
        )
