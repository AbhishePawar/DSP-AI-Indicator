"""Illustrative IndustryMethodology examples (policy only — no metrics/peers)."""

from __future__ import annotations

from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.enums import ComparisonDimension, MetricImportance, PeerUse
from industry.methodology import (
    IndustryMethodology,
    MetricApplicability,
    PeerEligibilityPolicyRef,
    ValuationProfile,
)
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.models import IndustryIdentity
from industry.seeds import register_example_archetypes
from industry.taxonomy import IndustryTaxonomy

__all__ = [
    "EXAMPLE_METHODOLOGY_IDS",
    "build_example_methodologies",
    "register_example_methodologies",
    "seed_example_industry_context",
]

EXAMPLE_METHODOLOGY_IDS: tuple[str, ...] = (
    "dsp.methodology.commercial_banking",
    "dsp.methodology.electric_utilities",
    "dsp.methodology.premium_consumer_franchise",
)

_EXAMPLE_INDUSTRIES: tuple[tuple[str, str], ...] = (
    ("dsp.industry.commercial_banking", "Commercial Banking"),
    ("dsp.industry.electric_utilities", "Electric Utilities"),
    ("dsp.industry.premium_consumer_franchise", "Premium Consumer Franchise"),
)


def seed_example_industry_context(
    taxonomy: IndustryTaxonomy,
    characteristics: InvestmentCharacteristicsRegistry,
) -> None:
    """Register identities + characteristic archetypes needed by examples."""
    for industry_id, name in _EXAMPLE_INDUSTRIES:
        if not taxonomy.contains(industry_id):
            taxonomy.register(IndustryIdentity(id=industry_id, name=name))
    register_example_archetypes(characteristics)


def build_example_methodologies() -> tuple[IndustryMethodology, ...]:
    """Return illustrative methodologies — no operating metric implementations."""
    return (
        IndustryMethodology(
            id="dsp.methodology.commercial_banking",
            industry_id="dsp.industry.commercial_banking",
            version="1.0.0",
            name="Commercial Banking",
            description=(
                "Deposit-franchise banking policy. Classic FCFF DCF is "
                "unsupported; book / residual-income preferred."
            ),
            characteristic_ids=(),
            valuation=ValuationProfile(
                preferred=("book_value", "residual_income"),
                acceptable=("earnings_multiple",),
                unsupported=("dcf",),
                interpretation_notes=(
                    "MoS on book is not interchangeable with FCFF MoS.",
                    "Naive DCF for banks is explicitly unsupported.",
                ),
                requires_engine_extension=("residual_income",),
            ),
            dimensions=(
                ComparisonDimension.QUALITY,
                ComparisonDimension.FINANCIAL_STRENGTH,
                ComparisonDimension.RISK,
                ComparisonDimension.VALUATION,
                ComparisonDimension.DECISION_ROBUSTNESS,
            ),
            metrics=(
                MetricApplicability(
                    metric_id="metric.nim",
                    importance=MetricImportance.CORE,
                    peer_use=PeerUse.ALLOWED,
                    interpretation_notes=(
                        "Placeholder — NIM calculation not implemented in C2.3.",
                    ),
                ),
            ),
            peer_policy=PeerEligibilityPolicyRef(
                policy_id="dsp.peer_policy.commercial_banking",
                notes=("See PeerEligibilityPolicy registry (C2.4).",),
            ),
            interpretation_notes=(
                "Banks must never share methodology with insurance or exchanges.",
            ),
            changelog="Initial illustrative commercial banking methodology.",
        ),
        IndustryMethodology(
            id="dsp.methodology.electric_utilities",
            industry_id="dsp.industry.electric_utilities",
            version="1.0.0",
            name="Electric Utilities",
            description=(
                "Regulated utility policy inheriting Stable Regulated Cash Flow "
                "defaults with income-oriented valuation override."
            ),
            characteristic_ids=(
                "dsp.characteristics.stable_regulated_cash_flow",
            ),
            valuation=ValuationProfile(
                preferred=("dividend_discount", "nav", "dcf"),
                acceptable=("earnings_multiple",),
                unsupported=(),
                interpretation_notes=(
                    "Prefer contracted/regulated cash-flow anchors.",
                ),
            ),
            dimensions=None,  # inherit characteristic dimension emphasis
            metrics=(),
            peer_policy=PeerEligibilityPolicyRef(
                policy_id="dsp.peer_policy.electric_utilities",
            ),
            interpretation_notes=(
                "Sharing Stable Regulated Cash Flow does not imply peers "
                "with towers or InvITs."
            ),
            changelog="Initial illustrative electric utilities methodology.",
        ),
        IndustryMethodology(
            id="dsp.methodology.premium_consumer_franchise",
            industry_id="dsp.industry.premium_consumer_franchise",
            version="1.0.0",
            name="Premium Consumer Franchise",
            description=(
                "Pricing-power consumer franchise; inherits Pricing Power "
                "Franchise characteristic defaults unless overridden."
            ),
            characteristic_ids=(
                "dsp.characteristics.pricing_power_franchise",
            ),
            valuation=None,  # characteristics → preferred methods
            dimensions=(
                ComparisonDimension.QUALITY,
                ComparisonDimension.GROWTH,
                ComparisonDimension.CAPITAL_ALLOCATION,
                ComparisonDimension.VALUATION,
                ComparisonDimension.DECISION_ROBUSTNESS,
            ),
            metrics=(),
            peer_policy=PeerEligibilityPolicyRef(
                policy_id="dsp.peer_policy.premium_consumer_franchise",
            ),
            interpretation_notes=(
                "Franchise economics; brand durability over near-term volume."
            ),
            changelog="Initial illustrative premium consumer franchise methodology.",
        ),
    )


def register_example_methodologies(
    registry: IndustryMethodologyRegistry,
) -> IndustryMethodologyRegistry:
    """Register illustrative methodologies (idempotent)."""
    for methodology in build_example_methodologies():
        registry.register(methodology)
    return registry
