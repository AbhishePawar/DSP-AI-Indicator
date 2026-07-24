"""Canonical Cash Flow Statement model — values only, no ratios."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

__all__ = ["CashFlowStatement", "CASH_FLOW_FIELDS"]

CASH_FLOW_FIELDS: tuple[str, ...] = (
    "operating_cash_flow",
    "capex",
    "acquisitions",
    "investments",
    "asset_sales",
    "investing_cash_flow",
    "debt_issued",
    "debt_repaid",
    "dividends_paid",
    "share_buybacks",
    "share_issuance",
    "financing_cash_flow",
    "fx_effects",
    "net_cash_change",
    "free_cash_flow",
    "owner_earnings",
)


@dataclass(frozen=True, slots=True)
class CashFlowStatement:
    """Immutable cash-flow line items (canonical research schema).

    ``owner_earnings`` is a placeholder for future intelligence modules —
    no calculation is performed in F2.1.
    """

    operating_cash_flow: float | None = None
    capex: float | None = None
    acquisitions: float | None = None
    investments: float | None = None
    asset_sales: float | None = None
    investing_cash_flow: float | None = None
    debt_issued: float | None = None
    debt_repaid: float | None = None
    dividends_paid: float | None = None
    share_buybacks: float | None = None
    share_issuance: float | None = None
    financing_cash_flow: float | None = None
    fx_effects: float | None = None
    net_cash_change: float | None = None
    free_cash_flow: float | None = None
    owner_earnings: float | None = None  # placeholder — no calc in F2.1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CashFlowStatement:
        kwargs = {k: data.get(k) for k in CASH_FLOW_FIELDS}
        return cls(**kwargs)

    def values(self) -> dict[str, float | None]:
        return self.to_dict()
