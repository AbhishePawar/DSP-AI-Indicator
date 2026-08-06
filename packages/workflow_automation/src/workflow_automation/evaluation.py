"""Pure alert-rule evaluation — compares already-computed signals only.

Every function here takes an already-computed value (a live quote price, a
valuation classification, a "last analysed at" timestamp) supplied by the
caller and returns a triggered/not-triggered/unavailable verdict. **No
provider call, no valuation math, no risk math happens here** — that is the
job of the frozen engines this package's caller (``dsp_platform``) already
reuses (market quotes, the Portfolio Intelligence Engine).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from workflow_automation.enums import AlertStatus

__all__ = [
    "AlertEvaluation",
    "evaluate_earnings_alert",
    "evaluate_price_alert",
    "evaluate_research_stale_alert",
    "evaluate_valuation_alert",
]


@dataclass(frozen=True, slots=True)
class AlertEvaluation:
    status: AlertStatus
    message: str
    observed_value: float | str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "message": self.message,
            "observed_value": self.observed_value,
        }


def evaluate_price_alert(
    *,
    direction: str,
    threshold_price: float,
    current_price: float | None,
    symbol: str,
) -> AlertEvaluation:
    """``direction`` is ``"above"`` or ``"below"``."""
    if current_price is None:
        return AlertEvaluation(
            status=AlertStatus.UNAVAILABLE,
            message=f"Data unavailable. No live quote for {symbol}.",
        )
    if direction == "above" and current_price >= threshold_price:
        return AlertEvaluation(
            status=AlertStatus.TRIGGERED,
            message=(
                f"{symbol} is at {current_price:,.2f}, at or above the "
                f"{threshold_price:,.2f} threshold."
            ),
            observed_value=current_price,
        )
    if direction == "below" and current_price <= threshold_price:
        return AlertEvaluation(
            status=AlertStatus.TRIGGERED,
            message=(
                f"{symbol} is at {current_price:,.2f}, at or below the "
                f"{threshold_price:,.2f} threshold."
            ),
            observed_value=current_price,
        )
    return AlertEvaluation(
        status=AlertStatus.NOT_TRIGGERED,
        message=f"{symbol} is at {current_price:,.2f}.",
        observed_value=current_price,
    )


def evaluate_valuation_alert(
    *,
    watch_class: str,
    current_class: str | None,
    symbol: str,
) -> AlertEvaluation:
    """``watch_class``/``current_class`` are Valuation Heatmap classes
    (``undervalued``/``fairly_valued``/``overvalued``/``unavailable``)."""
    if current_class is None or current_class == "unavailable":
        return AlertEvaluation(
            status=AlertStatus.UNAVAILABLE,
            message=(
                f"Data unavailable. No linked valuation for {symbol} — "
                "link a Research Object to enable this alert."
            ),
        )
    if current_class == watch_class:
        return AlertEvaluation(
            status=AlertStatus.TRIGGERED,
            message=f"{symbol} is now classified {current_class.replace('_', ' ')}.",
            observed_value=current_class,
        )
    return AlertEvaluation(
        status=AlertStatus.NOT_TRIGGERED,
        message=f"{symbol} is classified {current_class.replace('_', ' ')}.",
        observed_value=current_class,
    )


def evaluate_research_stale_alert(
    *,
    last_analysed_at: str | None,
    max_age_days: int,
    symbol: str,
    as_of: date | None = None,
) -> AlertEvaluation:
    """Simple date-difference check — not a new staleness engine."""
    if not last_analysed_at:
        return AlertEvaluation(
            status=AlertStatus.UNAVAILABLE,
            message=(
                f"Data unavailable. No prior analysis date recorded for {symbol}."
            ),
        )
    try:
        analysed_date = datetime.fromisoformat(
            last_analysed_at.replace("Z", "+00:00")
        ).date()
    except ValueError:
        return AlertEvaluation(
            status=AlertStatus.UNAVAILABLE,
            message=f"Data unavailable. Unparseable analysis date for {symbol}.",
        )
    today = as_of or datetime.now().date()
    age_days = (today - analysed_date).days
    if age_days >= max_age_days:
        return AlertEvaluation(
            status=AlertStatus.TRIGGERED,
            message=(
                f"{symbol} was last analysed {age_days} days ago "
                f"(threshold {max_age_days} days)."
            ),
            observed_value=age_days,
        )
    return AlertEvaluation(
        status=AlertStatus.NOT_TRIGGERED,
        message=f"{symbol} was last analysed {age_days} days ago.",
        observed_value=age_days,
    )


def evaluate_earnings_alert(*, symbol: str) -> AlertEvaluation:
    """Always unavailable — no earnings calendar data source exists in the
    platform. This function exists only to keep the rule-type dispatch
    complete and honest, never to fabricate an earnings date."""
    return AlertEvaluation(
        status=AlertStatus.UNAVAILABLE,
        message=(
            "Data unavailable. No earnings-calendar data source is connected "
            f"for {symbol} — this rule type is reserved for a future Data "
            "Connector Framework provider."
        ),
    )
