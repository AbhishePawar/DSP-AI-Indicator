"""Engine-owned Decimal quantize / rounding policy (E2.2).

Domain model constructors remain precision-neutral; the engine applies
these scales before constructing public metric artifacts.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

__all__ = [
    "ANNUALIZATION_FACTOR_DAILY",
    "METRIC_QUANTUM",
    "RETURN_QUANTUM",
    "WEIGHT_QUANTUM",
    "quantize_metric",
    "quantize_return",
    "quantize_weight",
]

#: Weight / allocation fraction scale (1e-8).
WEIGHT_QUANTUM = Decimal("0.00000001")

#: Period return scale (1e-8).
RETURN_QUANTUM = Decimal("0.00000001")

#: Published metric value scale (1e-8).
METRIC_QUANTUM = Decimal("0.00000001")

#: Trading-day annualization factor for realized daily volatility method.
ANNUALIZATION_FACTOR_DAILY = Decimal("252")

_ROUNDING = ROUND_HALF_EVEN


def quantize_weight(value: Decimal) -> Decimal:
    return value.quantize(WEIGHT_QUANTUM, rounding=_ROUNDING)


def quantize_return(value: Decimal) -> Decimal:
    return value.quantize(RETURN_QUANTUM, rounding=_ROUNDING)


def quantize_metric(value: Decimal) -> Decimal:
    return value.quantize(METRIC_QUANTUM, rounding=_ROUNDING)
