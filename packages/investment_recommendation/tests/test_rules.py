"""Decision rule and conflict tests."""

from __future__ import annotations

from investment_recommendation.models import MarginOfSafetyAssessment
from investment_recommendation.rules import apply_decision_rules, cap_action
from investment_recommendation.scoring import InvestmentRecommendationAction


def _mos(
    *,
    mos: float | None,
    premium: float | None = None,
    classification: str = "fairly_valued",
) -> MarginOfSafetyAssessment:
    return MarginOfSafetyAssessment(
        intrinsic_value_per_share=100.0,
        current_market_price=70.0 if mos and mos > 0 else 120.0,
        margin_of_safety=mos,
        premium_discount=premium if premium is not None else (
            None if mos is None else -mos
        ),
        valuation_score=50.0,
        valuation_confidence=0.7,
        classification=classification,
        reasoning="test",
    )


def test_material_premium_caps_at_hold() -> None:
    result = apply_decision_rules(
        raw_score=90.0,
        quality=85.0,
        moat=80.0,
        management=80.0,
        strength=80.0,
        earnings=80.0,
        growth=80.0,
        mos=_mos(mos=-0.30, premium=0.30, classification="extremely_overvalued"),
    )
    assert any(r.rule_id == "materially_above_intrinsic_value" for r in result.rules)
    assert result.action_cap is InvestmentRecommendationAction.HOLD
    capped = cap_action(InvestmentRecommendationAction.STRONG_BUY, result.action_cap)
    assert capped is InvestmentRecommendationAction.HOLD


def test_excellent_business_undervalued_boost() -> None:
    result = apply_decision_rules(
        raw_score=70.0,
        quality=85.0,
        moat=80.0,
        management=70.0,
        strength=70.0,
        earnings=70.0,
        growth=70.0,
        mos=_mos(mos=0.35, premium=-0.35, classification="deep_value"),
    )
    assert any(r.rule_id == "excellent_business_undervalued" for r in result.rules)
    assert result.adjusted_score is not None
    assert result.adjusted_score > 70.0


def test_weak_business_cheap_value_trap() -> None:
    result = apply_decision_rules(
        raw_score=60.0,
        quality=30.0,
        moat=30.0,
        management=30.0,
        strength=30.0,
        earnings=30.0,
        growth=30.0,
        mos=_mos(mos=0.25, premium=-0.25, classification="undervalued"),
    )
    assert any(r.rule_id == "weak_business_cheap" for r in result.rules)
    assert result.action_cap is InvestmentRecommendationAction.REDUCE


def test_strong_growth_weak_balance_sheet() -> None:
    result = apply_decision_rules(
        raw_score=65.0,
        quality=60.0,
        moat=60.0,
        management=60.0,
        strength=40.0,
        earnings=60.0,
        growth=80.0,
        mos=_mos(mos=0.10, classification="fairly_valued"),
    )
    assert any(
        r.rule_id == "strong_growth_weak_balance_sheet" for r in result.rules
    )


def test_wide_moat_poor_capital_allocation() -> None:
    result = apply_decision_rules(
        raw_score=65.0,
        quality=60.0,
        moat=80.0,
        management=40.0,
        strength=60.0,
        earnings=60.0,
        growth=60.0,
        mos=_mos(mos=0.10, classification="fairly_valued"),
    )
    assert any(
        r.rule_id == "wide_moat_poor_capital_allocation" for r in result.rules
    )
