"""PriceSnapshot construction with price_kind and raw-field discipline."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from data_engine.official_research.models import (
    PRICE_KINDS,
    PriceSnapshot,
    ResearchMode,
    UdiffCashRow,
)

__all__ = [
    "CANONICAL_EOD_FIELD",
    "FORBIDDEN_CURRENT_FIELDS",
    "PriceContractError",
    "eod_close_snapshot",
    "validate_price_snapshot",
]

CANONICAL_EOD_FIELD = "ClsPric"
FORBIDDEN_CURRENT_FIELDS = frozenset({"PrvsClsgPric", "PREV_CLOSE", "previous_close"})


class PriceContractError(ValueError):
    """Raised when a snapshot would corrupt price semantics."""


def validate_price_snapshot(snapshot: PriceSnapshot) -> PriceSnapshot:
    if snapshot.price_kind not in PRICE_KINDS:
        raise PriceContractError(f"unknown price_kind {snapshot.price_kind!r}")
    if snapshot.price <= 0:
        raise PriceContractError("price must be positive")
    if (
        snapshot.raw_price_field in FORBIDDEN_CURRENT_FIELDS
        and snapshot.price_kind in {"REALTIME", "DELAYED_15M", "EOD"}
    ):
        raise PriceContractError(
            "PrvsClsgPric cannot be labeled as current or EOD close"
        )
    if (
        snapshot.raw_price_field == CANONICAL_EOD_FIELD
        and snapshot.price_kind == "PREVIOUS_CLOSE"
    ):
        raise PriceContractError("ClsPric is not previous close")
    if snapshot.price_kind == "UNKNOWN":
        raise PriceContractError("UNKNOWN price_kind is not a valuation input")
    return snapshot


def eod_close_snapshot(
    row: UdiffCashRow,
    *,
    isin: str,
    mic: str,
    retrieved_at: datetime,
    source_url: str,
    mode: ResearchMode,
    currency: str = "INR",
) -> PriceSnapshot:
    """Map official ClsPric → EOD close. Never uses PrvsClsgPric."""
    if row.cls_pric is None or row.cls_pric <= 0:
        raise PriceContractError("ClsPric unavailable")
    if row.isin != isin:
        raise PriceContractError("ISIN mismatch")
    snapshot = PriceSnapshot(
        price=Decimal(row.cls_pric),
        price_kind="EOD",
        as_of=row.trad_dt,
        retrieved_at=retrieved_at,
        currency=currency,
        source=row.src,
        isin=isin,
        mic=mic,
        raw_price_field=CANONICAL_EOD_FIELD,
        ticker=row.tckr_symb,
        venue=row.venue,
        source_url=source_url,
        evidence_locator=(
            f"UDiFF row ISIN={row.isin} TckrSymb={row.tckr_symb} "
            f"SctySrs={row.scty_srs} ClsPric TradDt={row.trad_dt.isoformat()}"
        ),
        mode=mode,
    )
    return validate_price_snapshot(snapshot)


def as_of_is_not_retrieved_today(as_of: date, retrieved_at: datetime) -> bool:
    """retrieved_today ≠ current_today."""
    return as_of != retrieved_at.date()
