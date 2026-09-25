"""Unit tests for FMP investment quote/statement adapters (mocked HTTP)."""

from __future__ import annotations

from typing import Any, Mapping

import pytest
from contracts.domain.instrument import AssetClass, Instrument
from data_engine.financial_statement.adapters import (
    build_default_statement_adapter_from_env,
)
from data_engine.financial_statement.service import StatementQuery
from data_engine.fmp_investment import (
    FinancialModelingPrepQuoteAdapter,
    FinancialModelingPrepStatementAdapter,
    resolve_fmp_api_key,
)
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env


def _equity(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


class _FakeHttp:
    def __init__(self, routes: Mapping[str, Any]) -> None:
        self._routes = dict(routes)
        self.calls: list[str] = []

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        self.calls.append(url)
        # Never assert secret values — only that apikey param is present.
        assert params is not None and "apikey" in params
        assert params["apikey"]
        for key, payload in self._routes.items():
            if key in url:
                return payload
        raise AssertionError(f"unexpected url {url}")


def test_resolve_fmp_api_key_prefers_primary() -> None:
    assert (
        resolve_fmp_api_key(
            {
                "DSP_FMP_API_KEY": "primary",
                "DSP_INVESTMENT_FMP_API_KEY": "alias",
            }
        )
        == "primary"
    )
    assert resolve_fmp_api_key({"DSP_INVESTMENT_FMP_API_KEY": "alias"}) == "alias"
    assert resolve_fmp_api_key({}) == ""


def test_fmp_quote_maps_authenticated_fields() -> None:
    http = _FakeHttp(
        {
            "/quote/AAPL": [
                {
                    "symbol": "AAPL",
                    "price": 190.5,
                    "open": 189.0,
                    "dayHigh": 191.0,
                    "dayLow": 188.0,
                    "previousClose": 188.5,
                    "yearHigh": 200.0,
                    "yearLow": 150.0,
                    "volume": 1_000_000,
                    "avgVolume": 900_000,
                    "marketCap": 3_000_000_000_000,
                    "sharesOutstanding": 15_000_000_000,
                    "exchange": "NASDAQ",
                    "currency": "USD",
                    "change": 2.0,
                    "changesPercentage": 1.0610079576,
                }
            ]
        }
    )
    adapter = FinancialModelingPrepQuoteAdapter(api_key="test-key", http_client=http)
    quote = adapter.get_quote(_equity())
    assert quote is not None
    assert quote.symbol == "AAPL"
    assert quote.current_price.value == pytest.approx(190.5)
    assert quote.shares_outstanding.value == pytest.approx(15_000_000_000)
    assert quote.provenance.provider_id == "fmp_market_quote"
    assert quote.provenance.auth_mode == "api_key"
    assert adapter.health().authenticated is True
    # Figma Watchlist "Change" column — provider-reported, never derived.
    assert float(quote.change.value) == pytest.approx(2.0)
    assert float(quote.change_percent.value) == pytest.approx(1.0610079576)
    public = quote.to_public_dict()["fields"]
    assert public["change"] == pytest.approx(2.0)
    assert public["change_percent"] == pytest.approx(1.0610079576)


def test_fmp_quote_change_fields_stay_unavailable_when_missing() -> None:
    http = _FakeHttp(
        {"/quote/AAPL": [{"symbol": "AAPL", "price": 190.5, "previousClose": 188.5}]}
    )
    adapter = FinancialModelingPrepQuoteAdapter(api_key="test-key", http_client=http)
    quote = adapter.get_quote(_equity())
    assert quote is not None
    assert quote.change.available is False
    assert quote.change_percent.available is False
    public = quote.to_public_dict()["fields"]
    assert public["change"] is None
    assert public["change_percent"] is None


def test_fmp_statements_merge_income_balance_cash() -> None:
    http = _FakeHttp(
        {
            "/profile/AAPL": [
                {
                    "symbol": "AAPL",
                    "companyName": "Apple Inc.",
                    "exchangeShortName": "NASDAQ",
                    "currency": "USD",
                    "isin": "US0378331005",
                    "cik": "0000320193",
                }
            ],
            "/income-statement/AAPL": [
                {
                    "date": "2024-09-28",
                    "calendarYear": "2024",
                    "period": "FY",
                    "reportedCurrency": "USD",
                    "fillingDate": "2024-11-01",
                    "revenue": 391035000000,
                    "costOfRevenue": 210352000000,
                    "grossProfit": 180683000000,
                    "operatingIncome": 123216000000,
                    "ebitda": 134661000000,
                    "netIncome": 93736000000,
                    "grossProfitRatio": 0.4620634982,
                    "operatingIncomeRatio": 0.3151022287,
                    "netIncomeRatio": 0.2397125577,
                    "eps": 6.11,
                    "epsdiluted": 6.08,
                }
            ],
            "/balance-sheet-statement/AAPL": [
                {
                    "date": "2024-09-28",
                    "cashAndCashEquivalents": 29943000000,
                    "totalCurrentAssets": 152987000000,
                    "totalAssets": 364980000000,
                    "totalCurrentLiabilities": 176392000000,
                    "totalLiabilities": 308030000000,
                    "totalStockholdersEquity": 56950000000,
                    "totalDebt": 106600000000,
                    "longTermDebt": 85750000000,
                }
            ],
            "/cash-flow-statement/AAPL": [
                {
                    "date": "2024-09-28",
                    "operatingCashFlow": 118254000000,
                    "netCashUsedForInvestingActivites": -10000000000,
                    "netCashUsedProvidedByFinancingActivities": -100000000000,
                    "capitalExpenditure": -9447000000,
                    "freeCashFlow": 108807000000,
                    "dividendsPaid": -15234000000,
                    "commonStockRepurchased": -94949000000,
                }
            ],
        }
    )
    adapter = FinancialModelingPrepStatementAdapter(
        api_key="test-key", http_client=http
    )
    statements = adapter.get_statements(
        StatementQuery(instrument=_equity(), limit=4)
    )
    assert statements is not None
    assert statements.identity.symbol == "AAPL"
    assert statements.identity.company_name == "Apple Inc."
    assert len(statements.periods) == 1
    period = statements.periods[0]
    assert period.statement_basis == "consolidated"
    assert period.unit_scale == "actual"
    assert period.reporting_currency == "USD"
    assert period.revenue.value == pytest.approx(391035000000)
    assert period.total_equity.value == pytest.approx(56950000000)
    assert period.free_cash_flow.value == pytest.approx(108807000000)
    # Provider-reported ratios pass through untouched (Figma margin trend source).
    assert float(period.net_margin.value) == pytest.approx(0.2397125577)
    assert float(period.gross_margin.value) == pytest.approx(0.4620634982)
    assert float(period.operating_margin.value) == pytest.approx(0.3151022287)
    public_ratios = statements.to_public_dict()["periods"][0]["ratios"]
    assert public_ratios["net_margin"] == pytest.approx(0.2397125577)
    assert statements.provenance.provider_id == "fmp_financial_statements"
    assert statements.provenance.auth_mode == "api_key"


def test_fmp_statements_missing_ratio_fields_stay_unavailable() -> None:
    """No ``*Ratio`` field from the vendor → ratio is missing, never computed."""
    http = _FakeHttp(
        {
            "/profile/AAPL": [{"symbol": "AAPL", "currency": "USD"}],
            "/income-statement/AAPL": [
                {
                    "date": "2024-09-28",
                    "calendarYear": "2024",
                    "period": "FY",
                    "reportedCurrency": "USD",
                    "revenue": 391035000000,
                    "netIncome": 93736000000,
                }
            ],
            "/balance-sheet-statement/AAPL": [{"date": "2024-09-28"}],
            "/cash-flow-statement/AAPL": [{"date": "2024-09-28"}],
        }
    )
    adapter = FinancialModelingPrepStatementAdapter(
        api_key="test-key", http_client=http
    )
    statements = adapter.get_statements(
        StatementQuery(instrument=_equity(), limit=1)
    )
    assert statements is not None
    period = statements.periods[0]
    assert period.net_margin.available is False
    assert statements.to_public_dict()["periods"][0]["ratios"]["net_margin"] is None


def test_factory_selects_fmp_when_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "DSP_MARKET_QUOTE_API_KEY",
        "DSP_MARKET_QUOTE_BASE_URL",
        "DSP_FINANCIAL_STATEMENT_API_KEY",
        "DSP_FINANCIAL_STATEMENT_BASE_URL",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_FINANCIAL_STATEMENT_MEMORY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_ENVIRONMENT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DSP_FMP_API_KEY", "unit-test-key")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert type(quote).__name__ == "FinancialModelingPrepQuoteAdapter"
    assert type(stmt).__name__ == "FinancialModelingPrepStatementAdapter"
    assert quote.provider_id == "fmp_market_quote"
    assert stmt.provider_id == "fmp_financial_statements"
