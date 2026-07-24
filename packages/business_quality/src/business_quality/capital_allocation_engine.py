"""Capital Allocation Intelligence engine (F3.3).

Composes assessments from FinancialAnalysis cash-flow / ratio / trend
outputs only — no duplicated financial calculations.
"""

from __future__ import annotations

from typing import Any

from business_quality.capital_allocation_explainability import (
    CAPITAL_ALLOCATION_DISCLAIMER,
    ca_explanation,
)
from business_quality.capital_allocation_models import (
    CapitalAllocationAnalysis,
    CapitalAllocationFlag,
)
from business_quality.capital_allocation_validation import (
    validate_capital_allocation_input,
)
from business_quality.earnings_quality_engine import (
    _aggregate_confidence,
    _confidence_from_present,
    _rating_from_01,
    _risk_from_01,
    _score_01,
)
from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import FRAMEWORK_VERSION, BusinessQualityMetadata
from business_quality.scoring import (
    Assessment,
    Confidence,
    EvidenceLevel,
    Rating,
    weighted_mean,
)

__all__ = ["CapitalAllocationEngine", "CAPITAL_ALLOCATION_VERSION"]

CAPITAL_ALLOCATION_VERSION = "0.3.0-capital-allocation"


class CapitalAllocationEngine:
    """Evaluate capital allocation quality from FinancialAnalysis."""

    def analyze(self, financial_analysis: Any) -> CapitalAllocationAnalysis:
        validation = validate_capital_allocation_input(financial_analysis)
        fa = financial_analysis
        cash = fa.cash_flow
        ratios = fa.ratios
        trends = getattr(fa, "trends", None)
        summary = fa.overall_summary

        explanations: list[BusinessQualityExplainability] = []
        assessments: list[Assessment] = []
        evidence: list[str] = []

        cap = ratios.capital_allocation
        assessments.append(
            self._assess(
                "capital_allocation_discipline",
                "Capital Allocation Discipline",
                cap.capital_allocation_score
                if cap.capital_allocation_score is not None
                else cash.financing.capital_allocation_quality,
                "FinancialAnalysis.ratios.capital_allocation",
                "Reuses capital_allocation_score / financing quality.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "reinvestment_quality",
                "Reinvestment Quality",
                cash.investing.investment_discipline
                if cash.investing.investment_discipline is not None
                else cash.quality.investment_discipline,
                "FinancialAnalysis.cash_flow.investing",
                "Reuses investment_discipline from cash-flow intelligence.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "capex_discipline",
                "Capital Expenditure Discipline",
                cap.capex_discipline
                if cap.capex_discipline is not None
                else _capex_from_intensity(cash.investing.capex_intensity),
                "FinancialAnalysis.ratios.capital_allocation.capex_discipline",
                "Reuses capex_discipline / investing intensity proxy.",
                explanations,
                evidence,
                extra_evidence=f"capex_intensity={cash.investing.capex_intensity}",
            )
        )
        assessments.append(
            self._assess(
                "dividend_allocation_quality",
                "Dividend Allocation Quality",
                cap.dividend_sustainability
                if cap.dividend_sustainability is not None
                else cash.quality.dividend_sustainability,
                "FinancialAnalysis.ratios.capital_allocation",
                "Reuses dividend sustainability fields.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "share_buyback_quality",
                "Share Buyback Quality",
                cap.buyback_sustainability
                if cap.buyback_sustainability is not None
                else cash.quality.buyback_sustainability,
                "FinancialAnalysis.ratios.capital_allocation",
                "Reuses buyback sustainability fields.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "debt_reduction_discipline",
                "Debt Reduction Discipline",
                cap.debt_reduction_quality
                if cap.debt_reduction_quality is not None
                else cash.quality.debt_sustainability,
                "FinancialAnalysis.ratios.capital_allocation",
                "Reuses debt reduction / debt sustainability fields.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "cash_deployment_quality",
                "Cash Deployment Quality",
                cash.quality.cash_sustainability
                if cash.quality.cash_sustainability is not None
                else cash.financing.capital_allocation_quality,
                "FinancialAnalysis.cash_flow.quality",
                "Reuses cash sustainability / financing allocation quality.",
                explanations,
                evidence,
                extra_evidence=f"fcf={cash.free_cash_flow.free_cash_flow}",
            )
        )
        flex = _flexibility(
            cash.financing.financing_dependence,
            cash.quality.cash_sustainability,
        )
        assessments.append(
            self._assess(
                "financial_flexibility",
                "Financial Flexibility",
                flex,
                "FinancialAnalysis.cash_flow.financing",
                "Inverts financing_dependence and blends cash sustainability.",
                explanations,
                evidence,
                extra_evidence=(
                    f"financing_dependence={cash.financing.financing_dependence}"
                ),
            )
        )
        assessments.append(
            self._consistency(trends, cap.capital_allocation_score, explanations, evidence)
        )
        assessments.append(
            self._stewardship(cash, cap, explanations, evidence)
        )

        scored = [
            (a.score.value / 100.0, 1.0)
            for a in assessments
            if a.score is not None and a.score.value is not None
        ]
        overall_01 = weighted_mean(scored)
        overall_score = _score_01(overall_01)
        overall_rating = _rating_from_01(overall_01)
        confidence = _aggregate_confidence([a.confidence for a in assessments])
        flags = self._flags(assessments, cash, ratios, trends, overall_01)

        # Surface financial summary snippets as evidence only
        if getattr(summary, "health_label", None):
            evidence.append(f"financial_summary.health_label={summary.health_label}")
        for s in getattr(summary, "strengths", ())[:2]:
            evidence.append(f"financial_summary.strength={s}")

        meta = getattr(fa, "metadata", None)
        metadata = BusinessQualityMetadata(
            engine_version=CAPITAL_ALLOCATION_VERSION,
            framework_version=FRAMEWORK_VERSION,
            company=str(getattr(meta, "company", "") or ""),
            ticker=str(getattr(meta, "ticker", "") or ""),
            modules_composed=(
                "capital_allocation_intelligence",
                "financial_analysis",
            ),
        )
        explanations.append(
            ca_explanation(
                title="Overall Capital Allocation",
                description="Composite of capital-allocation dimension assessments.",
                evidence=tuple(evidence[:12]),
                reasoning=(
                    f"Overall rating={overall_rating.value}; "
                    f"score={None if overall_01 is None else round(overall_01, 4)}."
                ),
                confidence=confidence,
                limitations=(
                    "Equal-weight mean of available dimensions; not a valuation "
                    "of management skill."
                ),
                references=(
                    "FinancialAnalysis.cash_flow",
                    "FinancialAnalysis.ratios.capital_allocation",
                    "FinancialAnalysis.trends",
                    "FinancialAnalysis.overall_summary",
                ),
            )
        )
        return CapitalAllocationAnalysis(
            metadata=metadata,
            validation=validation,
            assessments=tuple(assessments),
            overall_score=overall_score,
            overall_rating=overall_rating,
            confidence=confidence,
            quality_flags=flags,
            evidence=tuple(dict.fromkeys(evidence)),
            explainability=tuple(explanations),
            research_disclaimer=CAPITAL_ALLOCATION_DISCLAIMER,
        )

    def _assess(
        self,
        name: str,
        title: str,
        value: float | None,
        reference: str,
        reasoning: str,
        out: list,
        evidence: list[str],
        *,
        extra_evidence: str | None = None,
    ) -> Assessment:
        evidence.append(f"{name}={value}")
        if extra_evidence:
            evidence.append(extra_evidence)
        conf = _confidence_from_present(value)
        out.append(
            ca_explanation(
                title=title,
                description=f"Assessment of {title.lower()}.",
                evidence=(f"{name}={value}",)
                + ((extra_evidence,) if extra_evidence else ()),
                reasoning=reasoning,
                confidence=conf,
                limitations="Does not recalculate statement ratios or cash flows.",
                references=(reference,),
            )
        )
        return Assessment(
            name=name,
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=(
                EvidenceLevel.STRONG
                if conf is Confidence.HIGH
                else EvidenceLevel.ADEQUATE
                if conf is Confidence.MEDIUM
                else EvidenceLevel.LIMITED
                if conf is Confidence.LOW
                else EvidenceLevel.NONE
            ),
            risk_level=_risk_from_01(value, invert=True),
        )

    def _consistency(
        self, trends, score: float | None, out: list, evidence: list[str]
    ) -> Assessment:
        value = score
        trend_cls = None
        if trends is not None:
            alloc = next(
                (
                    t
                    for t in trends.ratio_trends
                    if t.name == "capital_allocation_score"
                ),
                None,
            )
            if alloc is not None:
                trend_cls = alloc.classification
                if alloc.consistency is not None:
                    value = alloc.consistency
                evidence.append(f"trend.capital_allocation_score={alloc.classification}")
        conf = _confidence_from_present(value, 1.0 if trend_cls is not None else None)
        out.append(
            ca_explanation(
                title="Capital Allocation Consistency",
                description="Consistency of capital allocation over reporting periods.",
                evidence=(
                    f"score={score}",
                    f"trend_class={trend_cls}",
                ),
                reasoning="Uses ratio capital_allocation_score and/or trend consistency.",
                confidence=conf,
                limitations="Single-period histories omit trend consistency.",
                references=(
                    "FinancialAnalysis.trends.ratio_trends",
                    "FinancialAnalysis.ratios.capital_allocation",
                ),
            )
        )
        return Assessment(
            name="capital_allocation_consistency",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE
            if trend_cls is not None
            else EvidenceLevel.LIMITED,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _stewardship(self, cash, cap, out: list, evidence: list[str]) -> Assessment:
        parts = [
            p
            for p in (
                cap.dividend_sustainability,
                cap.buyback_sustainability,
                cash.financing.capital_allocation_quality,
            )
            if p is not None
        ]
        value = sum(parts) / len(parts) if parts else None
        flag_vals = {getattr(f, "value", str(f)) for f in cash.quality_flags}
        if "shareholder_friendly" in flag_vals and value is None:
            value = 0.75
        evidence.append(f"shareholder_stewardship={value}")
        conf = _confidence_from_present(*parts) if parts else _confidence_from_present(value)
        out.append(
            ca_explanation(
                title="Shareholder Capital Stewardship",
                description="Dividend/buyback sustainability and shareholder-friendly signals.",
                evidence=tuple(f"{p}" for p in parts) or (f"value={value}",),
                reasoning="Mean of dividend/buyback sustainability and financing quality.",
                confidence=conf,
                limitations="Does not judge payout policy optimality.",
                references=(
                    "FinancialAnalysis.ratios.capital_allocation",
                    "FinancialAnalysis.cash_flow.quality_flags",
                ),
            )
        )
        return Assessment(
            name="shareholder_capital_stewardship",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _flags(
        self,
        assessments: list[Assessment],
        cash,
        ratios,
        trends,
        overall_01: float | None,
    ) -> tuple[CapitalAllocationFlag, ...]:
        by_name = {a.name: a for a in assessments}
        flags: list[CapitalAllocationFlag] = []
        cf_flags = {getattr(f, "value", str(f)) for f in cash.quality_flags}
        ratio_flags = {getattr(f, "value", str(f)) for f in ratios.quality_flags}

        if overall_01 is not None and overall_01 >= 0.75:
            flags.append(CapitalAllocationFlag.EXCELLENT_CAPITAL_ALLOCATION)
        elif overall_01 is not None and overall_01 < 0.45:
            flags.append(CapitalAllocationFlag.WEAK_CAPITAL_ALLOCATION)

        rein = by_name.get("reinvestment_quality")
        capex = by_name.get("capex_discipline")
        if rein and rein.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(CapitalAllocationFlag.DISCIPLINED_REINVESTMENT)
        if capex and capex.rating in (Rating.WEAK, Rating.POOR):
            flags.append(CapitalAllocationFlag.EXCESSIVE_CAPITAL_SPENDING)
        if "heavy_capex" in cf_flags:
            if CapitalAllocationFlag.EXCESSIVE_CAPITAL_SPENDING not in flags:
                flags.append(CapitalAllocationFlag.EXCESSIVE_CAPITAL_SPENDING)

        stew = by_name.get("shareholder_capital_stewardship")
        if stew and stew.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(CapitalAllocationFlag.SHAREHOLDER_FRIENDLY)
        if "shareholder_friendly" in cf_flags:
            if CapitalAllocationFlag.SHAREHOLDER_FRIENDLY not in flags:
                flags.append(CapitalAllocationFlag.SHAREHOLDER_FRIENDLY)

        deploy = by_name.get("cash_deployment_quality")
        if deploy and deploy.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(CapitalAllocationFlag.HEALTHY_CASH_DEPLOYMENT)
        if "healthy_capital_allocation" in cf_flags:
            if CapitalAllocationFlag.HEALTHY_CASH_DEPLOYMENT not in flags:
                flags.append(CapitalAllocationFlag.HEALTHY_CASH_DEPLOYMENT)

        dep = cash.financing.financing_dependence
        if dep is not None and dep >= 0.55:
            flags.append(CapitalAllocationFlag.DEBT_DEPENDENT)

        div = by_name.get("dividend_allocation_quality")
        if div and div.rating in (Rating.WEAK, Rating.POOR):
            flags.append(CapitalAllocationFlag.DIVIDEND_AT_RISK)
        if ratios.capital_allocation.dividend_sustainability is not None:
            if ratios.capital_allocation.dividend_sustainability < 0.4:
                if CapitalAllocationFlag.DIVIDEND_AT_RISK not in flags:
                    flags.append(CapitalAllocationFlag.DIVIDEND_AT_RISK)

        consist = by_name.get("capital_allocation_consistency")
        if consist and consist.rating in (Rating.WEAK, Rating.POOR):
            flags.append(CapitalAllocationFlag.INCONSISTENT_ALLOCATION)
        if trends is not None:
            alloc = next(
                (
                    t
                    for t in trends.ratio_trends
                    if t.name == "capital_allocation_score"
                ),
                None,
            )
            if alloc is not None and getattr(alloc.classification, "value", "") in (
                "highly_volatile",
                "strongly_weakening",
            ):
                if CapitalAllocationFlag.INCONSISTENT_ALLOCATION not in flags:
                    flags.append(CapitalAllocationFlag.INCONSISTENT_ALLOCATION)

        if "capital_allocation_warning" in ratio_flags:
            if CapitalAllocationFlag.WEAK_CAPITAL_ALLOCATION not in flags:
                flags.append(CapitalAllocationFlag.WEAK_CAPITAL_ALLOCATION)

        return tuple(dict.fromkeys(flags))


def _capex_from_intensity(intensity: float | None) -> float | None:
    if intensity is None:
        return None
    return max(0.0, min(1.0, 1.0 - min(1.0, intensity)))


def _flexibility(
    dependence: float | None, cash_sust: float | None
) -> float | None:
    parts: list[float] = []
    if dependence is not None:
        parts.append(1.0 - min(1.0, max(0.0, dependence)))
    if cash_sust is not None:
        parts.append(cash_sust)
    if not parts:
        return None
    return sum(parts) / len(parts)
