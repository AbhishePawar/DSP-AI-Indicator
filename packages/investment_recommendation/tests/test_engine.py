"""Engine integration, determinism, and explainability tests."""

from __future__ import annotations

import pytest

from investment_recommendation import (
    DecisionComponent,
    InvestmentRecommendationAction,
    InvestmentRecommendationEngine,
    InvestmentRecommendationValidationError,
    ValuationSignals,
)


def test_analyze_produces_recommendation(domain_bundle, undervalued_signals) -> None:
    result = InvestmentRecommendationEngine().analyze(
        valuation=undervalued_signals, **domain_bundle
    )
    assert result.validation.ok is True
    assert result.score.value is not None
    assert 0.0 <= result.score.value <= 100.0
    assert result.recommendation in set(InvestmentRecommendationAction)
    assert len(result.contributions) == 7
    assert {c.component for c in result.contributions} == set(DecisionComponent)
    assert result.margin_of_safety is not None
    assert result.evidence
    assert result.investment_thesis and result.decision_summary
    assert result.explainability.decision_rules_triggered is not None
    assert result.explainability.engine_weights is not None
    payload = result.to_dict()
    assert payload["recommendation"] == result.recommendation.value


def test_analyze_is_deterministic(domain_bundle, undervalued_signals) -> None:
    engine = InvestmentRecommendationEngine()
    a = engine.analyze(valuation=undervalued_signals, **domain_bundle)
    b = engine.analyze(valuation=undervalued_signals, **domain_bundle)
    assert a.to_dict() == b.to_dict()


def test_overvalued_cannot_strong_buy(domain_bundle, overvalued_signals) -> None:
    result = InvestmentRecommendationEngine().analyze(
        valuation=overvalued_signals, **domain_bundle
    )
    assert result.recommendation != InvestmentRecommendationAction.STRONG_BUY
    assert result.recommendation in {
        InvestmentRecommendationAction.HOLD,
        InvestmentRecommendationAction.REDUCE,
        InvestmentRecommendationAction.SELL,
        InvestmentRecommendationAction.STRONG_SELL,
        InvestmentRecommendationAction.ACCUMULATE,
    }
    assert any(
        r.rule_id == "materially_above_intrinsic_value"
        for r in result.triggered_rules
    )


def test_explain_and_validate(domain_bundle, undervalued_signals) -> None:
    engine = InvestmentRecommendationEngine()
    analysis = engine.analyze(valuation=undervalued_signals, **domain_bundle)
    assert engine.explain(analysis) is analysis.explainability
    with pytest.raises(
        InvestmentRecommendationValidationError, match="InvestmentRecommendation"
    ):
        engine.explain(object())  # type: ignore[arg-type]
    assert engine.validate().ok is False


def test_valuation_signals_from_price() -> None:
    sig = ValuationSignals(
        intrinsic_value_per_share=100.0, current_market_price=80.0
    )
    assert sig.margin_of_safety == pytest.approx(0.20)
    assert sig.premium_discount == pytest.approx(-0.20)
