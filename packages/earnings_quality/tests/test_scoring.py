"""Scoring framework tests for Earnings Quality."""

from __future__ import annotations

import pytest

from earnings_quality import (
    DEFAULT_EARNINGS_WEIGHTS,
    EarningsQualityRating,
    EarningsQualityValidationError,
    EarningsQualityWeights,
    earnings_rating_from_score,
    validate_weights,
)
from earnings_quality.scoring import clip_score, weighted_mean


def test_default_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_EARNINGS_WEIGHTS.as_dict().values()) - 1.0) < 1e-9


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, EarningsQualityRating.VERY_POOR),
        (10.0, EarningsQualityRating.VERY_POOR),
        (40.0, EarningsQualityRating.POOR),
        (54.9, EarningsQualityRating.POOR),
        (55.0, EarningsQualityRating.AVERAGE),
        (69.9, EarningsQualityRating.AVERAGE),
        (70.0, EarningsQualityRating.GOOD),
        (84.9, EarningsQualityRating.GOOD),
        (85.0, EarningsQualityRating.EXCELLENT),
        (100.0, EarningsQualityRating.EXCELLENT),
    ],
)
def test_rating_boundaries(
    score: float | None, expected: EarningsQualityRating
) -> None:
    assert earnings_rating_from_score(score) is expected


def test_weighted_mean_and_validate() -> None:
    assert weighted_mean([]) is None
    assert weighted_mean([(100.0, 1.0), (0.0, 1.0)]) == 50.0
    assert clip_score(120) == 100.0
    with pytest.raises(EarningsQualityValidationError, match="sum"):
        validate_weights(
            EarningsQualityWeights(
                earnings_consistency=1.0,
                earnings_quality=1.0,
                margin_stability=0.0,
                earnings_predictability=0.0,
                accounting_quality=0.0,
                long_term_sustainability=0.0,
            )
        )
