"""Rule-based financial strength dimension evaluators (Buffett-aligned).

Reads public FinancialAnalysis (+ BQ supplements) only. Debt maturity profiles
and multi-year stress series are limited when upstream data is absent.
"""

from __future__ import annotations

from typing import Any

from financial_strength.models import (
    FinancialStrengthComponentScore,
    FinancialStrengthConfidence,
    FinancialStrengthEvidence,
    FinancialStrengthScore,
)
from financial_strength.scoring import (
    FinancialStrengthDimension,
    FinancialStrengthWeights,
    clip_score,
)
from financial_strength.signals import assessment_score_01, ratio_value, safe_getattr

__all__ = ["evaluate_all_components", "mean_present"]


def mean_present(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _score_100(value_01: float | None) -> FinancialStrengthScore:
    if value_01 is None:
        return FinancialStrengthScore(value=None, status="insufficient_data")
    return FinancialStrengthScore(
        value=clip_score(value_01 * 100.0), status="assessed"
    )


def _confidence(
    values: list[float | None], *, basis: str
) -> FinancialStrengthConfidence:
    present = sum(1 for v in values if v is not None)
    if present == 0:
        return FinancialStrengthConfidence(value=0.0, basis="insufficient_inputs")
    if present >= 3:
        return FinancialStrengthConfidence(value=0.85, basis=basis)
    if present == 2:
        return FinancialStrengthConfidence(value=0.65, basis=basis)
    return FinancialStrengthConfidence(value=0.40, basis=basis)


def _evidence(
    *,
    source: str,
    reference: str,
    summary: str,
    reasoning: str,
    confidence: float,
    metrics: list[str],
    limitations: list[str],
) -> FinancialStrengthEvidence:
    return FinancialStrengthEvidence(
        source=source,
        reference=reference,
        summary=summary,
        reasoning=reasoning,
        confidence=confidence,
        supporting_metrics=tuple(metrics),
        limitations=tuple(limitations),
    )


def _component(
    dimension: FinancialStrengthDimension,
    value_01: float | None,
    *,
    weight: float,
    confidence: FinancialStrengthConfidence,
    evidence: list[FinancialStrengthEvidence],
    reasoning: str,
    positives: list[str],
    negatives: list[str],
    risks: list[str],
    key_metrics: list[str],
) -> FinancialStrengthComponentScore:
    return FinancialStrengthComponentScore(
        dimension=dimension,
        score=_score_100(value_01),
        confidence=confidence,
        evidence=tuple(evidence),
        reasoning=reasoning,
        positive_factors=tuple(positives),
        negative_factors=tuple(negatives),
        risks=tuple(risks),
        key_metrics=tuple(key_metrics),
        weight=weight,
    )


def _map_ratio(value: float | None, *, good: float, bad: float, invert: bool = False) -> float | None:
    """Map a ratio into 0–1 between bad and good endpoints."""
    if value is None:
        return None
    v = float(value)
    if invert:
        # higher is worse (e.g. debt ratios)
        if v <= good:
            return 1.0
        if v >= bad:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (v - good) / (bad - good)))
    # higher is better
    if v >= good:
        return 1.0
    if v <= bad:
        return 0.0
    return max(0.0, min(1.0, (v - bad) / (good - bad)))


