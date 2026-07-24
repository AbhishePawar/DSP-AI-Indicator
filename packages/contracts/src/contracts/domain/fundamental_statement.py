"""FundamentalStatement domain contract.

A :class:`FundamentalStatement` captures the raw, as-reported line items
from a company's financial statements for a single reporting period. It
contains no ratios, scores, or derived metrics — those are computed by the
Fundamental Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from contracts._validation import ensure_non_empty_str
from contracts.domain.instrument import Instrument
from contracts.enums import StatementPeriodType
from contracts.exceptions import ContractValidationError

_MIN_FISCAL_YEAR = 1900
_MAX_FISCAL_YEAR = 2200


@dataclass(frozen=True, slots=True)
class FundamentalStatement:
    """Immutable, as-reported financial statement for one period.

    All line items below ``currency`` are optional because reporting
    completeness varies by provider, jurisdiction, and instrument type.
    Values are stored exactly as reported — no ratios or derived figures
    are computed here; that is the Fundamental Engine's responsibility.

    Attributes:
        instrument: The instrument this statement describes.
        period_end: Calendar date the reporting period ended.
        period_type: Whether this is an annual, quarterly, or TTM statement.
        fiscal_year: Fiscal year the period belongs to.
        currency: ISO 4217 currency code of all monetary values, normalized
            to uppercase.
        revenue: Total revenue / net sales.
        cost_of_revenue: Cost of goods or services sold.
        gross_profit: Revenue minus cost of revenue, as reported.
        operating_income: Income from core operations.
        net_income: Bottom-line net income attributable to shareholders.
        eps_basic: Basic earnings per share.
        eps_diluted: Diluted earnings per share.
        total_assets: Total reported assets.
        total_liabilities: Total reported liabilities.
        total_equity: Total shareholders' equity.
        cash_and_equivalents: Cash and cash equivalents on the balance sheet.
        total_debt: Total interest-bearing debt.
        operating_cash_flow: Net cash flow from operating activities.
        investing_cash_flow: Net cash flow from investing activities.
        financing_cash_flow: Net cash flow from financing activities.
        capital_expenditures: Cash used for capital expenditures.
        extra_line_items: Additional as-reported line items not covered by
            the explicit fields above, as ``(label, value)`` pairs.
    """

    instrument: Instrument
    period_end: date
    period_type: StatementPeriodType
    fiscal_year: int
    currency: str
    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps_basic: float | None = None
    eps_diluted: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    cash_and_equivalents: float | None = None
    total_debt: float | None = None
    operating_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None
    capital_expenditures: float | None = None
    extra_line_items: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        """Validate identifying fields and fiscal year plausibility.

        Raises:
            ContractValidationError: If ``currency`` is not a 3-letter
                code, or ``fiscal_year`` falls outside a plausible
                calendar-year range.
        """
        currency = ensure_non_empty_str(self.currency, field_name="currency")
        currency = currency.strip().upper()
        if len(currency) != 3:
            msg = f"currency must be a 3-letter ISO 4217 code, got {currency!r}"
            raise ContractValidationError(msg)
        if not _MIN_FISCAL_YEAR <= self.fiscal_year <= _MAX_FISCAL_YEAR:
            msg = f"fiscal_year must be plausible, got {self.fiscal_year}"
            raise ContractValidationError(msg)

        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "extra_line_items", tuple(self.extra_line_items))
