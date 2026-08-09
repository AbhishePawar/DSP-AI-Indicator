"""Rule-based earnings quality dimension evaluators (Buffett-aligned).

Composes explainable scores from FinancialAnalysis + BusinessQualityAnalysis
public façades. Does not recompute statement math. Restatement registries
are out of scope for Phase 1.
"""

from __future__ import annotations

from typing import Any

from earnings_quality.models import (
    EarningsQualityComponentScore,
    EarningsQualityConfidence,
    EarningsQualityEvidence,
    EarningsQualityScore,
)
from earnings_quality.scoring import (
    EarningsQualityDimension,
    EarningsQualityWeights,
    clip_score,
)
from earnings_quality.signals import assessment_score_01, ratio_value, safe_getattr

__all__ = ["evaluate_all_components", "mean_present"]


def mean_present(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _score_100(value_01: float | None) -> EarningsQualityScore:
    if value_01 is None:
        return EarningsQualityScore(value=None, status="insufficient_data")
    return EarningsQualityScore(value=clip_score(value_01 * 100.0), status="assessed")


def _confidence(values: list[float | None], *, basis: str) -> EarningsQualityConfidence:
    present = sum(1 for v in values if v is not None)
    if present == 0:
        return EarningsQualityConfidence(value=0.0, basis="insufficient_inputs")
    if present >= 3:
        return EarningsQualityConfidence(value=0.85, basis=basis)
    if present == 2:
        return EarningsQualityConfidence(value=0.65, basis=basis)
    return EarningsQualityConfidence(value=0.40, basis=basis)


def _evidence(
    *,
    source: str,
    reference: str,
    summary: str,
    reasoning: str,
    confidence: float,
    metrics: list[str],
    limitations: list[str],
) -> EarningsQualityEvidence:
    return EarningsQualityEvidence(
        source=source,
        reference=reference,
        summary=summary,
        reasoning=reasoning,
        confidence=confidence,
        supporting_metrics=tuple(metrics),
        limitations=tuple(limitations),
    )


def _component(
    dimension: EarningsQualityDimension,
    value_01: float | None,
    *,
    weight: float,
    confidence: EarningsQualityConfidence,
    evidence: list[EarningsQualityEvidence],
    reasoning: str,
    positives: list[str],
    negatives: list[str],
    risks: list[str],
) -> EarningsQualityComponentScore:
    return EarningsQualityComponentScore(
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


def _bq_eq(business_quality_analysis: Any, *names: str) -> float | None:
    module = safe_getattr(business_quality_analysis, "earnings_quality")
    for name in names:
        value = assessment_score_01(module, name)
        if value is not None:
            return value
    return None


def _bq_cp(business_quality_analysis: Any, name: str) -> float | None:
    return assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"), name
    )


def _bq_bc(business_quality_analysis: Any, name: str) -> float | None:
    return assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"), name
    )


def _map_ratio(
    value: float | None, *, good: float, bad: float, invert: bool = False
) -> float | None:
    if value is None:
        return None
    v = float(value)
    if invert:
        if v <= good:
            return 1.0
        if v >= bad:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (v - good) / (bad - good)))
    if v >= good:
        return 1.0
    if v <= bad:
        return 0.0
    return max(0.0, min(1.0, (v - bad) / (good - bad)))


