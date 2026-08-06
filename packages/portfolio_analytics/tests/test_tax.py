"""Tests for portfolio_analytics.tax — Tax Optimization."""

from __future__ import annotations

from datetime import date

import pytest

from portfolio_analytics.enums import AnalyticsStatus, TaxTerm
from portfolio_analytics.models import PositionInput
from portfolio_analytics.tax import compute_tax_report


class TestComputeTaxReport:
    def test_unavailable_lot_when_cost_basis_missing(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0)]
        report = compute_tax_report(
            positions, current_prices={"AAA": 150.0}, as_of=date(2024, 1, 1)
        )
        assert report.status == AnalyticsStatus.UNAVAILABLE
        assert report.lots[0].available is False
        assert "cost_basis_per_unit" in report.lots[0].reason_unavailable

    def test_computes_gain_loss_and_long_term(self) -> None:
        positions = [
            PositionInput(
                symbol="AAA",
                weight=1.0,
                cost_basis_per_unit=100.0,
                purchase_date=date(2022, 1, 1),
            )
        ]
        report = compute_tax_report(
            positions, current_prices={"AAA": 150.0}, as_of=date(2024, 1, 1)
        )
        lot = report.lots[0]
        assert lot.available is True
        assert lot.unrealized_gain_loss_per_unit == pytest.approx(50.0)
        assert lot.unrealized_gain_loss_pct == pytest.approx(0.5)
        assert lot.term == TaxTerm.LONG_TERM
        assert lot.harvesting_candidate is False
        assert report.status == AnalyticsStatus.COMPLETE

    def test_short_term_and_harvesting_candidate_on_loss(self) -> None:
        positions = [
            PositionInput(
                symbol="AAA",
                weight=1.0,
                cost_basis_per_unit=100.0,
                purchase_date=date(2023, 12, 1),
            )
        ]
        report = compute_tax_report(
            positions, current_prices={"AAA": 80.0}, as_of=date(2024, 1, 1)
        )
        lot = report.lots[0]
        assert lot.term == TaxTerm.SHORT_TERM
        assert lot.harvesting_candidate is True
        assert "AAA" in report.harvesting_candidates

    def test_partial_status_when_price_missing_for_one_symbol(self) -> None:
        positions = [
            PositionInput(
                symbol="AAA",
                weight=0.5,
                cost_basis_per_unit=100.0,
                purchase_date=date(2022, 1, 1),
            ),
            PositionInput(
                symbol="BBB",
                weight=0.5,
                cost_basis_per_unit=50.0,
                purchase_date=date(2022, 1, 1),
            ),
        ]
        report = compute_tax_report(
            positions, current_prices={"AAA": 110.0}, as_of=date(2024, 1, 1)
        )
        assert report.status == AnalyticsStatus.PARTIAL
