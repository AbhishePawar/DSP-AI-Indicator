"""U4 — Upstox authenticated fundamentals via U1 identity (mocked HTTP)."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from data_engine.exceptions import ProviderRequestError
from data_engine.upstox_fundamentals import (
    UPSTOX_FUNDAMENTALS_PREFIX,
    UpstoxFundamentalsClient,
    UpstoxFundamentalsRequest,
)


def _eq(*, symbol: str, name: str, exchange: str, isin: str) -> dict[str, Any]:
    return {
        "segment": f"{exchange}_EQ",
        "name": name,
        "exchange": exchange,
        "isin": isin,
        "instrument_type": "EQ",
        "instrument_key": f"{exchange}_EQ|{isin}",
        "trading_symbol": symbol,
        "short_name": symbol,
    }


_INFY = _eq(symbol="INFY", name="Infosys Limited", exchange="NSE", isin="INE009A01021")
_TCS_NSE = _eq(
    symbol="TCS",
    name="Tata Consultancy Services Limited",
    exchange="NSE",
    isin="INE467B01029",
)
_TCS_BSE = _eq(
    symbol="TCS",
    name="Tata Consultancy Services Limited",
    exchange="BSE",
    isin="INE467B01029",
)


def _annual_income() -> dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "type": "consolidated",
            "time_period": "yearly",
            "units_in": "crore",
            "income_statement": [
                {
                    "category": "revenue",
                    "history": [
                        {"period": "Mar 2025", "value": 150000},
                        {"period": "Mar 2024", "value": 140000},
                    ],
                },
                {
                    "category": "operating_profit",
                    "history": [
                        {"period": "Mar 2025", "value": 40000},
                        {"period": "Mar 2024", "value": 38000},
                    ],
                },
                {
                    "category": "net_profit",
                    "history": [
                        {"period": "Mar 2025", "value": 30000},
                        {"period": "Mar 2024", "value": 28000},
                    ],
                },
            ],
            "full_statement": [
                {
                    "particular": "Total Revenue",
                    "history": [
                        {"period": "Mar 2025", "value": 150000},
                        {"period": "Mar 2024", "value": 140000},
                    ],
                },
                {
                    "particular": "Total Expenses",
                    "history": [
                        {"period": "Mar 2025", "value": 110000},
                        {"period": "Mar 2024", "value": 102000},
                    ],
                },
                {
                    "particular": "Profit After Tax",
                    "history": [
                        {"period": "Mar 2025", "value": 30000},
                        {"period": "Mar 2024", "value": 28000},
                    ],
                },
                {
                    "particular": "EPS - Basic",
                    "history": [
                        {"period": "Mar 2025", "value": 50.0},
                        {"period": "Mar 2024", "value": 48.0},
                    ],
                },
                {
                    "particular": "EPS - Diluted",
                    "history": [
                        {"period": "Mar 2025", "value": 49.5},
                        {"period": "Mar 2024", "value": 47.5},
                    ],
                },
            ],
        },
    }


def _quarterly_income() -> dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "type": "consolidated",
            "time_period": "quarterly",
            "units_in": "crore",
            "income_statement": [
                {
                    "category": "revenue",
                    "history": [
                        {"period": "Mar 2025", "value": 40000},
                        {"period": "Dec 2024", "value": 38000},
                    ],
                },
                {
                    "category": "net_profit",
                    "history": [
                        {"period": "Mar 2025", "value": 8000},
                        {"period": "Dec 2024", "value": 7500},
                    ],
                },
            ],
            # Official: full_statement remains annual even for quarterly requests —
            # U4 must NOT merge these into quarterly periods.
            "full_statement": [
                {
                    "particular": "EPS - Diluted",
                    "history": [
                        {"period": "Mar 2025", "value": 49.5},
                        {"period": "Mar 2024", "value": 47.5},
                    ],
                }
            ],
        },
    }


def _balance() -> dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "type": "consolidated",
            "units_in": "crore",
            "history": [
                {"total_asset": 200000, "total_liability": 80000, "period": "Mar 2025"},
                {"total_asset": 180000, "total_liability": 70000, "period": "Mar 2024"},
            ],
            "full_statement": [
                {
                    "particular": "Current Assets",
                    "history": [
                        {"period": "Mar 2025", "value": 50000},
                        {"period": "Mar 2024", "value": 45000},
                    ],
                },
                {
                    "particular": "Current Liabilities",
                    "history": [
                        {"period": "Mar 2025", "value": 30000},
                        {"period": "Mar 2024", "value": 28000},
                    ],
                },
                {
                    "particular": "Net Current Asset",
                    "history": [
                        {"period": "Mar 2025", "value": 20000},
                        {"period": "Mar 2024", "value": 17000},
                    ],
                },
                {
                    "particular": "Total Assets",
                    "history": [
                        {"period": "Mar 2025", "value": 200000},
                        {"period": "Mar 2024", "value": 180000},
                    ],
                },
                {
                    "particular": "Equity Capital",
                    "history": [
                        {"period": "Mar 2025", "value": 120000},
                        {"period": "Mar 2024", "value": 110000},
                    ],
                },
            ],
        },
    }


def _cash() -> dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "type": "consolidated",
            "units_in": "crore",
            "cash_flow": [
                {
                    "category": "operating",
                    "history": [
                        {"period": "Mar 2025", "value": 35000},
                        {"period": "Mar 2024", "value": 32000},
                    ],
                },
                {
                    "category": "investing",
                    "history": [
                        {"period": "Mar 2025", "value": -10000},
                        {"period": "Mar 2024", "value": -9000},
                    ],
                },
                {
                    "category": "financing",
                    "history": [
                        {"period": "Mar 2025", "value": -5000},
                        {"period": "Mar 2024", "value": -4000},
                    ],
                },
            ],
            "full_statement": [
                {
                    "particular": "Cash flow from Operations",
                    "history": [
                        {"period": "Mar 2025", "value": 35000},
                        {"period": "Mar 2024", "value": 32000},
                    ],
                },
                {
                    "particular": "Cash (End of the year)",
                    "history": [
                        {"period": "Mar 2025", "value": 15000},
                        {"period": "Mar 2024", "value": 12000},
                    ],
                },
                {
                    "particular": "Change in WC",
                    "history": [
                        {"period": "Mar 2025", "value": 1000},
                        {"period": "Mar 2024", "value": 800},
                    ],
                },
            ],
        },
    }


class _FakeHttp:
    def __init__(
        self,
        *,
        search: Mapping[str, Any],
        income: Mapping[str, Any] | None = None,
        balance: Mapping[str, Any] | None = None,
        cash: Mapping[str, Any] | None = None,
        error_on: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.search = dict(search)
        self.income = dict(income or _annual_income())
        self.balance = dict(balance or _balance())
        self.cash = dict(cash or _cash())
        self.error_on = error_on
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def get_json(self, url: str, *, params=None, headers=None):
        self.calls.append(
            {"url": url, "params": dict(params or {}), "headers": dict(headers or {})}
        )
        assert headers and str(headers.get("Authorization", "")).startswith("Bearer ")
        if self.error is not None and (self.error_on is None or self.error_on in url):
            raise self.error
        if "instruments/search" in url:
            q = str((params or {}).get("query") or "").upper()
            return self.search.get(q, {"status": "success", "data": []})
        if "/income-statement" in url:
            return self.income
        if "/balance-sheet" in url:
            return self.balance
        if "/cash-flow" in url:
            return self.cash
        raise AssertionError(url)


def _client(
    *,
    search_rows: list[dict[str, Any]],
    symbol: str,
    income: dict[str, Any] | None = None,
    balance: dict[str, Any] | None = None,
    cash: dict[str, Any] | None = None,
    error_on: str | None = None,
    error: Exception | None = None,
    token: str = "u4-test-token",
) -> UpstoxFundamentalsClient:
    http = _FakeHttp(
        search={symbol: {"status": "success", "data": search_rows}},
        income=income,
        balance=balance,
        cash=cash,
        error_on=error_on,
        error=error,
    )
    return UpstoxFundamentalsClient(access_token=token, http_client=http)


def test_annual_income_via_u1() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(
        UpstoxFundamentalsRequest(symbol="INFY", period_type="annual", limit=2)
    )
    assert result.status == "OK"
    assert result.identity is not None
    assert result.identity.isin == "INE009A01021"
    assert result.statements is not None
    assert result.currency == "INR"
    assert result.annual_period_count == 2
    p0 = result.statements.periods[0]
    assert p0.period_type == "annual"
    assert float(p0.revenue.value) == 150000
    assert float(p0.net_income.value) == 30000
    assert float(p0.eps_basic.value) == 50.0
    assert float(p0.eps_diluted.value) == 49.5
    assert result.eps_cagr_basis == "diluted"
    # U1 ISIN used in fundamentals path
    assert any(
        f"{UPSTOX_FUNDAMENTALS_PREFIX}/INE009A01021/income-statement" in c["url"]
        for c in client.http_client.calls  # type: ignore[union-attr]
    )


def test_quarterly_income_does_not_merge_annual_full_statement() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY", income=_quarterly_income())
    result = client.get_fundamentals(
        UpstoxFundamentalsRequest(symbol="INFY", period_type="quarterly", limit=4)
    )
    assert result.status == "OK"
    assert result.quarterly_period_count == 2
    assert result.annual_period_count == 0
    for p in result.statements.periods:  # type: ignore[union-attr]
        assert p.period_type == "quarterly"
        # EPS from annual full_statement must not appear on quarterly periods
        assert not p.eps_diluted.available
    # No BS/CF calls for quarterly
    assert not any("/balance-sheet" in c["url"] for c in client.http_client.calls)  # type: ignore[union-attr]


def test_unknown_period_rejected() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(
        UpstoxFundamentalsRequest(symbol="INFY", period_type="ttm")
    )
    assert result.status == "REJECTED"


def test_unparseable_period_label_skipped() -> None:
    income = _annual_income()
    income["data"]["income_statement"][0]["history"].append(
        {"period": "FY25-H1", "value": 1}
    )
    client = _client(search_rows=[_INFY], symbol="INFY", income=income)
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "OK"
    labels_ok = all(
        p.period_end.month == 3 for p in result.statements.periods  # type: ignore[union-attr]
    )
    assert labels_ok


def test_basic_eps_fallback_basis() -> None:
    income = _annual_income()
    # Remove diluted EPS
    income["data"]["full_statement"] = [
        row
        for row in income["data"]["full_statement"]
        if row["particular"] != "EPS - Diluted"
    ] + [
        {
            "particular": "EPS - Basic",
            "history": [
                {"period": "Mar 2025", "value": 50.0},
                {"period": "Mar 2024", "value": 48.0},
            ],
        }
    ]
    # dedupe basic
    seen = set()
    cleaned = []
    for row in income["data"]["full_statement"]:
        if row["particular"] in seen:
            continue
        seen.add(row["particular"])
        cleaned.append(row)
    income["data"]["full_statement"] = cleaned
    client = _client(search_rows=[_INFY], symbol="INFY", income=income)
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.eps_cagr_basis == "basic"


def test_eps_bases_both_preserved_not_mixed_into_one_field() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    p = result.statements.periods[0]  # type: ignore[union-attr]
    assert p.eps_basic.available and p.eps_diluted.available
    assert float(p.eps_basic.value) != float(p.eps_diluted.value)


def test_ar_inventory_ap_not_fabricated() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    cov = {c.field: c for c in result.coverage}
    assert cov["AR"].upstox_available is False
    assert cov["inventory"].upstox_available is False
    assert cov["AP"].upstox_available is False
    assert cov["AR"].dsp_mapped is False
    # Net Current Asset must not become operating WC
    assert all(not p.working_capital.available for p in result.statements.periods)  # type: ignore[union-attr]


def test_weighted_shares_unavailable() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    cov = {c.field: c for c in result.coverage}
    assert cov["weighted shares"].upstox_available is False
    assert cov["weighted shares"].dsp_mapped is False


def test_ocf_mapped_fcf_capex_absent_in_official_shape() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    p = result.statements.periods[0]  # type: ignore[union-attr]
    assert p.operating_cash_flow.available
    assert float(p.operating_cash_flow.value) == 35000
    assert not p.free_cash_flow.available
    assert not p.capital_expenditures.available
    # OCF not substituted into FCF
    assert p.free_cash_flow.value is None


def test_balance_sheet_core_fields() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    p = result.statements.periods[0]  # type: ignore[union-attr]
    assert float(p.total_assets.value) == 200000
    assert float(p.current_assets.value) == 50000
    assert float(p.current_liabilities.value) == 30000
    assert float(p.total_equity.value) == 120000
    # cash from CF end-of-year when present
    assert p.cash_and_equivalents.available
    assert float(p.cash_and_equivalents.value) == 15000


def test_currency_inr_from_units_crore() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.currency == "INR"
    assert result.statements.reporting_currency == "INR"  # type: ignore[union-attr]
    assert result.statements.periods[0].unit_scale == "crore"  # type: ignore[union-attr]


def test_missing_units_fail_closed() -> None:
    income = _annual_income()
    del income["data"]["units_in"]
    client = _client(search_rows=[_INFY], symbol="INFY", income=income)
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "UNAVAILABLE"
    assert "units" in result.detail.lower() or "currency" in result.detail.lower()


def test_total_expenses_not_mapped_as_cogs() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert not result.statements.periods[0].cost_of_revenue.available  # type: ignore[union-attr]
    cov = {c.field: c for c in result.coverage}
    assert cov["COGS"].dsp_mapped is False


def test_ambiguous_identity() -> None:
    client = _client(search_rows=[_TCS_NSE, _TCS_BSE], symbol="TCS")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="TCS"))
    assert result.status == "AMBIGUOUS"
    assert result.statements is None
    assert not any("/income-statement" in c["url"] for c in client.http_client.calls)  # type: ignore[union-attr]


def test_missing_identity() -> None:
    client = _client(search_rows=[], symbol="ZZZZ")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="ZZZZ"))
    assert result.status == "NOT_FOUND"


def test_forged_client_isin_rejected() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(
        UpstoxFundamentalsRequest(symbol="INFY", client_isin="INE000000000")
    )
    assert result.status == "REJECTED"


def test_forged_client_instrument_key_rejected() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(
        UpstoxFundamentalsRequest(
            symbol="INFY", client_instrument_key="NSE_EQ|FORGED"
        )
    )
    assert result.status == "REJECTED"


def test_missing_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
    client = UpstoxFundamentalsClient(access_token="")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "UNAVAILABLE"
    assert "absent" in result.detail.lower()


@pytest.mark.parametrize("code,fragment", [(401, "401"), (403, "403"), (404, "404"), (429, "429")])
def test_http_errors(code: int, fragment: str) -> None:
    client = _client(
        search_rows=[_INFY],
        symbol="INFY",
        error_on="income-statement",
        error=ProviderRequestError(
            f"HTTP {fragment} for 'https://api.upstox.com/v2/fundamentals/x/income-statement'"
        ),
    )
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "UNAVAILABLE"
    assert fragment in result.detail
    assert result.http_status == code


def test_timeout() -> None:
    client = _client(
        search_rows=[_INFY],
        symbol="INFY",
        error_on="income-statement",
        error=ProviderRequestError(
            "HTTP request to 'https://api.upstox.com/v2/fundamentals/...' failed: TimeoutError"
        ),
    )
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "UNAVAILABLE"


def test_malformed_response() -> None:
    client = _client(
        search_rows=[_INFY],
        symbol="INFY",
        income={"status": "success", "data": "nope"},
    )
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "UNAVAILABLE"


def test_empty_response() -> None:
    empty = {
        "status": "success",
        "data": {
            "type": "consolidated",
            "time_period": "yearly",
            "units_in": "crore",
            "income_statement": [],
            "full_statement": [],
        },
    }
    client = _client(
        search_rows=[_INFY],
        symbol="INFY",
        income=empty,
        balance={"status": "success", "data": {"units_in": "crore", "history": [], "full_statement": []}},
        cash={"status": "success", "data": {"units_in": "crore", "cash_flow": [], "full_statement": []}},
    )
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "EMPTY"


def test_production_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)
    client = UpstoxFundamentalsClient(access_token="")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    assert result.status == "UNAVAILABLE"
    assert "fail-closed" in result.detail.lower()


def test_token_not_leaked() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY", token="super-secret-u4-token")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    blob = str(result.to_public_dict())
    assert "super-secret-u4-token" not in blob
    assert "Bearer" not in blob


def test_coverage_matrix_present() -> None:
    client = _client(search_rows=[_INFY], symbol="INFY")
    result = client.get_fundamentals(UpstoxFundamentalsRequest(symbol="INFY"))
    fields = {c.field for c in result.coverage}
    for required in {
        "revenue",
        "COGS",
        "net income",
        "basic EPS",
        "diluted EPS",
        "weighted shares",
        "OCF",
        "FCF",
        "capex",
        "cash",
        "debt",
        "current assets",
        "current liabilities",
        "total assets",
        "total liabilities",
        "equity",
        "AR",
        "inventory",
        "AP",
        "currency",
    }:
        assert required in fields


def test_live_upstox_u4_optional() -> None:
    from data_engine.upstox_connectivity import resolve_u0_upstox_analytics_token

    token = resolve_u0_upstox_analytics_token()
    if not token:
        pytest.skip("UPSTOX U4 LIVE TEST = NOT RUN; REASON = CREDENTIAL ABSENT")
    client = UpstoxFundamentalsClient(access_token=token)
    result = client.get_fundamentals(
        UpstoxFundamentalsRequest(
            symbol="TCS", preferred_exchange="NSE", period_type="annual", limit=2
        )
    )
    assert result.status in {"OK", "EMPTY", "UNAVAILABLE"}
    assert token not in str(result.to_public_dict())
