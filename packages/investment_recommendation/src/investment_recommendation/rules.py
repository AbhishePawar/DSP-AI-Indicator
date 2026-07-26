"""Deterministic decision / conflict rules for Investment Recommendation.

Documented rule groups. No LLM / ML. Hard caps prevent Strong Buy when
trading materially above conservative intrinsic value.
"""

from __future__ import annotations

from dataclasses import dataclass

from investment_recommendation.models import (
    MarginOfSafetyAssessment,
    TriggeredRule,
)
from investment_recommendation.scoring import (
    InvestmentRecommendationAction,
    clip_score,
)

__all__ = [
    "ACTION_RANK",
    "DecisionRuleResult",
    "apply_decision_rules",
    "cap_action",
]

# Documented thresholds
_EXCELLENT_QUALITY = 80.0
_WEAK_QUALITY = 40.0
_STRONG = 70.0
_WEAK = 45.0
_MATERIAL_PREMIUM = 0.25  # 25% above IV
_NEGATIVE_MOS = -0.15
_DEEP_MOS = 0.30

ACTION_RANK: dict[InvestmentRecommendationAction, int] = {
    InvestmentRecommendationAction.STRONG_SELL: 0,
    InvestmentRecommendationAction.SELL: 1,
    InvestmentRecommendationAction.REDUCE: 2,
    InvestmentRecommendationAction.HOLD: 3,
    InvestmentRecommendationAction.ACCUMULATE: 4,
    InvestmentRecommendationAction.BUY: 5,
    InvestmentRecommendationAction.STRONG_BUY: 6,
}


def cap_action(
    action: InvestmentRecommendationAction,
    cap: InvestmentRecommendationAction | None,
) -> InvestmentRecommendationAction:
    if cap is None:
        return action
    if ACTION_RANK[action] > ACTION_RANK[cap]:
        return cap
    return action


@dataclass(frozen=True, slots=True)
class DecisionRuleResult:
    rules: tuple[TriggeredRule, ...]
    adjusted_score: float | None
    action_cap: InvestmentRecommendationAction | None


