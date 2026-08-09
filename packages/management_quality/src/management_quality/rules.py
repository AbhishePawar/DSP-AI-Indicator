"""Rule-based management dimension evaluators (Buffett/Munger-aligned).

Maps public FinancialAnalysis + BusinessQualityAnalysis signals into scored
components with evidence. Governance and some integrity signals are
intentionally confidence-capped when proxy-only.
"""

from __future__ import annotations

from typing import Any

from management_quality.models import (
    ManagementComponentScore,
    ManagementConfidence,
    ManagementEvidence,
    ManagementScore,
)
from management_quality.scoring import ManagementDimension, ManagementWeights, clip_score
from management_quality.signals import assessment_score_01, ratio_value, safe_getattr

__all__ = ["evaluate_all_components", "mean_present"]


def mean_present(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _score_100(value_01: float | None) -> ManagementScore:
    if value_01 is None:
        return ManagementScore(value=None, status="insufficient_data")
    return ManagementScore(value=clip_score(value_01 * 100.0), status="assessed")


def _confidence(values: list[float | None], *, basis: str) -> ManagementConfidence:
    present = sum(1 for v in values if v is not None)
    if present == 0:
        return ManagementConfidence(value=0.0, basis="insufficient_inputs")
    if present >= 3:
        return ManagementConfidence(value=0.85, basis=basis)
    if present == 2:
        return ManagementConfidence(value=0.65, basis=basis)
    return ManagementConfidence(value=0.40, basis=basis)


def _evidence(
    *,
    source: str,
    reference: str,
    summary: str,
    reasoning: str,
    confidence: float,
    metrics: list[str],
    limitations: list[str],
) -> ManagementEvidence:
    return ManagementEvidence(
        source=source,
        reference=reference,
        summary=summary,
        reasoning=reasoning,
        confidence=confidence,
        supporting_metrics=tuple(metrics),
        limitations=tuple(limitations),
    )


def _component(
    dimension: ManagementDimension,
    value_01: float | None,
    *,
    weight: float,
    confidence: ManagementConfidence,
    evidence: list[ManagementEvidence],
    reasoning: str,
    positives: list[str],
    negatives: list[str],
    risks: list[str],
) -> ManagementComponentScore:
    return ManagementComponentScore(
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


def _bq_first(module: object | None, *names: str) -> float | None:
    for name in names:
        value = assessment_score_01(module, name)
        if value is not None:
            return value
    return None


def evaluate_capital_allocation(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> ManagementComponentScore:
    ca = safe_getattr(business_quality_analysis, "capital_allocation")
    discipline = _bq_first(ca, "capital_allocation_discipline")
    reinvest = _bq_first(ca, "reinvestment_quality")
    capex = _bq_first(ca, "capex_discipline")
    buyback = _bq_first(ca, "share_buyback_quality", "buyback_quality")
    # Dilution must never silently alias debt-reduction discipline (CV-001).
    dilution = _bq_first(ca, "dilution_discipline", "share_issuance_discipline")
    acquisition = _bq_first(
        ca, "cash_deployment_quality", "acquisition_quality", "m_and_a_discipline"
    )
    roc = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "return_on_capital_strength",
    )
    roic = ratio_value(
        safe_getattr(financial_analysis, "ratios", "profitability"), "roic"
    )
    roic_score = None if roic is None else max(0.0, min(1.0, roic / 0.20))
    value = mean_present(
        [discipline, reinvest, capex, buyback, dilution, acquisition, roc, roic_score]
    )
    conf = _confidence(
        [discipline, reinvest, capex, buyback, dilution, acquisition, roc, roic],
        basis="capital_allocation_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if discipline is not None and discipline >= 0.7:
        positives.append("Strong capital-allocation discipline signals")
    if reinvest is not None and reinvest < 0.4:
        negatives.append("Weak reinvestment discipline")
    if roic is not None and roic >= 0.15:
        positives.append("High ROIC supports rational capital deployment")
    risks = (
        "Acquisition quality inferred from BQ proxies; deal-level diligence not modeled",
    )
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="capital_allocation.assessments",
            summary="Reuses BQ capital allocation assessments",
            reasoning=(
                "Buffett and Munger emphasize rational capital allocation. "
                "We reuse Business Quality capital-allocation scores rather than "
                "recomputing cash-flow math."
            ),
            confidence=conf.value,
            metrics=[
                f"capital_allocation_discipline_01={discipline}",
                f"reinvestment_quality_01={reinvest}",
                f"capex_discipline_01={capex}",
                f"buyback_quality_01={buyback}",
                f"dilution_discipline_01={dilution}",
                f"acquisition_quality_01={acquisition}",
                f"roic={roic}",
            ],
            limitations=[
                "Does not score individual M&A transactions",
                "Share issuance context (employee plans vs secondary) not distinguished",
            ],
        )
    ]
    return _component(
        ManagementDimension.CAPITAL_ALLOCATION,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Capital allocation scored from BQ discipline/reinvestment/buyback "
            "proxies plus ROIC — prioritizing high returns on capital and "
            "reinvestment rationality."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_shareholder_orientation(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> ManagementComponentScore:
    ca = safe_getattr(business_quality_analysis, "capital_allocation")
    buyback = _bq_first(ca, "share_buyback_quality", "buyback_quality")
    dividend = _bq_first(
        ca,
        "dividend_allocation_quality",
        "dividend_quality",
        "dividend_discipline",
        "payout_discipline",
    )
    shareholder = _bq_first(
        ca,
        "shareholder_capital_stewardship",
        "shareholder_friendliness",
        "owner_orientation",
    )
    cash_gen = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "cash_generation",
    )
    fcf = safe_getattr(
        financial_analysis, "cash_flow", "free_cash_flow", "free_cash_flow"
    )
    fcf_score = None if fcf is None else (0.75 if fcf > 0 else 0.25)
    dividends_paid = safe_getattr(
        financial_analysis, "cash_flow", "financing", "dividends_paid"
    )
    # Presence of sustainable FCF with optional dividends/buybacks
    value = mean_present([buyback, dividend, shareholder, cash_gen, fcf_score])
    conf = _confidence(
        [buyback, dividend, shareholder, cash_gen, fcf],
        basis="shareholder_orientation_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if fcf is not None and fcf > 0:
        positives.append("Positive free cash flow supports owner distributions capacity")
    if buyback is not None and buyback < 0.35:
        negatives.append("Weak buyback-quality proxy")
    risks = (
        "Communication quality and incentive alignment not observable from statements",
        "Dividend policy intent inferred from cash-flow proxies only",
    )
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="capital_allocation / business_characteristics",
            summary="Owner orientation via buyback/dividend/cash generation proxies",
            reasoning=(
                "Shareholder orientation emphasizes long-term owner returns. "
                "Without proxy statements, we use distribution and cash-generation "
                "proxies with explicit communication/incentive limits."
            ),
            confidence=conf.value,
            metrics=[
                f"buyback_quality_01={buyback}",
                f"dividend_quality_01={dividend}",
                f"shareholder_friendliness_01={shareholder}",
                f"cash_generation_01={cash_gen}",
                f"free_cash_flow={fcf}",
                f"dividends_paid={dividends_paid}",
            ],
            limitations=[
                "No MD&A tone, earnings-call, or compensation-plan analysis",
                "Future AI extension: filings / proxy narrative providers",
            ],
        )
    ]
    return _component(
        ManagementDimension.SHAREHOLDER_ORIENTATION,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Shareholder orientation scored from distribution quality and cash "
            "generation proxies emphasizing long-term owner alignment."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_governance(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> ManagementComponentScore:
    """Governance — proxy-only and confidence-capped without board/ownership data."""
    resilience = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "financial_resilience",
    )
    simplicity = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "business_simplicity",
    )
    leverage = safe_getattr(
        financial_analysis, "balance_sheet", "leverage", "debt_to_equity"
    )
    if leverage is None:
        leverage = ratio_value(
            safe_getattr(financial_analysis, "ratios", "leverage"), "debt_to_equity"
        )
    # Conservative leverage as weak governance hygiene proxy
    lev_score = None
    if leverage is not None:
        if leverage <= 0.5:
            lev_score = 0.75
        elif leverage <= 1.0:
            lev_score = 0.55
        elif leverage <= 2.0:
            lev_score = 0.35
        else:
            lev_score = 0.20
    raw = mean_present([resilience, simplicity, lev_score])
    value = None if raw is None else min(raw * 0.8, 0.60)
    conf = _confidence(
        [resilience, simplicity, leverage],
        basis="governance_proxies_limited",
    )
    conf = ManagementConfidence(value=min(conf.value, 0.45), basis=conf.basis)
    risks = (
        "Board independence, promoter ownership, RPT, and auditor quality not available",
        "Score intentionally capped — do not treat as a full governance rating",
    )
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="ratios.leverage / BusinessQuality characteristics",
            summary="Weak governance hygiene proxies only",
            reasoning=(
                "True governance requires board, ownership, and audit evidence. "
                "Absent those inputs, only conservative financial-hygiene proxies "
                "are used and confidence/score are capped."
            ),
            confidence=conf.value,
            metrics=[
                f"financial_resilience_01={resilience}",
                f"business_simplicity_01={simplicity}",
                f"debt_to_equity={leverage}",
            ],
            limitations=[
                "No board roster, independence %, or related-party transaction feed",
                "Future AI extension: corporate governance / filings providers",
            ],
        )
    ]
    _ = business_quality_analysis
    return _component(
        ManagementDimension.GOVERNANCE,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Governance scored conservatively from financial-hygiene proxies; "
            "board/ownership/audit evidence is explicitly out of scope for Phase 1."
        ),
        positives=[],
        negatives=["Governance evidence incomplete without board/ownership data"],
        risks=list(risks),
    )


