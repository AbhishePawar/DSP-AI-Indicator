"""Outcome Engine (EPIC-011B) — measure only; never rewrite recommendations.

Missing market data → honest "Data unavailable." / Unable to calculate.
"""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_intelligence.models import (
    OUTCOME_WINDOWS_MONTHS,
    UNAVAILABLE_MESSAGE,
    OutcomeMeasurement,
    ResearchSnapshot,
    utc_now,
)

__all__ = [
    "OUTCOME_WINDOWS_MONTHS",
    "UNABLE_MESSAGE",
    "measure_outcome",
    "measure_outcomes_for_snapshot",
    "normalize_recommendation_stance",
]

UNABLE_MESSAGE = "Unable to calculate."

_BULLISH = frozenset(
    {
        "buy",
        "strong_buy",
        "strong buy",
        "overweight",
        "accumulate",
        "bullish",
        "long",
    }
)
_BEARISH = frozenset(
    {
        "sell",
        "strong_sell",
        "strong sell",
        "underweight",
        "reduce",
        "bearish",
        "short",
    }
)
_NEUTRAL = frozenset(
    {
        "hold",
        "neutral",
        "market_perform",
        "market perform",
        "equal_weight",
        "equal weight",
        "research mode",
        "research_mode",
    }
)


def normalize_recommendation_stance(recommendation: str | None) -> str | None:
    if recommendation is None:
        return None
    key = recommendation.strip().lower().replace("-", "_")
    key_spaced = recommendation.strip().lower()
    if key in _BULLISH or key_spaced in _BULLISH:
        return "bullish"
    if key in _BEARISH or key_spaced in _BEARISH:
        return "bearish"
    if key in _NEUTRAL or key_spaced in _NEUTRAL:
        return "neutral"
    return None


def _price_change_pct(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start == 0:
        return None
    return (end - start) / abs(start)


def _recommendation_accuracy(
    stance: str | None, price_change: float | None
) -> str | None:
    if stance is None or price_change is None:
        return None
    if stance == "bullish":
        return "correct" if price_change > 0 else "incorrect"
    if stance == "bearish":
        return "correct" if price_change < 0 else "incorrect"
    if stance == "neutral":
        return "correct" if abs(price_change) <= 0.05 else "incorrect"
    return None


def _confidence_accuracy(
    label: str | None, rec_accuracy: str | None
) -> str | None:
    if label is None or rec_accuracy is None:
        return None
    # High confidence should be correct more often; we only mark per-sample match.
    if rec_accuracy == "correct":
        return "aligned"
    if label == "high":
        return "miscalibrated"
    if label == "medium":
        return "partial"
    return "aligned"  # low confidence + incorrect is not a calibration failure


def _mos_performance(
    mos: float | None, price_change: float | None, stance: str | None
) -> str | None:
    if mos is None or price_change is None:
        return None
    # Positive MoS + bullish: expect positive price change support
    if mos > 0 and stance in {None, "bullish", "neutral"}:
        return "supported" if price_change >= 0 else "contradicted"
    if mos < 0:
        return "supported" if price_change <= 0 else "contradicted"
    return "inconclusive"


def _success_failure(rec_accuracy: str | None) -> str | None:
    if rec_accuracy == "correct":
        return "success"
    if rec_accuracy == "incorrect":
        return "failure"
    return None


def measure_outcome(
    snapshot: ResearchSnapshot,
    *,
    window_months: int,
    price_at_horizon: float | None = None,
    iv_at_horizon: float | None = None,
    measured_at: str | None = None,
) -> OutcomeMeasurement:
    """Measure a single snapshot outcome for a window.

    Callers supply horizon market prices when available. When missing,
    metrics remain unavailable — never fabricated.
    """
    if window_months not in OUTCOME_WINDOWS_MONTHS:
        raise ValueError(
            f"window_months must be one of {OUTCOME_WINDOWS_MONTHS}"
        )

    price_start = snapshot.price
    price_end = price_at_horizon
    change = _price_change_pct(price_start, price_end)
    stance = normalize_recommendation_stance(snapshot.recommendation)
    rec_acc = _recommendation_accuracy(stance, change)
    conf_acc = _confidence_accuracy(snapshot.confidence_label, rec_acc)
    mos_perf = _mos_performance(snapshot.margin_of_safety, change, stance)
    success = _success_failure(rec_acc)

    iv = snapshot.intrinsic_value
    iv_gap_start = None
    if iv is not None and price_start is not None and price_start != 0:
        iv_gap_start = (iv - price_start) / abs(price_start)
    iv_gap_end = None
    if iv_at_horizon is not None and price_end is not None and price_end != 0:
        iv_gap_end = (iv_at_horizon - price_end) / abs(price_end)
    elif iv is not None and price_end is not None and price_end != 0:
        # Use research IV vs horizon price when horizon IV unavailable
        iv_gap_end = (iv - price_end) / abs(price_end)

    market_available = price_end is not None
    availability = {
        "price_at_research": price_start is not None,
        "price_at_horizon": market_available,
        "intrinsic_value": iv is not None,
        "recommendation": snapshot.recommendation is not None,
        "confidence": snapshot.confidence is not None,
        "margin_of_safety": snapshot.margin_of_safety is not None,
        "outcome_calculable": change is not None and rec_acc is not None,
    }

    message = None
    if not market_available:
        message = UNAVAILABLE_MESSAGE
    elif change is None or rec_acc is None:
        message = UNABLE_MESSAGE

    return OutcomeMeasurement(
        research_id=snapshot.research_id,
        window_months=window_months,
        measured_at=measured_at or utc_now().isoformat(),
        price_at_research=price_start,
        price_at_horizon=price_end,
        price_change_pct=change,
        iv_at_research=iv,
        iv_gap_at_research=iv_gap_start,
        iv_gap_at_horizon=iv_gap_end,
        recommendation=snapshot.recommendation,
        recommendation_accuracy=rec_acc,
        confidence_label=snapshot.confidence_label,
        confidence_accuracy=conf_acc,
        mos_at_research=snapshot.margin_of_safety,
        mos_performance=mos_perf,
        success_failure=success,
        availability=availability,
        message=message,
    )


def measure_outcomes_for_snapshot(
    snapshot: ResearchSnapshot,
    *,
    horizon_prices: Mapping[int, float | None] | None = None,
    horizon_ivs: Mapping[int, float | None] | None = None,
    windows: tuple[int, ...] = OUTCOME_WINDOWS_MONTHS,
    measured_at: str | None = None,
) -> tuple[OutcomeMeasurement, ...]:
    prices = dict(horizon_prices or {})
    ivs = dict(horizon_ivs or {})
    return tuple(
        measure_outcome(
            snapshot,
            window_months=w,
            price_at_horizon=prices.get(w),
            iv_at_horizon=ivs.get(w),
            measured_at=measured_at,
        )
        for w in windows
    )
