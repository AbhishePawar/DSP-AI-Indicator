"""Scoring framework tests for Financial Strength."""

from __future__ import annotations

import pytest

from financial_strength import (
    DEFAULT_STRENGTH_WEIGHTS,
    FinancialStrengthRating,
    FinancialStrengthValidationError,
    FinancialStrengthWeights,
    strength_rating_from_score,
    validate_weights,
)
from financial_strength.scoring import clip_score, weighted_mean


def test_default_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_STRENGTH_WEIGHTS.as_dict().values()) - 1.0) < 1e-9


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, FinancialStrengthRating.VERY_WEAK),
        (10.0, FinancialStrengthRating.VERY_WEAK),
        (40.0, FinancialStrengthRating.WEAK),
        (54.9, FinancialStrengthRating.WEAK),
        (55.0, FinancialStrengthRating.AVERAGE),
        (69.9, FinancialStrengthRating.AVERAGE),
        (70.0, FinancialStrengthRating.STRONG),
        (84.9, FinancialStrengthRating.STRONG),
        (85.0, FinancialStrengthRating.EXCEPTIONAL),
        (100.0, FinancialStrengthRating.EXCEPTIONAL),
    ],
)
def test_rating_boundaries(
    score: float | None, expected: FinancialStrengthRating
) -> None:
    assert strength_rating_from_score(score) is expected


def test_weighted_mean_and_validate() -> None:
    assert weighted_mean([]) is None
    assert weighted_mean([(100.0, 1.0), (0.0, 1.0)]) == 50.0
    assert clip_score(-1) == 0.0
    with pytest.raises(FinancialStrengthValidationError, match="sum"):
        validate_weights(
            FinancialStrengthWeights(
                balance_sheet_strength=1.0,
                liquidity=1.0,
                cash_flow_quality=0.0,
                solvency=0.0,
                profitability_stability=0.0,
                financial_resilience=0.0,
            )
        )