def evaluate_financial_discipline(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> ManagementComponentScore:
    debt_to_assets = safe_getattr(
        financial_analysis, "balance_sheet", "leverage", "debt_to_assets"
    )
    cash_conv = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "cash_conversion_advantage",
    )
    cash_gen = assessment_score_01(
        safe_getattr(business_quality_analysis, "business_characteristics"),
        "cash_generation",
    )
    wc = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "operational_efficiency",
    )
    interest_burden = safe_getattr(
        financial_analysis, "income", "consistency", "interest_burden"
    )
    debt_score = None
    if debt_to_assets is not None:
        debt_score = max(0.0, min(1.0, 1.0 - float(debt_to_assets)))
    interest_score = None
    if interest_burden is not None:
        interest_score = max(0.0, min(1.0, 1.0 - float(interest_burden)))
    value = mean_present([debt_score, cash_conv, cash_gen, wc, interest_score])
    conf = _confidence(
        [debt_to_assets, cash_conv, cash_gen, wc, interest_burden],
        basis="financial_discipline_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if debt_to_assets is not None and debt_to_assets <= 0.35:
        positives.append("Conservative balance-sheet leverage")
    if debt_to_assets is not None and debt_to_assets > 0.60:
        negatives.append("Elevated leverage weakens financial-discipline claim")
    if cash_gen is not None and cash_gen >= 0.7:
        positives.append("Strong cash generation")
    risks = ("Working-capital cycles may be industry-specific; peers not compared",)
    evidence = [
        _evidence(
            source="FinancialAnalysis",
            reference="balance_sheet.leverage / cash_flow / BQ efficiency",
            summary="Debt conservatism, cash generation, working-capital proxies",
            reasoning=(
                "Buffett prefers managers who finance conservatively and generate "
                "cash. Leverage restraint and cash conversion are primary proxies."
            ),
            confidence=conf.value,
            metrics=[
                f"debt_to_assets={debt_to_assets}",
                f"cash_conversion_advantage_01={cash_conv}",
                f"cash_generation_01={cash_gen}",
                f"operational_efficiency_01={wc}",
                f"interest_burden={interest_burden}",
            ],
            limitations=["No covenant or refinancing-risk model"],
        )
    ]
    return _component(
        ManagementDimension.FINANCIAL_DISCIPLINE,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Financial discipline scored from leverage conservatism and cash/"
            "working-capital efficiency proxies."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_execution_quality(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> ManagementComponentScore:
    rev_stab = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "revenue_stability",
    )
    margin_def = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "margin_defensibility",
    )
    earn_cons = assessment_score_01(
        safe_getattr(business_quality_analysis, "earnings_quality"),
        "earnings_consistency",
    )
    profit_pers = assessment_score_01(
        safe_getattr(business_quality_analysis, "competitive_position"),
        "profitability_persistence",
    )
    # Guidance reliability unsupported without guidance history
    value = mean_present([rev_stab, margin_def, earn_cons, profit_pers])
    conf = _confidence(
        [rev_stab, margin_def, earn_cons, profit_pers],
        basis="execution_quality_proxies",
    )
    positives: list[str] = []
    negatives: list[str] = []
    if rev_stab is not None and rev_stab >= 0.7:
        positives.append("Stable revenue execution")
    if earn_cons is not None and earn_cons < 0.4:
        negatives.append("Inconsistent earnings undermine execution quality")
    risks = (
        "Guidance reliability not scored — no guidance history in Phase 1 inputs",
        "Strategic execution narrative not available from statements alone",
    )
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="competitive_position / earnings_quality",
            summary="Revenue/margin/earnings consistency as execution proxies",
            reasoning=(
                "Execution quality is evidenced by consistent operating results. "
                "Guidance reliability is deferred until a guidance evidence source exists."
            ),
            confidence=conf.value,
            metrics=[
                f"revenue_stability_01={rev_stab}",
                f"margin_defensibility_01={margin_def}",
                f"earnings_consistency_01={earn_cons}",
                f"profitability_persistence_01={profit_pers}",
            ],
            limitations=[
                "No guidance-vs-actual dataset",
                "Future AI extension: guidance / IR transcript providers",
            ],
        )
    ]
    _ = financial_analysis
    return _component(
        ManagementDimension.EXECUTION_QUALITY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Execution quality scored from revenue, margin, and earnings "
            "consistency proxies; guidance reliability explicitly deferred."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_integrity_transparency(
    financial_analysis: Any,
    business_quality_analysis: Any,
    *,
    weight: float,
) -> ManagementComponentScore:
    eq = safe_getattr(business_quality_analysis, "earnings_quality")
    eq_overall = None
    if eq is not None and getattr(eq, "overall_score", None) is not None:
        ov = eq.overall_score.value
        if ov is not None:
            eq_overall = max(0.0, min(1.0, float(ov) / 100.0))
    accruals = _bq_first(eq, "accrual_quality", "accruals_quality")
    fcf_support = _bq_first(eq, "free_cash_flow_support")
    recurring = _bq_first(eq, "recurring_earnings", "recurring_vs_non_recurring")
    one_time = safe_getattr(
        financial_analysis, "income", "consistency", "one_time_items_detected"
    )
    one_time_score = None if one_time is None else (0.35 if one_time else 0.75)
    value = mean_present([eq_overall, accruals, fcf_support, recurring, one_time_score])
    conf = _confidence(
        [eq_overall, accruals, fcf_support, recurring, one_time],
        basis="integrity_transparency_proxies",
    )
    # Restatements / regulatory actions not available — soft cap
    conf = ManagementConfidence(value=min(conf.value, 0.70), basis=conf.basis)
    positives: list[str] = []
    negatives: list[str] = []
    if eq_overall is not None and eq_overall >= 0.7:
        positives.append("Strong earnings-quality / accounting-quality proxies")
    if one_time:
        negatives.append("One-time items detected — review exceptional items carefully")
    risks = (
        "Restatements and regulatory actions not in Phase 1 evidence set",
        "Disclosure quality beyond statement completeness not assessed",
    )
    evidence = [
        _evidence(
            source="BusinessQualityAnalysis",
            reference="earnings_quality",
            summary="Accounting quality via earnings-quality and exceptional-item proxies",
            reasoning=(
                "Honest reporting is central to Buffett/Munger management assessment. "
                "Earnings quality, accrual/FCF support, and exceptional items are "
                "used; restatement/regulatory feeds are future extensions."
            ),
            confidence=conf.value,
            metrics=[
                f"earnings_quality_overall_01={eq_overall}",
                f"accrual_quality_01={accruals}",
                f"free_cash_flow_support_01={fcf_support}",
                f"recurring_earnings_01={recurring}",
                f"one_time_items_detected={one_time}",
            ],
            limitations=[
                "No restatement registry or enforcement-action feed",
                "Future AI extension: regulatory / disclosure providers",
            ],
        )
    ]
    return _component(
        ManagementDimension.INTEGRITY_TRANSPARENCY,
        value,
        weight=weight,
        confidence=conf,
        evidence=evidence,
        reasoning=(
            "Integrity & transparency scored from earnings-quality and "
            "exceptional-item proxies with explicit restatement/regulatory limits."
        ),
        positives=positives,
        negatives=negatives,
        risks=list(risks),
    )


def evaluate_all_components(
    financial_analysis: Any,
    business_quality_analysis: Any,
    weights: ManagementWeights,
) -> tuple[ManagementComponentScore, ...]:
    return (
        evaluate_capital_allocation(
            financial_analysis,
            business_quality_analysis,
            weight=weights.capital_allocation,
        ),
        evaluate_shareholder_orientation(
            financial_analysis,
            business_quality_analysis,
            weight=weights.shareholder_orientation,
        ),
        evaluate_governance(
            financial_analysis,
            business_quality_analysis,
            weight=weights.governance,
        ),
        evaluate_financial_discipline(
            financial_analysis,
            business_quality_analysis,
            weight=weights.financial_discipline,
        ),
        evaluate_execution_quality(
            financial_analysis,
            business_quality_analysis,
            weight=weights.execution_quality,
        ),
        evaluate_integrity_transparency(
            financial_analysis,
            business_quality_analysis,
            weight=weights.integrity_transparency,
        ),
    )
