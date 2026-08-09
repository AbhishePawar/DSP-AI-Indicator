"""Phase 2 — recommendation fail-closed integrity (MoS / weight renormalization).

Proves that missing MoS cannot renormalize into Buy/Hold/Sell from quality alone.
"""

from __future__ import annotations

import pytest

from investment_recommendation import (
    InvestmentRecommendationAction,
    InvestmentRecommendationEngine,
    ValuationSignals,
)
from investment_recommendation.models import MarginOfSafetyAssessment
from investment_recommendation.rules import apply_decision_rules


_DIRECTIONAL = {
    InvestmentRecommendationAction.STRONG_BUY,
    InvestmentRecommendationAction.BUY,
    InvestmentRecommendationAction.ACCUMULATE,
    InvestmentRecommendationAction.HOLD,
    InvestmentRecommendationAction.REDUCE,
    InvestmentRecommendationAction.SELL,
    InvestmentRecommendationAction.STRONG_SELL,
}


def _analyze(domain_bundle, **signals_kw):
    return InvestmentRecommendationEngine().analyze(
        valuation=ValuationSignals(**signals_kw),
        **domain_bundle,
    )


# --- A: happy path ---


def test_A_strong_quality_valid_iv_price_mos_directional(
    domain_bundle,
) -> None:
    result = _analyze(
        domain_bundle,
        intrinsic_value_per_share=100.0,
        current_market_price=70.0,
        confidence=0.7,
    )
    assert result.margin_of_safety.classification != "unavailable"
    assert result.margin_of_safety.margin_of_safety is not None
    assert result.recommendation in _DIRECTIONAL
    assert result.score.value is not None
    assert result.confidence.value > 0.0


# --- B / C / D / I: MoS unavailable → UNAVAILABLE ---


@pytest.mark.parametrize(
    "label,iv,price",
    [
        ("B_iv_unavailable", None, 70.0),
        ("C_price_unavailable", 100.0, None),
        ("D_mos_via_zero_iv", 0.0, 70.0),
        ("D_mos_via_negative_iv", -10.0, 70.0),
        ("I_missing_price_excellent_rest", 100.0, None),
    ],
)
def test_mos_unavailable_never_directional_action(
    domain_bundle, label: str, iv: float | None, price: float | None
) -> None:
    result = _analyze(
        domain_bundle,
        intrinsic_value_per_share=iv,
        current_market_price=price,
        confidence=0.7,
    )
    assert result.margin_of_safety.classification == "unavailable", label
    assert result.margin_of_safety.margin_of_safety is None, label
    assert result.recommendation is InvestmentRecommendationAction.UNAVAILABLE, label
    assert result.score.value is None, label
    assert result.score.status == "insufficient_data", label
    assert result.confidence.value == 0.0, label
    assert result.confidence.basis == "margin_of_safety_unavailable", label
    assert any(
        r.rule_id == "margin_of_safety_unavailable" for r in result.triggered_rules
    ), label
    assert result.recommendation not in _DIRECTIONAL, label


def test_weight_renormalization_cannot_buy_without_mos(domain_bundle) -> None:
    """Regression: quality-only weighted_mean previously produced BUY."""
    result = _analyze(
        domain_bundle,
        intrinsic_value_per_share=None,
        current_market_price=70.0,
        confidence=0.9,
    )
    assert result.recommendation is InvestmentRecommendationAction.UNAVAILABLE
    assert result.recommendation is not InvestmentRecommendationAction.BUY
    assert result.recommendation is not InvestmentRecommendationAction.HOLD
    assert result.recommendation is not InvestmentRecommendationAction.STRONG_BUY


def test_apply_decision_rules_mos_none_forces_unavailable() -> None:
    mos = MarginOfSafetyAssessment(
        intrinsic_value_per_share=None,
        current_market_price=70.0,
        margin_of_safety=None,
        premium_discount=None,
        valuation_score=None,
        valuation_confidence=0.0,
        classification="unavailable",
        reasoning="test",
    )
    result = apply_decision_rules(
        raw_score=90.0,
        quality=90.0,
        moat=90.0,
        management=90.0,
        strength=90.0,
        earnings=90.0,
        growth=90.0,
        mos=mos,
    )
    assert result.adjusted_score is None
    assert result.action_cap is InvestmentRecommendationAction.UNAVAILABLE
    assert any(r.rule_id == "margin_of_safety_unavailable" for r in result.rules)


