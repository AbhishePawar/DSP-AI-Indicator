"""Tests for DefaultFundamentalNormalizer and FundamentalStatementsBuilder."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from data_engine.builders import FundamentalStatementsBuilder
from data_engine.exceptions import InvalidProviderDataError, MissingFieldError
from data_engine.normalization import (
    DefaultFundamentalNormalizer,
    FundamentalNormalizer,
)
from data_engine.raw_models import RawFundamentalData


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


def _raw(**overrides: object) -> RawFundamentalData:
    defaults: dict[str, object] = {
        "provider_id": "fake_vendor",
        "symbol": "AAPL",
        "period_end": "2024-09-28",
        "period_type": "annual",
        "line_items": {
            "revenue": 100.0,
            "net_income": 20.0,
            "total_assets": 200.0,
            "shares_outstanding": 1_000.0,
            "market_cap": 50_000.0,
            "enterprise_value": 55_000.0,
        },
    }
    defaults.update(overrides)
    return RawFundamentalData(**defaults)  # type: ignore[arg-type]


class TestDefaultFundamentalNormalizer:
    def test_is_fundamental_normalizer(self) -> None:
        assert isinstance(DefaultFundamentalNormalizer(), FundamentalNormalizer)

    def test_maps_canonical_and_alias_fields(
        self, instrument: Instrument
    ) -> None:
        normalizer = DefaultFundamentalNormalizer()
        statement = normalizer.normalize(_raw(), instrument)

        assert statement.instrument is instrument
        assert statement.period_end == date(2024, 9, 28)
        assert statement.period_type is StatementPeriodType.ANNUAL
        assert statement.fiscal_year == 2024
        assert statement.currency == "USD"
        assert statement.revenue == pytest.approx(100.0)
        assert statement.net_income == pytest.approx(20.0)
        assert statement.total_assets == pytest.approx(200.0)
        extras = dict(statement.extra_line_items)
        assert extras["shares_outstanding"] == pytest.approx(1_000.0)
        assert extras["market_capitalization"] == pytest.approx(50_000.0)
        assert extras["enterprise_value"] == pytest.approx(55_000.0)

    def test_yahoo_style_aliases(self, instrument: Instrument) -> None:
        normalizer = DefaultFundamentalNormalizer()
        raw = _raw(
            line_items={
                "totalRevenue": 10.0,
                "netIncome": 2.0,
                "totalAssets": 30.0,
                "sharesOutstanding": 5.0,
            }
        )
        statement = normalizer.normalize(raw, instrument)
        assert statement.revenue == pytest.approx(10.0)
        assert statement.net_income == pytest.approx(2.0)
        assert dict(statement.extra_line_items)["shares_outstanding"] == pytest.approx(
            5.0
        )

    def test_missing_optional_fields_remain_none(
        self, instrument: Instrument
    ) -> None:
        normalizer = DefaultFundamentalNormalizer()
        statement = normalizer.normalize(
            _raw(line_items={"revenue": 1.0}), instrument
        )
        assert statement.revenue == pytest.approx(1.0)
        assert statement.net_income is None
        assert statement.total_debt is None

    def test_missing_period_end_raises(self, instrument: Instrument) -> None:
        normalizer = DefaultFundamentalNormalizer()
        with pytest.raises(MissingFieldError):
            normalizer.normalize(_raw(period_end=None), instrument)

    def test_invalid_period_type_raises(self, instrument: Instrument) -> None:
        normalizer = DefaultFundamentalNormalizer()
        with pytest.raises(InvalidProviderDataError, match="period_type"):
            normalizer.normalize(_raw(period_type="biweekly"), instrument)

    def test_invalid_currency_raises(self, instrument: Instrument) -> None:
        normalizer = DefaultFundamentalNormalizer()
        with pytest.raises(InvalidProviderDataError):
            normalizer.normalize(
                _raw(line_items={"currency": "US", "revenue": 1.0}), instrument
            )

    def test_non_numeric_line_item_raises(self, instrument: Instrument) -> None:
        normalizer = DefaultFundamentalNormalizer()
        with pytest.raises(InvalidProviderDataError, match="non-numeric"):
            normalizer.normalize(
                _raw(line_items={"revenue": "not-a-number"}), instrument
            )

    def test_uses_instrument_currency_when_omitted(
        self, instrument: Instrument
    ) -> None:
        statement = DefaultFundamentalNormalizer().normalize(
            _raw(line_items={"revenue": 1.0}), instrument
        )
        assert statement.currency == "USD"

    def test_deterministic_repeated_normalize(
        self, instrument: Instrument
    ) -> None:
        normalizer = DefaultFundamentalNormalizer()
        raw = _raw()
        assert normalizer.normalize(raw, instrument) == normalizer.normalize(
            raw, instrument
        )


class TestFundamentalStatementsBuilder:
    def _statement(
        self, instrument: Instrument, period_end: date, revenue: float
    ) -> FundamentalStatement:
        return FundamentalStatement(
            instrument=instrument,
            period_end=period_end,
            period_type=StatementPeriodType.ANNUAL,
            fiscal_year=period_end.year,
            currency="USD",
            revenue=revenue,
        )

    def test_orders_most_recent_first(self, instrument: Instrument) -> None:
        older = self._statement(instrument, date(2022, 12, 31), 1.0)
        newer = self._statement(instrument, date(2023, 12, 31), 2.0)
        result = FundamentalStatementsBuilder.build(instrument, (older, newer))
        assert result[0].period_end == date(2023, 12, 31)
        assert result[1].period_end == date(2022, 12, 31)

    def test_rejects_empty(self, instrument: Instrument) -> None:
        with pytest.raises(InvalidProviderDataError, match="empty"):
            FundamentalStatementsBuilder.build(instrument, ())

    def test_allow_empty(self, instrument: Instrument) -> None:
        assert FundamentalStatementsBuilder.build(
            instrument, (), allow_empty=True
        ) == ()

    def test_rejects_duplicate_period_end(self, instrument: Instrument) -> None:
        a = self._statement(instrument, date(2023, 12, 31), 1.0)
        b = self._statement(instrument, date(2023, 12, 31), 2.0)
        with pytest.raises(InvalidProviderDataError, match="duplicate"):
            FundamentalStatementsBuilder.build(instrument, (a, b))

    def test_rejects_mismatched_instrument(self, instrument: Instrument) -> None:
        other = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        statement = self._statement(other, date(2023, 12, 31), 1.0)
        with pytest.raises(InvalidProviderDataError, match="instrument"):
            FundamentalStatementsBuilder.build(instrument, (statement,))
