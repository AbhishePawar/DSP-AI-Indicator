"""Scoring framework tests for Management Quality."""

from __future__ import annotations

import pytest

from management_quality import (
    DEFAULT_MANAGEMENT_WEIGHTS,
    ManagementQualityValidationError,
    ManagementRating,
    ManagementWeights,
    management_rating_from_score,
    validate_weights,
)
from management_quality.scoring import clip_score, weighted_mean


def test_default_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_MANAGEMENT_WEIGHTS.as_dict().values()) - 1.0) < 1e-9


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, ManagementRating.POOR),
        (10.0, ManagementRating.POOR),
        (40.0, ManagementRating.BELOW_AVERAGE),
        (54.9, ManagementRating.BELOW_AVERAGE),
        (55.0, ManagementRating.AVERAGE),
        (69.9, ManagementRating.AVERAGE),
        (70.0, ManagementRating.GOOD),
        (84.9, ManagementRating.GOOD),
        (85.0, ManagementRating.EXCELLENT),
        (100.0, ManagementRating.EXCELLENT),
    ],
)
def test_rating_boundaries(score: float | None, expected: ManagementRating) -> None:
    assert management_rating_from_score(score) is expected


def test_weighted_mean_and_validate_weights() -> None:
    assert weighted_mean([]) is None
    assert weighted_mean([(100.0, 1.0), (0.0, 1.0)]) == 50.0
    assert clip_score(120) == 100.0
    with pytest.raises(ManagementQualityValidationError, match="sum"):
        validate_weights(
            ManagementWeights(
                capital_allocation=1.0,
                shareholder_orientation=1.0,
                governance=0.0,
                financial_discipline=0.0,
                execution_quality=0.0,
                integrity_transparency=0.0,
            )
        )
