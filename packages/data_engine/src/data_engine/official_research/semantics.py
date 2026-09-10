"""Financial/share semantic discipline and valuation input gate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from data_engine.official_research.currentness import CapitalEvent, market_cap_status
from data_engine.official_research.models import FailureStatus, PriceSnapshot

__all__ = [
    "SEMANTIC_ALIASES_FORBIDDEN",
    "ValuationGateResult",
    "cannot_derive_shares",
    "semantic_field_status",
    "valuation_gate",
]

SEMANTIC_ALIASES_FORBIDDEN: dict[str, frozenset[str]] = {
    "ebit": frozenset(
        {"operating profit", "operating_profit", "results from operating activities"}
    ),
    "capex": frozenset(
        {
            "ppe purchase",
            "purchase of property, plant and equipment",
            "intangible purchase",
        }
    ),
    "debt": frozenset({"lease liabilities", "leases"}),
}

_SHARE_FORBIDDEN_SOURCES = frozenset(
    {"eps", "market_cap", "price", "market capitalization"}
)


def semantic_field_status(
    *, requested_field: str, document_label: str
) -> FailureStatus:
    """If the document does not support the transformation, return UNKNOWN."""
    requested = requested_field.strip().lower().replace(" ", "_")
    label = document_label.strip().lower()
    forbidden = SEMANTIC_ALIASES_FORBIDDEN.get(requested, frozenset())
    if label in forbidden or label.replace(" ", "_") in forbidden:
        return "UNKNOWN"
    if requested == "ebit" and "ebit" not in label:
        return "UNKNOWN"
    if requested == "debt" and "lease" in label and "borrow" not in label:
        return "UNKNOWN"
    if requested == "capex" and label in forbidden:
        return "UNKNOWN"
    return "VERIFIED"


def cannot_derive_shares(source_kind: str) -> bool:
    return source_kind.strip().lower() in _SHARE_FORBIDDEN_SOURCES


@dataclass(frozen=True, slots=True)
class ValuationGateResult:
    method: str | None
    status: FailureStatus
    detail: str


def valuation_gate(
    *,
    cfo: bool = False,
    capex: bool = False,
    net_income: bool = False,
    equity: bool = False,
    shares: bool = False,
    price: PriceSnapshot | None = None,
    shares_as_of: date | None = None,
    shares_current_through: date | None = None,
    corporate_actions: tuple[CapitalEvent, ...] = (),
) -> ValuationGateResult:
    """Deterministic gate only. LLMs do not calculate."""
    if price is not None and shares and shares_as_of is not None:
        compat = market_cap_status(
            price_as_of=price.as_of,
            shares_as_of=shares_as_of,
            shares_current_through=shares_current_through,
            corporate_actions=corporate_actions,
        )
        if compat != "VERIFIED":
            return ValuationGateResult(
                method=None,
                status="REFRESH_REQUIRED",
                detail="price_as_of and shares_as_of are not compatible",
            )
        if price.price_kind in {"UNKNOWN", "PREVIOUS_CLOSE"}:
            return ValuationGateResult(
                method=None,
                status="UNAVAILABLE",
                detail=(
                    "MoS requires a labeled EOD/delayed/realtime price, "
                    "not previous close as current"
                ),
            )
        return ValuationGateResult(
            method="mos", status="VERIFIED", detail="MoS inputs present"
        )
    if cfo and capex:
        return ValuationGateResult(
            method="dcf", status="VERIFIED", detail="CFO + capex"
        )
    if net_income and shares:
        return ValuationGateResult(
            method="earnings", status="VERIFIED", detail="NI + shares"
        )
    if equity and shares:
        return ValuationGateResult(
            method="book", status="VERIFIED", detail="equity + shares"
        )
    return ValuationGateResult(
        method=None,
        status="UNAVAILABLE",
        detail="VALUATION UNAVAILABLE",
    )
