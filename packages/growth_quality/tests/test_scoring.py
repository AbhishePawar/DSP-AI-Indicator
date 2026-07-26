"""Scoring framework tests for Growth Quality."""

from __future__ import annotations

import pytest

from growth_quality import (
    DEFAULT_GROWTH_WEIGHTS,
    GrowthQualityRating,
    GrowthQualityValidationError,
    GrowthQualityWeights,
    growth_rating_from_score,
    validate_weights,
)
from growth_quality.scoring import clip_score, weighted_mean


def test_default_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_GROWTH_WEIGHTS.as_dict().values()) - 1.0) < 1e-9


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, GrowthQualityRating.VERY_WEAK),
        (10.0, GrowthQualityRating.VERY_WEAK),
        (39.9, GrowthQualityRating.VERY_WEAK),
        (40.0, GrowthQualityRating.WEAK),
        (54.9, GrowthQualityRating.WEAK),
        (55.0, GrowthQualityRating.MODERATE),
        (69.9, GrowthQualityRating.MODERATE),
        (70.0, GrowthQualityRating.STRONG),
        (84.9, GrowthQualityRating.STRONG),
        (85.0, GrowthQualityRating.EXCEPTIONAL),
        (100.0, GrowthQualityRating.EXCEPTIONAL),
    ],
)
def test_rating_boundaries(
    score: float | None, expected: GrowthQualityRating
) -> None:
    assert growth_rating_from_score(score) is expected


def test_weighted_mean_and_validate() -> None:
    assert weighted_mean([]) is None
    assert weighted_mean([(100.0, 1.0), (0.0, 1.0)]) == 50.0
    assert clip_score(120) == 100.0
    with pytest.raises(GrowthQualityValidationError, match="sum"):
        validate_weights(
            GrowthQualityWeights(
                revenue_growth_quality=1.0,
                earnings_growth_quality=1.0,
                reinvestment_capability=0.0,
                capital_allocation_support=0.0,
                growth_sustainability=0.0,
                growth_risk=0.0,
            )
        )
