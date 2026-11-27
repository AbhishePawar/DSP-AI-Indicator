"""Missing financial evidence must not become assumed zero."""

import pytest

from financial import FinancialEngine
from financial.balance_sheet import BalanceSheet
from financial.cash_flow import CashFlowStatement


@pytest.mark.parametrize(
    "goodwill,intangibles",
    [
        (None, None),
        (None, 25.0),
        (25.0, None),
    ],
)
def test_missing_intangibles_not_assumed_zero(
    goodwill,
    intangibles,
):

    statement = BalanceSheet(
        total_assets=1000.0,
        total_equity=600.0,
        equity=600.0,
        total_liabilities=400.0,
        current_assets=500.0,
        current_liabilities=200.0,
        goodwill=goodwill,
        intangibles=intangibles,
    )

    result = FinancialEngine().analyze_balance_sheet(
        statement
    )

    assert result.equity.tangible_book_value is None
    assert result.equity.capital_quality is None
    assert result.assets.asset_quality_score is None


def test_explicit_zero_intangibles_is_valid():

    statement = BalanceSheet(
        total_assets=1000.0,
        total_equity=600.0,
        equity=600.0,
        total_liabilities=400.0,
        goodwill=0.0,
        intangibles=0.0,
    )

    result = FinancialEngine().analyze_balance_sheet(
        statement
    )

    assert result.equity.tangible_book_value == 600.0

    assert result.equity.capital_quality == pytest.approx(
        0.6
    )

    assert result.assets.asset_quality_score == 1.0


def test_known_intangibles_are_deducted():

    statement = BalanceSheet(
        total_assets=1000.0,
        total_equity=600.0,
        equity=600.0,
        total_liabilities=400.0,
        goodwill=50.0,
        intangibles=50.0,
    )

    result = FinancialEngine().analyze_balance_sheet(
        statement
    )

    assert result.equity.tangible_book_value == 500.0

    assert result.assets.asset_quality_score == pytest.approx(
        0.9
    )


def test_unknown_dividends_do_not_produce_cash_surplus():

    statement = CashFlowStatement(
        operating_cash_flow=100.0,
        capex=-20.0,
        dividends_paid=None,
    )

    result = FinancialEngine().analyze_cash_flow(
        statement
    )

    payload = result.to_dict()

    def values(node, field):

        found = []

        if isinstance(node, dict):

            if field in node:
                found.append(node[field])

            for item in node.values():
                found.extend(values(item, field))

        elif isinstance(node, (list, tuple)):

            for item in node:
                found.extend(values(item, field))

        return found

    surplus = values(payload, "cash_surplus")

    assert surplus
    assert all(value is None for value in surplus)


def test_one_period_does_not_prove_cash_sustainability():

    statement = CashFlowStatement(
        operating_cash_flow=100.0,
        capex=-20.0,
    )

    result = FinancialEngine().analyze_cash_flow(
        statement
    )

    assert result.quality.cash_sustainability is None
