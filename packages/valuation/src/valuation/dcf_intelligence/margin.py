"""Margin of Safety classification for DCF intrinsic vs market.

Research posture bands — NOT trade recommendations. Research Mode UIs
must remap labels via compliance terminology ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from valuation.dcf_intelligence.assumptions import DcfMarketInputs
from valuation.dcf_intelligence.explain import ExplainedValue

__all__ = [
    "DcfMosClassification",
    "MarginOfSafetyResult",
    "compute_margin_of_safety",
]


class DcfMosClassification(str, Enum):
    """MoS cushion bands requested by V1.2 (research posture only)."""

    STRONG_BUY = "strong_buy"  # MoS >= 40%
    BUY = "buy"  # MoS >= 20%
    HOLD = "hold"  # MoS >= 0%
    OVERVALUED = "overvalued"  # MoS < 0%


@dataclass(frozen=True, slots=True)
class MarginOfSafetyResult:
    """Margin of safety with research-posture classification."""

    ratio: ExplainedValue
    classification: DcfMosClassification | None
    classification_explained: ExplainedValue
    disclaimer: str


_DISCLAIMER = (
    "Margin-of-safety classification is a research posture derived from "
    "(intrinsic − market) / intrinsic. It is NOT a Buy/Sell/Hold trade "
    "recommendation. Research Mode UIs must remap via compliance ports."
)


def _classify(ratio: float) -> DcfMosClassification:
    if ratio >= 0.40:
        return DcfMosClassification.STRONG_BUY
    if ratio >= 0.20:
        return DcfMosClassification.BUY
    if ratio >= 0.0:
        return DcfMosClassification.HOLD
    return DcfMosClassification.OVERVALUED


def compute_margin_of_safety(
    *,
    intrinsic_equity_value: float,
    intrinsic_per_share: float | None,
    market: DcfMarketInputs,
) -> MarginOfSafetyResult:
    """Compute MoS using equity market cap or price × shares."""
    market_value: float | None = market.equity_market_cap
    if (
        market_value is None
        and market.market_price_per_share is not None
        and intrinsic_per_share is not None
        and intrinsic_per_share != 0
    ):
        # Infer market cap from price if shares implied by IV
        # Prefer explicit market cap; otherwise use price vs IV/share ratio path
        market_value = None

    # Prefer equity market cap vs equity intrinsic
    if market.equity_market_cap is not None and intrinsic_equity_value != 0:
        mv = float(market.equity_market_cap)
        ratio = (intrinsic_equity_value - mv) / intrinsic_equity_value
        classification = _classify(ratio)
        return MarginOfSafetyResult(
            ratio=ExplainedValue(
                name="margin_of_safety_ratio",
                value=ratio,
                formula="MoS = (IntrinsicEquity − MarketCap) / IntrinsicEquity",
                inputs={
                    "intrinsic_equity_value": intrinsic_equity_value,
                    "equity_market_cap": mv,
                },
                intermediates={},
                confidence="high",
            ),
            classification=classification,
            classification_explained=ExplainedValue(
                name="mos_classification",
                value=None,
                formula=(
                    "strong_buy≥40%; buy≥20%; hold≥0%; else overvalued"
                ),
                inputs={"ratio": ratio, "class": classification.value},
                intermediates={},
                confidence="high",
                notes=_DISCLAIMER,
            ),
            disclaimer=_DISCLAIMER,
        )

    if (
        market.market_price_per_share is not None
        and intrinsic_per_share is not None
        and intrinsic_per_share != 0
    ):
        price = float(market.market_price_per_share)
        ratio = (intrinsic_per_share - price) / intrinsic_per_share
        classification = _classify(ratio)
        return MarginOfSafetyResult(
            ratio=ExplainedValue(
                name="margin_of_safety_ratio",
                value=ratio,
                formula="MoS = (IV/share − Price) / IV/share",
                inputs={
                    "intrinsic_value_per_share": intrinsic_per_share,
                    "market_price_per_share": price,
                },
                intermediates={},
                confidence="high",
            ),
            classification=classification,
            classification_explained=ExplainedValue(
                name="mos_classification",
                value=None,
                formula=(
                    "strong_buy≥40%; buy≥20%; hold≥0%; else overvalued"
                ),
                inputs={"ratio": ratio, "class": classification.value},
                intermediates={},
                confidence="high",
                notes=_DISCLAIMER,
            ),
            disclaimer=_DISCLAIMER,
        )

    return MarginOfSafetyResult(
        ratio=ExplainedValue(
            name="margin_of_safety_ratio",
            value=None,
            formula="MoS = (Intrinsic − Market) / Intrinsic",
            inputs={
                "intrinsic_equity_value": intrinsic_equity_value,
                "equity_market_cap": market.equity_market_cap,
                "market_price_per_share": market.market_price_per_share,
                "intrinsic_value_per_share": intrinsic_per_share,
            },
            intermediates={},
            confidence="insufficient",
            notes="Market context insufficient for MoS.",
        ),
        classification=None,
        classification_explained=ExplainedValue(
            name="mos_classification",
            value=None,
            formula="unavailable without market inputs",
            inputs={},
            intermediates={},
            confidence="insufficient",
            notes=_DISCLAIMER,
        ),
        disclaimer=_DISCLAIMER,
    )
