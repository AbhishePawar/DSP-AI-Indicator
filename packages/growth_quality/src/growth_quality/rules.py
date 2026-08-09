"""Rule-based growth quality dimension evaluators (Buffett-aligned).

Prioritises sustainable compounding and capital-efficient reinvestment.
Does not reward leverage- or dilution-driven expansion when proxies indicate it.
"""

from __future__ import annotations

from typing import Any

from growth_quality.models import (
    GrowthQualityComponentScore,
    GrowthQualityConfidence,
    GrowthQualityEvidence,
    GrowthQualityScore,
)
from growth_quality.scoring import (
    GrowthQualityDimension,
    GrowthQualityWeights,
    clip_score,
)
from growth_quality.signals import assessment_score_01, ratio_value, safe_getattr

__all__ = ["evaluate_all_components", "mean_present"]


def mean_present(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _score_100(value_01: float | None) -> GrowthQualityScore:
    if value_01 is None:
        return GrowthQualityScore(value=None, status="insufficient_data")
    return GrowthQualityScore(value=clip_score(value_01 * 100.0), status="assessed")


def _confidence(values: list[float | None], *, basis: str) -> GrowthQualityConfidence:
    present = sum(1 for v in values if v is not None)
    if present == 0:
        return GrowthQualityConfidence(value=0.0, basis="insufficient_inputs")
    if present >= 3:
        return GrowthQualityConfidence(value=0.85, basis=basis)
    if present == 2:
        return GrowthQualityConfidence(value=0.65, basis=basis)
    return GrowthQualityConfidence(value=0.40, basis=basis)


def _evidence(
    *,
    source: str,
    reference: str,
    summary: str,
    reasoning: str,
    confidence: float,
    metrics: list[str],
    limitations: list[str],
) -> GrowthQualityEvidence:
    return GrowthQualityEvidence(
        source=source,
        reference=reference,
        summary=summary,
        reasoning=reasoning,
        confidence=confidence,
        supporting_metrics=tuple(metrics),
        limitations=tuple(limitations),
    )


def _component(
    dimension: GrowthQualityDimension,
    value_01: float | None,
    *,
    weight: float,
    confidence: GrowthQualityConfidence,
    evidence: list[GrowthQualityEvidence],
    reasoning: str,
    positives: list[str],
    negatives: list[str],
    risks: list[str],
) -> GrowthQualityComponentScore:
    return GrowthQualityComponentScore(
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


def _bq(module: object | None, *names: str) -> float | None:
    for name in names:
        value = assessment_score_01(module, name)
        if value is not None:
            return value
    return None


def _map_growth(cagr: float | None) -> float | None:
    """Map growth rate to 0–1; prefer durable mid-teens over boom/bust extremes."""
    if cagr is None:
        return None
    v = float(cagr)
    # Negative growth is weak
    if v < 0:
        return max(0.0, 0.35 + v)  # mild penalty
    # 5–15% sweet spot for quality compounders
    if 0.05 <= v <= 0.15:
        return 0.75 + min(0.20, (v - 0.05) / 0.10 * 0.20)
    if v < 0.05:
        return max(0.35, v / 0.05 * 0.55)
    # Very high growth: cap unless consistency supports (handled elsewhere)
    if v <= 0.30:
        return 0.70
    return 0.55


def evaluate_revenue_growth(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> GrowthQualityComponentScore:
    cagr = safe_getattr(financial_analysis, "income", "revenue", "cagr")
    yoy = safe_getattr(financial_analysis, "income", "revenue", "yoy_growth")
    stab = safe_getattr(financial_analysis, "income", "revenue", "growth_stability")
    rev_stab = _bq(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "revenue_stability",
    )
    scale = _bq(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "business_scalability",
    )
    goodwill = safe_getattr(
        financial_analysis, "balance_sheet", "assets", "goodwill_pct"
    )
    # Organic vs acquisition proxy: high goodwill growth intensity softens score
    organic = None
    if goodwill is not None:
        organic = max(0.0, min(1.0, 1.0 - min(0.5, float(goodwill) * 1.5)))
    # Do not treat YoY as CAGR — separate mapped signals only.
    cagr_s = _map_growth(cagr) if cagr is not None else None
    yoy_s = _map_growth(yoy) if yoy is not None else None
    value = mean_present([cagr_s, yoy_s, stab, rev_stab, scale, organic])
    conf = _confidence(
        [cagr, yoy, stab, rev_stab, scale, goodwill],
        basis="revenue_growth_quality_proxies",
    )
    if cagr is None and yoy is None:
        conf = GrowthQualityConfidence(
            value=min(conf.value, 0.50),
            basis=conf.basis + "_insufficient_history",
        )
    elif cagr is None and yoy is not None:
        conf = GrowthQualityConfidence(
            value=min(conf.value, 0.60),
            basis=conf.basis + "_yoy_only_not_cagr",
        )
    positives: list[str] = []
    negatives: list[str] = []
    if cagr is not None and 0.05 <= float(cagr) <= 0.15:
        positives.append("Revenue CAGR in durable compounding range")
    if goodwill is not None and float(goodwill) > 0.20:
        negatives.append("Elevated goodwill may indicate acquisition-led growth")
    risks = (
        "Organic vs acquisition growth not proven without deal history",
        "Multi-year CAGR may be unavailable on short histories",
    )
    metrics = [
        f"revenue_cagr={cagr}",
        f"yoy_growth={yoy}",
        f"growth_stability={stab}",
        f"revenue_stability_01={rev_stab}",
        f"business_scalability_01={scale}",
        f"goodwill_pct={goodwill}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="income.revenue / BQ stability & scalability",
            summary="Revenue CAGR/stability with organic-growth proxies",
            reasoning=(
                "Buffett prefers durable organic growth over boom/bust spikes. "
                "We score CAGR quality, consistency, scalability, and soften for "
                "high goodwill intensity."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["No segment or acquisition attribution feed"],
        )
    ]
    return _component(
        GrowthQualityDimension.REVENUE_GROWTH_QUALITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Revenue growth quality scored from CAGR/consistency and organic proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_earnings_growth(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> GrowthQualityComponentScore:
    earn_cons = _bq(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "earnings_consistency",
    )
    profit_pers = _bq(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "profitability_persistence",
    )
    ocf_growth = safe_getattr(
        financial_analysis, "cash_flow", "operating", "operating_cash_flow_growth"
    )
    ni_quality = _bq(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "net_earnings_quality",
    )
    op_quality = _bq(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "operating_earnings_quality",
    )
    fcf_support = _bq(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "free_cash_flow_support",
    )
    eps_cagr = safe_getattr(
        financial_analysis, "income", "profitability", "eps_cagr"
    )
    eps_cagr_basis = safe_getattr(
        financial_analysis, "income", "profitability", "eps_cagr_basis"
    )
    ocf_s = _map_growth(ocf_growth)
    eps_cagr_s = _map_growth(eps_cagr) if eps_cagr is not None else None
    value = mean_present(
        [
            earn_cons,
            profit_pers,
            ni_quality,
            op_quality,
            fcf_support,
            ocf_s,
            eps_cagr_s,
        ]
    )
    conf = _confidence(
        [
            earn_cons,
            profit_pers,
            ni_quality,
            op_quality,
            fcf_support,
            ocf_growth,
            eps_cagr,
        ],
        basis="earnings_growth_quality_proxies",
    )
    if eps_cagr is None:
        conf = GrowthQualityConfidence(
            value=min(conf.value, 0.60),
            basis=conf.basis + "_eps_cagr_unavailable",
        )
    positives: list[str] = []
    negatives: list[str] = []
    if profit_pers is not None and profit_pers >= 0.7:
        positives.append("Persistent profitability supports earnings growth quality")
    if fcf_support is not None and fcf_support < 0.4:
        negatives.append("Weak cash backing of earnings growth")
    if eps_cagr is not None and 0.05 <= float(eps_cagr) <= 0.15:
        positives.append("EPS CAGR in durable compounding range")
    risks = (
        "EPS CAGR unavailable when diluted/basic series incomplete or non-positive",
        "Negative→positive EPS transitions do not yield a conventional CAGR",
    )
    metrics = [
        f"earnings_consistency_01={earn_cons}",
        f"profitability_persistence_01={profit_pers}",
        f"net_earnings_quality_01={ni_quality}",
        f"operating_earnings_quality_01={op_quality}",
        f"free_cash_flow_support_01={fcf_support}",
        f"operating_cash_flow_growth={ocf_growth}",
        f"eps_cagr={eps_cagr}",
        f"eps_cagr_basis={eps_cagr_basis}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="earnings_quality / competitive_position / cash_flow / eps_cagr",
            summary="Earnings/cash growth consistency, EPS CAGR, and cash support",
            reasoning=(
                "Quality earnings growth is cash-backed and persistent. We reuse "
                "BQ consistency/persistence and cash-support assessments, and score "
                "first-class annual-fiscal EPS CAGR when evidence allows."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=[
                "Does not invent multi-year EPS CAGR from a single period",
                "Does not mix diluted and basic EPS in one CAGR",
            ],
        )
    ]
    return _component(
        GrowthQualityDimension.EARNINGS_GROWTH_QUALITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Earnings growth quality scored from persistence, consistency, and "
            "cash-backed growth proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_reinvestment(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> GrowthQualityComponentScore:
    reinvest = _bq(
        safe_getattr(business_quality_analysis, "capital_allocation"),
        "reinvestment_quality",
    )
    capex = _bq(
        safe_getattr(business_quality_analysis, "capital_allocation"),
        "capex_discipline",
    )
    roc = _bq(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "return_on_capital_strength",
    )
    cap_eff = _bq(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "capital_efficiency",
    )
    roic = ratio_value(
        safe_getattr(financial_analysis, "ratios", "profitability"), "roic"
    )
    roic_s = None if roic is None else max(0.0, min(1.0, float(roic) / 0.18))
    # ROIC vs growth uses annual CAGR only — never silent YoY substitution.
    cagr = safe_getattr(financial_analysis, "income", "revenue", "cagr")
    roic_vs_g = None
    if roic is not None and cagr is not None and float(cagr) > 0:
        # Prefer ROIC comfortably above growth (value-creating reinvestment)
        spread = float(roic) - float(cagr)
        roic_vs_g = max(0.0, min(1.0, 0.5 + spread / 0.20))
    value = mean_present([reinvest, capex, roc, cap_eff, roic_s, roic_vs_g])
    conf = _confidence(
        [reinvest, capex, roc, cap_eff, roic, cagr],
        basis="reinvestment_capability_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if roic is not None and float(roic) >= 0.12:
        positives.append("High ROIC supports internal compounding")
    if reinvest is not None and reinvest < 0.4:
        negatives.append("Weak reinvestment quality")
    risks = ("Incremental ROIC not observed deal-by-deal",)
    metrics = [
        f"reinvestment_quality_01={reinvest}",
        f"capex_discipline_01={capex}",
        f"return_on_capital_strength_01={roc}",
        f"capital_efficiency_01={cap_eff}",
        f"roic={roic}",
        f"revenue_growth={cagr}",
        f"roic_vs_growth_proxy={roic_vs_g}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="capital_allocation / competitive_position / ROIC",
            summary="Reinvestment quality, ROIC, and capital efficiency",
            reasoning=(
                "Buffett prizes businesses that reinvest at high returns. We score "
                "reinvestment/capex discipline and ROIC versus growth spreads."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["No project-level incremental ROIC series"],
        )
    ]
    return _component(
        GrowthQualityDimension.REINVESTMENT_CAPABILITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Reinvestment capability scored from ROIC, capital efficiency, and "
            "reinvestment-discipline proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_capital_support(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> GrowthQualityComponentScore:
    ca = safe_getattr(business_quality_analysis, "capital_allocation")
    cash_deploy = _bq(ca, "cash_deployment_quality")
    flex = _bq(ca, "financial_flexibility")
    debt_red = _bq(ca, "debt_reduction_discipline")
    buyback = _bq(ca, "share_buyback_quality")
    fcf = safe_getattr(
        financial_analysis, "cash_flow", "free_cash_flow", "free_cash_flow"
    )
    debt_issued = safe_getattr(
        financial_analysis, "cash_flow", "financing", "debt_issued"
    )
    # Internal funding proxy
    internal = 0.80 if fcf is not None and float(fcf) > 0 else (
        0.30 if fcf is not None else None
    )
    # Debt-funded expansion penalty
    debt_fund = None
    if debt_issued is not None:
        debt_fund = 0.75 if float(debt_issued) <= 0 else 0.40
    # Dilution is independent of buybacks — never alias buyback quality as dilution.
    dilution = _bq(ca, "dilution_discipline")
    value = mean_present(
        [cash_deploy, flex, debt_red, buyback, internal, debt_fund, dilution]
    )
    conf = _confidence(
        [cash_deploy, flex, debt_red, fcf, debt_issued, buyback, dilution],
        basis="capital_allocation_support_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if fcf is not None and float(fcf) > 0:
        positives.append("Growth can be supported by positive free cash flow")
    if debt_issued is not None and float(debt_issued) > 0:
        negatives.append("Debt issuance observed — watch leverage-funded expansion")
    risks = (
        "Acquisition discipline inferred from BQ cash-deployment proxies only",
        "Share issuance / dilution detail may be incomplete",
    )
    metrics = [
        f"cash_deployment_quality_01={cash_deploy}",
        f"financial_flexibility_01={flex}",
        f"debt_reduction_discipline_01={debt_red}",
        f"share_buyback_quality_01={buyback}",
        f"free_cash_flow={fcf}",
        f"debt_issued={debt_issued}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="cash_flow.financing / BQ capital_allocation",
            summary="Internal vs debt-funded growth and allocation discipline",
            reasoning=(
                "Quality growth is funded by internal cash, not chronic dilution "
                "or reckless leverage. We reward FCF funding and debt discipline."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["No deal-level acquisition IRR evidence"],
        )
    ]
    return _component(
        GrowthQualityDimension.CAPITAL_ALLOCATION_SUPPORT,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Capital allocation support scored from internal funding capacity and "
            "BQ deployment/flexibility proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_sustainability(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> GrowthQualityComponentScore:
    margin_def = _bq(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "margin_defensibility",
    )
    margin_dur = _bq(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "margin_durability",
    )
    scale = _bq(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "business_scalability",
    )
    cash_gen = _bq(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "cash_generation",
    )
    fcf_support = _bq(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "free_cash_flow_support",
    )
    om = safe_getattr(financial_analysis, "income", "margins", "operating_margin")
    om_s = None if om is None else max(0.0, min(1.0, (float(om) - 0.03) / 0.20))
    value = mean_present(
        [margin_def, margin_dur, scale, cash_gen, fcf_support, om_s]
    )
    conf = _confidence(
        [margin_def, margin_dur, scale, cash_gen, fcf_support, om],
        basis="growth_sustainability_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if scale is not None and scale >= 0.7:
        positives.append("Scalability supports sustainable growth")
    if margin_def is not None and margin_def < 0.4:
        negatives.append("Weak margin defensibility during growth")
    risks = ("Competitive durability not peer-benchmarked in Phase 1",)
    metrics = [
        f"margin_defensibility_01={margin_def}",
        f"margin_durability_01={margin_dur}",
        f"business_scalability_01={scale}",
        f"cash_generation_01={cash_gen}",
        f"free_cash_flow_support_01={fcf_support}",
        f"operating_margin={om}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="margins / scalability / cash generation",
            summary="Margin preservation, scalability, cash-backed growth",
            reasoning=(
                "Sustainable growth preserves margins and remains cash-backed. "
                "We combine defensibility, scalability, and cash generation."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["Cyclicality may be under-specified without multi-cycle data"],
        )
    ]
    return _component(
        GrowthQualityDimension.GROWTH_SUSTAINABILITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Growth sustainability scored from margin preservation, scalability, "
            "and cash-backed growth proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_growth_risk(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> GrowthQualityComponentScore:
    """Higher score = lower growth risk (Buffett prefers less fragile growth)."""
    rev_stab = _bq(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "revenue_stability",
    )
    earn_cons = _bq(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "earnings_consistency",
    )
    resilience = _bq(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "financial_resilience",
    )
    cyclical = _bq(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "cyclicality",
    )
    # Invert cyclicality if present (high cyclicality = higher risk = lower score)
    cyclical_safe = None if cyclical is None else max(0.0, min(1.0, 1.0 - float(cyclical)))
    goodwill = safe_getattr(
        financial_analysis, "balance_sheet", "assets", "goodwill_pct"
    )
    concentration = None
    if goodwill is not None:
        # Soft proxy for integration / acquisition execution risk
        concentration = max(0.0, min(1.0, 1.0 - min(0.6, float(goodwill))))
    # Customer concentration / market saturation not available — confidence cap
    value = mean_present(
        [rev_stab, earn_cons, resilience, cyclical_safe, concentration]
    )
    conf = _confidence(
        [rev_stab, earn_cons, resilience, cyclical, goodwill],
        basis="growth_risk_proxies",
    )
    conf = GrowthQualityConfidence(
        value=min(conf.value, 0.55),
        basis=conf.basis + "_no_customer_concentration",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if rev_stab is not None and rev_stab >= 0.7:
        positives.append("Stable revenue reduces growth volatility risk")
    if goodwill is not None and float(goodwill) > 0.25:
        negatives.append("High goodwill raises acquisition/execution risk proxy")
    risks = (
        "Customer concentration and market saturation not observable in Phase 1",
        "Competitive pressure not peer-modeled",
    )
    metrics = [
        f"revenue_stability_01={rev_stab}",
        f"earnings_consistency_01={earn_cons}",
        f"financial_resilience_01={resilience}",
        f"cyclicality_01={cyclical}",
        f"goodwill_pct={goodwill}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="stability / resilience / goodwill intensity",
            summary="Growth volatility and execution-risk proxies",
            reasoning=(
                "Growth risk rises with volatility, cyclicality, and acquisition "
                "intensity. Score is inverted so higher = safer growth profile, "
                "with confidence capped without concentration data."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=[
                "No customer/geo concentration feed",
                "Future AI extension: market-structure / customer providers",
            ],
        )
    ]
    return _component(
        GrowthQualityDimension.GROWTH_RISK,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Growth risk scored (inverted) from volatility, cyclicality, and "
            "acquisition-intensity proxies; concentration deferred."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_all_components(
    financial_analysis: Any,
    business_quality_analysis: Any,
    weights: GrowthQualityWeights,
) -> tuple[GrowthQualityComponentScore, ...]:
    return (
        evaluate_revenue_growth(
            financial_analysis,
            business_quality_analysis,
            weight=weights.revenue_growth_quality,
        ),
        evaluate_earnings_growth(
            financial_analysis,
            business_quality_analysis,
            weight=weights.earnings_growth_quality,
        ),
        evaluate_reinvestment(
            financial_analysis,
            business_quality_analysis,
            weight=weights.reinvestment_capability,
        ),
        evaluate_capital_support(
            financial_analysis,
            business_quality_analysis,
            weight=weights.capital_allocation_support,
        ),
        evaluate_sustainability(
            financial_analysis,
            business_quality_analysis,
            weight=weights.growth_sustainability,
        ),
        evaluate_growth_risk(
            financial_analysis,
            business_quality_analysis,
            weight=weights.growth_risk,
        ),
    )