# --- E: strong Buffett quality + valuation unavailable ---


def test_E_strong_quality_valuation_unavailable(domain_bundle) -> None:
    result = _analyze(
        domain_bundle,
        intrinsic_value_per_share=None,
        current_market_price=None,
        confidence=0.0,
    )
    assert result.recommendation is InvestmentRecommendationAction.UNAVAILABLE
    assert result.margin_of_safety.classification == "unavailable"


# --- F: poor quality + extremely cheap ---


def test_F_poor_quality_cheap_caps_below_buy(domain_bundle) -> None:
    """Cheap + weak quality → value-trap rule; never Strong Buy."""
    # Use weak domain scores by applying rules path already covered; engine-level
    # uses real domain scores from fixtures (not artificially poor). Document
    # rule-level behaviour via apply_decision_rules (existing) and assert
    # excellent-undervalued path requires BOTH quality and MoS.
    result = apply_decision_rules(
        raw_score=70.0,
        quality=30.0,
        moat=30.0,
        management=30.0,
        strength=30.0,
        earnings=30.0,
        growth=30.0,
        mos=MarginOfSafetyAssessment(
            intrinsic_value_per_share=100.0,
            current_market_price=50.0,
            margin_of_safety=0.50,
            premium_discount=-0.50,
            valuation_score=90.0,
            valuation_confidence=0.7,
            classification="deep_value",
            reasoning="test",
        ),
    )
    assert any(r.rule_id == "weak_business_cheap" for r in result.rules)
    assert result.action_cap is InvestmentRecommendationAction.REDUCE


# --- G: excellent quality + extreme overvaluation ---


def test_G_excellent_quality_extreme_overvaluation_not_buy(
    domain_bundle,
) -> None:
    result = _analyze(
        domain_bundle,
        intrinsic_value_per_share=100.0,
        current_market_price=220.0,
        confidence=0.7,
    )
    assert result.margin_of_safety.margin_of_safety is not None
    assert result.margin_of_safety.margin_of_safety < 0
    assert result.recommendation is not InvestmentRecommendationAction.BUY
    assert result.recommendation is not InvestmentRecommendationAction.STRONG_BUY
    assert result.recommendation is not InvestmentRecommendationAction.UNAVAILABLE
    assert any(
        r.rule_id == "materially_above_intrinsic_value"
        for r in result.triggered_rules
    )


# --- H / J: insufficient inputs → validation fail (engine refuses) ---


def test_H_J_missing_core_domains_rejects_analysis(undervalued_signals) -> None:
    engine = InvestmentRecommendationEngine()
    with pytest.raises(Exception):
        engine.analyze(
            valuation=undervalued_signals,
            business_quality=None,  # type: ignore[arg-type]
            economic_moat=None,  # type: ignore[arg-type]
            management_quality=None,  # type: ignore[arg-type]
            financial_strength=None,  # type: ignore[arg-type]
            earnings_quality=None,  # type: ignore[arg-type]
            growth_quality=None,  # type: ignore[arg-type]
        )


# --- Quality ≠ automatic good investment (Buffett) ---


def test_quality_vs_valuation_high_quality_overpriced_not_buy(
    domain_bundle,
) -> None:
    result = _analyze(
        domain_bundle,
        intrinsic_value_per_share=100.0,
        current_market_price=160.0,
        confidence=0.8,
    )
    assert result.recommendation in {
        InvestmentRecommendationAction.HOLD,
        InvestmentRecommendationAction.REDUCE,
        InvestmentRecommendationAction.SELL,
        InvestmentRecommendationAction.STRONG_SELL,
        InvestmentRecommendationAction.ACCUMULATE,
    }
    assert result.recommendation not in {
        InvestmentRecommendationAction.BUY,
        InvestmentRecommendationAction.STRONG_BUY,
    }


def test_iv_le_zero_mos_unavailable_property() -> None:
    for iv in (0.0, -1.0):
        sig = ValuationSignals(
            intrinsic_value_per_share=iv, current_market_price=50.0
        )
        assert sig.margin_of_safety is None
        assert sig.premium_discount is None
