"""Factor exposure — portfolio-weighted rollup of caller-supplied signals only.

No new fundamental scoring happens here. Each factor is a pure weighted
average of a per-security proxy the caller already computed elsewhere
(e.g. Value = margin-of-safety from a Research Object's ``ValuationSummary``,
Quality = business/financial quality label, Momentum = trailing return from
price history, Size = market-cap bucket, Low-volatility = realized
volatility). Positions missing a given proxy are excluded from that factor's
average (never defaulted to zero).
"""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.models import (
    FactorExposure,
    FactorExposureProfile,
    PositionInput,
)

__all__ = ["compute_factor_exposures"]

_FACTOR_FIELDS: tuple[tuple[str, str], ...] = (
    ("value", "value_score"),
    ("quality", "quality_score"),
    ("momentum", "momentum_score"),
    ("size", "size_score"),
    ("low_volatility", "volatility_score"),
)


def compute_factor_exposures(
    positions: Sequence[PositionInput],
) -> FactorExposureProfile:
    total_positions = len(positions)
    factors: list[FactorExposure] = []
    limitations: list[str] = []

    for factor_name, attribute in _FACTOR_FIELDS:
        weighted_sum = 0.0
        weight_total = 0.0
        contributing = 0
        for position in positions:
            score = getattr(position, attribute)
            if score is None:
                continue
            weighted_sum += position.weight * score
            weight_total += position.weight
            contributing += 1
        exposure = weighted_sum / weight_total if weight_total > 0 else None
        if exposure is None:
            limitations.append(
                f"no positions supplied a {attribute} value; "
                f"{factor_name} factor exposure unavailable."
            )
        factors.append(
            FactorExposure(
                factor_name=factor_name,
                exposure_value=exposure,
                contributing_positions=contributing,
                total_positions=total_positions,
            )
        )

    available = [f for f in factors if f.exposure_value is not None]
    if not available:
        status = AnalyticsStatus.UNAVAILABLE
    elif len(available) < len(factors):
        status = AnalyticsStatus.PARTIAL
    else:
        status = AnalyticsStatus.COMPLETE

    return FactorExposureProfile(
        status=status, factors=tuple(factors), limitations=tuple(limitations)
    )
