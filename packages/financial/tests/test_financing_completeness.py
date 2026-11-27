"""Financial financing evidence completeness tests."""

import pytest

from financial import FinancialEngine
from financial.cash_flow import CashFlowStatement


def analyze(**kwargs):

    values = {
        "operating_cash_flow": 100.0,
        "capex": -20.0,
    }

    values.update(kwargs)

    return FinancialEngine().analyze_cash_flow(
        CashFlowStatement(**values)
    )


@pytest.mark.parametrize(
    "issued,repaid",
    [
        (50.0, None),
        (None, 20.0),
        (0.0, None),
        (None, 0.0),
        (None, None),
    ],
)
def test_incomplete_borrowing(issued, repaid):

    result = analyze(
        debt_issued=issued,
        debt_repaid=repaid,
    )

    assert result.financing.financing_dependence is None


@pytest.mark.parametrize(
    "issued,repaid,expected",
    [
        (50.0, -20.0, 0.3),
        (0.0, -20.0, 0.0),
        (50.0, 0.0, 0.5),
        (0.0, 0.0, 0.0),
    ],
)
def test_complete_borrowing(issued, repaid, expected):

    result = analyze(
        debt_issued=issued,
        debt_repaid=repaid,
    )

    assert (
        result.financing.financing_dependence
        == pytest.approx(expected)
    )


@pytest.mark.parametrize(
    "dividends,buybacks",
    [
        (10.0, None),
        (None, 10.0),
        (0.0, None),
        (None, 0.0),
        (None, None),
    ],
)
def test_incomplete_shareholder_distributions(
    dividends,
    buybacks,
):

    result = analyze(
        dividends_paid=dividends,
        share_buybacks=buybacks,
    )

    assert (
        result.financing.capital_allocation_quality
        is None
    )


def test_explicit_zero_distributions():

    result = analyze(
        dividends_paid=0.0,
        share_buybacks=0.0,
    )

    assert (
        result.financing.capital_allocation_quality
        == pytest.approx(0.7)
    )


def test_reported_investing_total_preserved():

    result = analyze(
        investing_cash_flow=-60.0,
    )

    assert result.investing.investment_activity == -60.0


def test_partial_investing_activity():

    result = analyze(
        investing_cash_flow=None,
        acquisitions=None,
        investments=None,
        asset_sales=None,
    )

    assert result.investing.investment_activity is None


def test_complete_investing_components():

    result = analyze(
        investing_cash_flow=None,
        acquisitions=0.0,
        investments=-10.0,
        asset_sales=5.0,
    )

    assert result.investing.investment_activity == -25.0


def test_zero_capex_intensity_preserved():

    result = analyze(capex=0.0)

    assert result.investing.capex_intensity == 0.0
