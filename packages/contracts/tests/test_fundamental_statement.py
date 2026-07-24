"""Tests for the FundamentalStatement domain contract."""

from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import StatementPeriodType
from contracts.exceptions import ContractValidationError


class TestFundamentalStatement:
    """Tests for FundamentalStatement construction and validation."""

    def test_valid_statement_defaults_none(self, instrument: Instrument) -> None:
        statement = FundamentalStatement(
            instrument=instrument,
            period_end=date(2025, 12, 31),
            period_type=StatementPeriodType.ANNUAL,
            fiscal_year=2025,
            currency="usd",
        )
        assert statement.currency == "USD"
        assert statement.revenue is None
        assert statement.extra_line_items == ()

    def test_line_items_are_stored_as_reported(self, instrument: Instrument) -> None:
        statement = FundamentalStatement(
            instrument=instrument,
            period_end=date(2025, 12, 31),
            period_type=StatementPeriodType.QUARTERLY,
            fiscal_year=2025,
            currency="USD",
            revenue=1_000_000.0,
            net_income=150_000.0,
            eps_diluted=1.23,
        )
        assert statement.revenue == 1_000_000.0
        assert statement.net_income == 150_000.0
        assert statement.eps_diluted == 1.23

    def test_extra_line_items_stored_as_tuple(self, instrument: Instrument) -> None:
        statement = FundamentalStatement(
            instrument=instrument,
            period_end=date(2025, 12, 31),
            period_type=StatementPeriodType.ANNUAL,
            fiscal_year=2025,
            currency="USD",
            extra_line_items=[("goodwill_impairment", 50_000.0)],
        )
        assert statement.extra_line_items == (("goodwill_impairment", 50_000.0),)

    def test_invalid_currency_raises(self, instrument: Instrument) -> None:
        with pytest.raises(ContractValidationError, match="ISO 4217"):
            FundamentalStatement(
                instrument=instrument,
                period_end=date(2025, 12, 31),
                period_type=StatementPeriodType.ANNUAL,
                fiscal_year=2025,
                currency="DOLLARS",
            )

    def test_implausible_fiscal_year_raises(self, instrument: Instrument) -> None:
        with pytest.raises(ContractValidationError, match="fiscal_year"):
            FundamentalStatement(
                instrument=instrument,
                period_end=date(2025, 12, 31),
                period_type=StatementPeriodType.ANNUAL,
                fiscal_year=27,
                currency="USD",
            )

    def test_ttm_period_type(self, instrument: Instrument) -> None:
        statement = FundamentalStatement(
            instrument=instrument,
            period_end=date(2025, 12, 31),
            period_type=StatementPeriodType.TRAILING_TWELVE_MONTHS,
            fiscal_year=2025,
            currency="USD",
        )
        assert statement.period_type is StatementPeriodType.TRAILING_TWELVE_MONTHS

    def test_immutable(self, instrument: Instrument) -> None:
        statement = FundamentalStatement(
            instrument=instrument,
            period_end=date(2025, 12, 31),
            period_type=StatementPeriodType.ANNUAL,
            fiscal_year=2025,
            currency="USD",
        )
        with pytest.raises(AttributeError):
            statement.revenue = 1.0  # type: ignore[misc]
