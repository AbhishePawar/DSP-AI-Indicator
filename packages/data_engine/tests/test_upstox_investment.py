from __future__ import annotations

from typing import Any

from data_engine.upstox_investment import (
    UpstoxQuoteAdapter,
    UpstoxStatementAdapter,
    resolve_upstox_analytics_token,
)


class FakeJsonClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str], dict[str, str]]] = []

    def get_json(self, url: str, *, params=None, headers=None):
        self.calls.append((url, dict(params or {}), dict(headers or {})))
        path = url.split("https://api.upstox.com/v2/")[-1]
        if path.startswith("instruments/search"):
            return {
                "status": "success",
                "data": [
                    {
                        "name": "STATE BANK OF INDIA",
                        "segment": "NSE_EQ",
                        "exchange": "NSE",
                        "isin": "INE062A01020",
                        "instrument_key": "NSE_EQ|INE062A01020",
                        "trading_symbol": "SBIN",
                        "instrument_type": "EQ",
                    }
                ],
            }
        if path.startswith("market-quote/quotes"):
            return {
                "status": "success",
                "data": {
                    "NSE_EQ:SBIN": {
                        "ohlc": {"open": 1000, "high": 1020, "low": 995, "close": 1002},
                        "timestamp": "2026-08-09T10:00:00+05:30",
                        "symbol": "SBIN",
                        "last_price": 1010.5,
                        "volume": 123456,
                        "average_price": 1008.2,
                    }
                },
            }
        if path.endswith("/profile"):
            return {"status": "success", "data": {"company_profile": "State Bank of India"}}
        if path.endswith("/income-statement"):
            return {
                "status": "success",
                "data": {
                    "type": "consolidated",
                    "time_period": "yearly",
                    "units_in": "crore",
                    "income_statement": [
                        {
                            "category": "revenue",
                            "history": [{"period": "Mar 2026", "value": 100}],
                        },
                        {
                            "category": "net_profit",
                            "history": [{"period": "Mar 2026", "value": 20}],
                        },
                    ],
                    "full_statement": [
                        {
                            "particular": "EPS - Basic",
                            "history": [{"period": "Mar 2026", "value": 5.0}],
                        },
                        {
                            "particular": "EPS - Diluted",
                            "history": [{"period": "Mar 2026", "value": 4.9}],
                        },
                    ],
                },
            }
        if path.endswith("/balance-sheet"):
            return {
                "status": "success",
                "data": {
                    "type": "consolidated",
                    "units_in": "crore",
                    "history": [
                        {"total_asset": 1000, "total_liability": 400, "period": "Mar 2026"}
                    ],
                    "full_statement": [
                        {
                            "particular": "Total Assets",
                            "history": [{"period": "Mar 2026", "value": 1000}],
                        },
                        {
                            "particular": "Current Assets",
                            "history": [{"period": "Mar 2026", "value": 300}],
                        },
                        {
                            "particular": "Current Liabilities",
                            "history": [{"period": "Mar 2026", "value": 200}],
                        },
                        {
                            "particular": "Equity Capital",
                            "history": [{"period": "Mar 2026", "value": 600}],
                        },
                    ],
                },
            }
        if path.endswith("/cash-flow"):
            return {
                "status": "success",
                "data": {
                    "type": "consolidated",
                    "units_in": "crore",
                    "cash_flow": [
                        {
                            "category": "operating",
                            "history": [{"period": "Mar 2026", "value": 200}],
                        }
                    ],
                    "full_statement": [
                        {
                            "particular": "Cash flow from Operations",
                            "history": [{"period": "Mar 2026", "value": 200}],
                        }
                    ],
                },
            }
        raise AssertionError(f"unexpected path: {path}")


def test_token_resolution_prefers_analytics_token() -> None:
    env = {"DSP_UPSTOX_ANALYTICS_TOKEN": "analytics", "DSP_UPSTOX_ACCESS_TOKEN": "oauth"}
    assert resolve_upstox_analytics_token(env) == "analytics"


def test_quote_adapter_maps_authenticated_upstox_quote() -> None:
    client = FakeJsonClient({})
    adapter = UpstoxQuoteAdapter(access_token="secret", http_client=client)
    from contracts.domain.instrument import Instrument
    from contracts.enums import AssetClass

    quote = adapter.get_quote(
        Instrument(symbol="SBIN", asset_class=AssetClass.EQUITY, currency="INR")
    )
    assert quote is not None
    assert quote.symbol == "SBIN"
    assert quote.currency == "INR"
    assert quote.exchange == "NSE"
    assert quote.current_price.value == 1010.5
    assert quote.provenance.provider_id == "upstox_market_quote"
    assert quote.provenance.auth_mode == "bearer_token"
    assert any("Authorization" in call[2] for call in client.calls)


def test_statement_adapter_maps_authenticated_upstox_statements() -> None:
    client = FakeJsonClient({})
    adapter = UpstoxStatementAdapter(access_token="secret", http_client=client)
    from contracts.domain.instrument import Instrument
    from contracts.enums import AssetClass
    from data_engine.financial_statement.service import StatementQuery

    bundle = adapter.get_statements(
        StatementQuery(
            instrument=Instrument(symbol="SBIN", asset_class=AssetClass.EQUITY, currency="INR"),
            limit=1,
        )
    )
    assert bundle is not None
    assert bundle.identity.symbol == "SBIN"
    assert bundle.identity.isin == "INE062A01020"
    assert bundle.reporting_currency == "INR"
    assert bundle.periods[0].period_end.year == 2026
    assert bundle.provenance.provider_id == "upstox_financial_statements"
    assert bundle.provenance.auth_mode == "bearer_token"
