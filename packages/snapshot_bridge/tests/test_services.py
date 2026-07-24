"""Tests for bridge services and public API."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.economic_series import EconomicDataPoint, EconomicSeries
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import (
    AssetClass,
    EconomicFrequency,
    StatementPeriodType,
)
from data_engine.adapters import BaseAdapter
from data_engine.cache import InMemoryCache
from data_engine.models import FundamentalsRequest
from data_engine.ports import EconomicDataPort, FundamentalsDataPort
from data_engine.providers import (
    ProviderCapabilities,
    ProviderMetadata,
    ProviderRegistry,
)
from data_engine.services import EconomicDataService, FundamentalsDataService
from economic.models import EconomicSnapshot
from fundamental.models import FinancialSnapshot
from snapshot_bridge import (
    EconomicBridgeService,
    EconomicSnapshotBuilder,
    FinancialBridgeService,
    FinancialSnapshotBuilder,
    SnapshotBridgeError,
)


class _FakeFundamentals(BaseAdapter, FundamentalsDataPort):
    def __init__(self, statements: tuple[FundamentalStatement, ...]) -> None:
        self._statements = statements

    @property
    def provider_name(self) -> str:
        return "fake_fundamentals"

    def get_fundamental_statements(
        self,
        instrument: Instrument,
        period_type: StatementPeriodType,
        *,
        limit: int | None = None,
    ) -> tuple[FundamentalStatement, ...]:
        return self._statements


class _FakeEconomic(BaseAdapter, EconomicDataPort):
    def __init__(self, series_by_code: dict[str, EconomicSeries]) -> None:
        self._series = series_by_code

    @property
    def provider_name(self) -> str:
        return "fake_economic"

    def get_economic_series(self, indicator_code: str, country: str) -> EconomicSeries:
        key = indicator_code.strip().upper()
        if key not in self._series:
            from data_engine.exceptions import DataEngineError

            raise DataEngineError(f"unsupported {key}")
        return self._series[key]


class TestPublicApi:
    def test_exports(self) -> None:
        assert FinancialSnapshotBuilder is not None
        assert EconomicSnapshotBuilder is not None
        assert FinancialBridgeService is not None
        assert EconomicBridgeService is not None
        assert issubclass(SnapshotBridgeError, Exception)


class TestFinancialBridgeService:
    def test_end_to_end(self) -> None:
        instrument = Instrument(
            symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
        )
        statements = (
            FundamentalStatement(
                instrument=instrument,
                period_end=date(2023, 12, 31),
                period_type=StatementPeriodType.ANNUAL,
                fiscal_year=2023,
                currency="USD",
                revenue=100.0,
            ),
        )
        registry = ProviderRegistry()
        registry.register(
            _FakeFundamentals(statements),
            ProviderMetadata(
                provider_id="fake_fundamentals",
                name="Fake",
                capabilities=ProviderCapabilities.from_flags(fundamentals=True),
            ),
        )
        service = FinancialBridgeService(
            fundamentals=FundamentalsDataService(
                providers=registry,
                cache=InMemoryCache(),
                default_provider="fake_fundamentals",
            )
        )
        snapshot = service.get_snapshot(
            FundamentalsRequest(
                instrument=instrument, period_type=StatementPeriodType.ANNUAL
            )
        )
        assert isinstance(snapshot, FinancialSnapshot)
        assert snapshot.latest.revenue == pytest.approx(100.0)


class TestEconomicBridgeService:
    def test_end_to_end_and_graceful_skip(self) -> None:
        series = {
            "PMI": EconomicSeries(
                indicator_code="PMI",
                indicator_name="PMI",
                country="US",
                frequency=EconomicFrequency.MONTHLY,
                points=(EconomicDataPoint(date(2023, 1, 1), 51.0),),
            ),
            "GDP": EconomicSeries(
                indicator_code="GDP",
                indicator_name="GDP",
                country="US",
                frequency=EconomicFrequency.QUARTERLY,
                points=(
                    EconomicDataPoint(date(2022, 1, 1), 100.0),
                    EconomicDataPoint(date(2023, 1, 1), 102.0),
                ),
            ),
        }
        registry = ProviderRegistry()
        registry.register(
            _FakeEconomic(series),
            ProviderMetadata(
                provider_id="fake_economic",
                name="Fake",
                capabilities=ProviderCapabilities.from_flags(economic_data=True),
            ),
        )
        bridge = EconomicBridgeService(
            economic=EconomicDataService(
                providers=registry,
                cache=InMemoryCache(),
                default_provider="fake_economic",
            )
        )
        snapshot = bridge.get_snapshot(
            country="US",
            indicator_codes=("GDP", "PMI", "VIX"),
        )
        assert isinstance(snapshot, EconomicSnapshot)
        assert snapshot.pmi == pytest.approx(51.0)
        assert snapshot.gdp_growth == pytest.approx(0.02)