def apply_decision_rules(
    *,
    raw_score: float | None,
    quality: float | None,
    moat: float | None,
    management: float | None,
    strength: float | None,
    earnings: float | None,
    growth: float | None,
    mos: MarginOfSafetyAssessment,
) -> DecisionRuleResult:
    rules: list[TriggeredRule] = []
    action_cap: InvestmentRecommendationAction | None = None
    delta = 0.0

    def _add(
        rule_id: str,
        group: str,
        description: str,
        *,
        score_delta: float = 0.0,
        cap: InvestmentRecommendationAction | None = None,
        engines: tuple[str, ...] = (),
        metrics: list[str] | None = None,
    ) -> None:
        nonlocal action_cap, delta
        rules.append(
            TriggeredRule(
                rule_id=rule_id,
                group=group,
                description=description,
                score_delta=score_delta,
                action_cap=cap,
                engines=engines,
                supporting_metrics=tuple(metrics or []),
            )
        )
        delta += score_delta
        if cap is not None:
            if action_cap is None or ACTION_RANK[cap] < ACTION_RANK[action_cap]:
                action_cap = cap

    mos_ratio = mos.margin_of_safety
    premium = mos.premium_discount

    # --- Valuation gates (hard) ---
    if premium is not None and premium >= _MATERIAL_PREMIUM:
        _add(
            "materially_above_intrinsic_value",
            "margin_of_safety",
            "Price is materially above conservative intrinsic value; "
            "Buy/Strong Buy capped at Hold unless other rules do not lift the cap.",
            score_delta=-8.0,
            cap=InvestmentRecommendationAction.HOLD,
            engines=("valuation",),
            metrics=[f"premium_discount={premium}", f"mos={mos_ratio}"],
        )

    if mos_ratio is not None and mos_ratio <= _NEGATIVE_MOS:
        _add(
            "negative_margin_of_safety",
            "margin_of_safety",
            "Negative margin of safety blocks Strong Buy; prefer patience.",
            score_delta=-5.0,
            cap=InvestmentRecommendationAction.ACCUMULATE,
            engines=("valuation",),
            metrics=[f"mos={mos_ratio}"],
        )
        # Stronger: also block Strong Buy specifically via accumulate cap already

    if (
        mos_ratio is not None
        and mos_ratio >= _DEEP_MOS
        and quality is not None
        and quality >= _EXCELLENT_QUALITY
    ):
        _add(
            "excellent_business_undervalued",
            "quality_valuation",
            "Excellent business quality with a deep margin of safety — "
            "Buffett-aligned entry posture.",
            score_delta=6.0,
            engines=("business_quality_aggregator", "valuation"),
            metrics=[f"quality={quality}", f"mos={mos_ratio}"],
        )

    if (
        quality is not None
        and quality >= _EXCELLENT_QUALITY
        and mos_ratio is not None
        and mos_ratio < 0
    ):
        _add(
            "excellent_business_overvalued",
            "quality_valuation",
            "Excellent business but overvalued — quality alone does not justify "
            "aggressive buying without MoS.",
            score_delta=-4.0,
            cap=InvestmentRecommendationAction.HOLD,
            engines=("business_quality_aggregator", "valuation"),
            metrics=[f"quality={quality}", f"mos={mos_ratio}"],
        )

    if (
        quality is not None
        and quality < _WEAK_QUALITY
        and mos_ratio is not None
        and mos_ratio >= 0.20
    ):
        _add(
            "weak_business_cheap",
            "quality_valuation",
            "Cheap valuation with weak business quality — classic value-trap risk.",
            score_delta=-7.0,
            cap=InvestmentRecommendationAction.REDUCE,
            engines=("business_quality_aggregator", "valuation"),
            metrics=[f"quality={quality}", f"mos={mos_ratio}"],
        )

    if (
        growth is not None
        and growth >= _STRONG
        and strength is not None
        and strength < _WEAK
    ):
        _add(
            "strong_growth_weak_balance_sheet",
            "conflict",
            "Strong growth with a weak balance sheet raises permanent-capital risk.",
            score_delta=-5.0,
            engines=("growth_quality", "financial_strength"),
            metrics=[f"growth={growth}", f"strength={strength}"],
        )

    if (
        moat is not None
        and moat >= _STRONG
        and management is not None
        and management < _WEAK
    ):
        _add(
            "wide_moat_poor_capital_allocation",
            "conflict",
            "Wide/strong moat with weak management/capital allocation can destroy "
            "franchise value over time.",
            score_delta=-5.0,
            engines=("economic_moat", "management_quality"),
            metrics=[f"moat={moat}", f"management={management}"],
        )

    if (
        quality is not None
        and quality >= _EXCELLENT_QUALITY
        and mos_ratio is not None
        and 0 <= mos_ratio < 0.10
    ):
        _add(
            "high_quality_low_margin_of_safety",
            "quality_valuation",
            "High quality with low MoS — accumulate selectively; avoid Strong Buy.",
            score_delta=-2.0,
            cap=InvestmentRecommendationAction.ACCUMULATE,
            engines=("business_quality_aggregator", "valuation"),
            metrics=[f"quality={quality}", f"mos={mos_ratio}"],
        )

    if earnings is not None and earnings < _WEAK and quality is not None and quality >= _STRONG:
        _add(
            "strong_quality_weak_earnings_quality",
            "conflict",
            "Composite quality elevated while earnings quality is weak — "
            "scrutinise cash-backed earnings.",
            score_delta=-3.0,
            engines=("earnings_quality", "business_quality_aggregator"),
            metrics=[f"earnings={earnings}", f"quality={quality}"],
        )

    adjusted: float | None
    if raw_score is None:
        adjusted = None
    else:
        adjusted = clip_score(raw_score + delta)

    return DecisionRuleResult(
        rules=tuple(rules),
        adjusted_score=None if adjusted is None else round(adjusted, 4),
        action_cap=action_cap,
    )
