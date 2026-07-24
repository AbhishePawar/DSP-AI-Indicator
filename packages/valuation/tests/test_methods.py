"""Unit tests for individual valuation methods."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import StatementPeriodType
from fundamental.models import FinancialSnapshot
from valuation.assumptions import ValuationAssumptions
from valuation.enums import ValuationMethod
from valuation.methods.book_value import BookValueMethod
from valuation.methods.dcf import DcfMethod
from valuation.methods.earnings_multiple import EarningsMultipleMethod
from valuation.methods.owner_earnings import OwnerEarningsMethod
from valuation.methods.residual_income import ResidualIncomeMethod


def _snap(
    instrument: Instrument,
    *,
    net_income: float | None = 100.0,
    total_equity: float | None = 500.0,
    operating_cash_flow: float | None = 180.0,
    capital_expenditures: float | None = 40.0,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        instrument=instrument,
        statements=(
            FundamentalStatement(
                instrument=instrument,
                period_end=date(2023, 12, 31),
                period_type=StatementPeriodType.ANNUAL,
                fiscal_year=2023,
                currency="USD",
                net_income=net_income,
                total_equity=total_equity,
                operating_cash_flow=operating_cash_flow,
                capital_expenditures=capital_expenditures,
            ),
        ),
    )


class TestBookValue:
    def test_computes(self, snapshot: FinancialSnapshot) -> None:
        result = BookValueMethod().estimate(snapshot, ValuationAssumptions())
        assert result.applicable is True
        assert result.method is ValuationMethod.BOOK_VALUE
        assert result.intrinsic_value == pytest.approx(500.0)

    def test_missing(self, empty_inputs_snapshot: FinancialSnapshot) -> None:
        result = BookValueMethod().estimate(
            empty_inputs_snapshot, ValuationAssumptions()
        )
        assert result.applicable is False
        assert result.intrinsic_value is None


class TestEarningsMultiple:
    def test_computes(self, snapshot: FinancialSnapshot) -> None:
        assumptions = ValuationAssumptions(earnings_multiple=10.0)
        result = EarningsMultipleMethod().estimate(snapshot, assumptions)
        assert result.applicable is True
        assert result.intrinsic_value == pytest.approx(1000.0)

    def test_missing(self, empty_inputs_snapshot: FinancialSnapshot) -> None:
        result = EarningsMultipleMethod().estimate(
            empty_inputs_snapshot, ValuationAssumptions()
        )
        assert result.applicable is False


class TestOwnerEarnings:
    def test_computes(self, snapshot: FinancialSnapshot) -> None:
        assumptions = ValuationAssumptions(owner_earnings_cap_rate=0.08)
        result = OwnerEarningsMethod().estimate(snapshot, assumptions)
        assert result.applicable is True
        assert result.intrinsic_value == pytest.approx(1750.0)

    def test_missing_capex(self, instrument: Instrument) -> None:
        result = OwnerEarningsMethod().estimate(
            _snap(instrument, capital_expenditures=None),
            ValuationAssumptions(),
        )
        assert result.applicable is False

    def test_non_positive_oe(self, instrument: Instrument) -> None:
        result = OwnerEarningsMethod().estimate(
            _snap(instrument, operating_cash_flow=10.0, capital_expenditures=50.0),
            ValuationAssumptions(),
        )
        assert result.applicable is False


class TestDcf:
    def test_computes_positive(self, snapshot: FinancialSnapshot) -> None:
        assumptions = ValuationAssumptions(
            discount_rate=0.10,
            fcf_growth_rate=0.0,
            terminal_growth_rate=0.0,
            projection_years=1,
        )
        result = DcfMethod().estimate(snapshot, assumptions)
        assert result.applicable is True
        assert result.intrinsic_value == pytest.approx(1400.0)

    def test_missing(self, empty_inputs_snapshot: FinancialSnapshot) -> None:
        result = DcfMethod().estimate(empty_inputs_snapshot, ValuationAssumptions())
        assert result.applicable is False


class TestResidualIncome:
    def test_computes(self, snapshot: FinancialSnapshot) -> None:
        assumptions = ValuationAssumptions(residual_income_required_return=0.10)
        result = ResidualIncomeMethod().estimate(snapshot, assumptions)
        assert result.applicable is True
        assert result.intrinsic_value == pytest.approx(1000.0)

    def test_missing(self, empty_inputs_snapshot: FinancialSnapshot) -> None:
        result = ResidualIncomeMethod().estimate(
            empty_inputs_snapshot, ValuationAssumptions()
        )
        assert result.applicable is False
