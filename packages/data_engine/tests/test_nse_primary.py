"""Official NSE primary parsers — fail closed on unlabeled values."""

from __future__ import annotations

from datetime import date

from data_engine.official_research.nse_primary import (
    parse_financial_results,
    parse_quote_equity_shares,
    parse_shareholding_shares,
)
from data_engine.official_research.source_policy import SourcePolicy


def test_quote_equity_last_price_is_not_shares() -> None:
    payload = {
        "info": {
            "symbol": "INFY",
            "isin": "INE009A01021",
            "issuedSize": 4151511667,
        },
        "priceInfo": {"lastPrice": 1.0, "previousClose": 2.0},
    }
    extracted, last_ignored, issue = parse_quote_equity_shares(
        payload, isin="INE009A01021", ticker="INFY"
    )
    assert last_ignored is True
    assert extracted is not None
    assert extracted.as_of is None
    assert issue is None or "as_of" not in (issue or "")


def test_quote_equity_wrong_isin_rejected() -> None:
    payload = {"info": {"symbol": "INFY", "isin": "INE000000000", "issuedSize": 10}}
    extracted, _, issue = parse_quote_equity_shares(
        payload, isin="INE009A01021", ticker="INFY"
    )
    assert extracted is None
    assert issue == "quote-equity ISIN mismatch"


def test_shareholding_dated_shares() -> None:
    payload = [
        {
            "symbol": "INFY",
            "date": "30-Jun-2026",
            "totalNoOfShares": 4151511667,
        }
    ]
    extracted = parse_shareholding_shares(payload, ticker="INFY")
    assert extracted is not None
    assert extracted.as_of == date(2026, 6, 30)
    assert extracted.value == "4151511667"


def test_financial_results_require_annual_consolidated_unit() -> None:
    payload = [
        {
            "symbol": "INFY",
            "period": "Annual",
            "fromTo": "01-Apr-2025 to 31-Mar-2026",
            "toDate": "31-Mar-2026",
            "resultType": "Consolidated",
            "unit": "Rs. Crore",
            "particulars": "Profit after tax",
            "value": "26733",
        }
    ]
    fields, basis, unit, issue = parse_financial_results(payload, ticker="INFY")
    assert issue is None
    assert basis == "consolidated"
    assert unit == "crore_to_actual"
    assert "net_income" in fields
    assert fields["net_income"].as_of == date(2026, 3, 31)
    assert fields["net_income"].value == "267330000000"


def test_operating_profit_is_not_ebit() -> None:
    payload = [
        {
            "symbol": "INFY",
            "period": "Annual",
            "toDate": "31-Mar-2026",
            "resultType": "Consolidated",
            "unit": "Rs. Crore",
            "particulars": "Operating profit",
            "value": "100",
        }
    ]
    fields, _, _, _ = parse_financial_results(payload, ticker="INFY")
    assert "ebit" not in fields or fields["ebit"].semantic_status == "UNKNOWN"


def test_quarterly_results_rejected() -> None:
    payload = [
        {
            "symbol": "INFY",
            "period": "Quarterly",
            "toDate": "30-Jun-2026",
            "resultType": "Consolidated",
            "unit": "Rs. Crore",
            "ProfitAfterTax": "1",
        }
    ]
    fields, _, _, issue = parse_financial_results(payload, ticker="INFY")
    assert fields == {}
    assert issue == "no annual NSE financial result row"


def test_unlabeled_unit_rejected() -> None:
    payload = [
        {
            "symbol": "INFY",
            "period": "Annual",
            "toDate": "31-Mar-2026",
            "resultType": "Consolidated",
            "ProfitAfterTax": "26733",
        }
    ]
    fields, _, _, issue = parse_financial_results(payload, ticker="INFY")
    assert fields == {}
    assert issue is not None
    assert "unit" in issue


def test_yahoo_still_cannot_verify() -> None:
    policy = SourcePolicy()
    assert not policy.may_verify("https://finance.yahoo.com/quote/INFY")
    assert policy.may_verify(
        "https://www.nseindia.com/api/corporates-financial-results",
        source_type="regulator",
    )
