"""Golden Decision Pack regression cases (semantic, not prose)."""

from __future__ import annotations

import pytest

from ai_committee import Decision
from contracts import Instrument, RecommendationAction
from decision_intelligence import AssuranceLevel, GuidanceStance

from .conftest import available_mos, build_pack, unavailable_mos


class TestGoldenDecisionPacks:
    def test_golden_robust_buy(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.BUY,
                Decision.BUY,
                Decision.BUY,
                Decision.HOLD,
            ),
            sources=("technical", "fundamental", "economic", "valuation"),
            mos=available_mos(ratio=0.25),
            with_valuation_summary=True,
        )
        assert pack.recommendation.action is RecommendationAction.BUY
        assert pack.assurance.assurance_level in {
            AssuranceLevel.HIGH,
            AssuranceLevel.MODERATE,
        }
        assert pack.assurance.investor_guidance.stance in {
            GuidanceStance.INVEST_IMMEDIATELY,
            GuidanceStance.ACCUMULATE_GRADUALLY,
        }
        assert pack.recommendation.margin_of_safety is not None
        assert pack.recommendation.margin_of_safety.available is True
        assert any(a.role == "neutral" for a in pack.brief.attribution)
        assert pack.brief.monitoring_watchlist

    def test_golden_fragile_valuation_buy(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(
                Decision.HOLD,
                Decision.HOLD,
                Decision.HOLD,
                Decision.BUY,
            ),
            mos=available_mos(ratio=0.30),
            with_valuation_summary=True,
        )
        assert pack.recommendation.action is RecommendationAction.BUY
        assert pack.assurance.single_engine_dependence is True
        assert pack.assurance.assurance_level in {
            AssuranceLevel.GUARDED,
            AssuranceLevel.LOW,
        }
        assert pack.assurance.investor_guidance.stance in {
            GuidanceStance.WATCH_VALUATION,
            GuidanceStance.WAIT_FOR_CONFIRMATION,
            GuidanceStance.STAND_ASIDE,
        }

    def test_golden_conflict_hold(self, instrument: Instrument) -> None:
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
        assert pack.recommendation.conviction == pytest.approx(0.5)

    def test_golden_sell_without_mos(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL,) * 4,
            mos=unavailable_mos(),
            with_valuation_summary=True,
        )
        assert pack.recommendation.action is RecommendationAction.SELL
        assert (
            pack.assurance.investor_guidance.stance
            is GuidanceStance.WAIT_FOR_CONFIRMATION
        )
        assert (
            pack.assurance.investor_guidance.stance
            is not GuidanceStance.ACCUMULATE_GRADUALLY
        )
