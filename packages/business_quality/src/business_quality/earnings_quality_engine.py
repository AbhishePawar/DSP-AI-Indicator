"""Earnings Quality Intelligence engine (F3.2).

Composes assessments from FinancialAnalysis outputs only —
no duplicated financial statement calculations.
"""

from __future__ import annotations

from typing import Any

from business_quality.earnings_quality_explainability import (
    EARNINGS_QUALITY_DISCLAIMER,
    eq_explanation,
)
from business_quality.earnings_quality_models import (
    EarningsQualityAnalysis,
    EarningsQualityFlag,
)
from business_quality.earnings_quality_validation import (
    validate_earnings_quality_input,
)
from business_quality.metadata import (
    FRAMEWORK_VERSION,
    BusinessQualityMetadata,
)
from business_quality.scoring import (
    Assessment,
    Confidence,
    EvidenceLevel,
    Rating,
    RiskLevel,
    Score,
    clip_score,
    weighted_mean,
)
from business_quality.explainability import BusinessQualityExplainability
from financial.intelligence.quality_signals import map_fcf_to_earnings_01

__all__ = ["EarningsQualityEngine", "EARNINGS_QUALITY_VERSION"]

EARNINGS_QUALITY_VERSION = "0.2.0-earnings-quality"


def _score_01(value: float | None) -> Score | None:
    if value is None:
        return None
    return Score(value=clip_score(value * 100.0), unit="index")


def _rating_from_01(value: float | None) -> Rating:
    if value is None:
        return Rating.INSUFFICIENT_DATA
    if value >= 0.85:
        return Rating.EXCELLENT
    if value >= 0.70:
        return Rating.STRONG
    if value >= 0.55:
        return Rating.AVERAGE
    if value >= 0.40:
        return Rating.WEAK
    return Rating.POOR


def _confidence_from_present(*values: float | None) -> Confidence:
    present = sum(1 for v in values if v is not None)
    if present == 0:
        return Confidence.INSUFFICIENT
    if present >= 3:
        return Confidence.HIGH
    if present == 2:
        return Confidence.MEDIUM
    return Confidence.LOW


def _risk_from_01(value: float | None, *, invert: bool = False) -> RiskLevel:
    if value is None:
        return RiskLevel.UNKNOWN
    v = (1.0 - value) if invert else value
    if v >= 0.75:
        return RiskLevel.HIGH
    if v >= 0.55:
        return RiskLevel.ELEVATED
    if v >= 0.35:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def _aggregate_confidence(confidences: list[Confidence]) -> Confidence:
    rank = {
        Confidence.HIGH: 3,
        Confidence.MEDIUM: 2,
        Confidence.LOW: 1,
        Confidence.INSUFFICIENT: 0,
    }
    if not confidences:
        return Confidence.INSUFFICIENT
    avg = sum(rank[c] for c in confidences) / len(confidences)
    if avg >= 2.5:
        return Confidence.HIGH
    if avg >= 1.5:
        return Confidence.MEDIUM
    if avg >= 0.5:
        return Confidence.LOW
    return Confidence.INSUFFICIENT