def evaluate_consistency(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> EarningsQualityComponentScore:
    earn_cons = _bq_eq(business_quality_analysis, "earnings_consistency")
    rev_stab = _bq_cp(business_quality_analysis, "revenue_stability")
    op_qual = _bq_eq(business_quality_analysis, "operating_earnings_quality")
    net_qual = _bq_eq(business_quality_analysis, "net_earnings_quality")
    rev_cons = safe_getattr(
        financial_analysis, "income", "consistency", "revenue_consistency"
    )
    eps_stab = safe_getattr(
        financial_analysis, "income", "profitability", "eps_stability"
    )
    value = mean_present(
        [earn_cons, rev_stab, op_qual, net_qual, rev_cons, eps_stab]
    )
    conf = _confidence(
        [earn_cons, rev_stab, op_qual, net_qual, rev_cons, eps_stab],
        basis="earnings_consistency_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if earn_cons is not None and earn_cons >= 0.7:
        positives.append("Strong earnings-consistency assessment")
    if rev_stab is not None and rev_stab < 0.4:
        negatives.append("Unstable revenue weakens consistency claim")
    risks = ("Multi-year trend quality depends on upstream history depth",)
    metrics = [
        f"earnings_consistency_01={earn_cons}",
        f"revenue_stability_01={rev_stab}",
        f"operating_earnings_quality_01={op_qual}",
        f"net_earnings_quality_01={net_qual}",
        f"revenue_consistency={rev_cons}",
        f"eps_stability={eps_stab}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="earnings_quality / competitive_position",
            summary="Consistency of revenue, EPS, and earnings series",
            reasoning=(
                "Buffett prefers businesses with predictable results. We reuse "
                "BQ consistency/stability assessments plus FA income consistency "
                "fields rather than inventing new time-series math."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["History length is owned by FinancialAnalysis"],
        )
    ]
    return _component(
        EarningsQualityDimension.EARNINGS_CONSISTENCY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Earnings consistency scored from revenue/EPS/earnings stability proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_quality(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> EarningsQualityComponentScore:
    cash_eq = _bq_eq(business_quality_analysis, "cash_earnings_quality")
    accruals = _bq_eq(business_quality_analysis, "accrual_quality")
    fcf_support = _bq_eq(business_quality_analysis, "free_cash_flow_support")
    conversion = safe_getattr(
        financial_analysis, "cash_flow", "operating", "cash_conversion"
    )
    ocf_to_earn = safe_getattr(
        financial_analysis, "cash_flow", "operating", "ocf_to_earnings"
    )
    one_time = safe_getattr(
        financial_analysis, "income", "consistency", "one_time_items_detected"
    )
    recurring = _bq_eq(business_quality_analysis, "recurring_earnings")
    ar_vs_rev = safe_getattr(
        financial_analysis,
        "balance_sheet",
        "working_capital",
        "receivables_vs_revenue_growth",
    )
    one_time_s = None if one_time is None else (0.35 if one_time else 0.80)
    conv_s = None
    if conversion is not None:
        conv_s = max(0.0, min(1.0, float(conversion) if float(conversion) <= 1.5 else 1.0))
    ocf_ni_s = None
    if ocf_to_earn is not None:
        ocf_ni_s = max(0.0, min(1.0, float(ocf_to_earn) if float(ocf_to_earn) <= 1.5 else 1.0))
        if float(ocf_to_earn) < 0:
            ocf_ni_s = 0.15
    # Soften slightly when receivables grow faster than revenue (evidence gap, not a hard flag).
    wc_drag = None
    if ar_vs_rev is not None:
        gap = float(ar_vs_rev)
        if gap > 0:
            wc_drag = max(0.20, 1.0 - min(0.80, gap))
        else:
            wc_drag = 0.85
    value = mean_present(
        [cash_eq, accruals, fcf_support, conv_s, ocf_ni_s, one_time_s, recurring, wc_drag]
    )
    conf = _confidence(
        [
            cash_eq,
            accruals,
            fcf_support,
            conversion,
            ocf_to_earn,
            one_time,
            recurring,
            ar_vs_rev,
        ],
        basis="earnings_quality_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if fcf_support is not None and fcf_support >= 0.7:
        positives.append("Earnings well supported by free cash flow")
    if ocf_to_earn is not None and float(ocf_to_earn) >= 1.0:
        positives.append("Operating cash flow covers net income")
    if one_time:
        negatives.append("One-time items detected — review non-recurring adjustments")
    if accruals is not None and accruals < 0.4:
        negatives.append("Weak accrual quality")
    if ar_vs_rev is not None and float(ar_vs_rev) > 0.10:
        negatives.append("Receivables growing faster than revenue")
    risks = (
        "Forensic accrual models not computed",
        "Authenticated vendor statements may omit AR/Inv/AP → WC gaps unavailable",
    )
    metrics = [
        f"cash_earnings_quality_01={cash_eq}",
        f"accrual_quality_01={accruals}",
        f"free_cash_flow_support_01={fcf_support}",
        f"cash_conversion_fcf_ocf={conversion}",
        f"ocf_to_earnings={ocf_to_earn}",
        f"receivables_vs_revenue_growth={ar_vs_rev}",
        f"one_time_items_detected={one_time}",
        f"recurring_earnings_01={recurring}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="cash_flow / balance_sheet.working_capital + BQ earnings_quality",
            summary="Cash-backed earnings, OCF/NI accruals, WC growth gaps, one-time items",
            reasoning=(
                "High-quality earnings are cash-backed and recurring. We emphasise "
                "OCF/NI, FCF/OCF retention, accrual quality, FCF support, receivables "
                "vs revenue growth evidence, and exceptional items."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["Does not invent forensic accounting adjustments"],
        )
    ]
    return _component(
        EarningsQualityDimension.EARNINGS_QUALITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Earnings quality scored from cash support, accruals, and recurring/"
            "one-time proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_margin_stability(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> EarningsQualityComponentScore:
    margin_stab = _bq_eq(business_quality_analysis, "margin_stability")
    margin_def = _bq_cp(business_quality_analysis, "margin_defensibility")
    gm = safe_getattr(financial_analysis, "income", "margins", "gross_margin")
    om = safe_getattr(financial_analysis, "income", "margins", "operating_margin")
    nm = safe_getattr(financial_analysis, "income", "margins", "net_margin")
    ebitda_m = safe_getattr(financial_analysis, "income", "margins", "ebitda_margin")
    gm_s = _map_ratio(gm, good=0.40, bad=0.10)
    om_s = _map_ratio(om, good=0.18, bad=0.02)
    nm_s = _map_ratio(nm, good=0.10, bad=0.0)
    ebitda_s = _map_ratio(ebitda_m, good=0.22, bad=0.05)
    value = mean_present([margin_stab, margin_def, gm_s, om_s, nm_s, ebitda_s])
    conf = _confidence(
        [margin_stab, margin_def, gm, om, nm, ebitda_m],
        basis="margin_stability_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if margin_def is not None and margin_def >= 0.7:
        positives.append("Defensible margin profile")
    if om is not None and float(om) < 0.05:
        negatives.append("Thin operating margin")
    risks = ("Margin trend depth depends on FA trend history",)
    metrics = [
        f"margin_stability_01={margin_stab}",
        f"margin_defensibility_01={margin_def}",
        f"gross_margin={gm}",
        f"operating_margin={om}",
        f"net_margin={nm}",
        f"ebitda_margin={ebitda_m}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="income.margins / BQ stability",
            summary="Margin levels plus stability/defensibility assessments",
            reasoning=(
                "Stable margins support predictable earnings power. Levels and "
                "BQ stability scores are combined without optimistic stretch."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["EBITDA margin trend not separately modeled beyond level"],
        )
    ]
    return _component(
        EarningsQualityDimension.MARGIN_STABILITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning="Margin stability scored from margin levels and BQ stability proxies.",
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_predictability(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> EarningsQualityComponentScore:
    earn_cons = _bq_eq(business_quality_analysis, "earnings_consistency")
    rev_stab = _bq_cp(business_quality_analysis, "revenue_stability")
    profit_pers = _bq_cp(business_quality_analysis, "profitability_persistence")
    cyclical = _bq_bc(business_quality_analysis, "business_scalability")
    # Invert high operating leverage / cyclical flags when present
    cyclical_flag = False
    flags = safe_getattr(
        business_quality_analysis, "business_characteristics", "quality_flags"
    ) or ()
    for flag in flags:
        name = getattr(flag, "value", str(flag)).lower()
        if "cyclical" in name:
            cyclical_flag = True
            break
    cyclical_s = 0.35 if cyclical_flag else (
        None if cyclical is None else max(0.0, min(1.0, 0.55 + 0.3 * float(cyclical)))
    )
    growth_stab = safe_getattr(
        financial_analysis, "income", "revenue", "growth_stability"
    )
    value = mean_present(
        [earn_cons, rev_stab, profit_pers, cyclical_s, growth_stab]
    )
    conf = _confidence(
        [earn_cons, rev_stab, profit_pers, growth_stab],
        basis="earnings_predictability_proxies",
    )
    # Forecastability without forward models — soft cap
    conf = EarningsQualityConfidence(
        value=min(conf.value, 0.70),
        basis=conf.basis + "_no_forward_model",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if profit_pers is not None and profit_pers >= 0.7:
        positives.append("Persistent profitability supports forecastability")
    if cyclical_flag:
        negatives.append("Cyclical business flag reduces predictability")
    risks = (
        "No analyst-estimate or guidance forecast model in Phase 1",
        "Predictability inferred from historical stability only",
    )
    metrics = [
        f"earnings_consistency_01={earn_cons}",
        f"revenue_stability_01={rev_stab}",
        f"profitability_persistence_01={profit_pers}",
        f"cyclical_flag={cyclical_flag}",
        f"growth_stability={growth_stab}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="consistency / persistence / cyclicality proxies",
            summary="Historical stability and cyclicality as predictability proxies",
            reasoning=(
                "Predictable earnings are easier to value. Without forward estimates, "
                "we use historical consistency, persistence, and cyclical flags, "
                "with confidence capped."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=[
                "Not a statistical forecasting engine",
                "Future AI extension: guidance / estimate providers",
            ],
        )
    ]
    return _component(
        EarningsQualityDimension.EARNINGS_PREDICTABILITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Earnings predictability scored from historical stability and "
            "cyclicality proxies; forward models deferred."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_accounting_quality(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> EarningsQualityComponentScore:
    accruals = _bq_eq(business_quality_analysis, "accrual_quality")
    non_op = _bq_eq(business_quality_analysis, "non_operating_dependence")
    cash_eq = _bq_eq(business_quality_analysis, "cash_earnings_quality")
    one_time = safe_getattr(
        financial_analysis, "income", "consistency", "one_time_items_detected"
    )
    other_dep = safe_getattr(
        financial_analysis, "income", "consistency", "other_income_dependence"
    )
    one_time_s = None if one_time is None else (0.30 if one_time else 0.80)
    other_s = None
    if other_dep is not None:
        other_s = max(0.0, min(1.0, 1.0 - float(other_dep)))
    # Aggressive accounting risk: weak accruals + one-time + high other income
    value = mean_present([accruals, non_op, cash_eq, one_time_s, other_s])
    conf = _confidence(
        [accruals, non_op, cash_eq, one_time, other_dep],
        basis="accounting_quality_proxies",
    )
    conf = EarningsQualityConfidence(
        value=min(conf.value, 0.65),
        basis=conf.basis + "_no_restatement_feed",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if accruals is not None and accruals >= 0.7:
        positives.append("Adequate accrual quality")
    if one_time:
        negatives.append("Exceptional items present")
    if accruals is not None and accruals < 0.35:
        negatives.append("Aggressive-accounting risk indicator (rule-based)")
    risks = (
        "Restatements and enforcement actions not available in Phase 1",
        "Manipulation risk is rule-based heuristic only — not a forensic finding",
    )
    metrics = [
        f"accrual_quality_01={accruals}",
        f"non_operating_dependence_01={non_op}",
        f"cash_earnings_quality_01={cash_eq}",
        f"one_time_items_detected={one_time}",
        f"other_income_dependence={other_dep}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="earnings_quality + income.consistency",
            summary="Accruals, exceptional items, non-operating dependence",
            reasoning=(
                "Conservative accounting is a Buffett hallmark. We score accrual "
                "quality, cash support, and exceptional/non-operating dependence. "
                "Restatement registries are deferred."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=[
                "No restatement registry or auditor opinion feed",
                "Future AI extension: regulatory disclosure providers",
            ],
        )
    ]
    return _component(
        EarningsQualityDimension.ACCOUNTING_QUALITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Accounting quality scored from accrual/cash proxies and exceptional "
            "items; restatement feeds deferred."
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
) -> EarningsQualityComponentScore:
    fcf_support = _bq_eq(business_quality_analysis, "free_cash_flow_support")
    cash_eq = _bq_eq(business_quality_analysis, "cash_earnings_quality")
    profit_pers = _bq_cp(business_quality_analysis, "profitability_persistence")
    reinvest = assessment_score_01(
        safe_getattr(business_quality_analysis, "capital_allocation"),
        "reinvestment_quality",
    )
    roc = _bq_cp(business_quality_analysis, "return_on_capital_strength")
    roic = ratio_value(
        safe_getattr(financial_analysis, "ratios", "profitability"), "roic"
    )
    roic_s = _map_ratio(roic, good=0.15, bad=0.05)
    value = mean_present(
        [fcf_support, cash_eq, profit_pers, reinvest, roc, roic_s]
    )
    conf = _confidence(
        [fcf_support, cash_eq, profit_pers, reinvest, roc, roic],
        basis="long_term_sustainability_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if roic is not None and float(roic) >= 0.12:
        positives.append("Sustainable return-on-capital profile")
    if fcf_support is not None and fcf_support < 0.4:
        negatives.append("Weak cash backing undermines sustainability")
    risks = ("Durability inferred from current proxies; no full-cycle stress model",)
    metrics = [
        f"free_cash_flow_support_01={fcf_support}",
        f"cash_earnings_quality_01={cash_eq}",
        f"profitability_persistence_01={profit_pers}",
        f"reinvestment_quality_01={reinvest}",
        f"return_on_capital_strength_01={roc}",
        f"roic={roic}",
    ]
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="cash support / ROIC / reinvestment",
            summary="Cash-backed earnings, returns, and reinvestment support",
            reasoning=(
                "Long-term earnings durability requires cash-backed profits and "
                "reinvestment that preserves high returns on capital."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["No explicit competitive-moat linkage in this package"],
        )
    ]
    return _component(
        EarningsQualityDimension.LONG_TERM_SUSTAINABILITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Long-term sustainability scored from cash-backed earnings, ROIC, "
            "and reinvestment-quality proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_all_components(
    financial_analysis: Any,
    business_quality_analysis: Any,
    weights: EarningsQualityWeights,
) -> tuple[EarningsQualityComponentScore, ...]:
    return (
        evaluate_consistency(
            financial_analysis,
            business_quality_analysis,
            weight=weights.earnings_consistency,
        ),
        evaluate_quality(
            financial_analysis,
            business_quality_analysis,
            weight=weights.earnings_quality,
        ),
        evaluate_margin_stability(
            financial_analysis,
            business_quality_analysis,
            weight=weights.margin_stability,
        ),
        evaluate_predictability(
            financial_analysis,
            business_quality_analysis,
            weight=weights.earnings_predictability,
        ),
        evaluate_accounting_quality(
            financial_analysis,
            business_quality_analysis,
            weight=weights.accounting_quality,
        ),
        evaluate_sustainability(
            financial_analysis,
            business_quality_analysis,
            weight=weights.long_term_sustainability,
        ),
    )
