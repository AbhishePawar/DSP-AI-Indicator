"""Tests for portfolio_analytics.factor_exposure."""

from __future__ import annotations

import pytest

from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.factor_exposure import compute_factor_exposures
from portfolio_analytics.models import PositionInput


class TestComputeFactorExposures:
    def test_unavailable_when_no_scores_supplied(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0)]
        profile = compute_factor_exposures(positions)
        assert profile.status == AnalyticsStatus.UNAVAILABLE
        assert all(f.exposure_value is None for f in profile.factors)

    def test_weighted_rollup_of_value_score(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.5, value_score=0.2),
            PositionInput(symbol="BBB", weight=0.5, value_score=0.4),
        ]
        profile = compute_factor_exposures(positions)
        value_factor = next(f for f in profile.factors if f.factor_name == "value")
        assert value_factor.exposure_value == pytest.approx(0.3)
        assert value_factor.contributing_positions == 2

    def test_partial_status_when_some_factors_missing(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0, value_score=0.3)]
        profile = compute_factor_exposures(positions)
        assert profile.status == AnalyticsStatus.PARTIAL
        assert profile.limitations

    def test_excludes_positions_without_score_from_average(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.5, momentum_score=0.1),
            PositionInput(symbol="BBB", weight=0.5, momentum_score=None),
        ]
        profile = compute_factor_exposures(positions)
        momentum = next(f for f in profile.factors if f.factor_name == "momentum")
        assert momentum.exposure_value == pytest.approx(0.1)
        assert momentum.contributing_positions == 1
        assert momentum.total_positions == 2
