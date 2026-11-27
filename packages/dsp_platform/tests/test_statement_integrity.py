"""Accounting reconciliation regression tests."""

from copy import deepcopy

import pytest

from dsp_platform.research_retrieval.statement_integrity import (
    FinancialIntegrityError,
    validate_statement_period,
)


@pytest.fixture
def metrics():

    values = {
        "current_liabilities": "42850",
        "non_current_liabilities": "9850",
        "total_assets": "148903",
        "total_equity": "96203",
        "cash_and_equivalents": "24455",
        "cash_end_of_period": "24455",
        "operating_cash_flow": "35694",
        "capital_expenditure_reported": "-2237",
    }

    return {
        key: {
            "value": value,
            "unit": "INR crore",
            "statement_basis": "consolidated",
        }
        for key, value in values.items()
    }


def test_valid_financial_statement(metrics):

    result = validate_statement_period(metrics)

    assert result["balance_sheet_reconciled"]
    assert result["closing_cash_reconciled"]

    assert result["total_liabilities"] == "52700"

    assert (
        result["operating_cash_flow_less_capex"]
        == "33457"
    )

    assert result["authorized_for_valuation"] is False


@pytest.mark.parametrize(
    "metric,field,value",
    [
        ("total_assets", "value", "17419"),
        ("total_equity", "value", "90000"),
        ("cash_end_of_period", "value", "4321"),
        ("capital_expenditure_reported", "value", "2237"),
        ("total_assets", "value", "NaN"),
        ("total_assets", "value", "Infinity"),
        ("total_assets", "unit", "USD million"),
        ("total_assets", "statement_basis", "standalone"),
        ("current_liabilities", "value", "-100"),
    ],
)
def test_invalid_statement(metrics, metric, field, value):

    changed = deepcopy(metrics)

    changed[metric][field] = value

    with pytest.raises(FinancialIntegrityError):

        validate_statement_period(changed)


def test_missing_metric(metrics):

    metrics.pop("total_assets")

    with pytest.raises(FinancialIntegrityError):

        validate_statement_period(metrics)


def test_negative_operating_cash_flow_allowed(metrics):

    metrics["operating_cash_flow"]["value"] = "-100"

    result = validate_statement_period(metrics)

    assert (
        result["operating_cash_flow_less_capex"]
        == "-2337"
    )


def test_zero_capex_allowed(metrics):

    metrics["capital_expenditure_reported"]["value"] = "0"

    result = validate_statement_period(metrics)

    assert (
        result["operating_cash_flow_less_capex"]
        == "35694"
    )
