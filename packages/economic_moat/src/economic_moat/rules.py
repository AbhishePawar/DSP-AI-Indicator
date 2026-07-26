"""Rule-based moat dimension evaluators (Buffett-aligned, explainable).

Each dimension maps public FinancialAnalysis + BusinessQualityAnalysis signals
into a scored component with evidence, confidence, reasoning, and limitations.
No opaque scoring. No market sentiment. No peer datasets.
"""

from __future__ import annotations

from typing import Any

from economic_moat.models import (
    EconomicConfidence,
    EconomicEvidence,
    EconomicScore,
    MoatComponentScore,
)
from economic_moat.scoring import MoatDimension, MoatWeights, clip_score
from economic_moat.signals import (
    assessment_score_01,
    goodwill_pct,
    gross_margin,
    intangible_pct,
    operating_margin,
    ratio_value,
    safe_getattr,
)

__all__ = ["evaluate_all_components", "mean_present"]


def mean_present(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _score_100(value_01: float | None) -> EconomicScore:
    if value_01 is None:
        return EconomicScore(value=None, status="insufficient_data")
    return EconomicScore(
        value=clip_score(value_01 * 100.0),
        status="assessed",
    )


def _confidence(values: list[float | None], *, basis: str) -> EconomicConfidence:
    present = sum(1 for v in values if v is not None)
    if present == 0:
        return EconomicConfidence(value=0.0, basis="insufficient_inputs")
    if present >= 3:
        return EconomicConfidence(value=0.85, basis=basis)
    if present == 2:
        return EconomicConfidence(value=0.65, basis=basis)
    return EconomicConfidence(value=0.40, basis=basis)


def _evidence(
    *,
    source: str,
    reference: str,
    summary: str,
    reasoning: str,
    confidence: float,
    metrics: list[str],
    limitations: list[str],
) -> EconomicEvidence:
    return EconomicEvidence(
        source=source,
        reference=reference,
        summary=summary,
        reasoning=reasoning,
        confidence=confidence,
        supporting_metrics=tuple(metrics),
        limitations=tuple(limitations),
    )


def _component(
    dimension: MoatDimension,
    value_01: float | None,
    *,
    weight: float,
    confidence: EconomicConfidence,
    evidence: list[EconomicEvidence],
    reasoning: str,
    positives: list[str],
    negatives: list[str],
    risks: list[str],
) -> MoatComponentScore:
    return MoatComponentScore(
        dimension=dimension,
        score=_score_100(value_01),
        confidence=confidence,
        evidence=tuple(evidence),
        reasoning=reasoning,
        positive_factors=tuple(positives),
        negative_factors=tuple(negatives),
        risks=tuple(risks),
        weight=weight,
    )


def evaluate_brand(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> MoatComponentScore:
    """Brand strength / pricing power / loyalty proxies from FA + BQ."""
    gm = gross_margin(financial_analysis)
    om = operating_margin(financial_analysis)
    pricing = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "pricing_power",
    )
    margin_def = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "margin_defensibility",
    )
    revenue_stab = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "revenue_stability",
    )
    # Margin levels as brand/pricing proxies (Buffett: pricing power)
    gm_score = None if gm is None else max(0.0, min(1.0, (gm - 0.15) / 0.45))
    om_score = None if om is None else max(0.0, min(1.0, (om - 0.05) / 0.30))
    value = mean_present([pricing, margin_def, revenue_stab, gm_score, om_score])
    conf = _confidence(
        [pricing, margin_def, revenue_stab, gm, om],
        basis="brand_pricing_power_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if gm is not None and gm >= 0.40:
        positives.append("Elevated gross margin supports pricing power narrative")
    if gm is not None and gm < 0.25:
        negatives.append("Thin gross margin weakens brand/pricing-power evidence")
    if pricing is not None and pricing >= 0.7:
        positives.append("Business Quality pricing-power assessment is strong")
    if revenue_stab is not None and revenue_stab < 0.4:
        negatives.append("Unstable revenue weakens loyalty/recognition proxy")
    risks = (
        "Brand strength inferred from financial proxies; no survey/brand-equity data",
    )
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="income.margins",
            summary="Gross/operating margins as pricing-power proxies",
            reasoning=(
                "Buffett emphasizes durable pricing power. High, stable margins are "
                "consistent with brand strength; they do not prove brand alone."
            ),
            confidence=conf.value,
            metrics=[f"gross_margin={gm}", f"operating_margin={om}"],
            limitations=[
                "Margins also reflect cost structure and industry norms",
                "No direct brand awareness or NPS inputs",
            ],
        ),
        _evidence(
            source="BusinessQualityAnalysis",
            reference="competitive_position.assessments",
            summary="Reuses BQ pricing power / margin / revenue stability",
            reasoning=(
                "Competitive Position Indicators already map FA margins and "
                "consistency into research scores; moat brand reuses them."
            ),
            confidence=conf.value,
            metrics=[
                f"pricing_power_01={pricing}",
                f"margin_defensibility_01={margin_def}",
                f"revenue_stability_01={revenue_stab}",
            ],
            limitations=["Does not invent brand surveys or advertising share"],
        ),
    ]
    return _component(
        MoatDimension.BRAND,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Brand moat scored from durable pricing-power and margin/revenue "
            "stability proxies aligned with Buffett's preference for businesses "
            "customers pay up for and stick with."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_network_effects(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> MoatComponentScore:
    """Network effects — conservative proxies only (scalability + cash growth)."""
    scalability = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "business_scalability",
    )
    cash_gen = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "cash_generation",
    )
    asset_light = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "asset_light",
    )
    # Network effects cannot be proven from statements alone — cap optimism
    raw = mean_present([scalability, cash_gen, asset_light])
    value = None if raw is None else min(raw * 0.85, 0.75)
    conf = _confidence(
        [scalability, cash_gen, asset_light],
        basis="network_effects_proxies_limited",
    )
    # Lower confidence ceiling for this dimension
    conf = EconomicConfidence(
        value=min(conf.value, 0.55),
        basis=conf.basis,
    )
    positives: list[str] = []
    negatives: list[str] = []
    if scalability is not None and scalability >= 0.7:
        positives.append("High scalability is consistent with platform-like economics")
    else:
        negatives.append("Limited scalability evidence for network-effect claims")
    risks = (
        "Network effects require user/platform data; financial proxies are weak",
        "Score intentionally capped to avoid overstating platform moats",
    )
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="business_characteristics.assessments",
            summary="Scalability / asset-light / cash generation as weak proxies",
            reasoning=(
                "True network effects reinforce with each incremental user. "
                "Statements lack user graphs; we use scalability/asset-light "
                "flags as cautious, capped proxies only."
            ),
            confidence=conf.value,
            metrics=[
                f"business_scalability_01={scalability}",
                f"cash_generation_01={cash_gen}",
                f"asset_light_01={asset_light}",
            ],
            limitations=[
                "No MAU/DAU, engagement, or ecosystem data",
                "Future AI extension point: platform telemetry providers",
            ],
        )
    ]
    _ = financial_analysis  # reserved for future provider hooks
    return _component(
        MoatDimension.NETWORK_EFFECTS,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Network-effects dimension is deliberately conservative: without "
            "platform usage data, only weak scalability proxies are used and "
            "scores are capped."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_switching_costs(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> MoatComponentScore:
    """Switching costs / lock-in proxies from recurring economics + resilience."""
    recurring = assessment_score_01(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "recurring_vs_non_recurring",
    )
    if recurring is None:
        recurring = assessment_score_01(
            safe_getattr(business_quality_analysis, "earnings_quality"),
            "recurring_earnings",
        )
    # Try common EQ assessment names
    for name in (
        "recurring_vs_non_recurring_earnings",
        "recurring_vs_non_recurring",
        "earnings_consistency",
    ):
        if recurring is None:
            recurring = assessment_score_01(
                safe_getattr(business_quality_analysis, "earnings_quality"),
                name,
            )
    resilience = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "financial_resilience",
    )
    cash_conv = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "cash_conversion_advantage",
    )
    fcf_stab = safe_getattr(
        financial_analysis, "cash_flow", "free_cash_flow", "fcf_stability"
    )
    value = mean_present([recurring, resilience, cash_conv, fcf_stab])
    conf = _confidence(
        [recurring, resilience, cash_conv, fcf_stab],
        basis="switching_cost_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if recurring is not None and recurring >= 0.7:
        positives.append("Recurring earnings support customer lock-in narrative")
    if resilience is not None and resilience < 0.4:
        negatives.append("Weak resilience reduces switching-cost durability claim")
    risks = (
        "Contractual / integration switching costs not directly observable in FA",
    )
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="earnings_quality / business_characteristics",
            summary="Recurring earnings and resilience as lock-in proxies",
            reasoning=(
                "Buffett values businesses customers find painful to leave. "
                "Recurring, resilient cash economics are consistent with — "
                "but not proof of — switching costs."
            ),
            confidence=conf.value,
            metrics=[
                f"recurring_01={recurring}",
                f"financial_resilience_01={resilience}",
                f"cash_conversion_advantage_01={cash_conv}",
                f"fcf_stability={fcf_stab}",
            ],
            limitations=[
                "No contract tenure, migration-cost, or tech-integration data",
                "Future AI extension: CRM / contract metadata providers",
            ],
        )
    ]
    return _component(
        MoatDimension.SWITCHING_COSTS,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Switching-cost moat scored from recurring earnings quality and "
            "financial resilience proxies emphasizing durable customer economics."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_cost_advantage(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> MoatComponentScore:
    """Cost advantage from scale economies / efficiency / ROIC proxies."""
    op_eff = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "operational_efficiency",
    )
    roc = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "return_on_capital_strength",
    )
    capital_int = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "capital_intensity",
    )
    # Lower capital intensity can indicate process advantage; invert for cost edge
    capital_adv = None if capital_int is None else max(0.0, min(1.0, 1.0 - capital_int))
    roic = ratio_value(
        safe_getattr(financial_analysis, "ratios", "profitability"), "roic"
    )
    roic_score = None if roic is None else max(0.0, min(1.0, roic / 0.20))
    om = operating_margin(financial_analysis)
    om_score = None if om is None else max(0.0, min(1.0, (om - 0.05) / 0.25))
    value = mean_present([op_eff, roc, capital_adv, roic_score, om_score])
    conf = _confidence(
        [op_eff, roc, capital_int, roic, om],
        basis="cost_advantage_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if roic is not None and roic >= 0.15:
        positives.append("High ROIC supports durable cost/capital advantage")
    if op_eff is not None and op_eff < 0.4:
        negatives.append("Weak operational efficiency undermines cost-advantage claim")
    risks = (
        "Procurement / manufacturing / distribution advantages not line-item proven",
    )
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="ratios.profitability / income.margins",
            summary="ROIC and operating margin as cost/capital efficiency proxies",
            reasoning=(
                "Buffett prizes high returns on capital sustained over time. "
                "Elevated ROIC and efficient operations are consistent with "
                "structural cost advantage."
            ),
            confidence=conf.value,
            metrics=[
                f"roic={roic}",
                f"operating_margin={om}",
                f"operational_efficiency_01={op_eff}",
                f"return_on_capital_strength_01={roc}",
                f"capital_intensity_01={capital_int}",
            ],
            limitations=[
                "Does not separate scale vs process vs location cost edges",
                "Industry cost curves not modeled",
            ],
        )
    ]
    return _component(
        MoatDimension.COST_ADVANTAGE,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Cost-advantage moat scored from ROIC, operating efficiency, and "
            "capital-intensity proxies emphasizing long-term capital efficiency."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_intangible_assets(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> MoatComponentScore:
    """Intangibles / IP proxies from balance-sheet composition + BQ simplicity."""
    int_pct = intangible_pct(financial_analysis)
    gw_pct = goodwill_pct(financial_analysis)
    simplicity = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "business_simplicity",
    )
    # Moderate intangibles can signal IP; extreme goodwill alone is weaker (M&A)
    int_score = None
    if int_pct is not None:
        # Peak around 5–25% of assets
        if int_pct <= 0.02:
            int_score = 0.25
        elif int_pct <= 0.25:
            int_score = 0.35 + (int_pct / 0.25) * 0.45
        else:
            int_score = 0.70  # high intangibles — still useful but capped
    gw_score = None
    if gw_pct is not None:
        gw_score = max(0.0, min(0.55, gw_pct * 2.0))
    value = mean_present([int_score, gw_score, simplicity])
    conf = _confidence(
        [int_pct, gw_pct, simplicity],
        basis="intangible_asset_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if int_pct is not None and int_pct >= 0.05:
        positives.append("Material intangible asset share on the balance sheet")
    if gw_pct is not None and gw_pct > 0.25:
        negatives.append("High goodwill concentration may reflect acquisitions, not IP")
    risks = (
        "Patents, licences, and regulatory approvals not identified by name",
        "Accounting intangibles ≠ economic IP quality",
    )
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="balance_sheet.assets",
            summary="Intangible and goodwill intensity as IP/accounting proxies",
            reasoning=(
                "Buffett values hard-to-replicate intangible advantages. "
                "Reported intangible intensity is a starting proxy; patent "
                "quality and regulatory franchises require dedicated data."
            ),
            confidence=conf.value,
            metrics=[
                f"intangible_asset_pct={int_pct}",
                f"goodwill_pct={gw_pct}",
                f"business_simplicity_01={simplicity}",
            ],
            limitations=[
                "No patent counts, licence lists, or FDA/regulatory registries",
                "Future AI extension: IP / regulatory document providers",
            ],
        )
    ]
    return _component(
        MoatDimension.INTANGIBLE_ASSETS,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Intangible-assets moat scored from balance-sheet intangible/goodwill "
            "intensity with explicit limits on accounting vs economic IP."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_efficient_scale(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> MoatComponentScore:
    """Efficient scale / natural-monopoly-like proxies (conservative)."""
    capital_int = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "capital_intensity",
    )
    scalability = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "business_scalability",
    )
    margin_dur = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "margin_durability",
    )
    if margin_dur is None:
        margin_dur = assessment_score_01(
            safe_getattr(business_quality_analysis, "competitive_position"),
            "margin_defensibility",
        )
    # Efficient scale: high capital intensity + durable margins, limited new entry
    # Inverse of easy scalability for many natural-monopoly settings
    limited_entry = None
    if capital_int is not None and scalability is not None:
        limited_entry = max(
            0.0, min(1.0, 0.55 * capital_int + 0.45 * (1.0 - scalability * 0.5))
        )
    elif capital_int is not None:
        limited_entry = capital_int
    value = mean_present([limited_entry, margin_dur, capital_int])
    # Cap — single-company FA cannot prove market concentration
    if value is not None:
        value = min(value, 0.70)
    conf = _confidence(
        [capital_int, scalability, margin_dur],
        basis="efficient_scale_proxies_limited",
    )
    conf = EconomicConfidence(value=min(conf.value, 0.50), basis=conf.basis)
    positives: list[str] = []
    negatives: list[str] = []
    if capital_int is not None and capital_int >= 0.6:
        positives.append("High capital intensity can deter new entrants")
    if margin_dur is not None and margin_dur < 0.4:
        negatives.append("Weak margin durability reduces efficient-scale claim")
    risks = (
        "Market concentration and geographic exclusivity not observable here",
        "Score capped without industry structure data",
    )
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="business_characteristics.assessments",
            summary="Capital intensity + margin durability as efficient-scale proxies",
            reasoning=(
                "Efficient scale moats appear when a market supports few players. "
                "Without industry HHI or franchise maps, we use capital intensity "
                "and durable margins as cautious, capped proxies."
            ),
            confidence=conf.value,
            metrics=[
                f"capital_intensity_01={capital_int}",
                f"business_scalability_01={scalability}",
                f"margin_durability_01={margin_dur}",
            ],
            limitations=[
                "No peer count, HHI, or geographic exclusivity inputs",
                "Future AI extension: industry structure providers",
            ],
        )
    ]
    _ = financial_analysis
    return _component(
        MoatDimension.EFFICIENT_SCALE,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Efficient-scale moat scored conservatively from capital intensity "
            "and margin durability; market-structure proof is deferred."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_all_components(
    financial_analysis: Any,
    business_quality_analysis: Any,
    weights: MoatWeights,
) -> tuple[MoatComponentScore, ...]:
    """Evaluate all six moat dimensions deterministically."""
    return (
        evaluate_brand(
            financial_analysis,
            business_quality_analysis,
            weight=weights.brand,
        ),
        evaluate_network_effects(
            financial_analysis,
            business_quality_analysis,
            weight=weights.network_effects,
        ),
        evaluate_switching_costs(
            financial_analysis,
            business_quality_analysis,
            weight=weights.switching_costs,
        ),
        evaluate_cost_advantage(
            financial_analysis,
            business_quality_analysis,
            weight=weights.cost_advantage,
        ),
        evaluate_intangible_assets(
            financial_analysis,
            business_quality_analysis,
            weight=weights.intangible_assets,
        ),
        evaluate_efficient_scale(
            financial_analysis,
            business_quality_analysis,
            weight=weights.efficient_scale,
        ),
    )
