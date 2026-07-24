"""Canonical Income Statement model — values only, no ratios."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

__all__ = ["IncomeStatement", "INCOME_STATEMENT_FIELDS"]

INCOME_STATEMENT_FIELDS: tuple[str, ...] = (
    "revenue",
    "cogs",
    "gross_profit",
    "operating_expenses",
    "rd",
    "sga",
    "ebit",
    "ebitda",
    "depreciation",
    "amortization",
    "interest_expense",
    "other_income",
    "pretax_income",
    "tax",
    "net_income",
    "eps",
    "diluted_eps",
    "weighted_shares",
)


@dataclass(frozen=True, slots=True)
class IncomeStatement:
    """Immutable income-statement line items (canonical research schema).

    All monetary fields are optional floats in the statement's unit scale.
    No derived ratios or valuations are computed here.
    """

    revenue: float | None = None
    cogs: float | None = None
    gross_profit: float | None = None
    operating_expenses: float | None = None
    rd: float | None = None
    sga: float | None = None
    ebit: float | None = None
    ebitda: float | None = None
    depreciation: float | None = None
    amortization: float | None = None
    interest_expense: float | None = None
    other_income: float | None = None
    pretax_income: float | None = None
    tax: float | None = None
    net_income: float | None = None
    eps: float | None = None
    diluted_eps: float | None = None
    weighted_shares: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IncomeStatement:
        kwargs = {k: data.get(k) for k in INCOME_STATEMENT_FIELDS}
        return cls(**kwargs)

    def values(self) -> dict[str, float | None]:
        return self.to_dict()
