"""Canonical Balance Sheet model — values only, no ratios."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

__all__ = ["BalanceSheet", "BALANCE_SHEET_FIELDS"]

BALANCE_SHEET_FIELDS: tuple[str, ...] = (
    "cash",
    "short_term_investments",
    "accounts_receivable",
    "inventory",
    "other_current_assets",
    "current_assets",
    "ppe",
    "goodwill",
    "intangibles",
    "investments",
    "other_assets",
    "total_assets",
    "accounts_payable",
    "short_term_debt",
    "current_liabilities",
    "long_term_debt",
    "lease_liabilities",
    "deferred_tax",
    "other_liabilities",
    "total_liabilities",
    "minority_interest",
    "share_capital",
    "reserves",
    "retained_earnings",
    "treasury_shares",
    "equity",
    "total_equity",
)


@dataclass(frozen=True, slots=True)
class BalanceSheet:
    """Immutable balance-sheet line items (canonical research schema)."""

    cash: float | None = None
    short_term_investments: float | None = None
    accounts_receivable: float | None = None
    inventory: float | None = None
    other_current_assets: float | None = None
    current_assets: float | None = None
    ppe: float | None = None
    goodwill: float | None = None
    intangibles: float | None = None
    investments: float | None = None
    other_assets: float | None = None
    total_assets: float | None = None
    accounts_payable: float | None = None
    short_term_debt: float | None = None
    current_liabilities: float | None = None
    long_term_debt: float | None = None
    lease_liabilities: float | None = None
    deferred_tax: float | None = None
    other_liabilities: float | None = None
    total_liabilities: float | None = None
    minority_interest: float | None = None
    share_capital: float | None = None
    reserves: float | None = None
    retained_earnings: float | None = None
    treasury_shares: float | None = None
    equity: float | None = None
    total_equity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BalanceSheet:
        kwargs = {k: data.get(k) for k in BALANCE_SHEET_FIELDS}
        return cls(**kwargs)

    def values(self) -> dict[str, float | None]:
        return self.to_dict()
