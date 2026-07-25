"""Competitive Position Indicators engine (F3.5).

Composes competitive assessments from FinancialAnalysis outputs only —
no peer comparisons, industry data, valuation, or forecasting.
"""

from __future__ import annotations

from typing import Any

from business_quality.competitive_position_explainability import (
    COMPETITIVE_POSITION_DISCLAIMER,
    cp_explanation,
)
from business_quality.competitive_position_models import (
    CompetitivePositionAnalysis,
    CompetitivePositionFlag,
)
from business_quality.competitive_position_validation import (
    validate_competitive_position_input,
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

__all__ = ["CompetitivePositionEngine", "COMPETITIVE_POSITION_VERSION"]

COMPETITIVE_POSITION_VERSION = "0.5.0-competitive-position"

_BENCHMARK_01 = {
    "excellent": 1.0,
    "strong": 0.8,
    "adequate": 0.6,
    "weak": 0.35,
    "poor": 0.15,
}


class CompetitivePositionEngine:
    """Evaluate competitive position indicators from FinancialAnalysis."""

    def analyze(self, financial_analysis: Any) -> CompetitivePositionAnalysis:
        validation = validate_competitive_position_input(financial_analysis)
        fa = financial_analysis
        income = fa.income
        balance = fa.balance_sheet
        cash = fa.cash_flow
        ratios = fa.ratios
        trends = getattr(fa, "trends", None)
        summary = fa.overall_summary

        explanations: list[BusinessQualityExplainability] = []
        assessments: list[Assessment] = []
        evidence: list[str] = []

        assessments.append(
            self._assess(
                "pricing_power",
                "Pricing Power Indicators",
                _pricing_power(income),
                "FinancialAnalysis.income.margins / profitability",
                "Reuses gross/operating margins and margin expansion/compression.",
                explanations,
                evidence,
                extra_evidence=f"gross_margin={income.margins.gross_margin}",
            )
        )
        assessments.append(
            self._assess(
                "margin_defensibility",
                "Margin Defensibility",
                _margin_defensibility(income),
                "FinancialAnalysis.income.profitability / consistency",
                "Reuses margin stability/consistency; inverts compression.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "return_on_capital_strength",
                "Return on Capital Strength",
                _return_on_capital(ratios),
                "FinancialAnalysis.ratios.profitability",
                "Maps existing ROA/ROE/ROIC/ROCE benchmarks to scores.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "cash_conversion_advantage",
                "Cash Conversion Advantage",
                _cash_conversion(cash, ratios),
                "FinancialAnalysis.cash_flow.operating / ratios.cash_flow",
                "Reuses cash conversion, FCF margin, and operating cash quality.",
                explanations,
                evidence,
                extra_evidence=f"cash_conversion={cash.operating.cash_conversion}",
            )
        )
        assessments.append(
            self._assess(
                "operational_efficiency",
                "Operational Efficiency",
                _operational_efficiency(ratios, balance),
                "FinancialAnalysis.ratios.efficiency / balance_sheet",
                "Reuses efficiency ratio benchmarks and working-capital signals.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "revenue_stability",
                "Revenue Stability",
                _revenue_stability(income),
                "FinancialAnalysis.income.revenue / consistency",
                "Reuses growth_stability and revenue_consistency.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "profitability_persistence",
                "Profitability Persistence",
                _profitability_persistence(income, trends),
                "FinancialAnalysis.income / trends",
                "Reuses earnings consistency/stability and profitability trends.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "capital_efficiency",
                "Capital Efficiency",
                _capital_efficiency(ratios, cash),
                "FinancialAnalysis.ratios.profitability / efficiency / cash_flow",
                "Blends return benchmarks, asset turnover, and inverted capex intensity.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "competitive_resilience",
                "Competitive Resilience",
                _competitive_resilience(income, balance, cash),
                "FinancialAnalysis.income / balance_sheet / cash_flow",
                "Blends margin durability with balance-sheet and cash resilience.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "financial_competitive_strength",
                "Financial Competitive Strength",
                _financial_competitive_strength(income, ratios, cash, summary),
                "FinancialAnalysis.overall_summary / ratios / income / cash_flow",
                "Composite of profitability, cash quality, and summary health signals.",
                explanations,
                evidence,
            )
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
        flags = self._flags(assessments, income, ratios, trends, overall_01)

        if getattr(summary, "health_label", None):
            evidence.append(f"financial_summary.health_label={summary.health_label}")
        for s in getattr(summary, "strengths", ())[:2]:
            evidence.append(f"financial_summary.strength={s}")

        meta = getattr(fa, "metadata", None)
        metadata = BusinessQualityMetadata(
            engine_version=COMPETITIVE_POSITION_VERSION,
            framework_version=FRAMEWORK_VERSION,
            company=str(getattr(meta, "company", "") or ""),
            ticker=str(getattr(meta, "ticker", "") or ""),
            modules_composed=(
                "competitive_position_indicators",
                "financial_analysis",
            ),
        )
        explanations.append(
            cp_explanation(
                title="Overall Competitive Position",
                description="Composite of competitive-position dimension assessments.",
                evidence=tuple(evidence[:12]),
                reasoning=(
                    f"Overall rating={overall_rating.value}; "
                    f"score={None if overall_01 is None else round(overall_01, 4)}."
                ),
                confidence=confidence,
                limitations=(
                    "Equal-weight mean of available dimensions; no peer or "
                    "industry relative ranking. Not a valuation or forecast."
                ),
                references=(
                    "FinancialAnalysis.income",
                    "FinancialAnalysis.balance_sheet",
                    "FinancialAnalysis.cash_flow",
                    "FinancialAnalysis.ratios",
                    "FinancialAnalysis.trends",
                    "FinancialAnalysis.overall_summary",
                ),
            )
        )
        return CompetitivePositionAnalysis(
            metadata=metadata,
            validation=validation,
            assessments=tuple(assessments),
            overall_score=overall_score,
            overall_rating=overall_rating,
            confidence=confidence,
            quality_flags=flags,
            evidence=tuple(dict.fromkeys(evidence)),
            explainability=tuple(explanations),
            research_disclaimer=COMPETITIVE_POSITION_DISCLAIMER,
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
            cp_explanation(
                title=title,
                description=f"Assessment of {title.lower()}.",
                evidence=(f"{name}={value}",)
                + ((extra_evidence,) if extra_evidence else ()),
                reasoning=reasoning,
                confidence=conf,
                limitations=(
                    "Does not recalculate statement ratios or use peer data."
                ),
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

    def _flags(
        self,
        assessments: list[Assessment],
        income,
        ratios,
        trends,
        overall_01: float | None,
    ) -> tuple[CompetitivePositionFlag, ...]:
        by_name = {a.name: a for a in assessments}
        flags: list[CompetitivePositionFlag] = []
        income_flags = {getattr(f, "value", str(f)) for f in income.quality_flags}
        ratio_flags = {getattr(f, "value", str(f)) for f in ratios.quality_flags}

        if overall_01 is not None and overall_01 >= 0.75:
            flags.append(CompetitivePositionFlag.STRONG_COMPETITIVE_POSITION)
        elif overall_01 is not None and overall_01 < 0.45:
            flags.append(CompetitivePositionFlag.WEAK_COMPETITIVE_POSITION)

        pricing = by_name.get("pricing_power")
        if pricing and pricing.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(CompetitivePositionFlag.STRONG_PRICING_POWER)
        if "margin_expansion" in income_flags:
            if CompetitivePositionFlag.STRONG_PRICING_POWER not in flags:
                flags.append(CompetitivePositionFlag.STRONG_PRICING_POWER)

        margins = by_name.get("margin_defensibility")
        if margins and margins.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(CompetitivePositionFlag.DURABLE_MARGINS)
        if margins and margins.rating in (Rating.WEAK, Rating.POOR):
            flags.append(CompetitivePositionFlag.MARGIN_PRESSURE)
        if "margin_compression" in income_flags:
            if CompetitivePositionFlag.MARGIN_PRESSURE not in flags:
                flags.append(CompetitivePositionFlag.MARGIN_PRESSURE)

        cap_eff = by_name.get("capital_efficiency")
        if cap_eff and cap_eff.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(CompetitivePositionFlag.HIGH_CAPITAL_EFFICIENCY)
        if cap_eff and cap_eff.rating in (Rating.WEAK, Rating.POOR):
            flags.append(CompetitivePositionFlag.WEAK_CAPITAL_EFFICIENCY)
        if "poor_efficiency" in ratio_flags:
            if CompetitivePositionFlag.WEAK_CAPITAL_EFFICIENCY not in flags:
                flags.append(CompetitivePositionFlag.WEAK_CAPITAL_EFFICIENCY)

        ops = by_name.get("operational_efficiency")
        if ops and ops.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(CompetitivePositionFlag.OPERATIONAL_EXCELLENCE)
        if "efficient_operations" in ratio_flags:
            if CompetitivePositionFlag.OPERATIONAL_EXCELLENCE not in flags:
                flags.append(CompetitivePositionFlag.OPERATIONAL_EXCELLENCE)

        persist = by_name.get("profitability_persistence")
        if persist and persist.rating in (Rating.WEAK, Rating.POOR):
            flags.append(CompetitivePositionFlag.DECLINING_PROFITABILITY)
        if "weak_profitability" in ratio_flags:
            if CompetitivePositionFlag.DECLINING_PROFITABILITY not in flags:
                flags.append(CompetitivePositionFlag.DECLINING_PROFITABILITY)
        if trends is not None:
            summary = getattr(trends, "trend_summary", None)
            profit = getattr(summary, "profitability", None) if summary else None
            pv = getattr(profit, "value", str(profit or ""))
            if pv in {"strongly_weakening", "weakening", "highly_volatile"}:
                if CompetitivePositionFlag.DECLINING_PROFITABILITY not in flags:
                    flags.append(CompetitivePositionFlag.DECLINING_PROFITABILITY)

        return tuple(dict.fromkeys(flags))


def _clip01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def _invert(value: float | None) -> float | None:
    clipped = _clip01(value)
    if clipped is None:
        return None
    return 1.0 - clipped


def _mean(parts: list[float | None]) -> float | None:
    present = [p for p in parts if p is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _ratio_metric(metrics: Any, name: str) -> Any | None:
    if metrics is None:
        return None
    for m in metrics:
        if getattr(m, "name", None) == name:
            return m
    return None


def _benchmark_score(metric: Any | None) -> float | None:
    if metric is None:
        return None
    bench = getattr(metric, "benchmark", None)
    key = getattr(bench, "value", str(bench or "")).lower()
    return _BENCHMARK_01.get(key)


def _normalize_turnover(value: float | None, *, scale: float = 2.0) -> float | None:
    if value is None or scale <= 0:
        return None
    return max(0.0, min(1.0, float(value) / scale))


def _pricing_power(income) -> float | None:
    expansion = getattr(income.profitability, "margin_expansion", None)
    expansion_score = None
    if expansion is not None:
        expansion_score = max(0.0, min(1.0, 0.5 + float(expansion)))
    return _mean(
        [
            _clip01(getattr(income.margins, "gross_margin", None)),
            _clip01(getattr(income.margins, "operating_margin", None)),
            expansion_score,
            _invert(getattr(income.profitability, "margin_compression", None)),
        ]
    )


def _margin_defensibility(income) -> float | None:
    return _mean(
        [
            _clip01(getattr(income.profitability, "margin_stability", None)),
            _clip01(getattr(income.consistency, "margin_consistency", None)),
            _invert(getattr(income.profitability, "margin_compression", None)),
        ]
    )


def _return_on_capital(ratios) -> float | None:
    profitability = getattr(ratios, "profitability", None)
    return _mean(
        [
            _benchmark_score(_ratio_metric(profitability, "roa")),
            _benchmark_score(_ratio_metric(profitability, "roe")),
            _benchmark_score(_ratio_metric(profitability, "roic")),
            _benchmark_score(_ratio_metric(profitability, "roce")),
        ]
    )


def _cash_conversion(cash, ratios) -> float | None:
    ratio_conv = _ratio_metric(getattr(ratios, "cash_flow", None), "cash_conversion_ratio")
    return _mean(
        [
            _clip01(getattr(cash.operating, "cash_conversion", None)),
            _benchmark_score(ratio_conv),
            _clip01(getattr(cash.free_cash_flow, "fcf_margin", None)),
            _clip01(getattr(cash.quality, "operating_cash_quality", None)),
            _clip01(getattr(cash.quality, "cash_sustainability", None)),
        ]
    )


def _operational_efficiency(ratios, balance) -> float | None:
    efficiency = getattr(ratios, "efficiency", None)
    ato = _ratio_metric(efficiency, "asset_turnover")
    fat = _ratio_metric(efficiency, "fixed_asset_turnover")
    return _mean(
        [
            _benchmark_score(ato),
            _normalize_turnover(getattr(ato, "value", None) if ato else None),
            _normalize_turnover(
                getattr(fat, "value", None) if fat else None, scale=3.0
            ),
            _clip01(getattr(balance.working_capital, "inventory_efficiency", None)),
        ]
    )


def _revenue_stability(income) -> float | None:
    return _mean(
        [
            _clip01(getattr(income.revenue, "growth_stability", None)),
            _clip01(getattr(income.consistency, "revenue_consistency", None)),
        ]
    )


def _profitability_persistence(income, trends) -> float | None:
    parts: list[float | None] = [
        _clip01(getattr(income.profitability, "earnings_consistency", None)),
        _clip01(getattr(income.consistency, "earnings_stability", None)),
        _clip01(getattr(income.consistency, "recurring_earnings", None)),
        _clip01(getattr(income.profitability, "margin_stability", None)),
    ]
    if trends is not None:
        consistency = getattr(trends, "consistency", None)
        parts.append(_clip01(getattr(consistency, "persistence_score", None)))
        parts.append(_clip01(getattr(consistency, "consistency_score", None)))
        summary = getattr(trends, "trend_summary", None)
        profit = getattr(summary, "profitability", None) if summary else None
        pv = getattr(profit, "value", str(profit or ""))
        if pv in {"strongly_improving", "improving", "stable"}:
            parts.append(0.75 if pv != "stable" else 0.65)
        elif pv in {"strongly_weakening", "weakening"}:
            parts.append(0.25)
    return _mean(parts)


def _capital_efficiency(ratios, cash) -> float | None:
    profitability = getattr(ratios, "profitability", None)
    efficiency = getattr(ratios, "efficiency", None)
    ato = _ratio_metric(efficiency, "asset_turnover")
    return _mean(
        [
            _benchmark_score(_ratio_metric(profitability, "roic")),
            _benchmark_score(_ratio_metric(profitability, "roa")),
            _benchmark_score(ato),
            _normalize_turnover(getattr(ato, "value", None) if ato else None),
            _invert(getattr(cash.investing, "capex_intensity", None)),
        ]
    )


def _competitive_resilience(income, balance, cash) -> float | None:
    return _mean(
        [
            _clip01(getattr(income.profitability, "margin_stability", None)),
            _clip01(getattr(balance.working_capital, "balance_sheet_strength", None)),
            _clip01(getattr(balance.working_capital, "financial_flexibility", None)),
            _invert(getattr(balance.working_capital, "debt_burden", None)),
            _clip01(getattr(cash.quality, "cash_sustainability", None)),
        ]
    )


def _financial_competitive_strength(income, ratios, cash, summary) -> float | None:
    parts: list[float | None] = [
        _clip01(getattr(income.profitability, "operating_profit_quality", None)),
        _clip01(getattr(income.profitability, "net_income_quality", None)),
        _return_on_capital(ratios),
        _clip01(getattr(cash.quality, "cash_sustainability", None)),
    ]
    ratio_flags = {getattr(f, "value", str(f)) for f in ratios.quality_flags}
    if "excellent_profitability" in ratio_flags:
        parts.append(0.9)
    if "weak_profitability" in ratio_flags:
        parts.append(0.2)
    health = str(getattr(summary, "health_label", "") or "").lower()
    if "excellent" in health or "healthy" in health:
        parts.append(0.8)
    elif "deterioration" in health or "weak" in health or "poor" in health:
        parts.append(0.25)
    return _mean(parts)
