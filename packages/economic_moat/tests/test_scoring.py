"""Scoring framework tests for Economic Moat Intelligence."""

from __future__ import annotations

import pytest

from economic_moat import (
    DEFAULT_MOAT_WEIGHTS,
    EconomicMoatValidationError,
    MoatRating,
    MoatWeights,
    moat_rating_from_score,
    validate_weights,
)
from economic_moat.scoring import clip_score, weighted_mean


def test_default_weights_sum_to_one() -> None:
    total = sum(DEFAULT_MOAT_WEIGHTS.as_dict().values())
    assert abs(total - 1.0) < 1e-9


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (None, MoatRating.NO_MOAT),
        (10.0, MoatRating.NO_MOAT),
        (25.0, MoatRating.WEAK),
        (44.9, MoatRating.WEAK),
        (45.0, MoatRating.NARROW),
        (64.9, MoatRating.NARROW),
        (65.0, MoatRating.STRONG),
        (79.9, MoatRating.STRONG),
        (80.0, MoatRating.WIDE),
        (100.0, MoatRating.WIDE),
    ],
)
def test_moat_rating_boundaries(score: float | None, expected: MoatRating) -> None:
    assert moat_rating_from_score(score) is expected


def test_weighted_mean_and_clip() -> None:
    assert weighted_mean([]) is None
    assert weighted_mean([(50.0, 0.0)]) is None
    assert weighted_mean([(100.0, 1.0), (0.0, 1.0)]) == 50.0
    assert clip_score(120.0) == 100.0
    assert clip_score(-5.0) == 0.0


def test_validate_weights_rejects_bad_sums() -> None:
    with pytest.raises(EconomicMoatValidationError, match="sum"):
        validate_weights(
            MoatWeights(
                brand=0.5,
                network_effects=0.5,
                switching_costs=0.5,
                cost_advantage=0.0,
                intangible_assets=0.0,
                efficient_scale=0.0,
            )
        )
    assert validate_weights(None) == DEFAULT_MOAT_WEIGHTS
