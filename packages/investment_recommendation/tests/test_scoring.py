"""Scoring framework tests for Investment Recommendation."""

from __future__ import annotations

import pytest

from investment_recommendation import (
    DEFAULT_DECISION_WEIGHTS,
    DecisionWeights,
    InvestmentRecommendationAction,
    InvestmentRecommendationValidationError,
    action_from_score,
    validate_weights,
)
from investment_recommendation.scoring import clip_score, mos_to_valuation_score, weighted_mean


def test_default_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_DECISION_WEIGHTS.as_dict().values()) - 1.0) < 1e-9


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, InvestmentRecommendationAction.UNAVAILABLE),
        (10.0, InvestmentRecommendationAction.STRONG_SELL),
        (24.9, InvestmentRecommendationAction.STRONG_SELL),
        (25.0, InvestmentRecommendationAction.SELL),
        (39.9, InvestmentRecommendationAction.SELL),
        (40.0, InvestmentRecommendationAction.REDUCE),
        (49.9, InvestmentRecommendationAction.REDUCE),
        (50.0, InvestmentRecommendationAction.HOLD),
        (64.9, InvestmentRecommendationAction.HOLD),
        (65.0, InvestmentRecommendationAction.ACCUMULATE),
        (74.9, InvestmentRecommendationAction.ACCUMULATE),
        (75.0, InvestmentRecommendationAction.BUY),
        (84.9, InvestmentRecommendationAction.BUY),
        (85.0, InvestmentRecommendationAction.STRONG_BUY),
        (100.0, InvestmentRecommendationAction.STRONG_BUY),
    ],
)
def test_action_boundaries(
    score: float | None, expected: InvestmentRecommendationAction
) -> None:
    assert action_from_score(score) is expected


def test_mos_mapping_and_weights() -> None:
    assert mos_to_valuation_score(None) is None
    assert mos_to_valuation_score(0.0) == pytest.approx(50.0)
    assert mos_to_valuation_score(0.40) == pytest.approx(90.0)
    assert weighted_mean([]) is None
    assert clip_score(120) == 100.0
    with pytest.raises(InvestmentRecommendationValidationError, match="sum"):
        validate_weights(
            DecisionWeights(
                business_quality=1.0,
                valuation_mos=1.0,
                economic_moat=0.0,
                management_quality=0.0,
                financial_strength=0.0,
                earnings_quality=0.0,
                growth_quality=0.0,
            )
        )
