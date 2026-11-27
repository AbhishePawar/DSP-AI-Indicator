"""Accounting integrity checks for extracted public financial statements."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


class FinancialIntegrityError(ValueError):
    pass


def validate_statement_period(metrics):

    def value(name):

        record = metrics.get(name)

        if record is None:
            raise FinancialIntegrityError(
                f"Missing financial metric: {name}"
            )

        if record.get("unit") != "INR crore":
            raise FinancialIntegrityError(
                f"Unexpected reporting unit: {name}"
            )

        if record.get("statement_basis") != "consolidated":
            raise FinancialIntegrityError(
                f"Unexpected statement basis: {name}"
            )

        try:

            number = Decimal(str(record["value"]))

        except (InvalidOperation, KeyError, TypeError):

            raise FinancialIntegrityError(
                f"Invalid numeric value: {name}"
            ) from None

        if not number.is_finite():

            raise FinancialIntegrityError(
                f"Non-finite financial value: {name}"
            )

        return number

    current_liabilities = value("current_liabilities")

    non_current_liabilities = value(
        "non_current_liabilities"
    )

    liabilities = (
        current_liabilities
        + non_current_liabilities
    )

    assets = value("total_assets")
    equity = value("total_equity")

    if assets <= 0:
        raise FinancialIntegrityError(
            "Invalid total assets"
        )

    if (
        current_liabilities < 0
        or non_current_liabilities < 0
    ):
        raise FinancialIntegrityError(
            "Negative reported liabilities"
        )

    if assets != liabilities + equity:

        raise FinancialIntegrityError(
            "Balance sheet reconciliation failed"
        )

    cash = value("cash_and_equivalents")

    closing_cash = value("cash_end_of_period")

    if cash != closing_cash:

        raise FinancialIntegrityError(
            "Closing cash reconciliation failed"
        )

    if cash < 0:

        raise FinancialIntegrityError(
            "Negative reported cash balance"
        )

    operating_cash_flow = value(
        "operating_cash_flow"
    )

    capex = value(
        "capital_expenditure_reported"
    )

    if capex > 0:

        raise FinancialIntegrityError(
            "Incorrect reported capex sign"
        )

    return {
        "balance_sheet_reconciled": True,
        "closing_cash_reconciled": True,
        "total_liabilities": str(liabilities),
        "operating_cash_flow_less_capex": str(
            operating_cash_flow + capex
        ),
        "unit": "INR crore",
        "authorized_for_valuation": False,
    }