def evaluate_balance_sheet(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> FinancialStrengthComponentScore:
    dte = safe_getattr(
        financial_analysis, "balance_sheet", "leverage", "debt_to_equity"
    )
    dta = safe_getattr(
        financial_analysis, "balance_sheet", "leverage", "debt_to_assets"
    )
    net_debt = safe_getattr(
        financial_analysis, "balance_sheet", "leverage", "net_debt"
    )
    equity_ratio = safe_getattr(
        financial_analysis, "balance_sheet", "leverage", "equity_ratio"
    )
    goodwill_pct = safe_getattr(
        financial_analysis, "balance_sheet", "assets", "goodwill_pct"
    )
    intangible_pct = safe_getattr(
        financial_analysis, "balance_sheet", "assets", "intangible_asset_pct"
    )
    # Tangible equity proxy: equity share reduced by intangibles/goodwill intensity
    tangible_proxy = None
    if equity_ratio is not None:
        soft = 0.0
        if goodwill_pct is not None:
            soft += float(goodwill_pct)
        if intangible_pct is not None:
            soft += float(intangible_pct)
        tangible_proxy = max(0.0, min(1.0, float(equity_ratio) * (1.0 - min(0.5, soft))))

    dte_score = _map_ratio(dte, good=0.3, bad=2.0, invert=True)
    dta_score = _map_ratio(dta, good=0.2, bad=0.7, invert=True)
    equity_score = _map_ratio(equity_ratio, good=0.55, bad=0.20)
    net_debt_score = None
    if net_debt is not None:
        # Prefer ratio-linked signal; net cash is a positive fortress signal
        if float(net_debt) <= 0:
            net_debt_score = 0.90
        elif dta_score is not None:
            net_debt_score = dta_score
        else:
            net_debt_score = 0.40

    value = mean_present([dte_score, dta_score, equity_score, tangible_proxy, net_debt_score])
    conf = _confidence(
        [dte, dta, equity_ratio, goodwill_pct, intangible_pct, net_debt],
        basis="balance_sheet_strength_proxies",
    )
    # Debt maturity profile unavailable — soft confidence cap note
    if conf.value > 0.75:
        conf = FinancialStrengthConfidence(value=0.75, basis=conf.basis + "_no_maturity")

    positives: list[str] = []
    negatives: list[str] = []
    if dte is not None and float(dte) <= 0.5:
        positives.append("Conservative debt-to-equity")
    if dte is not None and float(dte) > 1.5:
        negatives.append("Elevated debt-to-equity")
    if equity_ratio is not None and float(equity_ratio) >= 0.5:
        positives.append("Solid equity buffer")
    risks = (
        "Debt maturity profile not available in Phase 1 inputs",
        "Equity growth trend limited without multi-period series",
    )
    metrics = [
        f"debt_to_equity={dte}",
        f"debt_to_assets={dta}",
        f"net_debt={net_debt}",
        f"equity_ratio={equity_ratio}",
        f"goodwill_pct={goodwill_pct}",
        f"intangible_asset_pct={intangible_pct}",
        f"tangible_net_worth_proxy={tangible_proxy}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="balance_sheet.leverage / assets",
            summary="Leverage, equity buffer, tangible net-worth proxies",
            reasoning=(
                "Buffett prefers fortress balance sheets: low leverage and real "
                "equity. We score D/E, debt-to-assets, equity ratio, and a "
                "tangible-equity proxy after soft assets."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=[
                "No debt maturity schedule / refinancing calendar",
                "Absolute net-debt levels are scale-sensitive; prefer ratios",
            ],
        )
    ]
    _ = business_quality_analysis
    return _component(
        FinancialStrengthDimension.BALANCE_SHEET_STRENGTH,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Balance-sheet strength scored from conservative leverage and "
            "tangible equity proxies; maturity profile deferred."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
        key_metrics=metrics,
    )


def evaluate_liquidity(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> FinancialStrengthComponentScore:
    liq = safe_getattr(financial_analysis, "balance_sheet", "liquidity")
    current = safe_getattr(liq, "current_ratio")
    quick = safe_getattr(liq, "quick_ratio")
    cash_ratio = safe_getattr(liq, "cash_ratio")
    wc = safe_getattr(liq, "working_capital")
    nwc = safe_getattr(liq, "net_working_capital")
    cash = None
    # operating cash buffer proxy from OCF / current liabilities if available
    ocf = safe_getattr(
        financial_analysis, "cash_flow", "operating", "operating_cash_flow"
    )
    current_liab = None  # not always exposed; use cash_ratio/current as primary

    current_s = _map_ratio(current, good=2.0, bad=0.8)
    quick_s = _map_ratio(quick, good=1.2, bad=0.5)
    cash_s = _map_ratio(cash_ratio, good=0.5, bad=0.05)
    wc_s = None
    if wc is not None:
        wc_s = 0.8 if float(wc) > 0 else 0.25
    elif nwc is not None:
        wc_s = 0.8 if float(nwc) > 0 else 0.25
    ocf_buffer = None
    if ocf is not None:
        ocf_buffer = 0.75 if float(ocf) > 0 else 0.30

    value = mean_present([current_s, quick_s, cash_s, wc_s, ocf_buffer])
    conf = _confidence(
        [current, quick, cash_ratio, wc, nwc, ocf],
        basis="liquidity_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if current is not None and float(current) >= 1.5:
        positives.append("Healthy current ratio")
    if current is not None and float(current) < 1.0:
        negatives.append("Current ratio below 1.0")
    if cash_ratio is not None and float(cash_ratio) >= 0.3:
        positives.append("Meaningful cash ratio buffer")
    risks = ("Seasonal working-capital needs not peer-adjusted",)
    metrics = [
        f"current_ratio={current}",
        f"quick_ratio={quick}",
        f"cash_ratio={cash_ratio}",
        f"working_capital={wc}",
        f"net_working_capital={nwc}",
        f"operating_cash_flow={ocf}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="balance_sheet.liquidity / cash_flow.operating",
            summary="Current/quick/cash ratios and working-capital buffers",
            reasoning=(
                "Liquidity is a first line of financial strength. Conservative "
                "managers keep ample near-term coverage without relying on "
                "optimistic refinancing."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["No undrawn revolver / committed facility data"],
        )
    ]
    _ = business_quality_analysis
    _ = cash
    _ = current_liab
    return _component(
        FinancialStrengthDimension.LIQUIDITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning="Liquidity scored from classic coverage ratios and WC/OCF buffers.",
        positives=positives,
        negatives=negatives,
        risks=list(risks),
        key_metrics=metrics,
    )


def evaluate_cash_flow(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> FinancialStrengthComponentScore:
    ocf = safe_getattr(
        financial_analysis, "cash_flow", "operating", "operating_cash_flow"
    )
    conversion = safe_getattr(
        financial_analysis, "cash_flow", "operating", "cash_conversion"
    )
    fcf = safe_getattr(
        financial_analysis, "cash_flow", "free_cash_flow", "free_cash_flow"
    )
    fcf_stab = safe_getattr(
        financial_analysis, "cash_flow", "free_cash_flow", "fcf_stability"
    )
    cash_quality = assessment_score_01(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "cash_earnings_quality",
    )
    fcf_support = assessment_score_01(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "free_cash_flow_support",
    )
    revenue = safe_getattr(financial_analysis, "income", "margins")
    # FCF margin needs revenue - try ratio
    fcf_margin = ratio_value(
        safe_getattr(financial_analysis, "ratios", "cash_flow"), "fcf_margin"
    )
    if fcf_margin is None and fcf is not None:
        # leave None rather than invent revenue
        pass

    ocf_s = 0.8 if ocf is not None and float(ocf) > 0 else (0.25 if ocf is not None else None)
    fcf_s = 0.8 if fcf is not None and float(fcf) > 0 else (0.25 if fcf is not None else None)
    conv_s = None if conversion is None else max(0.0, min(1.0, float(conversion) if float(conversion) <= 1.5 else 1.0))
    fcf_m_s = _map_ratio(fcf_margin, good=0.12, bad=0.0)
    value = mean_present(
        [ocf_s, fcf_s, conv_s, fcf_stab, cash_quality, fcf_support, fcf_m_s]
    )
    conf = _confidence(
        [ocf, fcf, conversion, fcf_stab, cash_quality, fcf_support, fcf_margin],
        basis="cash_flow_quality_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if fcf is not None and float(fcf) > 0:
        positives.append("Positive free cash flow")
    if conversion is not None and float(conversion) >= 0.9:
        positives.append("Strong cash conversion of earnings")
    if fcf is not None and float(fcf) < 0:
        negatives.append("Negative free cash flow")
    risks = ("Multi-year cash-flow consistency depends on upstream history depth",)
    metrics = [
        f"operating_cash_flow={ocf}",
        f"free_cash_flow={fcf}",
        f"cash_conversion={conversion}",
        f"fcf_stability={fcf_stab}",
        f"fcf_margin={fcf_margin}",
        f"cash_earnings_quality_01={cash_quality}",
        f"free_cash_flow_support_01={fcf_support}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="cash_flow / BusinessQuality earnings_quality",
            summary="OCF, FCF, conversion, and earnings-cash support",
            reasoning=(
                "High-quality cash generation is central to financial strength. "
                "We emphasise positive OCF/FCF, conversion vs earnings, and BQ "
                "cash-support assessments."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["CFO vs NI accrual bridge not recomputed line-by-line"],
        )
    ]
    _ = revenue
    return _component(
        FinancialStrengthDimension.CASH_FLOW_QUALITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Cash-flow quality scored from OCF/FCF, conversion, stability, and "
            "earnings-cash support proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
        key_metrics=metrics,
    )


def evaluate_solvency(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> FinancialStrengthComponentScore:
    interest_cov = ratio_value(
        safe_getattr(financial_analysis, "ratios", "coverage"), "interest_coverage"
    )
    if interest_cov is None:
        interest_cov = ratio_value(
            safe_getattr(financial_analysis, "ratios", "leverage"), "interest_coverage"
        )
    debt_ebitda = ratio_value(
        safe_getattr(financial_analysis, "ratios", "leverage"), "debt_to_ebitda"
    )
    if debt_ebitda is None:
        debt_ebitda = ratio_value(
            safe_getattr(financial_analysis, "ratios", "coverage"), "debt_to_ebitda"
        )
    flex = assessment_score_01(
        safe_getattr(business_quality_analysis, "capital_allocation"),
        "financial_flexibility",
    )
    debt_red = assessment_score_01(
        safe_getattr(business_quality_analysis, "capital_allocation"),
        "debt_reduction_discipline",
    )
    interest_burden = safe_getattr(
        financial_analysis, "income", "consistency", "interest_burden"
    )
    cov_s = _map_ratio(interest_cov, good=8.0, bad=1.5)
    de_s = _map_ratio(debt_ebitda, good=1.0, bad=4.5, invert=True)
    burden_s = None
    if interest_burden is not None:
        burden_s = max(0.0, min(1.0, 1.0 - float(interest_burden)))
    value = mean_present([cov_s, de_s, flex, debt_red, burden_s])
    conf = _confidence(
        [interest_cov, debt_ebitda, flex, debt_red, interest_burden],
        basis="solvency_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if interest_cov is not None and float(interest_cov) >= 5.0:
        positives.append("Comfortable interest coverage")
    if debt_ebitda is not None and float(debt_ebitda) > 3.5:
        negatives.append("Elevated debt/EBITDA")
    risks = ("Debt service capacity approximated; no full amortization schedule",)
    metrics = [
        f"interest_coverage={interest_cov}",
        f"debt_to_ebitda={debt_ebitda}",
        f"financial_flexibility_01={flex}",
        f"debt_reduction_discipline_01={debt_red}",
        f"interest_burden={interest_burden}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="ratios coverage/leverage / BQ capital_allocation",
            summary="Interest coverage, leverage multiples, financial flexibility",
            reasoning=(
                "Solvency asks whether the firm can service obligations from "
                "operations. Coverage and debt/EBITDA are primary; BQ flexibility "
                "supplements when present."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["Debt/EBITDA unavailable for some statement sets"],
        )
    ]
    return _component(
        FinancialStrengthDimension.SOLVENCY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning="Solvency scored from coverage, leverage multiples, and flexibility proxies.",
        positives=positives,
        negatives=negatives,
        risks=list(risks),
        key_metrics=metrics,
    )


def evaluate_profitability_stability(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> FinancialStrengthComponentScore:
    gm = safe_getattr(financial_analysis, "income", "margins", "gross_margin")
    om = safe_getattr(financial_analysis, "income", "margins", "operating_margin")
    nm = safe_getattr(financial_analysis, "income", "margins", "net_margin")
    roe = ratio_value(
        safe_getattr(financial_analysis, "ratios", "profitability"), "roe"
    )
    roic = ratio_value(
        safe_getattr(financial_analysis, "ratios", "profitability"), "roic"
    )
    margin_stab = assessment_score_01(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "margin_stability",
    )
    earn_cons = assessment_score_01(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "earnings_consistency",
    )
    margin_def = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "margin_defensibility",
    )
    profit_pers = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "profitability_persistence",
    )
    # Level quality + stability proxies
    gm_s = _map_ratio(gm, good=0.45, bad=0.15)
    om_s = _map_ratio(om, good=0.20, bad=0.03)
    nm_s = _map_ratio(nm, good=0.12, bad=0.01)
    roe_s = _map_ratio(roe, good=0.18, bad=0.05)
    roic_s = _map_ratio(roic, good=0.15, bad=0.05)
    value = mean_present(
        [gm_s, om_s, nm_s, roe_s, roic_s, margin_stab, earn_cons, margin_def, profit_pers]
    )
    conf = _confidence(
        [gm, om, nm, roe, roic, margin_stab, earn_cons, margin_def, profit_pers],
        basis="profitability_stability_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if roic is not None and float(roic) >= 0.12:
        positives.append("Attractive ROIC level")
    if om is not None and float(om) < 0.05:
        negatives.append("Thin operating margin")
    risks = (
        "True multi-year stability depends on trend history depth in FinancialAnalysis",
    )
    metrics = [
        f"gross_margin={gm}",
        f"operating_margin={om}",
        f"net_margin={nm}",
        f"roe={roe}",
        f"roic={roic}",
        f"margin_stability_01={margin_stab}",
        f"earnings_consistency_01={earn_cons}",
        f"margin_defensibility_01={margin_def}",
        f"profitability_persistence_01={profit_pers}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="income.margins / ratios.profitability / BQ stability",
            summary="Margin and return levels plus stability assessments",
            reasoning=(
                "Sustainable returns matter more than one-year spikes. We combine "
                "margin/ROIC levels with BQ stability and persistence scores."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=["ROE can be distorted by leverage; ROIC preferred when present"],
        )
    ]
    return _component(
        FinancialStrengthDimension.PROFITABILITY_STABILITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Profitability stability scored from margin/return levels and "
            "consistency/defensibility proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
        key_metrics=metrics,
    )


def evaluate_resilience(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> FinancialStrengthComponentScore:
    cash_ratio = safe_getattr(
        financial_analysis, "balance_sheet", "liquidity", "cash_ratio"
    )
    dte = safe_getattr(
        financial_analysis, "balance_sheet", "leverage", "debt_to_equity"
    )
    resilience = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "financial_resilience",
    )
    cash_gen = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "cash_generation",
    )
    health = safe_getattr(
        financial_analysis, "overall_summary", "health_label"
    )
    health_s = None
    if isinstance(health, str):
        mapping = {
            "excellent_financial_health": 0.95,
            "healthy_financial_position": 0.80,
            "needs_attention": 0.45,
            "liquidity_concern": 0.25,
            "leverage_concern": 0.30,
            "cash_flow_concern": 0.30,
        }
        # overall_summary.health_label may be simpler strings
        health_s = mapping.get(health.lower(), None)
        if health_s is None:
            if "healthy" in health.lower() or "excellent" in health.lower():
                health_s = 0.8
            elif "attention" in health.lower() or "concern" in health.lower():
                health_s = 0.35
            else:
                health_s = 0.55

    cash_s = _map_ratio(cash_ratio, good=0.4, bad=0.05)
    lev_s = _map_ratio(dte, good=0.4, bad=2.0, invert=True)
    value = mean_present([cash_s, lev_s, resilience, cash_gen, health_s])
    conf = _confidence(
        [cash_ratio, dte, resilience, cash_gen, health],
        basis="financial_resilience_proxies",
    )
    # Historical stress indicators limited
    conf = FinancialStrengthConfidence(
        value=min(conf.value, 0.70),
        basis=conf.basis + "_limited_stress_history",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if resilience is not None and resilience >= 0.7:
        positives.append("Strong financial-resilience assessment")
    if dte is not None and float(dte) > 1.5:
        negatives.append("Leverage reduces downturn resilience")
    risks = (
        "Downturn / stress-test history limited without multi-cycle series",
    )
    metrics = [
        f"cash_ratio={cash_ratio}",
        f"debt_to_equity={dte}",
        f"financial_resilience_01={resilience}",
        f"cash_generation_01={cash_gen}",
        f"health_label={health}",
    ]
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="liquidity / leverage / BQ business_characteristics",
            summary="Cash reserves, conservative leverage, resilience flags",
            reasoning=(
                "Financial resilience is the ability to endure stress without "
                "forced financing. Cash buffers, low leverage, and BQ resilience "
                "flags are primary Phase 1 proxies."
            ),
            confidence=conf.value,
            metrics=metrics,
            limitations=[
                "No formal stress-test or recession backtest in Phase 1",
                "Future extension: multi-period drawdown providers",
            ],
        )
    ]
    return _component(
        FinancialStrengthDimension.FINANCIAL_RESILIENCE,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Resilience scored from cash reserves, leverage conservatism, and "
            "BQ resilience/cash-generation proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
        key_metrics=metrics,
    )


def evaluate_all_components(
    financial_analysis: Any,
    business_quality_analysis: Any,
    weights: FinancialStrengthWeights,
) -> tuple[FinancialStrengthComponentScore, ...]:
    return (
        evaluate_balance_sheet(
            financial_analysis,
            business_quality_analysis,
            weight=weights.balance_sheet_strength,
        ),
        evaluate_liquidity(
            financial_analysis,
            business_quality_analysis,
            weight=weights.liquidity,
        ),
        evaluate_cash_flow(
            financial_analysis,
            business_quality_analysis,
            weight=weights.cash_flow_quality,
        ),
        evaluate_solvency(
            financial_analysis,
            business_quality_analysis,
            weight=weights.solvency,
        ),
        evaluate_profitability_stability(
            financial_analysis,
            business_quality_analysis,
            weight=weights.profitability_stability,
        ),
        evaluate_resilience(
            financial_analysis,
            business_quality_analysis,
            weight=weights.financial_resilience,
        ),
    )
