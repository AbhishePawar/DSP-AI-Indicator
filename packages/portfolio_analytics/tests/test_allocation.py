"""Tests for portfolio_analytics.allocation."""

from __future__ import annotations

import pytest

from portfolio_analytics.allocation import (
    compute_country_allocation,
    compute_sector_allocation,
)
from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.models import PositionInput


class TestSectorAllocation:
    def test_groups_by_declared_sector(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.6, sector="Technology"),
            PositionInput(symbol="BBB", weight=0.4, sector="Energy"),
        ]
        breakdown = compute_sector_allocation(positions)
        assert breakdown.status == AnalyticsStatus.COMPLETE
        by_label = {b.label: b.weight for b in breakdown.buckets}
        assert by_label["Technology"] == pytest.approx(0.6)
        assert by_label["Energy"] == pytest.approx(0.4)
        assert breakdown.unclassified_weight == 0.0

    def test_unclassified_when_sector_missing(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0)]
        breakdown = compute_sector_allocation(positions)
        assert breakdown.status == AnalyticsStatus.UNAVAILABLE
        assert breakdown.unclassified_weight == pytest.approx(1.0)

    def test_partial_when_mixed(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.5, sector="Technology"),
            PositionInput(symbol="BBB", weight=0.5),
        ]
        breakdown = compute_sector_allocation(positions)
        assert breakdown.status == AnalyticsStatus.PARTIAL


class TestCountryAllocation:
    def test_uses_declared_country_first(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=1.0, country="India", exchange="NASDAQ"),
        ]
        breakdown = compute_country_allocation(positions)
        assert breakdown.buckets[0].label == "India"

    def test_falls_back_to_exchange_lookup(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0, exchange="NSE")]
        breakdown = compute_country_allocation(positions)
        assert breakdown.buckets[0].label == "India"

    def test_unknown_exchange_is_unclassified(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0, exchange="UNKNOWNX")]
        breakdown = compute_country_allocation(positions)
        assert breakdown.buckets == ()
        assert breakdown.unclassified_weight == pytest.approx(1.0)
        assert breakdown.status == AnalyticsStatus.UNAVAILABLE
