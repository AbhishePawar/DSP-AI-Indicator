"""Deterministic DSP derived fields. Calculations are not source evidence.

Formulas reuse existing DSP definitions:

* market_cap = verified_price × verified_total_outstanding  (composition verified_evidence)
* net_debt = total_debt − cash  (financial FORMULA_NET_DEBT)
  Debt is the verified ``debt`` field (total borrowings). Leases/payables are not substituted.
* enterprise_value = market_cap + net_debt
* fcf = operating_cash_flow − abs(capex)  (financial FORMULA_FCF)

Derived values never become EvidenceItem source rows and cannot establish their inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from data_engine.official_research.currentness import derived_market_cap_input_status
from data_engine.official_research.extraction import (
    VALUATION_SHARE_SEMANTIC,
    canonicalize_period,
    normalize_numeric_to_actual,
    periods_comparable,
)
from data_engine.official_research.models import PriceSnapshot
from data_engine.official_research.verified_dataset import (
    FinancialField,
    FinancialSnapshotVerified,
    ShareCountSnapshot,
    VerifiedDataset,
)

__all__ = [
    "DERIVED_FORMULAS",
    "DerivedFieldResult",
    "DerivedFieldSet",
    "derive_dsp_fields",
    "refuse_derived_as_evidence",
]

FORMULA_MARKET_CAP = "official_research.derived.market_cap.v1"
FORMULA_NET_DEBT = "net_debt"
FORMULA_ENTERPRISE_VALUE = "official_research.derived.enterprise_value.v1"
FORMULA_FCF = "fcf"
FORMULA_FCF_YIELD = "official_research.derived.fcf_yield.v1"
FORMULA_EV_EBIT = "official_research.derived.ev_ebit.v1"
FORMULA_EV_EBITDA = "official_research.derived.ev_ebitda.v1"
FORMULA_PE = "official_research.derived.price_to_earnings.v1"

DERIVED_FORMULAS: dict[str, str] = {
    "market_cap": "price * shares_outstanding",
    "net_debt": "total_debt - cash",
    "enterprise_value": "market_cap + net_debt",
    "fcf": "operating_cash_flow - abs(capex)",
    "fcf_yield": "fcf / market_cap",
    "ev_ebit": "enterprise_value / ebit",
    "ev_ebitda": "enterprise_value / ebitda",
    "price_to_earnings": "market_cap / net_income",
}

_PRICE_OK = frozenset({"EOD", "REALTIME", "DELAYED_15M"})
_DERIVED_NAMES = frozenset(DERIVED_FORMULAS)


@dataclass(frozen=True, slots=True)
class DerivedFieldResult:
    field: str
    value: Decimal | None
    status: str
    formula_version: str
    formula: str
    input_fields: tuple[str, ...]
    input_evidence_ids: tuple[str, ...]
    calculated_at: datetime
    detail: str
    as_of: date | None = None
    currency: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "derived_field": self.field,
            "value": None if self.value is None else str(self.value),
            "calculation_status": self.status,
            "formula_version": self.formula_version,
            "formula": self.formula,
            "input_fields": list(self.input_fields),
            "input_evidence_ids": list(self.input_evidence_ids),
            "calculated_at": self.calculated_at.isoformat(),
            "detail": self.detail,
            "as_of": None if self.as_of is None else self.as_of.isoformat(),
            "currency": self.currency,
            "is_source_evidence": False,
        }


@dataclass(frozen=True, slots=True)
class DerivedFieldSet:
    market_cap: DerivedFieldResult
    net_debt: DerivedFieldResult
    enterprise_value: DerivedFieldResult
    fcf: DerivedFieldResult
    fcf_yield: DerivedFieldResult
    ev_ebit: DerivedFieldResult
    ev_ebitda: DerivedFieldResult
    price_to_earnings: DerivedFieldResult
    calculated_at: datetime

    def as_tuple(self) -> tuple[DerivedFieldResult, ...]:
        return (
            self.market_cap,
            self.net_debt,
            self.enterprise_value,
            self.fcf,
            self.fcf_yield,
            self.ev_ebit,
            self.ev_ebitda,
            self.price_to_earnings,
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {item.field: item.to_public_dict() for item in self.as_tuple()}


def refuse_derived_as_evidence(field: str) -> None:
    if field in _DERIVED_NAMES:
        raise ValueError(f"{field} is derived data and cannot become source evidence")


def derive_dsp_fields(
    dataset: VerifiedDataset,
    *,
    calculated_at: datetime | None = None,
) -> DerivedFieldSet:
    """Calculate derived DSP fields from VERIFIED primitives only."""
    now = calculated_at or datetime.now(tz=UTC)
    market_cap = _market_cap(dataset, now)
    net_debt = _net_debt(dataset, now)
    enterprise_value = _enterprise_value(market_cap, net_debt, now)
    fcf = _fcf(dataset, now)
    return DerivedFieldSet(
        market_cap=market_cap,
        net_debt=net_debt,
        enterprise_value=enterprise_value,
        fcf=fcf,
        fcf_yield=_ratio(
            "fcf_yield",
            FORMULA_FCF_YIELD,
            DERIVED_FORMULAS["fcf_yield"],
            fcf,
            market_cap,
            now,
        ),
        ev_ebit=_ratio_with_field(
            "ev_ebit",
            FORMULA_EV_EBIT,
            DERIVED_FORMULAS["ev_ebit"],
            enterprise_value,
            dataset,
            "ebit",
            now,
        ),
        ev_ebitda=_ratio_with_field(
            "ev_ebitda",
            FORMULA_EV_EBITDA,
            DERIVED_FORMULAS["ev_ebitda"],
            enterprise_value,
            dataset,
            "ebitda",
            now,
        ),
        price_to_earnings=_ratio_with_field(
            "price_to_earnings",
            FORMULA_PE,
            DERIVED_FORMULAS["price_to_earnings"],
            market_cap,
            dataset,
            "net_income",
            now,
        ),
        calculated_at=now,
    )


def _blocked(
    field: str,
    formula_version: str,
    formula: str,
    inputs: tuple[str, ...],
    now: datetime,
    *,
    status: str,
    detail: str,
    evidence_ids: tuple[str, ...] = (),
) -> DerivedFieldResult:
    return DerivedFieldResult(
        field=field,
        value=None,
        status=status,
        formula_version=formula_version,
        formula=formula,
        input_fields=inputs,
        input_evidence_ids=evidence_ids,
        calculated_at=now,
        detail=detail,
    )


def _stale_or_conflict(status: str) -> str | None:
    if status == "REFRESH_REQUIRED":
        return "STALE_INPUT"
    if status == "CONFLICT":
        return "CONFLICT_INPUT"
    if status in {
        "UNKNOWN",
        "UNAVAILABLE",
        "REJECTED",
        "BLOCKED",
        "CALCULATION_BLOCKED",
    }:
        return "BLOCKED"
    return None


def _ids(price: PriceSnapshot, shares: ShareCountSnapshot) -> tuple[str, ...]:
    found: list[str] = []
    if shares.evidence_ids:
        found.extend(shares.evidence_ids)
    elif shares.evidence_id:
        found.append(shares.evidence_id)
    if price.source_url:
        found.append(price.source_url)
    return tuple(found)


def _market_cap(dataset: VerifiedDataset, now: datetime) -> DerivedFieldResult:
    inputs = ("price", "shares_outstanding")
    for status, name in (
        (dataset.price_status, "price"),
        (dataset.shares_status, "shares"),
    ):
        mapped = _stale_or_conflict(status)
        if mapped:
            return _blocked(
                "market_cap",
                FORMULA_MARKET_CAP,
                DERIVED_FORMULAS["market_cap"],
                inputs,
                now,
                status=mapped,
                detail=f"{name} status={status}",
            )
    price = dataset.price
    shares = dataset.shares
    if price is None or shares is None:
        return _blocked(
            "market_cap",
            FORMULA_MARKET_CAP,
            DERIVED_FORMULAS["market_cap"],
            inputs,
            now,
            status="BLOCKED",
            detail="missing verified price or shares",
        )
    if price.price_kind not in _PRICE_OK:
        return _blocked(
            "market_cap",
            FORMULA_MARKET_CAP,
            DERIVED_FORMULAS["market_cap"],
            inputs,
            now,
            status="BLOCKED",
            detail=f"price_kind={price.price_kind} cannot feed current market cap",
        )
    if shares.semantic_type != VALUATION_SHARE_SEMANTIC:
        return _blocked(
            "market_cap",
            FORMULA_MARKET_CAP,
            DERIVED_FORMULAS["market_cap"],
            inputs,
            now,
            status="BLOCKED",
            detail="only TOTAL_OUTSTANDING may feed market cap",
        )
    compat = derived_market_cap_input_status(
        price_as_of=price.as_of,
        shares_as_of=shares.as_of,
        corporate_actions=dataset.capital_events,
        shares_current_through=shares.current_through,
        ca_checked_through=shares.ca_checked_through,
    )
    if compat != "VERIFIED":
        return _blocked(
            "market_cap",
            FORMULA_MARKET_CAP,
            DERIVED_FORMULAS["market_cap"],
            inputs,
            now,
            status="STALE_INPUT" if compat == "REFRESH_REQUIRED" else "BLOCKED",
            detail="price and shares as_of are not compatible",
        )
    currency = price.currency
    if dataset.identity is not None and dataset.identity.currency != currency:
        return _blocked(
            "market_cap",
            FORMULA_MARKET_CAP,
            DERIVED_FORMULAS["market_cap"],
            inputs,
            now,
            status="CALCULATION_BLOCKED",
            detail="price currency incompatible with listing currency",
        )
    return DerivedFieldResult(
        field="market_cap",
        value=price.price * shares.shares,
        status="CALCULATED",
        formula_version=FORMULA_MARKET_CAP,
        formula=DERIVED_FORMULAS["market_cap"],
        input_fields=inputs,
        input_evidence_ids=_ids(price, shares),
        calculated_at=now,
        detail="verified_price × verified_total_outstanding",
        as_of=price.as_of,
        currency=currency,
    )


def _financial_amount(
    dataset: VerifiedDataset, name: str
) -> tuple[Decimal | None, str, FinancialField | None]:
    if name not in {"revenue", "ebit", "net_income", "equity", "cash", "cfo", "capex", "debt"}:
        return None, "BLOCKED", None
    status = dataset.field_status(name)
    mapped = _stale_or_conflict(status)
    if mapped:
        return None, mapped, None
    if dataset.financials is None:
        return None, "BLOCKED", None
    item = getattr(dataset.financials, name, None)
    if not isinstance(item, FinancialField) or item.value is None:
        return None, "BLOCKED", None
    return item.value, "OK", item


def _unit_ok(financials: FinancialSnapshotVerified | None) -> bool:
    if financials is None:
        return False
    scale = str(financials.unit_scale or "").strip().lower()
    if not scale:
        return False
    return normalize_numeric_to_actual("1", scale) is not None


def _same_period(left: FinancialField | None, right: FinancialField | None) -> bool:
    if left is None or right is None:
        return False
    if left.as_of and right.as_of and left.as_of == right.as_of:
        return True
    a = canonicalize_period(None, as_of=left.as_of)
    b = canonicalize_period(None, as_of=right.as_of)
    return periods_comparable(a, b)


def _net_debt(dataset: VerifiedDataset, now: datetime) -> DerivedFieldResult:
    inputs = ("debt", "cash")
    if dataset.financials is not None and not _unit_ok(dataset.financials):
        return _blocked(
            "net_debt",
            FORMULA_NET_DEBT,
            DERIVED_FORMULAS["net_debt"],
            inputs,
            now,
            status="CALCULATION_BLOCKED",
            detail="financial unit cannot be established",
        )
    debt, debt_status, debt_field = _financial_amount(dataset, "debt")
    cash, cash_status, cash_field = _financial_amount(dataset, "cash")
    if debt_status != "OK":
        return _blocked(
            "net_debt",
            FORMULA_NET_DEBT,
            DERIVED_FORMULAS["net_debt"],
            inputs,
            now,
            status=debt_status,
            detail="debt unavailable; zero is not substituted",
        )
    if cash_status != "OK":
        return _blocked(
            "net_debt",
            FORMULA_NET_DEBT,
            DERIVED_FORMULAS["net_debt"],
            inputs,
            now,
            status=cash_status,
            detail="cash unavailable; zero is not substituted",
        )
    if not _same_period(debt_field, cash_field):
        return _blocked(
            "net_debt",
            FORMULA_NET_DEBT,
            DERIVED_FORMULAS["net_debt"],
            inputs,
            now,
            status="CALCULATION_BLOCKED",
            detail="debt and cash periods are not compatible",
        )
    assert debt is not None and cash is not None
    return DerivedFieldResult(
        field="net_debt",
        value=debt - cash,
        status="CALCULATED",
        formula_version=FORMULA_NET_DEBT,
        formula=DERIVED_FORMULAS["net_debt"],
        input_fields=inputs,
        input_evidence_ids=tuple(
            item
            for item in (
                None if debt_field is None else debt_field.evidence_id,
                None if cash_field is None else cash_field.evidence_id,
            )
            if item
        ),
        calculated_at=now,
        detail="verified total borrowings minus verified cash; leases not included",
        as_of=None if debt_field is None else debt_field.as_of,
        currency=None if dataset.identity is None else dataset.identity.currency,
    )


def _enterprise_value(
    market_cap: DerivedFieldResult,
    net_debt: DerivedFieldResult,
    now: datetime,
) -> DerivedFieldResult:
    inputs = ("market_cap", "debt", "cash")
    if market_cap.status != "CALCULATED" or market_cap.value is None:
        status = (
            market_cap.status
            if market_cap.status in {"STALE_INPUT", "CONFLICT_INPUT", "CALCULATION_BLOCKED"}
            else "BLOCKED"
        )
        return _blocked(
            "enterprise_value",
            FORMULA_ENTERPRISE_VALUE,
            DERIVED_FORMULAS["enterprise_value"],
            inputs,
            now,
            status=status,
            detail="market_cap is not calculated",
        )
    if net_debt.status != "CALCULATED" or net_debt.value is None:
        status = (
            net_debt.status
            if net_debt.status in {"STALE_INPUT", "CONFLICT_INPUT", "CALCULATION_BLOCKED"}
            else "BLOCKED"
        )
        return _blocked(
            "enterprise_value",
            FORMULA_ENTERPRISE_VALUE,
            DERIVED_FORMULAS["enterprise_value"],
            inputs,
            now,
            status=status,
            detail="net_debt is not calculated; missing debt or cash is not zero",
        )
    return DerivedFieldResult(
        field="enterprise_value",
        value=market_cap.value + net_debt.value,
        status="CALCULATED",
        formula_version=FORMULA_ENTERPRISE_VALUE,
        formula=DERIVED_FORMULAS["enterprise_value"],
        input_fields=inputs,
        input_evidence_ids=market_cap.input_evidence_ids + net_debt.input_evidence_ids,
        calculated_at=now,
        detail="market_cap + (debt − cash)",
        as_of=market_cap.as_of,
        currency=market_cap.currency,
    )


def _fcf(dataset: VerifiedDataset, now: datetime) -> DerivedFieldResult:
    inputs = ("cfo", "capex")
    if dataset.financials is not None and not _unit_ok(dataset.financials):
        return _blocked(
            "fcf",
            FORMULA_FCF,
            DERIVED_FORMULAS["fcf"],
            inputs,
            now,
            status="CALCULATION_BLOCKED",
            detail="financial unit cannot be established",
        )
    cfo, cfo_status, cfo_field = _financial_amount(dataset, "cfo")
    capex, capex_status, capex_field = _financial_amount(dataset, "capex")
    if cfo_status != "OK":
        return _blocked(
            "fcf",
            FORMULA_FCF,
            DERIVED_FORMULAS["fcf"],
            inputs,
            now,
            status=cfo_status,
            detail="CFO missing; capex is not inferred",
        )
    if capex_status != "OK":
        return _blocked(
            "fcf",
            FORMULA_FCF,
            DERIVED_FORMULAS["fcf"],
            inputs,
            now,
            status=capex_status,
            detail="capex missing; FCF is not inferred",
        )
    if not _same_period(cfo_field, capex_field):
        return _blocked(
            "fcf",
            FORMULA_FCF,
            DERIVED_FORMULAS["fcf"],
            inputs,
            now,
            status="CALCULATION_BLOCKED",
            detail="CFO and capex periods are not compatible",
        )
    assert cfo is not None and capex is not None
    return DerivedFieldResult(
        field="fcf",
        value=cfo - abs(capex),
        status="CALCULATED",
        formula_version=FORMULA_FCF,
        formula=DERIVED_FORMULAS["fcf"],
        input_fields=inputs,
        input_evidence_ids=tuple(
            item
            for item in (
                None if cfo_field is None else cfo_field.evidence_id,
                None if capex_field is None else capex_field.evidence_id,
            )
            if item
        ),
        calculated_at=now,
        detail="existing DSP FCF = CFO − |capex|",
        as_of=None if cfo_field is None else cfo_field.as_of,
        currency=None if dataset.identity is None else dataset.identity.currency,
    )


def _ratio(
    field: str,
    version: str,
    formula: str,
    numerator: DerivedFieldResult,
    denominator: DerivedFieldResult,
    now: datetime,
) -> DerivedFieldResult:
    if numerator.status != "CALCULATED" or denominator.status != "CALCULATED":
        return _blocked(
            field,
            version,
            formula,
            (numerator.field, denominator.field),
            now,
            status="BLOCKED",
            detail="required derived inputs are not calculated",
        )
    if numerator.value is None or denominator.value is None or denominator.value == 0:
        return _blocked(
            field,
            version,
            formula,
            (numerator.field, denominator.field),
            now,
            status="BLOCKED",
            detail="denominator missing or zero",
        )
    return DerivedFieldResult(
        field=field,
        value=numerator.value / denominator.value,
        status="CALCULATED",
        formula_version=version,
        formula=formula,
        input_fields=(numerator.field, denominator.field),
        input_evidence_ids=numerator.input_evidence_ids + denominator.input_evidence_ids,
        calculated_at=now,
        detail=formula,
        as_of=numerator.as_of or denominator.as_of,
        currency=None,
    )


def _ratio_with_field(
    field: str,
    version: str,
    formula: str,
    numerator: DerivedFieldResult,
    dataset: VerifiedDataset,
    denom_name: str,
    now: datetime,
) -> DerivedFieldResult:
    if numerator.status != "CALCULATED" or numerator.value is None:
        return _blocked(
            field,
            version,
            formula,
            (numerator.field, denom_name),
            now,
            status="BLOCKED",
            detail="numerator is not calculated",
        )
    amount, status, item = _financial_amount(dataset, denom_name)
    if status != "OK" or amount is None or amount == 0:
        return _blocked(
            field,
            version,
            formula,
            (numerator.field, denom_name),
            now,
            status="BLOCKED" if status == "BLOCKED" else status,
            detail=f"{denom_name} unavailable",
        )
    return DerivedFieldResult(
        field=field,
        value=numerator.value / amount,
        status="CALCULATED",
        formula_version=version,
        formula=formula,
        input_fields=(numerator.field, denom_name),
        input_evidence_ids=numerator.input_evidence_ids
        + ((item.evidence_id,) if item is not None and item.evidence_id else ()),
        calculated_at=now,
        detail=formula,
        as_of=numerator.as_of,
        currency=None,
    )
