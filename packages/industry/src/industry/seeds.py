"""Illustrative Investment Characteristics archetypes (not industry mappings)."""

from __future__ import annotations

from industry.characteristics import CharacteristicDefaults, InvestmentCharacteristics
from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.enums import (
    AssetIntensity,
    CapitalAllocationStyle,
    CapitalIntensity,
    CashFlowProfile,
    ComparisonDimensionHint,
    CompetitiveCharacter,
    Cyclicality,
    EarningsStability,
    GrowthProfile,
    PricingPower,
    RegulatoryIntensity,
    ValuationPhilosophyHint,
)

__all__ = [
    "EXAMPLE_ARCHETYPE_IDS",
    "build_example_archetypes",
    "register_example_archetypes",
]

EXAMPLE_ARCHETYPE_IDS: tuple[str, ...] = (
    "dsp.characteristics.stable_regulated_cash_flow",
    "dsp.characteristics.pricing_power_franchise",
    "dsp.characteristics.asset_heavy_cyclical",
    "dsp.characteristics.capital_light_compounder",
    "dsp.characteristics.network_effects",
)


def build_example_archetypes() -> tuple[InvestmentCharacteristics, ...]:
    """Return seed archetypes for documentation and tests."""
    return (
        InvestmentCharacteristics(
            id="dsp.characteristics.stable_regulated_cash_flow",
            name="Stable Regulated Cash Flow",
            version="1.0.0",
            description=(
                "Regulated or contracted cash flows with high asset intensity "
                "and income-oriented valuation philosophy."
            ),
            capital_intensity=CapitalIntensity.HIGH,
            cash_flow_profile=CashFlowProfile.STABLE,
            growth_profile=GrowthProfile.LOW,
            earnings_stability=EarningsStability.HIGH,
            cyclicality=Cyclicality.LOW,
            pricing_power=PricingPower.MODERATE,
            regulatory_intensity=RegulatoryIntensity.HIGH,
            asset_intensity=AssetIntensity.HIGH,
            capital_allocation_style=CapitalAllocationStyle.DISTRIBUTE,
            competitive_character=CompetitiveCharacter.REGULATED,
            business_economics_notes=(
                "Returns often constrained by regulation or long-term contracts.",
            ),
            defaults=CharacteristicDefaults(
                valuation_philosophy=ValuationPhilosophyHint.INCOME,
                preferred_method_hints=("dividend_discount", "nav", "dcf"),
                dimension_emphasis=(
                    ComparisonDimensionHint.PREDICTABILITY,
                    ComparisonDimensionHint.VALUATION,
                    ComparisonDimensionHint.FINANCIAL_STRENGTH,
                ),
                investment_philosophy_notes=(
                    "Prefer income/asset anchors; treat classic growth DCF cautiously.",
                ),
            ),
        ),
        InvestmentCharacteristics(
            id="dsp.characteristics.pricing_power_franchise",
            name="Pricing Power Franchise",
            version="1.0.0",
            description=(
                "Brand or franchise economics with strong pricing power, "
                "high returns on capital, and moderate capital needs."
            ),
            capital_intensity=CapitalIntensity.LOW,
            cash_flow_profile=CashFlowProfile.STABLE,
            growth_profile=GrowthProfile.MODERATE,
            earnings_stability=EarningsStability.HIGH,
            cyclicality=Cyclicality.LOW,
            pricing_power=PricingPower.STRONG,
            regulatory_intensity=RegulatoryIntensity.LOW,
            asset_intensity=AssetIntensity.LOW,
            capital_allocation_style=CapitalAllocationStyle.REINVEST,
            competitive_character=CompetitiveCharacter.FRANCHISE,
            business_economics_notes=(
                "Quality and capital allocation often dominate near-term multiples.",
            ),
            defaults=CharacteristicDefaults(
                valuation_philosophy=ValuationPhilosophyHint.EARNINGS,
                preferred_method_hints=("owner_earnings", "dcf", "earnings_multiple"),
                dimension_emphasis=(
                    ComparisonDimensionHint.QUALITY,
                    ComparisonDimensionHint.CAPITAL_ALLOCATION,
                    ComparisonDimensionHint.GROWTH,
                ),
            ),
        ),
        InvestmentCharacteristics(
            id="dsp.characteristics.asset_heavy_cyclical",
            name="Asset Heavy Cyclical",
            version="1.0.0",
            description=(
                "High asset intensity with cyclical earnings and commodity-like "
                "or utilization-driven economics."
            ),
            capital_intensity=CapitalIntensity.HIGH,
            cash_flow_profile=CashFlowProfile.CYCLICAL,
            growth_profile=GrowthProfile.MODERATE,
            earnings_stability=EarningsStability.LOW,
            cyclicality=Cyclicality.HIGH,
            pricing_power=PricingPower.WEAK,
            regulatory_intensity=RegulatoryIntensity.LOW,
            asset_intensity=AssetIntensity.HIGH,
            capital_allocation_style=CapitalAllocationStyle.OPPORTUNISTIC,
            competitive_character=CompetitiveCharacter.COMMODITY,
            defaults=CharacteristicDefaults(
                valuation_philosophy=ValuationPhilosophyHint.ASSET,
                preferred_method_hints=("book_value", "ev_ebitda", "replacement"),
                dimension_emphasis=(
                    ComparisonDimensionHint.VALUATION,
                    ComparisonDimensionHint.EFFICIENCY,
                    ComparisonDimensionHint.RISK,
                ),
            ),
        ),
        InvestmentCharacteristics(
            id="dsp.characteristics.capital_light_compounder",
            name="Capital Light Compounder",
            version="1.0.0",
            description=(
                "Low capital intensity businesses that can compound via "
                "reinvestment at attractive incremental returns."
            ),
            capital_intensity=CapitalIntensity.LOW,
            cash_flow_profile=CashFlowProfile.STABLE,
            growth_profile=GrowthProfile.HIGH,
            earnings_stability=EarningsStability.MODERATE,
            cyclicality=Cyclicality.LOW,
            pricing_power=PricingPower.MODERATE,
            regulatory_intensity=RegulatoryIntensity.LOW,
            asset_intensity=AssetIntensity.LOW,
            capital_allocation_style=CapitalAllocationStyle.REINVEST,
            competitive_character=CompetitiveCharacter.NICHE,
            defaults=CharacteristicDefaults(
                valuation_philosophy=ValuationPhilosophyHint.CASH_FLOW,
                preferred_method_hints=("dcf", "owner_earnings"),
                dimension_emphasis=(
                    ComparisonDimensionHint.GROWTH,
                    ComparisonDimensionHint.QUALITY,
                    ComparisonDimensionHint.CAPITAL_ALLOCATION,
                ),
            ),
        ),
        InvestmentCharacteristics(
            id="dsp.characteristics.network_effects",
            name="Network Effects",
            version="1.0.0",
            description=(
                "Platform or network businesses where scale and switching costs "
                "can reinforce competitive position."
            ),
            capital_intensity=CapitalIntensity.LOW,
            cash_flow_profile=CashFlowProfile.STABLE,
            growth_profile=GrowthProfile.EXPONENTIAL,
            earnings_stability=EarningsStability.MODERATE,
            cyclicality=Cyclicality.MODERATE,
            pricing_power=PricingPower.STRONG,
            regulatory_intensity=RegulatoryIntensity.MODERATE,
            asset_intensity=AssetIntensity.LOW,
            capital_allocation_style=CapitalAllocationStyle.REINVEST,
            competitive_character=CompetitiveCharacter.NETWORK,
            defaults=CharacteristicDefaults(
                valuation_philosophy=ValuationPhilosophyHint.HYBRID,
                preferred_method_hints=("dcf", "earnings_multiple"),
                dimension_emphasis=(
                    ComparisonDimensionHint.GROWTH,
                    ComparisonDimensionHint.QUALITY,
                    ComparisonDimensionHint.RISK,
                ),
            ),
        ),
    )


def register_example_archetypes(
    registry: InvestmentCharacteristicsRegistry,
) -> InvestmentCharacteristicsRegistry:
    """Register illustrative archetypes into ``registry`` (idempotent)."""
    for archetype in build_example_archetypes():
        registry.register(archetype)
    return registry