class EarningsQualityEngine:
    """Evaluate earnings quality from a FinancialAnalysis artifact."""

    def analyze(self, financial_analysis: Any) -> EarningsQualityAnalysis:
        """Run Earnings Quality Intelligence on FinancialAnalysis only."""
        validation = validate_earnings_quality_input(financial_analysis)
        fa = financial_analysis
        income = fa.income
        cash = fa.cash_flow

        explanations: list[BusinessQualityExplainability] = []
        assessments: list[Assessment] = []
        evidence: list[str] = []

        assessments.append(
            self._assess_revenue_quality(income, explanations, evidence)
        )
        assessments.append(
            self._assess_operating_earnings(income, explanations, evidence)
        )
        assessments.append(
            self._assess_net_earnings(income, explanations, evidence)
        )
        assessments.append(
            self._assess_cash_earnings(cash, explanations, evidence)
        )
        assessments.append(
            self._assess_accrual_quality(cash, income, explanations, evidence)
        )
        assessments.append(
            self._assess_margin_stability(income, explanations, evidence)
        )
        assessments.append(
            self._assess_earnings_consistency(income, explanations, evidence)
        )
        assessments.append(
            self._assess_fcf_support(cash, explanations, evidence)
        )
        assessments.append(
            self._assess_non_operating(income, explanations, evidence)
        )
        assessments.append(
            self._assess_recurring(income, explanations, evidence)
        )

        scored = [
            (a.score.value / 100.0, 1.0)
            for a in assessments
            if a.score is not None and a.score.value is not None
        ]
        overall_01 = weighted_mean(scored)
        overall_score = _score_01(overall_01)
        overall_rating = _rating_from_01(overall_01)
        confidences = [a.confidence for a in assessments]
        confidence = _aggregate_confidence(confidences)

        flags = self._flags(assessments, income, cash, overall_01)
        meta = getattr(fa, "metadata", None)
        metadata = BusinessQualityMetadata(
            engine_version=EARNINGS_QUALITY_VERSION,
            framework_version=FRAMEWORK_VERSION,
            company=str(getattr(meta, "company", "") or ""),
            ticker=str(getattr(meta, "ticker", "") or ""),
            modules_composed=(
                "earnings_quality_intelligence",
                "financial_analysis",
            ),
            schema_version="1",
        )
        explanations.append(
            eq_explanation(
                title="Overall Earnings Quality",
                description="Composite of dimension assessments from FinancialAnalysis.",
                evidence=tuple(evidence[:12]),
                reasoning=(
                    f"Overall rating={overall_rating.value}; "
                    f"score={None if overall_01 is None else round(overall_01, 4)}."
                ),
                confidence=confidence,
                limitations=(
                    "Composite is an equal-weight mean of available dimension "
                    "scores; it does not forecast earnings."
                ),
                references=(
                    "FinancialAnalysis.income",
                    "FinancialAnalysis.cash_flow",
                    "FinancialAnalysis.ratios",
                ),
            )
        )
        return EarningsQualityAnalysis(
            metadata=metadata,
            validation=validation,
            assessments=tuple(assessments),
            overall_score=overall_score,
            overall_rating=overall_rating,
            confidence=confidence,
            quality_flags=flags,
            evidence=tuple(dict.fromkeys(evidence)),
            explainability=tuple(explanations),
            research_disclaimer=EARNINGS_QUALITY_DISCLAIMER,
        )

    def _assess_revenue_quality(self, income, out, evidence) -> Assessment:
        rev = income.revenue
        consistency = income.consistency
        value = rev.growth_stability
        if value is None:
            value = consistency.revenue_consistency
        evidence.append(f"revenue={rev.revenue}")
        if value is not None:
            evidence.append(f"revenue_stability={value}")
        conf = _confidence_from_present(rev.revenue, value)
        out.append(
            eq_explanation(
                title="Revenue Quality",
                description="Stability / consistency of reported revenue.",
                evidence=(f"revenue={rev.revenue}", f"stability={value}"),
                reasoning="Uses income.revenue / consistency fields from FinancialAnalysis.",
                confidence=conf,
                limitations="Does not inspect revenue recognition policies.",
                references=("FinancialAnalysis.income.revenue",),
            )
        )
        return Assessment(
            name="revenue_quality",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=(
                EvidenceLevel.STRONG
                if conf is Confidence.HIGH
                else EvidenceLevel.LIMITED
            ),
            risk_level=_risk_from_01(value, invert=True),
            notes="From income revenue stability / consistency",
        )

    def _assess_operating_earnings(self, income, out, evidence) -> Assessment:
        value = income.profitability.operating_profit_quality
        evidence.append(f"operating_profit_quality={value}")
        conf = _confidence_from_present(value, income.margins.operating_margin)
        out.append(
            eq_explanation(
                title="Operating Earnings Quality",
                description="Quality of operating earnings signals.",
                evidence=(f"operating_profit_quality={value}",),
                reasoning="Reuses income.profitability.operating_profit_quality.",
                confidence=conf,
                limitations="Does not recompute operating income.",
                references=("FinancialAnalysis.income.profitability",),
            )
        )
        return Assessment(
            name="operating_earnings_quality",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _assess_net_earnings(self, income, out, evidence) -> Assessment:
        value = income.profitability.net_income_quality
        evidence.append(f"net_income_quality={value}")
        conf = _confidence_from_present(value, income.margins.net_margin)
        out.append(
            eq_explanation(
                title="Net Earnings Quality",
                description="Quality of bottom-line earnings signals.",
                evidence=(f"net_income_quality={value}",),
                reasoning="Reuses income.profitability.net_income_quality.",
                confidence=conf,
                limitations="Does not adjust GAAP/non-GAAP differences.",
                references=("FinancialAnalysis.income.profitability",),
            )
        )
        return Assessment(
            name="net_earnings_quality",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _assess_cash_earnings(self, cash, out, evidence) -> Assessment:
        value = cash.operating.cash_earnings_quality
        if value is None:
            value = cash.quality.operating_cash_quality
        evidence.append(f"cash_earnings_quality={value}")
        conf = _confidence_from_present(
            value, cash.operating.operating_cash_flow, cash.operating.cash_conversion
        )
        out.append(
            eq_explanation(
                title="Cash Earnings Quality",
                description="Cash earnings quality from cash-flow intelligence.",
                evidence=(
                    f"cash_earnings_quality={value}",
                    f"ocf={cash.operating.operating_cash_flow}",
                ),
                reasoning="Reuses cash_flow.operating / quality fields.",
                confidence=conf,
                limitations="Does not recompute cash flow line items.",
                references=("FinancialAnalysis.cash_flow.operating",),
            )
        )
        return Assessment(
            name="cash_earnings_quality",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.STRONG
            if conf is Confidence.HIGH
            else EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _assess_accrual_quality(self, cash, income, out, evidence) -> Assessment:
        # Accrual quality ≈ cash conversion support (already computed)
        conversion = cash.operating.cash_conversion
        # Map conversion into [0,1]-ish quality: higher conversion → better
        value = None
        if conversion is not None:
            # clip conversion into a quality index without recomputing OCF/NI
            if conversion >= 1.0:
                value = 0.95
            elif conversion >= 0.8:
                value = 0.80
            elif conversion >= 0.5:
                value = 0.60
            elif conversion >= 0.0:
                value = 0.35
            else:
                value = 0.20
        evidence.append(f"cash_conversion={conversion}")
        conf = _confidence_from_present(conversion, income.profitability.net_income_quality)
        out.append(
            eq_explanation(
                title="Accrual Quality",
                description="Accrual risk inferred from cash conversion support.",
                evidence=(f"cash_conversion={conversion}",),
                reasoning=(
                    "Uses FinancialAnalysis cash_conversion as accrual-support "
                    "proxy; does not recompute accruals."
                ),
                confidence=conf,
                limitations="Heuristic mapping of conversion → accrual quality.",
                references=(
                    "FinancialAnalysis.cash_flow.operating.cash_conversion",
                ),
            )
        )
        return Assessment(
            name="accrual_quality",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
            notes="Derived from cash_conversion only",
        )

    def _assess_margin_stability(self, income, out, evidence) -> Assessment:
        value = income.profitability.margin_stability
        if value is None:
            value = income.consistency.margin_consistency
        evidence.append(f"margin_stability={value}")
        conf = _confidence_from_present(value, income.margins.net_margin)
        out.append(
            eq_explanation(
                title="Margin Stability",
                description="Stability of profitability margins.",
                evidence=(f"margin_stability={value}",),
                reasoning="Reuses income profitability/consistency margin fields.",
                confidence=conf,
                limitations="Does not forecast future margins.",
                references=("FinancialAnalysis.income.profitability",),
            )
        )
        return Assessment(
            name="margin_stability",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _assess_earnings_consistency(self, income, out, evidence) -> Assessment:
        value = income.profitability.earnings_consistency
        if value is None:
            value = income.consistency.earnings_stability
        evidence.append(f"earnings_consistency={value}")
        conf = _confidence_from_present(value, income.profitability.eps_stability)
        out.append(
            eq_explanation(
                title="Earnings Consistency",
                description="Consistency / stability of earnings series.",
                evidence=(f"earnings_consistency={value}",),
                reasoning="Reuses income profitability/consistency fields.",
                confidence=conf,
                limitations="Multi-period depth depends on FinancialAnalysis history.",
                references=("FinancialAnalysis.income.profitability",),
            )
        )
        return Assessment(
            name="earnings_consistency",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _assess_fcf_support(self, cash, out, evidence) -> Assessment:
        fcf = cash.free_cash_flow.free_cash_flow
        stability = cash.free_cash_flow.fcf_stability
        conversion = cash.operating.cash_conversion
        fcf_to_earn = getattr(cash.free_cash_flow, "fcf_to_earnings", None)
        # Prefer first-class FCF/NI when available; keep FCF/OCF as secondary.
        fte_01 = map_fcf_to_earnings_01(fcf_to_earn)
        parts = [p for p in (fte_01, stability) if p is not None]
        value = sum(parts) / len(parts) if parts else None
        if value is None and conversion is not None:
            value = min(1.0, max(0.0, conversion if conversion <= 1.5 else 1.0))
        if value is None and fcf is not None:
            value = 0.7 if fcf > 0 else 0.25
        evidence.append(f"fcf={fcf}")
        evidence.append(f"fcf_stability={stability}")
        evidence.append(f"fcf_to_earnings={fcf_to_earn}")
        conf = _confidence_from_present(fcf, stability, conversion, fcf_to_earn)
        out.append(
            eq_explanation(
                title="Free Cash Flow Support",
                description="FCF support for reported earnings.",
                evidence=(
                    f"fcf={fcf}",
                    f"fcf_stability={stability}",
                    f"fcf_to_earnings={fcf_to_earn}",
                ),
                reasoning=(
                    "Prefers fcf_to_earnings (FCF/NI) with FCF stability; "
                    "falls back to cash_conversion (FCF/OCF) then FCF sign."
                ),
                confidence=conf,
                limitations="Does not recompute FCF from statements.",
                references=(
                    "FinancialAnalysis.cash_flow.free_cash_flow",
                    "FinancialAnalysis.cash_flow.free_cash_flow.fcf_to_earnings",
                ),
            )
        )
        return Assessment(
            name="free_cash_flow_support",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _assess_non_operating(self, income, out, evidence) -> Assessment:
        # Lower dependence is better quality
        dep = income.consistency.other_income_dependence
        burden = income.consistency.interest_burden
        value = None
        parts = []
        if dep is not None:
            parts.append(1.0 - min(1.0, max(0.0, dep)))
        if burden is not None:
            parts.append(1.0 - min(1.0, max(0.0, burden)))
        if parts:
            value = sum(parts) / len(parts)
        evidence.append(f"other_income_dependence={dep}")
        evidence.append(f"interest_burden={burden}")
        conf = _confidence_from_present(dep, burden)
        out.append(
            eq_explanation(
                title="Non-operating Earnings Dependence",
                description="Lower non-operating dependence implies cleaner earnings.",
                evidence=(
                    f"other_income_dependence={dep}",
                    f"interest_burden={burden}",
                ),
                reasoning="Inverts income.consistency dependence/burden fields.",
                confidence=conf,
                limitations="Does not classify line items as operating/non-operating anew.",
                references=("FinancialAnalysis.income.consistency",),
            )
        )
        return Assessment(
            name="non_operating_dependence",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.LIMITED
            if conf is Confidence.LOW
            else EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _assess_recurring(self, income, out, evidence) -> Assessment:
        value = income.consistency.recurring_earnings
        one_time = income.consistency.one_time_items_detected
        if value is None and one_time:
            value = 0.35
        elif value is None and not one_time:
            value = 0.65
        evidence.append(f"recurring_earnings={value}")
        evidence.append(f"one_time_items_detected={one_time}")
        conf = _confidence_from_present(
            income.consistency.recurring_earnings,
            1.0 if one_time else None,
            income.profitability.net_income_quality,
        )
        out.append(
            eq_explanation(
                title="Recurring vs Non-recurring Earnings",
                description="Recurring earnings share / one-time detection.",
                evidence=(
                    f"recurring_earnings={income.consistency.recurring_earnings}",
                    f"one_time={one_time}",
                ),
                reasoning="Reuses income.consistency recurring / one-time fields.",
                confidence=conf,
                limitations="One-time detection depends on upstream income intelligence.",
                references=("FinancialAnalysis.income.consistency",),
            )
        )
        return Assessment(
            name="recurring_earnings",
            rating=_rating_from_01(value),
            score=_score_01(value),
            confidence=conf,
            evidence_level=EvidenceLevel.ADEQUATE,
            risk_level=_risk_from_01(value, invert=True),
        )

    def _flags(
        self,
        assessments: list[Assessment],
        income,
        cash,
        overall_01: float | None,
    ) -> tuple[EarningsQualityFlag, ...]:
        by_name = {a.name: a for a in assessments}
        flags: list[EarningsQualityFlag] = []

        accrual = by_name.get("accrual_quality")
        cash_a = by_name.get("cash_earnings_quality")
        fcf = by_name.get("free_cash_flow_support")
        margin = by_name.get("margin_stability")
        consist = by_name.get("earnings_consistency")
        recurring = by_name.get("recurring_earnings")

        if overall_01 is not None and overall_01 >= 0.75:
            flags.append(EarningsQualityFlag.HIGH_EARNINGS_QUALITY)

        conversion = cash.operating.cash_conversion
        if conversion is not None and conversion >= 0.8:
            flags.append(EarningsQualityFlag.CASH_SUPPORTED_EARNINGS)
        if (
            (cash_a and cash_a.rating in (Rating.STRONG, Rating.EXCELLENT))
            or (fcf and fcf.rating in (Rating.STRONG, Rating.EXCELLENT))
        ):
            if EarningsQualityFlag.CASH_SUPPORTED_EARNINGS not in flags:
                flags.append(EarningsQualityFlag.CASH_SUPPORTED_EARNINGS)

        if recurring and recurring.rating in (
            Rating.STRONG,
            Rating.EXCELLENT,
            Rating.AVERAGE,
        ):
            if not income.consistency.one_time_items_detected:
                flags.append(EarningsQualityFlag.RECURRING_EARNINGS)
            elif recurring.rating in (Rating.STRONG, Rating.EXCELLENT):
                flags.append(EarningsQualityFlag.RECURRING_EARNINGS)

        if margin and margin.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(EarningsQualityFlag.STABLE_MARGINS)

        # Risk flags
        if conversion is not None and conversion < 0.5:
            flags.append(EarningsQualityFlag.WEAK_CASH_SUPPORT)
        if fcf and fcf.rating in (Rating.WEAK, Rating.POOR):
            if EarningsQualityFlag.WEAK_CASH_SUPPORT not in flags:
                flags.append(EarningsQualityFlag.WEAK_CASH_SUPPORT)

        if accrual and accrual.rating in (Rating.WEAK, Rating.POOR):
            flags.append(EarningsQualityFlag.HIGH_ACCRUAL_RISK)
        if conversion is not None and conversion < 0.3:
            if EarningsQualityFlag.HIGH_ACCRUAL_RISK not in flags:
                flags.append(EarningsQualityFlag.HIGH_ACCRUAL_RISK)

        if consist and consist.rating in (Rating.WEAK, Rating.POOR):
            flags.append(EarningsQualityFlag.VOLATILE_EARNINGS)

        # Aggressive accounting: weak cash + weak accrual or upstream weak quality
        income_flag_values = {
            getattr(f, "value", str(f)) for f in income.quality_flags
        }
        if (
            EarningsQualityFlag.WEAK_CASH_SUPPORT in flags
            and EarningsQualityFlag.HIGH_ACCRUAL_RISK in flags
        ) or "weak_earnings_quality" in income_flag_values:
            flags.append(EarningsQualityFlag.AGGRESSIVE_ACCOUNTING_RISK)

        return tuple(dict.fromkeys(flags))
