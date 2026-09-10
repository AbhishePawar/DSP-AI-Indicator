"""Evidence judge → DSP gate. Only VERIFIED fields may cross the truth boundary."""

from __future__ import annotations

from dataclasses import dataclass

from data_engine.official_research.models import FailureStatus, PriceSnapshot
from data_engine.official_research.semantics import ValuationGateResult, valuation_gate
from data_engine.official_research.verified_dataset import (
    AssumptionRecord,
    DSPAnalysisResult,
    VerifiedDataset,
)

__all__ = [
    "DSP_BLOCKED_STATUSES",
    "DspGateDecision",
    "assert_field_verified",
    "default_unverified_assumptions",
    "dsp_gate",
    "refuse_non_verified",
]

DSP_BLOCKED_STATUSES: frozenset[str] = frozenset(
    {"RAW", "RECONCILED", "CONFLICT", "UNKNOWN", "UNAVAILABLE", "REFRESH_REQUIRED"}
)

_ASSUMPTION_NAMES = (
    "discount_rate",
    "fcf_growth_rate",
    "terminal_growth_rate",
    "earnings_multiple",
    "owner_earnings_cap_rate",
    "residual_income_required_return",
)


@dataclass(frozen=True, slots=True)
class DspGateDecision:
    allowed: bool
    allowed_methods: tuple[str, ...]
    valuation: ValuationGateResult
    blocked_reason: str | None
    assumptions: tuple[AssumptionRecord, ...]


def default_unverified_assumptions() -> tuple[AssumptionRecord, ...]:
    """Engine defaults are documented but not VERIFIED production truth."""
    return tuple(
        AssumptionRecord(
            name=name,
            source="ValuationAssumptions.default",
            agent="dsp_engine",
            value=None,
            unit=None,
            period=None,
            status="UNAVAILABLE",
        )
        for name in _ASSUMPTION_NAMES
    )


def refuse_non_verified(status: FailureStatus | str, *, field: str) -> None:
    if status != "VERIFIED":
        raise ValueError(f"{field} cannot enter DSP: status={status}")


def assert_field_verified(dataset: VerifiedDataset, field: str) -> None:
    refuse_non_verified(dataset.field_status(field), field=field)


