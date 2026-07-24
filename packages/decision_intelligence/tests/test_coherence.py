"""Coherence invariants for Decision Pack outputs.

These catch logically suspicious combinations without changing investment
policy silently — failures indicate a policy bug to fix explicitly.
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

_BUY = {RecommendationAction.BUY, RecommendationAction.STRONG_BUY}
_SELL = {RecommendationAction.SELL, RecommendationAction.STRONG_SELL}


def _packs(instrument: Instrument):
    return [
        build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 4,
            mos=available_mos(),
            with_valuation_summary=True,
        ),
        build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 4,
            mos=unavailable_mos(),
            with_valuation_summary=True,
        ),
        build_pack(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL, Decision.SELL, Decision.HOLD),
            sources=("technical", "fundamental", "economic"),
        ),
        build_pack(
            instrument,
            decision=Decision.HOLD,
            member_decisions=(Decision.HOLD,) * 3,
            sources=("technical", "fundamental", "economic"),
        ),
        build_pack(
            instrument,
            decision=Decision.NEUTRAL,
            member_decisions=(Decision.BUY, Decision.SELL, Decision.HOLD),
            sources=("technical", "fundamental", "economic"),
        ),
        build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.HOLD, Decision.HOLD),
            sources=("technical", "fundamental", "economic"),
        ),
        build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.HOLD,
                Decision.HOLD,
                Decision.HOLD,
                Decision.BUY,
            ),
            mos=available_mos(ratio=0.4),
            with_valuation_summary=True,
        ),
        build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.SELL),
            sources=("technical", "fundamental", "economic"),
        ),
    ]


class TestCoherenceInvariants:
    def test_no_buy_low_invest_immediately(self, instrument: Instrument) -> None:
        for pack in _packs(instrument):
            action = pack.recommendation.action
            level = pack.assurance.assurance_level
            stance = pack.assurance.investor_guidance.stance
            if action in _BUY and level is AssuranceLevel.LOW:
                assert stance is not GuidanceStance.INVEST_IMMEDIATELY

    def test_no_sell_accumulate(self, instrument: Instrument) -> None:
        for pack in _packs(instrument):
            if pack.recommendation.action in _SELL:
                assert (
                    pack.assurance.investor_guidance.stance
                    is not GuidanceStance.ACCUMULATE_GRADUALLY
                )
                assert (
                    "accumulat"
                    not in pack.assurance.investor_guidance.rationale.lower()
                )

    def test_hold_never_implies_buy(self, instrument: Instrument) -> None:
        for pack in _packs(instrument):
            if pack.recommendation.action is RecommendationAction.HOLD:
                assert (
                    pack.assurance.investor_guidance.stance
                    is GuidanceStance.STAND_ASIDE
                )
                rationale = pack.assurance.investor_guidance.rationale.lower()
                assert "invest immediately" not in rationale
                assert "accumulate" not in rationale

    def test_no_high_with_thin_evidence(self, instrument: Instrument) -> None:
        for pack in _packs(instrument):
            if pack.assurance.evidence_consistency.value == "thin":
                assert pack.assurance.assurance_level is not AssuranceLevel.HIGH

    def test_no_high_with_conflict_agreement(self, instrument: Instrument) -> None:
        for pack in _packs(instrument):
            if pack.assurance.agreement_quality.value == "conflict":
                assert pack.assurance.assurance_level is AssuranceLevel.LOW

    def test_valuation_buy_without_mos_not_invest_immediately(
        self, instrument: Instrument
    ) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 4,
            mos=unavailable_mos(),
            with_valuation_summary=True,
        )
        assert (
            pack.assurance.investor_guidance.stance
            is GuidanceStance.WAIT_FOR_CONFIRMATION
        )
        assert pack.assurance.assurance_level is not AssuranceLevel.HIGH

    def test_pack_internal_consistency(self, instrument: Instrument) -> None:
        for pack in _packs(instrument):
            assert pack.brief.action is pack.recommendation.action
            assert pack.assurance.action is pack.recommendation.action
            assert pack.brief.instrument == pack.recommendation.instrument
            assert pack.assurance.instrument == pack.recommendation.instrument

    def test_mos_not_recalculated(self, instrument: Instrument) -> None:
        mos = available_mos(ratio=0.33)
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 4,
            mos=mos,
            with_valuation_summary=True,
        )
        assert pack.recommendation.margin_of_safety is not None
        assert pack.recommendation.margin_of_safety.ratio == pytest.approx(0.33)
