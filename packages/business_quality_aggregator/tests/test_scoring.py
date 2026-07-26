"""Scoring framework tests for Business Quality Aggregator."""

from __future__ import annotations

import pytest

from business_quality_aggregator import (
    DEFAULT_AGGREGATOR_WEIGHTS,
    BusinessQualityAggregatorRating,
    BusinessQualityAggregatorValidationError,
    BusinessQualityAggregatorWeights,
    aggregator_rating_from_score,
    validate_weights,
)
from business_quality_aggregator.scoring import clip_score, weighted_mean


def test_default_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_AGGREGATOR_WEIGHTS.as_dict().values()) - 1.0) < 1e-9
    assert DEFAULT_AGGREGATOR_WEIGHTS.economic_moat == pytest.approx(0.25)
    assert DEFAULT_AGGREGATOR_WEIGHTS.growth_quality == pytest.approx(0.15)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, BusinessQualityAggregatorRating.POOR),
        (10.0, BusinessQualityAggregatorRating.POOR),
        (39.9, BusinessQualityAggregatorRating.POOR),
        (40.0, BusinessQualityAggregatorRating.BELOW_AVERAGE),
        (54.9, BusinessQualityAggregatorRating.BELOW_AVERAGE),
        (55.0, BusinessQualityAggregatorRating.AVERAGE),
        (69.9, BusinessQualityAggregatorRating.AVERAGE),
        (70.0, BusinessQualityAggregatorRating.GOOD),
        (79.9, BusinessQualityAggregatorRating.GOOD),
        (80.0, BusinessQualityAggregatorRating.EXCELLENT),
        (89.9, BusinessQualityAggregatorRating.EXCELLENT),
        (90.0, BusinessQualityAggregatorRating.EXCEPTIONAL),
        (100.0, BusinessQualityAggregatorRating.EXCEPTIONAL),
    ],
)
def test_rating_boundaries(
    score: float | None, expected: BusinessQualityAggregatorRating
) -> None:
    assert aggregator_rating_from_score(score) is expected


def test_weighted_mean_and_validate() -> None:
    assert weighted_mean([]) is None
    assert weighted_mean([(100.0, 0.25), (0.0, 0.75)]) == 25.0
    assert clip_score(120) == 100.0
    with pytest.raises(BusinessQualityAggregatorValidationError, match="sum"):
        validate_weights(
            BusinessQualityAggregatorWeights(
                economic_moat=1.0,
                management_quality=1.0,
                financial_strength=0.0,
                earnings_quality=0.0,
                growth_quality=0.0,
            )
        )