def dsp_gate(dataset: VerifiedDataset) -> DspGateDecision:
    """Select deterministic methods from VERIFIED inputs only."""
    assumptions = dataset.assumptions or default_unverified_assumptions()
    assumptions_verified = all(item.status == "VERIFIED" for item in assumptions)
    if dataset.identity_status != "VERIFIED" or dataset.identity is None:
        return DspGateDecision(
            allowed=False,
            allowed_methods=(),
            valuation=ValuationGateResult(
                method=None, status="UNKNOWN", detail="identity not VERIFIED"
            ),
            blocked_reason="identity not VERIFIED",
            assumptions=assumptions,
        )
    if dataset.mode == "MOCK":
        # Caller must also set production=False; production path refuses MOCK earlier.
        pass

    price = dataset.price if dataset.price_status == "VERIFIED" else None
    shares_ok = dataset.shares_status == "VERIFIED" and dataset.shares is not None
    cfo_ok = dataset.field_status("cfo") == "VERIFIED"
    capex_ok = dataset.field_status("capex") == "VERIFIED"
    ni_ok = dataset.field_status("net_income") == "VERIFIED"
    equity_ok = dataset.field_status("equity") == "VERIFIED"

    methods: list[str] = []
    dcf = valuation_gate(cfo=cfo_ok, capex=capex_ok)
    if dcf.status == "VERIFIED" and assumptions_verified:
        methods.append("dcf")
    elif dcf.status == "VERIFIED" and not assumptions_verified:
        dcf = ValuationGateResult(
            method=None,
            status="UNAVAILABLE",
            detail="DCF UNAVAILABLE: discount/growth assumptions are not VERIFIED",
        )

    earnings = valuation_gate(net_income=ni_ok, shares=shares_ok)
    if earnings.status == "VERIFIED" and assumptions_verified:
        methods.append("earnings_multiple")

    book = valuation_gate(equity=equity_ok, shares=shares_ok)
    if book.status == "VERIFIED":
        methods.append("book_value")

    mos = ValuationGateResult(
        method=None, status="UNAVAILABLE", detail="VALUATION UNAVAILABLE"
    )
    if price is not None and shares_ok and dataset.shares is not None and methods:
        mos = valuation_gate(
            price=price,
            shares=True,
            shares_as_of=dataset.shares.as_of,
            shares_current_through=dataset.shares.current_through,
            corporate_actions=dataset.capital_events,
        )
        if (
            dataset.shares.current_through
            and price.as_of > dataset.shares.current_through
        ):
            mos = ValuationGateResult(
                method=None,
                status="REFRESH_REQUIRED",
                detail="price_as_of exceeds shares_current_through",
            )

    primary = mos
    if not methods:
        primary = ValuationGateResult(
            method=None,
            status="UNAVAILABLE",
            detail="VALUATION UNAVAILABLE",
        )
    elif mos.status in {"REFRESH_REQUIRED", "UNAVAILABLE", "CONFLICT"}:
        primary = mos
        methods = []

    if price is not None and price.price_kind == "PREVIOUS_CLOSE":
        return DspGateDecision(
            allowed=False,
            allowed_methods=(),
            valuation=ValuationGateResult(
                method=None,
                status="UNAVAILABLE",
                detail="PREVIOUS_CLOSE cannot be used as current price",
            ),
            blocked_reason="PREVIOUS_CLOSE cannot become current",
            assumptions=assumptions,
        )
    if price is not None and price.price_kind == "UNKNOWN":
        return DspGateDecision(
            allowed=False,
            allowed_methods=(),
            valuation=ValuationGateResult(
                method=None, status="UNAVAILABLE", detail="UNKNOWN price_kind"
            ),
            blocked_reason="UNKNOWN price_kind",
            assumptions=assumptions,
        )

    allowed = bool(methods) and primary.status == "VERIFIED"
    return DspGateDecision(
        allowed=allowed,
        allowed_methods=tuple(methods),
        valuation=(
            primary
            if methods or primary.status != "VERIFIED"
            else ValuationGateResult(
                method=None, status="UNAVAILABLE", detail="VALUATION UNAVAILABLE"
            )
        ),
        blocked_reason=None if allowed else primary.detail,
        assumptions=assumptions,
    )


def analysis_from_dataset(
    dataset: VerifiedDataset, *, gate: DspGateDecision | None = None
) -> DSPAnalysisResult:
    decision = gate or dsp_gate(dataset)
    identity = None
    if dataset.identity is not None:
        identity = {
            "isin": dataset.identity.isin,
            "mic": dataset.identity.mic,
            "ticker": dataset.identity.ticker,
            "company_name": dataset.identity.company_name,
        }
    val_status: FailureStatus = decision.valuation.status
    mos_status: FailureStatus = (
        "VERIFIED"
        if decision.allowed and "book_value" in decision.allowed_methods
        else val_status
    )
    return DSPAnalysisResult(
        identity=identity,
        data_status=dataset.data_quality_status,
        overall_score=None,
        quality="UNAVAILABLE",
        business_quality="UNAVAILABLE",
        management_quality="UNAVAILABLE",
        moat="UNAVAILABLE",
        risk="UNAVAILABLE",
        financial_quality=(
            "UNAVAILABLE"
            if dataset.financials is None
            else dataset.field_status("net_income")
        ),
        valuation=val_status,
        buffett_indicator="UNAVAILABLE",
        margin_of_safety=mos_status if decision.allowed else val_status,
        evidence=dataset.evidence,
        confidence=None,
        currentness=dataset.currentness_status,
        unresolved_issues=dataset.unresolved
        + ((decision.blocked_reason,) if decision.blocked_reason else ()),
        allowed_methods=decision.allowed_methods,
        dataset=dataset,
    )


def labeled_eod_price(snapshot: PriceSnapshot) -> PriceSnapshot:
    """EOD remains EOD. Never rewrite as REALTIME."""
    if snapshot.price_kind == "EOD":
        return snapshot
    if snapshot.price_kind == "PREVIOUS_CLOSE":
        return snapshot
    return snapshot
