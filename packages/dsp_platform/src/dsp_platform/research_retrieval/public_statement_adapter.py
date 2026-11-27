"""Convert supported public filings into canonical financial inputs.

This research-only adapter does not authorize production valuation
or represent public filings as authenticated provider data.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from financial.balance_sheet import BalanceSheet
from financial.cash_flow import CashFlowStatement
from financial.currency import CurrencyRef
from financial.income_statement import IncomeStatement
from financial.models import FinancialStatements
from financial.period import FinancialPeriod, PeriodType
from financial.metadata import (
    StatementMetadata,
    UnitScale,
)

from dsp_platform.research_retrieval.sec_statement_extractor import (
    extract_infosys_fy2025,
)

from dsp_platform.research_retrieval.statement_integrity import (
    validate_statement_period,
)


class PublicStatementError(ValueError):
    pass


def build_public_financial_statements(
    document,
    *,
    period_end: str,
) -> FinancialStatements:

    extracted = extract_infosys_fy2025(document)

    metrics = extracted["periods"].get(period_end)

    if metrics is None:
        raise PublicStatementError(
            "Requested reporting period unavailable"
        )

    integrity = validate_statement_period(metrics)

    def number(name, *, per_share=False):

        record = metrics.get(name)

        if record is None:
            return None

        expected_unit = (
            "INR per share" if per_share else "INR crore"
        )

        if record.get("unit") != expected_unit:

            raise PublicStatementError(
                f"Unexpected unit: {name}"
            )

        if record.get("statement_basis") != "consolidated":

            raise PublicStatementError(
                f"Unexpected statement basis: {name}"
            )

        try:

            value = Decimal(str(record["value"]))

        except (InvalidOperation, KeyError, TypeError):

            raise PublicStatementError(
                f"Invalid financial field: {name}"
            ) from None

        if not value.is_finite():

            raise PublicStatementError(
                f"Non-finite financial field: {name}"
            )

        if per_share:
            return float(value)

        return float(value * Decimal("10000000"))

    period_date = date.fromisoformat(period_end)

    liabilities = (
        Decimal(integrity["total_liabilities"])
        * Decimal("10000000")
    )

    return FinancialStatements(
        period=FinancialPeriod(
            period_type=PeriodType("annual"),
            period_end=period_date,
            fiscal_year=period_date.year,
            currency=CurrencyRef.parse("INR"),
            source="public_sec_filing",
        ),
        income_statement=IncomeStatement(
            revenue=number("revenue"),
            pretax_income=number("profit_before_tax"),
            net_income=number("net_income_total"),
            eps=number("eps_basic", per_share=True),
            diluted_eps=number(
                "eps_diluted",
                per_share=True,
            ),
        ),
        balance_sheet=BalanceSheet(
            cash=number("cash_and_equivalents"),
            current_assets=number("current_assets"),
            current_liabilities=number("current_liabilities"),
            share_capital=number("equity_share_capital"),
            lease_liabilities=(
                number("current_lease_liabilities")
                + number("non_current_lease_liabilities")
                if (
                    number("current_lease_liabilities") is not None
                    and number("non_current_lease_liabilities") is not None
                )
                else None
            ),
            total_assets=number("total_assets"),
            total_liabilities=float(liabilities),
            equity=number("total_equity"),
            total_equity=number("total_equity"),
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=number(
                "operating_cash_flow"
            ),
            capex=number(
                "capital_expenditure_reported"
            ),
            dividends_paid=number("dividends_paid_reported"),
            free_cash_flow=None,
        ),
        statement_metadata=StatementMetadata(
            unit_scale=UnitScale.ACTUAL,
            currency=CurrencyRef.parse("INR"),
            source=extracted["source_url"],
            notes=(
                "Historical consolidated Ind-AS filing. "
                "Monetary values converted from INR crore "
                "to actual INR. Public research evidence, "
                "not authenticated provider data."
            ),
        ),
    )
