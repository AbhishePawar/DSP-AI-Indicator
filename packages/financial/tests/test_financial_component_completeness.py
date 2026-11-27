"""Incomplete financial components must not become complete totals."""

import pytest

from financial.balance_sheet import BalanceSheet

from financial.intelligence.balance_engine import (
    _current_assets,
    _total_debt,
)


@pytest.mark.parametrize(
    "short_term,long_term",
    [
        (100.0, None),
        (None, 200.0),
        (0.0, None),
        (None, 0.0),
        (None, None),
    ],
)
def test_incomplete_debt(short_term, long_term):

    bs = BalanceSheet(
        short_term_debt=short_term,
        long_term_debt=long_term,
    )

    assert _total_debt(bs) is None


@pytest.mark.parametrize(
    "short_term,long_term,expected",
    [
        (100.0, 200.0, 300.0),
        (0.0, 200.0, 200.0),
        (100.0, 0.0, 100.0),
        (0.0, 0.0, 0.0),
    ],
)
def test_complete_debt(
    short_term,
    long_term,
    expected,
):

    bs = BalanceSheet(
        short_term_debt=short_term,
        long_term_debt=long_term,
    )

    assert _total_debt(bs) == expected


def test_cash_is_not_total_current_assets():

    bs = BalanceSheet(cash=100.0)

    assert _current_assets(bs) is None


def test_incomplete_asset_components():

    bs = BalanceSheet(
        cash=100.0,
        short_term_investments=50.0,
        accounts_receivable=200.0,
        inventory=None,
        other_current_assets=20.0,
    )

    assert _current_assets(bs) is None


def test_complete_asset_components():

    bs = BalanceSheet(
        cash=100.0,
        short_term_investments=50.0,
        accounts_receivable=200.0,
        inventory=0.0,
        other_current_assets=20.0,
    )

    assert _current_assets(bs) == 370.0


def test_reported_current_assets_take_priority():

    bs = BalanceSheet(
        current_assets=500.0,
        cash=100.0,
    )

    assert _current_assets(bs) == 500.0


def test_reported_zero_current_assets_preserved():

    bs = BalanceSheet(current_assets=0.0)

    assert _current_assets(bs) == 0.0


from financial import FinancialEngine


def test_unknown_inventory_not_assumed_zero():

    bs = BalanceSheet(
        total_assets=1000.0,
        total_liabilities=400.0,
        total_equity=600.0,
        current_assets=400.0,
        current_liabilities=200.0,
        inventory=None,
    )

    result = FinancialEngine().analyze_balance_sheet(bs)

    assert result.liquidity.current_ratio == 2.0
    assert result.liquidity.working_capital == 200.0
    assert result.liquidity.quick_ratio is None
    assert result.liquidity.net_working_capital is None


def test_reported_zero_inventory_is_valid():

    bs = BalanceSheet(
        total_assets=1000.0,
        total_liabilities=400.0,
        total_equity=600.0,
        current_assets=400.0,
        current_liabilities=200.0,
        inventory=0.0,
    )

    result = FinancialEngine().analyze_balance_sheet(bs)

    assert result.liquidity.quick_ratio == 2.0
    assert result.liquidity.net_working_capital == 200.0


def test_unknown_short_term_investments():

    bs = BalanceSheet(
        total_assets=1000.0,
        total_liabilities=400.0,
        total_equity=600.0,
        cash=100.0,
        current_assets=400.0,
        current_liabilities=200.0,
        short_term_investments=None,
    )

    result = FinancialEngine().analyze_balance_sheet(bs)

    assert result.liquidity.cash_ratio is None


def test_reported_zero_short_term_investments():

    bs = BalanceSheet(
        total_assets=1000.0,
        total_liabilities=400.0,
        total_equity=600.0,
        cash=100.0,
        current_assets=400.0,
        current_liabilities=200.0,
        short_term_investments=0.0,
    )

    result = FinancialEngine().analyze_balance_sheet(bs)

    assert result.liquidity.cash_ratio == 0.5


def test_unknown_cash_prevents_net_debt():

    bs = BalanceSheet(
        short_term_debt=100.0,
        long_term_debt=200.0,
        cash=None,
        total_equity=600.0,
        total_assets=1000.0,
    )

    result = FinancialEngine().analyze_balance_sheet(bs)

    assert result.leverage.debt_to_equity == 0.5
    assert result.leverage.net_debt is None
    assert result.leverage.net_debt_to_equity is None


def test_explicit_zero_cash_preserved():

    bs = BalanceSheet(
        short_term_debt=100.0,
        long_term_debt=200.0,
        cash=0.0,
        total_equity=600.0,
        total_assets=1000.0,
    )

    result = FinancialEngine().analyze_balance_sheet(bs)

    assert result.leverage.net_debt == 300.0
    assert result.leverage.net_debt_to_equity == 0.5


def test_partial_debt_prevents_leverage_calculation():

    bs = BalanceSheet(
        short_term_debt=100.0,
        long_term_debt=None,
        cash=50.0,
        total_equity=600.0,
        total_assets=1000.0,
    )

    result = FinancialEngine().analyze_balance_sheet(bs)

    assert result.leverage.debt_to_equity is None
    assert result.leverage.debt_to_assets is None
    assert result.leverage.net_debt is None
