"""Tests for ``YahooFinanceFundamentalsAdapter``.

All tests inject a fake ``JsonHttpClient`` and never touch the network.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from data_engine.adapters.yahoo_finance.fundamentals_adapter import (
    YahooFinanceFundamentalsAdapter,
)
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    ProviderRequestError,
)


def _raw(value: Any) -> dict[str, Any]:
    return {"raw": value, "fmt": str(value)}


def _quote_summary_payload(
    *,
    income_rows: list[dict[str, Any]] | None = None,
    balance_rows: list[dict[str, Any]] | None = None,
    cashflow_rows: list[dict[str, Any]] | None = None,
    key_stats: dict[str, Any] | None = None,
    financial_data: dict[str, Any] | None = None,
    quarterly: bool = False,
    error: Any = None,
) -> dict[str, Any]:
    if income_rows is None:
        income_rows = [
            {
                "endDate": _raw(1_704_067_200),  # 2024-01-01 UTC-ish
                "totalRevenue": _raw(394_328_000_000),
                "costOfRevenue": _raw(214_137_000_000),
                "grossProfit": _raw(180_191_000_000),
                "operatingIncome": _raw(114_301_000_000),
                "netIncome": _raw(96_995_000_000),
                "basicEPS": _raw(6.16),
                "dilutedEPS": _raw(6.13),
            },
            {
                "endDate": _raw(1_672_531_200),  # 2022-12-31-ish
                "totalRevenue": _raw(365_817_000_000),
                "netIncome": _raw(99_803_000_000),
                "basicEPS": _raw(6.15),
            },
        ]
    if balance_rows is None:
        balance_rows = [
            {
                "endDate": _raw(1_704_067_200),
                "totalAssets": _raw(352_583_000_000),
                "totalLiab": _raw(290_437_000_000),
                "totalStockholderEquity": _raw(62_146_000_000),
                "cash": _raw(29_965_000_000),
                "longTermDebt": _raw(95_000_000_000),
            },
            {
                "endDate": _raw(1_672_531_200),
                "totalAssets": _raw(323_888_000_000),
                "totalStockholderEquity": _raw(50_672_000_000),
            },
        ]
    if cashflow_rows is None:
        cashflow_rows = [
            {
                "endDate": _raw(1_704_067_200),
                "totalCashFromOperatingActivities": _raw(110_543_000_000),
                "totalCashflowsFromInvestingActivities": _raw(-14_545_000_000),
                "totalCashFromFinancingActivities": _raw(-110_000_000_000),
                "capitalExpenditures": _raw(-10_959_000_000),
            }
        ]
    if key_stats is None:
        key_stats = {
            "sharesOutstanding": _raw(15_550_000_000),
            "enterpriseValue": _raw(2_800_000_000_000),
        }
    if financial_data is None:
        financial_data = {
            "marketCap": _raw(2_900_000_000_000),
            "currentRatio": _raw(0.99),
            "debtToEquity": _raw(152.0),
            "returnOnEquity": _raw(1.47),
        }

    income_module = "incomeStatementHistoryQuarterly" if quarterly else "incomeStatementHistory"
    balance_module = "balanceSheetHistoryQuarterly" if quarterly else "balanceSheetHistory"
    cashflow_module = (
        "cashflowStatementHistoryQuarterly" if quarterly else "cashflowStatementHistory"
    )

    return {
        "quoteSummary": {
            "result": [
                {
                    income_module: {"incomeStatementHistory": income_rows},
                    balance_module: {"balanceSheetStatements": balance_rows},
                    cashflow_module: {"cashflowStatements": cashflow_rows},
                    "defaultKeyStatistics": key_stats,
                    "financialData": financial_data,
                }
            ],
            "error": error,
        }
    }


class _FakeHttpClient:
    def __init__(
        self,
        payload: Mapping[str, Any] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._error = error
        self.last_url: str | None = None
        self.last_params: Mapping[str, str] | None = None
        self.call_count = 0

    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        self.call_count += 1
        self.last_url = url
        self.last_params = params
        if self._error is not None:
            raise self._error
        assert self._payload is not None
        return self._payload


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


class TestSuccessfulRetrieval:
    def test_returns_statements_most_recent_first(self, instrument: Instrument) -> None:
        client = _FakeHttpClient(_quote_summary_payload())
        adapter = YahooFinanceFundamentalsAdapter(http_client=client)

        statements = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL
        )

        assert len(statements) == 2
        assert all(isinstance(item, FundamentalStatement) for item in statements)
        assert statements[0].period_end >= statements[1].period_end
        assert statements[0].revenue == pytest.approx(394_328_000_000)
        assert statements[0].net_income == pytest.approx(96_995_000_000)
        assert statements[0].total_assets == pytest.approx(352_583_000_000)
        assert statements[0].operating_cash_flow == pytest.approx(110_543_000_000)
        assert statements[0].currency == "USD"

    def test_maps_shares_market_cap_and_ev_into_extra_line_items(
        self, instrument: Instrument
    ) -> None:
        adapter = YahooFinanceFundamentalsAdapter(
            http_client=_FakeHttpClient(_quote_summary_payload())
        )

        latest = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL
        )[0]
        extras = dict(latest.extra_line_items)

        assert extras["shares_outstanding"] == pytest.approx(15_550_000_000)
        assert extras["market_capitalization"] == pytest.approx(2_900_000_000_000)
        assert extras["enterprise_value"] == pytest.approx(2_800_000_000_000)
        assert extras["current_ratio"] == pytest.approx(0.99)

    def test_requests_expected_modules(self, instrument: Instrument) -> None:
        client = _FakeHttpClient(_quote_summary_payload())
        adapter = YahooFinanceFundamentalsAdapter(http_client=client)

        adapter.get_fundamental_statements(instrument, StatementPeriodType.ANNUAL)

        assert client.last_url is not None
        assert client.last_url.endswith("/AAPL")
        assert client.last_params is not None
        modules = client.last_params["modules"]
        assert "incomeStatementHistory" in modules
        assert "balanceSheetHistory" in modules
        assert "cashflowStatementHistory" in modules

    def test_limit_returns_most_recent_only(self, instrument: Instrument) -> None:
        adapter = YahooFinanceFundamentalsAdapter(
            http_client=_FakeHttpClient(_quote_summary_payload())
        )

        statements = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL, limit=1
        )

        assert len(statements) == 1
        assert statements[0].revenue == pytest.approx(394_328_000_000)

    def test_quarterly_uses_quarterly_modules(self, instrument: Instrument) -> None:
        client = _FakeHttpClient(_quote_summary_payload(quarterly=True))
        adapter = YahooFinanceFundamentalsAdapter(http_client=client)

        statements = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.QUARTERLY
        )

        assert len(statements) == 2
        assert client.last_params is not None
        assert "incomeStatementHistoryQuarterly" in client.last_params["modules"]

    def test_ttm_builds_single_statement(self, instrument: Instrument) -> None:
        payload = _quote_summary_payload()
        client = _FakeHttpClient(payload)
        adapter = YahooFinanceFundamentalsAdapter(http_client=client)

        statements = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.TRAILING_TWELVE_MONTHS
        )

        assert len(statements) == 1
        assert statements[0].period_type is StatementPeriodType.TRAILING_TWELVE_MONTHS

    def test_provider_name(self) -> None:
        assert (
            YahooFinanceFundamentalsAdapter().provider_name
            == "yahoo_finance_fundamentals"
        )

    def test_repeated_calls_are_deterministic(self, instrument: Instrument) -> None:
        payload = _quote_summary_payload()
        adapter = YahooFinanceFundamentalsAdapter(
            http_client=_FakeHttpClient(payload)
        )
        first = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL
        )
        adapter2 = YahooFinanceFundamentalsAdapter(
            http_client=_FakeHttpClient(payload)
        )
        second = adapter2.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL
        )
        assert first == second


class TestMissingAndOptionalFields:
    def test_missing_optional_line_items_become_none(
        self, instrument: Instrument
    ) -> None:
        payload = _quote_summary_payload(
            income_rows=[
                {
                    "endDate": _raw(1_704_067_200),
                    "totalRevenue": _raw(100.0),
                    # netIncome intentionally omitted
                }
            ],
            balance_rows=[
                {"endDate": _raw(1_704_067_200), "totalAssets": _raw(200.0)}
            ],
            cashflow_rows=[],
            key_stats={},
            financial_data={},
        )
        adapter = YahooFinanceFundamentalsAdapter(http_client=_FakeHttpClient(payload))

        statement = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL
        )[0]

        assert statement.revenue == pytest.approx(100.0)
        assert statement.net_income is None
        assert statement.operating_cash_flow is None

    def test_fully_null_period_end_rows_are_skipped(
        self, instrument: Instrument
    ) -> None:
        payload = _quote_summary_payload(
            income_rows=[
                {"endDate": None, "totalRevenue": _raw(1.0)},
                {
                    "endDate": _raw(1_704_067_200),
                    "totalRevenue": _raw(2.0),
                },
            ],
            balance_rows=[],
            cashflow_rows=[],
            key_stats={},
            financial_data={},
        )
        adapter = YahooFinanceFundamentalsAdapter(http_client=_FakeHttpClient(payload))

        statements = adapter.get_fundamental_statements(
            instrument, StatementPeriodType.ANNUAL
        )

        assert len(statements) == 1
        assert statements[0].revenue == pytest.approx(2.0)


class TestValidationFailures:
    def test_negative_limit_rejected(self, instrument: Instrument) -> None:
        adapter = YahooFinanceFundamentalsAdapter(
            http_client=_FakeHttpClient(_quote_summary_payload())
        )
        with pytest.raises(DataEngineError, match="limit"):
            adapter.get_fundamental_statements(
                instrument, StatementPeriodType.ANNUAL, limit=-1
            )

    def test_provider_error_payload_raises(self, instrument: Instrument) -> None:
        payload = _quote_summary_payload(error={"code": "Not Found"})
        adapter = YahooFinanceFundamentalsAdapter(http_client=_FakeHttpClient(payload))
        with pytest.raises(InvalidProviderDataError, match="reported an error"):
            adapter.get_fundamental_statements(
                instrument, StatementPeriodType.ANNUAL
            )

    def test_empty_result_raises(self, instrument: Instrument) -> None:
        payload = {"quoteSummary": {"result": [], "error": None}}
        adapter = YahooFinanceFundamentalsAdapter(http_client=_FakeHttpClient(payload))
        with pytest.raises(InvalidProviderDataError, match="no quoteSummary result"):
            adapter.get_fundamental_statements(
                instrument, StatementPeriodType.ANNUAL
            )

    def test_unexpected_shape_raises(self, instrument: Instrument) -> None:
        adapter = YahooFinanceFundamentalsAdapter(
            http_client=_FakeHttpClient({"not": "quoteSummary"})
        )
        with pytest.raises(InvalidProviderDataError, match="unexpected payload"):
            adapter.get_fundamental_statements(
                instrument, StatementPeriodType.ANNUAL
            )

    def test_no_usable_statements_raises(self, instrument: Instrument) -> None:
        payload = _quote_summary_payload(
            income_rows=[],
            balance_rows=[],
            cashflow_rows=[],
            key_stats={},
            financial_data={},
        )
        adapter = YahooFinanceFundamentalsAdapter(http_client=_FakeHttpClient(payload))
        with pytest.raises(InvalidProviderDataError, match="no usable statements"):
            adapter.get_fundamental_statements(
                instrument, StatementPeriodType.ANNUAL
            )

    def test_http_failure_surfaces_provider_request_error(
        self, instrument: Instrument
    ) -> None:
        adapter = YahooFinanceFundamentalsAdapter(
            http_client=_FakeHttpClient(
                error=ProviderRequestError("network down")
            )
        )
        with pytest.raises(ProviderRequestError, match="network down"):
            adapter.get_fundamental_statements(
                instrument, StatementPeriodType.ANNUAL
            )
