"""B1 contract tests — FMP India symbol pass-through + field honesty (mocked HTTP).

No live vendor calls. Credentials remain ABSENT in CI; these tests lock the
adapter contract so private-beta operators know exact symbol/field behaviour.
"""

from __future__ import annotations

from typing import Any, Mapping

import pytest
from contracts.domain.instrument import AssetClass, Instrument
from data_engine.evidence_classes import (
    MEMORY_SEED_REFUSED_AS_LIVE,
    TEST_FIXTURE,
    may_clear_g2,
)
from data_engine.exceptions import ProviderRequestError
from data_engine.financial_statement.service import StatementQuery
from data_engine.fmp_investment import (
    FinancialModelingPrepQuoteAdapter,
    FinancialModelingPrepStatementAdapter,
)
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env


def _equity(symbol: str, *, currency: str = "INR") -> Instrument:
    return Instrument(
        symbol=symbol, asset_class=AssetClass.EQUITY, currency=currency
    )


class _RecordingHttp:
    def __init__(self, routes: Mapping[str, Any]) -> None:
        self._routes = dict(routes)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        self.calls.append((url, dict(params or {})))
        assert params is not None and "apikey" in params and params["apikey"]
        for key, payload in self._routes.items():
            if key in url:
                return payload
        raise AssertionError(f"unexpected url {url}")


@pytest.mark.parametrize(
    "symbol,url_fragment",
    [
        ("HDFCBANK.NS", "/quote/HDFCBANK.NS"),
        ("TCS.NS", "/quote/TCS.NS"),
        ("RELIANCE.NS", "/quote/RELIANCE.NS"),
        ("SBIN.NS", "/quote/SBIN.NS"),
        ("INFY.NS", "/quote/INFY.NS"),
        ("TATAMOTORS.NS", "/quote/TATAMOTORS.NS"),
        # Bare tickers are passed through — DSP does NOT invent .NS/.BO.
        ("HDFCBANK", "/quote/HDFCBANK"),
        ("RELIANCE.BO", "/quote/RELIANCE.BO"),
    ],
)
def test_fmp_quote_preserves_indian_symbol_exactly(
    symbol: str, url_fragment: str
) -> None:
    http = _RecordingHttp(
        {
            url_fragment: [
                {
                    "symbol": symbol,
                    "price": 100.0,
                    "currency": "INR",
                    "sharesOutstanding": 1_000_000,
                    "exchange": "NSE",
                }
            ]
        }
    )
    adapter = FinancialModelingPrepQuoteAdapter(api_key="test-key", http_client=http)
    quote = adapter.get_quote(_equity(symbol))
    assert quote is not None
    assert quote.symbol == symbol.strip().upper()
    assert any(url_fragment in url for url, _ in http.calls)
    assert quote.currency == "INR"
    assert quote.provenance.source_type == "licensed_vendor"
    assert quote.provenance.auth_mode == "api_key"


def test_fmp_does_not_map_ar_inventory_ap_even_when_vendor_sends_them() -> None:
    """AuthenticatedStatementPeriod has no AR/Inv/AP — FMP must not invent them."""
    http = _RecordingHttp(
        {
            "/profile/HDFCBANK.NS": [
                {
                    "symbol": "HDFCBANK.NS",
                    "companyName": "HDFC Bank",
                    "exchangeShortName": "NSE",
                    "currency": "INR",
                }
            ],
            "/income-statement/HDFCBANK.NS": [
                {
                    "date": "2024-03-31",
                    "calendarYear": "2024",
                    "period": "FY",
                    "reportedCurrency": "INR",
                    "revenue": 1000,
                    "netIncome": 100,
                    "eps": 10.0,
                    "epsdiluted": 9.9,
                    "weightedAverageShsOut": 50,
                }
            ],
            "/balance-sheet-statement/HDFCBANK.NS": [
                {
                    "date": "2024-03-31",
                    "cashAndCashEquivalents": 200,
                    "totalCurrentAssets": 500,
                    "totalAssets": 2000,
                    "totalCurrentLiabilities": 300,
                    "totalLiabilities": 1200,
                    "totalStockholdersEquity": 800,
                    "totalDebt": 400,
                    "longTermDebt": 350,
                    # Vendor may send WC lines — DSP authenticated period has no slots.
                    "netReceivables": 111,
                    "inventory": 222,
                    "accountPayables": 333,
                }
            ],
            "/cash-flow-statement/HDFCBANK.NS": [
                {
                    "date": "2024-03-31",
                    "operatingCashFlow": 150,
                    "capitalExpenditure": -40,
                    "freeCashFlow": 110,
                }
            ],
        }
    )
    adapter = FinancialModelingPrepStatementAdapter(
        api_key="test-key", http_client=http
    )
    statements = adapter.get_statements(
        StatementQuery(instrument=_equity("HDFCBANK.NS"), limit=4)
    )
    assert statements is not None
    period = statements.periods[0]
    assert period.period_type == "annual"
    assert period.reporting_currency == "INR"
    assert period.revenue.value == pytest.approx(1000)
    # No AR / inventory / AP attributes on authenticated period model.
    assert not hasattr(period, "accounts_receivable")
    assert not hasattr(period, "inventory")
    assert not hasattr(period, "accounts_payable")
    # Weighted shares from income not mapped either (quote shares used later).
    assert not hasattr(period, "weighted_shares")
    public_bs = period.to_public_dict()["balance_sheet"]
    assert "accounts_receivable" not in public_bs
    assert "inventory" not in public_bs
    assert "accounts_payable" not in public_bs


def test_fmp_unknown_period_label_not_silently_annual() -> None:
    http = _RecordingHttp(
        {
            "/profile/TCS.NS": [
                {
                    "symbol": "TCS.NS",
                    "exchangeShortName": "NSE",
                    "currency": "INR",
                }
            ],
            "/income-statement/TCS.NS": [
                {
                    "date": "2024-03-31",
                    "calendarYear": "2024",
                    "period": "H1",  # unknown — must skip, not invent annual
                    "reportedCurrency": "INR",
                    "revenue": 1,
                    "netIncome": 1,
                    "eps": 1,
                    "epsdiluted": 1,
                }
            ],
            "/balance-sheet-statement/TCS.NS": [],
            "/cash-flow-statement/TCS.NS": [],
        }
    )
    adapter = FinancialModelingPrepStatementAdapter(
        api_key="test-key", http_client=http
    )
    statements = adapter.get_statements(
        StatementQuery(instrument=_equity("TCS.NS"), limit=4)
    )
    assert statements is None


def test_fmp_quote_auth_failure_without_api_key() -> None:
    adapter = FinancialModelingPrepQuoteAdapter(api_key="", http_client=_RecordingHttp({}))
    with pytest.raises(ProviderRequestError, match="api_key"):
        adapter.get_quote(_equity("INFY.NS"))


def test_memory_and_fixture_never_clear_g2() -> None:
    assert may_clear_g2(MEMORY_SEED_REFUSED_AS_LIVE) is False
    assert may_clear_g2(TEST_FIXTURE) is False
    assert may_clear_g2("credentials_unavailable") is False


def test_factory_does_not_select_upstox_when_only_upstox_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Upstox exists but is not on the default investment factory path."""
    for name in (
        "DSP_MARKET_QUOTE_API_KEY",
        "DSP_MARKET_QUOTE_BASE_URL",
        "DSP_FMP_API_KEY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_ENVIRONMENT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "upstox-only-token")
    adapter = build_default_quote_adapter_from_env()
    assert type(adapter).__name__ != "UpstoxQuoteAdapter"
    assert adapter.provider_id == "null_market_quote"
