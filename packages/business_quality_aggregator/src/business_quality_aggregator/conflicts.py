"""Deterministic cross-domain conflict resolution (Buffett-aligned).

Conflicts reduce the aggregated score and must explain WHY. Penalties are
documented constants — never reward leverage-driven growth over conservatism.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from business_quality_aggregator.adapters import component_score_01, safe_score_value
from business_quality_aggregator.models import ConflictAdjustment
from business_quality_aggregator.scoring import AggregatorComponent, clip_score

__all__ = [
    "CONFLICT_PENALTY_CAP",
    "ConflictResolutionResult",
    "resolve_conflicts",
]

# Documented penalty constants (points on 0–100 scale)
_STRONG = 70.0
_WEAK = 45.0
_PENALTY_STD = 4.0
_PENALTY_MILD = 3.0
CONFLICT_PENALTY_CAP = 12.0


@dataclass(frozen=True, slots=True)
class ConflictResolutionResult:
    adjustments: tuple[ConflictAdjustment, ...]
    total_penalty: float
    adjusted_score: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "adjustments": [a.to_dict() for a in self.adjustments],
            "total_penalty": self.total_penalty,
            "adjusted_score": self.adjusted_score,
        }


def resolve_conflicts(
    *,
    raw_score: float | None,
    economic_moat: object | None,
    management_quality: object | None,
    financial_strength: object | None,
    earnings_quality: object | None,
    growth_quality: object | None,
) -> ConflictResolutionResult:
    moat = safe_score_value(economic_moat)
    mgmt = safe_score_value(management_quality)
    strength = safe_score_value(financial_strength)
    earnings = safe_score_value(earnings_quality)
    growth = safe_score_value(growth_quality)

    cash_flow = component_score_01(financial_strength, "cash_flow_quality")
    liquidity = component_score_01(financial_strength, "liquidity")
    capital_alloc = component_score_01(management_quality, "capital_allocation")
    margin_stab = component_score_01(earnings_quality, "margin_stability")
    # Proxy profitability from financial strength profitability_stability
    profitability = component_score_01(financial_strength, "profitability_stability")

    adjustments: list[ConflictAdjustment] = []

    def _add(
        rule_id: str,
        description: str,
        penalty: float,
        engines: tuple[str, ...],
        metrics: list[str],
    ) -> None:
        adjustments.append(
            ConflictAdjustment(
                rule_id=rule_id,
                description=description,
                penalty_points=penalty,
                engines=engines,
                supporting_metrics=tuple(metrics),
            )
        )

    if moat is not None and strength is not None and moat >= _STRONG and strength < _WEAK:
        _add(
            "strong_moat_weak_balance_sheet",
            "Strong economic moat with a weak balance sheet reduces durability "
            "of the franchise; leverage or liquidity stress can erase moat value.",
            _PENALTY_STD,
            (
                AggregatorComponent.ECONOMIC_MOAT.value,
                AggregatorComponent.FINANCIAL_STRENGTH.value,
            ),
            [f"moat_score={moat}", f"financial_strength_score={strength}"],
        )

    if (
        mgmt is not None
        and earnings is not None
        and mgmt >= _STRONG
        and earnings < _WEAK
    ):
        _add(
            "excellent_management_weak_earnings_quality",
            "Owner-oriented management is undermined when earnings quality is weak; "
            "reported results may not be cash-backed or sustainable.",
            _PENALTY_STD,
            (
                AggregatorComponent.MANAGEMENT_QUALITY.value,
                AggregatorComponent.EARNINGS_QUALITY.value,
            ),
            [f"management_score={mgmt}", f"earnings_quality_score={earnings}"],
        )

    if (
        growth is not None
        and cash_flow is not None
        and growth >= _STRONG
        and cash_flow < (_WEAK / 100.0)
    ):
        _add(
            "strong_growth_poor_cash_generation",
            "Strong growth with poor cash generation is not Buffett-aligned; "
            "growth without cash conversion is treated as a quality conflict.",
            _PENALTY_STD,
            (
                AggregatorComponent.GROWTH_QUALITY.value,
                AggregatorComponent.FINANCIAL_STRENGTH.value,
            ),
            [f"growth_score={growth}", f"cash_flow_quality_01={cash_flow}"],
        )

    if (
        profitability is not None
        and capital_alloc is not None
        and profitability >= (_STRONG / 100.0)
        and capital_alloc < (_WEAK / 100.0)
    ):
        _add(
            "high_profitability_weak_capital_allocation",
            "High profitability with weak capital allocation wastes compounding "
            "potential; returns may not be reinvested owner-intelligently.",
            _PENALTY_MILD,
            (
                AggregatorComponent.FINANCIAL_STRENGTH.value,
                AggregatorComponent.MANAGEMENT_QUALITY.value,
            ),
            [
                f"profitability_stability_01={profitability}",
                f"capital_allocation_01={capital_alloc}",
            ],
        )

    if (
        strength is not None
        and liquidity is not None
        and strength >= _STRONG
        and liquidity < (_WEAK / 100.0)
    ):
        # Low leverage / strong overall FS but weak liquidity
        _add(
            "strong_strength_weak_liquidity",
            "Overall financial strength with weak liquidity creates near-term "
            "fragility despite low leverage optics.",
            _PENALTY_MILD,
            (AggregatorComponent.FINANCIAL_STRENGTH.value,),
            [
                f"financial_strength_score={strength}",
                f"liquidity_01={liquidity}",
            ],
        )

    if (
        growth is not None
        and margin_stab is not None
        and growth >= _STRONG
        and margin_stab < (_WEAK / 100.0)
    ):
        _add(
            "outstanding_growth_deteriorating_margins",
            "Outstanding growth with deteriorating or unstable margins signals "
            "low-quality expansion; not rewarded as durable compounding.",
            _PENALTY_STD,
            (
                AggregatorComponent.GROWTH_QUALITY.value,
                AggregatorComponent.EARNINGS_QUALITY.value,
            ),
            [f"growth_score={growth}", f"margin_stability_01={margin_stab}"],
        )

    total = min(CONFLICT_PENALTY_CAP, sum(a.penalty_points for a in adjustments))
    adjusted: float | None
    if raw_score is None:
        adjusted = None
    else:
        adjusted = clip_score(raw_score - total)
    return ConflictResolutionResult(
        adjustments=tuple(adjustments),
        total_penalty=round(total, 4),
        adjusted_score=None if adjusted is None else round(adjusted, 4),
    )
