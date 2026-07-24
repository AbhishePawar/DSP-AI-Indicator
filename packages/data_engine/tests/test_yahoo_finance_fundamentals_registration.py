"""Tests for Yahoo Finance fundamentals registration and service wiring."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import StatementPeriodType
from data_engine.adapters.yahoo_finance.fundamentals_adapter import (
    YahooFinanceFundamentalsAdapter,
)
from data_engine.adapters.yahoo_finance.fundamentals_registration import (
    YAHOO_FINANCE_FUNDAMENTALS_METADATA,
    build_yahoo_finance_fundamentals_adapter,
    register_yahoo_finance_fundamentals,
)
from data_engine.cache import InMemoryCache
from data_engine.models import FundamentalsRequest
from data_engine.providers import DataCapability, ProviderFactory, ProviderRegistry
from data_engine.services import FundamentalsDataService


def _raw(value: Any) -> dict[str, Any]:
    return {"raw": value, "fmt": str(value)}


class _FakeHttpClient:
    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        return {
            "quoteSummary": {
                "result": [
                    {
                        "incomeStatementHistory": {
                            "incomeStatementHistory": [
                                {
                                    "endDate": _raw(1_704_067_200),
                                    "totalRevenue": _raw(100.0),
                                    "netIncome": _raw(10.0),
                                }
                            ]
                        },
                        "balanceSheetHistory": {
                            "balanceSheetStatements": [
                                {
                                    "endDate": _raw(1_704_067_200),
                                    "totalAssets": _raw(200.0),
                                }
                            ]
                        },
                        "cashflowStatementHistory": {"cashflowStatements": []},
                        "defaultKeyStatistics": {},
                        "financialData": {},
                    }
                ],
                "error": None,
            }
        }


class TestBuildAndRegister:
    def test_builds_adapter(self) -> None:
        adapter = build_yahoo_finance_fundamentals_adapter({})
        assert isinstance(adapter, YahooFinanceFundamentalsAdapter)
        assert adapter.provider_name == "yahoo_finance_fundamentals"

    def test_registers_with_fundamentals_capability(self) -> None:
        factory = ProviderFactory()
        registry = ProviderRegistry()

        adapter = register_yahoo_finance_fundamentals(factory, registry)

        assert factory.is_registered("yahoo_finance_fundamentals")
        assert registry.get("yahoo_finance_fundamentals") is adapter
        assert (
            registry.get_metadata("yahoo_finance_fundamentals")
            == YAHOO_FINANCE_FUNDAMENTALS_METADATA
        )
        assert registry.filter_by_capability(DataCapability.FUNDAMENTALS) == (
            "yahoo_finance_fundamentals",
        )


class TestFundamentalsServiceThroughRegistry:
    @pytest.fixture
    def registry(self) -> ProviderRegistry:
        registry = ProviderRegistry()
        adapter = YahooFinanceFundamentalsAdapter(http_client=_FakeHttpClient())
        registry.register(adapter, YAHOO_FINANCE_FUNDAMENTALS_METADATA)
        return registry

    def test_service_retrieves_statements(
        self, registry: ProviderRegistry, instrument: Instrument
    ) -> None:
        service = FundamentalsDataService(
            providers=registry,
            cache=InMemoryCache(),
            default_provider="yahoo_finance_fundamentals",
        )
        request = FundamentalsRequest(
            instrument=instrument, period_type=StatementPeriodType.ANNUAL
        )

        statements = service.get_fundamental_statements(request)

        assert isinstance(statements, tuple)
        assert len(statements) == 1
        assert isinstance(statements[0], FundamentalStatement)
        assert statements[0].revenue == pytest.approx(100.0)
