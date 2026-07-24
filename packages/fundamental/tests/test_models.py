"""Tests for fundamental.models."""

from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from core.exceptions import ValidationError
from fundamental.enums import MetricUnit
from fundamental.models import (
    FinancialSnapshot,
    FundamentalMetric,
    FundamentalResult,
    format_metric_value,
)

StatementFactory = Callable[..., FundamentalStatement]
SnapshotFactory = Callable[..., FinancialSnapshot]


class TestFormatMetricValue:
    """Tests for the shared value-formatting helper."""

    def test_percent(self) -> None:
        assert format_metric_value(0.183, MetricUnit.PERCENT) == "18.3%"

    def test_currency(self) -> None:
        assert format_metric_value(1_234_567.0, MetricUnit.CURRENCY) == "$1,234,567"

    def test_ratio(self) -> None:
        assert format_metric_value(1.2, MetricUnit.RATIO) == "1.20x"


class TestFinancialSnapshot:
    """Tests for FinancialSnapshot validation and convenience properties."""

    def test_latest_and_previous(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        latest = statement_factory(fiscal_year=2024, period_end=date(2024, 12, 31))
        previous = statement_factory(fiscal_year=2023, period_end=date(2023, 12, 31))
        snapshot = snapshot_factory([latest, previous])
        assert snapshot.latest is latest
        assert snapshot.previous is previous

    def test_previous_is_none_with_a_single_statement(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        latest = statement_factory()
        snapshot = snapshot_factory([latest])
        assert snapshot.previous is None

    def test_empty_statements_rejected(self) -> None:
        instrument = Instrument(
            symbol="TEST", asset_class=AssetClass.EQUITY, currency="USD"
        )
        with pytest.raises(ValidationError, match="must not be empty"):
            FinancialSnapshot(instrument=instrument, statements=())

    def test_mismatched_instrument_rejected(
        self, statement_factory: StatementFactory
    ) -> None:
        own = statement_factory(symbol="AAA")
        other = statement_factory(symbol="BBB")
        with pytest.raises(ValidationError, match="belong to the snapshot"):
            FinancialSnapshot(instrument=own.instrument, statements=(own, other))

    def test_duplicate_period_end_rejected(
        self, statement_factory: StatementFactory
    ) -> None:
        first = statement_factory(period_end=date(2024, 12, 31))
        second = statement_factory(period_end=date(2024, 12, 31))
        with pytest.raises(ValidationError, match="duplicate"):
            statements = (first, second)
            FinancialSnapshot(instrument=first.instrument, statements=statements)

    def test_out_of_order_statements_rejected(
        self, statement_factory: StatementFactory
    ) -> None:
        older = statement_factory(period_end=date(2023, 12, 31))
        newer = statement_factory(period_end=date(2024, 12, 31))
        with pytest.raises(ValidationError, match="most-recent-first"):
            statements = (older, newer)
            FinancialSnapshot(instrument=older.instrument, statements=statements)


class TestFundamentalMetric:
    """Tests for FundamentalMetric normalization and display helpers."""

    def _instrument(self) -> Instrument:
        return Instrument(symbol="TEST", asset_class=AssetClass.EQUITY, currency="USD")

    def test_name_is_normalized_to_lowercase(self) -> None:
        metric = FundamentalMetric(
            instrument=self._instrument(),
            name="ROE",
            value=0.2,
            unit=MetricUnit.PERCENT,
            period_end=date(2024, 12, 31),
        )
        assert metric.name == "roe"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            FundamentalMetric(
                instrument=self._instrument(),
                name="   ",
                value=0.2,
                unit=MetricUnit.PERCENT,
                period_end=date(2024, 12, 31),
            )

    def test_known_label(self) -> None:
        metric = FundamentalMetric(
            instrument=self._instrument(),
            name="debt_to_equity",
            value=1.2,
            unit=MetricUnit.RATIO,
            period_end=date(2024, 12, 31),
        )
        assert metric.label == "Debt-to-Equity"

    def test_unknown_metric_falls_back_to_title_case(self) -> None:
        metric = FundamentalMetric(
            instrument=self._instrument(),
            name="current_ratio",
            value=1.5,
            unit=MetricUnit.RATIO,
            period_end=date(2024, 12, 31),
        )
        assert metric.label == "Current Ratio"

    def test_formatted_value_is_none_when_value_is_none(self) -> None:
        metric = FundamentalMetric(
            instrument=self._instrument(),
            name="roe",
            value=None,
            unit=MetricUnit.PERCENT,
            period_end=date(2024, 12, 31),
        )
        assert metric.formatted_value is None

    def test_formatted_value_uses_the_metric_unit(self) -> None:
        metric = FundamentalMetric(
            instrument=self._instrument(),
            name="roe",
            value=0.2,
            unit=MetricUnit.PERCENT,
            period_end=date(2024, 12, 31),
        )
        assert metric.formatted_value == "20.0%"


class TestFundamentalResult:
    """Tests for the FundamentalResult container."""

    def test_carries_instrument_analyzer_and_metrics(self) -> None:
        instrument = Instrument(
            symbol="TEST", asset_class=AssetClass.EQUITY, currency="USD"
        )
        metric = FundamentalMetric(
            instrument=instrument,
            name="roe",
            value=0.2,
            unit=MetricUnit.PERCENT,
            period_end=date(2024, 12, 31),
        )
        result = FundamentalResult(
            instrument=instrument,
            analyzer_name="profitability",
            metrics=(metric,),
            computed_at=datetime(2024, 6, 1, tzinfo=UTC),
        )
        assert result.analyzer_name == "profitability"
        assert result.metrics == (metric,)
