"""Business Characteristics Intelligence engine (F3.4).

Composes structural assessments from FinancialAnalysis outputs only —
no duplicated financial calculations, valuation, or forecasting.
"""

from __future__ import annotations

from typing import Any

from business_quality.business_characteristics_explainability import (
    BUSINESS_CHARACTERISTICS_DISCLAIMER,
    bc_explanation,
)
from business_quality.business_characteristics_models import (
    BusinessCharacteristicsAnalysis,
    BusinessCharacteristicsFlag,
)
from business_quality.business_characteristics_validation import (
    validate_business_characteristics_input,
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

__all__ = ["BusinessCharacteristicsEngine", "BUSINESS_CHARACTERISTICS_VERSION"]

BUSINESS_CHARACTERISTICS_VERSION = "0.4.0-business-characteristics"


class BusinessCharacteristicsEngine:
    """Evaluate structural business characteristics from FinancialAnalysis."""

    def analyze(self, financial_analysis: Any) -> BusinessCharacteristicsAnalysis:
        validation = validate_business_characteristics_input(financial_analysis)
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
                "business_simplicity",
                "Business Simplicity",
                _business_simplicity(income, balance),
                "FinancialAnalysis.income / balance_sheet.assets",
                "Blends asset-quality and inverted complexity proxies "
                "(other-income dependence, goodwill/intangibles).",
                explanations,
                evidence,
            )
        )
        capital_intensity = _capital_intensity(cash, balance)
        assessments.append(
            self._assess(
                "capital_intensity",
                "Capital Intensity",
                capital_intensity,
                "FinancialAnalysis.cash_flow.investing / balance_sheet.assets",
                "Reuses capex_intensity and non-current asset composition.",
                explanations,
                evidence,
                extra_evidence=f"capex_intensity={cash.investing.capex_intensity}",
            )
        )
        asset_light = _asset_light(cash, balance, capital_intensity)
        assessments.append(
            self._assess(
                "asset_light",
                "Asset-Light Characteristics",
                asset_light,
                "FinancialAnalysis.balance_sheet.assets / cash_flow.investing",
                "Inverts capital intensity proxies and favors current-asset mix.",
                explanations,
                evidence,
            )
        )
        op_lev = _operating_leverage(income)
        assessments.append(
            self._assess(
                "operating_leverage",
                "Operating Leverage",
                op_lev,
                "FinancialAnalysis.income.growth / consistency",
                "Reuses consistency.operating_leverage or normalized growth OL.",
                explanations,
                evidence,
                extra_evidence=f"growth.operating_leverage={income.growth.operating_leverage}",
            )
        )
        assessments.append(
            self._assess(
                "business_scalability",
                "Business Scalability",
                _scalability(income, ratios, op_lev),
                "FinancialAnalysis.ratios.efficiency / income",
                "Blends normalized asset turnover, OL, margin expansion, growth stability.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "margin_durability",
                "Margin Durability",
                _margin_durability(income),
                "FinancialAnalysis.income.profitability / consistency",
                "Reuses margin_stability and margin_consistency.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "cash_generation",
                "Cash Generation Characteristics",
                _cash_generation(cash),
                "FinancialAnalysis.cash_flow.quality / free_cash_flow",
                "Reuses cash_sustainability, FCF stability, operating cash quality.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "financial_resilience",
                "Financial Resilience",
                _financial_resilience(balance, cash),
                "FinancialAnalysis.balance_sheet.working_capital / cash_flow",
                "Blends balance-sheet strength, flexibility, and cash sustainability.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "cyclicality",
                "Cyclicality Indicators",
                _cyclicality(income, trends),
                "FinancialAnalysis.income.revenue / consistency / trends",
                "Inverts growth/earnings stability; volatile revenue trend raises cyclicality.",
                explanations,
                evidence,
            )
        )
        assessments.append(
            self._assess(
                "operational_stability",
                "Operational Stability",
                _operational_stability(income),
                "FinancialAnalysis.income.consistency / profitability / revenue",
                "Mean of earnings, growth, margin, and revenue consistency scores.",
                explanations,
                evidence,
            )
        )

        # Overall favors durable / scalable / resilient traits; inverts
        # capital intensity and cyclicality so higher overall ≠ more cyclical.
        overall_parts: list[tuple[float, float]] = []
        by_name = {a.name: a for a in assessments}
        for name, weight, invert in (
            ("business_simplicity", 1.0, False),
            ("asset_light", 1.0, False),
            ("business_scalability", 1.0, False),
            ("margin_durability", 1.0, False),
            ("cash_generation", 1.0, False),
            ("financial_resilience", 1.0, False),
            ("operational_stability", 1.0, False),
            ("capital_intensity", 0.5, True),
            ("cyclicality", 0.5, True),
            ("operating_leverage", 0.5, False),
        ):
            a = by_name.get(name)
            if a is None or a.score is None or a.score.value is None:
                continue
            v = a.score.value / 100.0
            overall_parts.append((1.0 - v if invert else v, weight))

        overall_01 = weighted_mean(overall_parts)
        overall_score = _score_01(overall_01)
        overall_rating = _rating_from_01(overall_01)
        confidence = _aggregate_confidence([a.confidence for a in assessments])
        flags = self._flags(assessments, income, cash, balance, overall_01)

        if getattr(summary, "health_label", None):
            evidence.append(f"financial_summary.health_label={summary.health_label}")
        for s in getattr(summary, "strengths", ())[:2]:
            evidence.append(f"financial_summary.strength={s}")

        meta = getattr(fa, "metadata", None)
        metadata = BusinessQualityMetadata(
            engine_version=BUSINESS_CHARACTERISTICS_VERSION,
            framework_version=FRAMEWORK_VERSION,
            company=str(getattr(meta, "company", "") or ""),
            ticker=str(getattr(meta, "ticker", "") or ""),
            modules_composed=(
                "business_characteristics_intelligence",
                "financial_analysis",
            ),
        )
        explanations.append(
            bc_explanation(
                title="Overall Business Characteristics",
                description="Composite of structural characteristic assessments.",
                evidence=tuple(evidence[:12]),
                reasoning=(
                    f"Overall rating={overall_rating.value}; "
                    f"score={None if overall_01 is None else round(overall_01, 4)}."
                ),
                confidence=confidence,
                limitations=(
                    "Composite weights durable/scalable traits more heavily; "
                    "capital intensity and cyclicality are inverted in the overall. "
                    "Not a valuation or forecast."
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
        return BusinessCharacteristicsAnalysis(
            metadata=metadata,
            validation=validation,
            assessments=tuple(assessments),
            overall_score=overall_score,
            overall_rating=overall_rating,
            confidence=confidence,
            quality_flags=flags,
            evidence=tuple(dict.fromkeys(evidence)),
            explainability=tuple(explanations),
            research_disclaimer=BUSINESS_CHARACTERISTICS_DISCLAIMER,
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
            bc_explanation(
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

    def _flags(
        self,
        assessments: list[Assessment],
        income,
        cash,
        balance,
        overall_01: float | None,
    ) -> tuple[BusinessCharacteristicsFlag, ...]:
        by_name = {a.name: a for a in assessments}
        flags: list[BusinessCharacteristicsFlag] = []
        income_flags = {getattr(f, "value", str(f)) for f in income.quality_flags}
        cash_flags = {getattr(f, "value", str(f)) for f in cash.quality_flags}
        balance_flags = {getattr(f, "value", str(f)) for f in balance.quality_flags}

        asset = by_name.get("asset_light")
        if asset and asset.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.ASSET_LIGHT)

        intensity = by_name.get("capital_intensity")
        if intensity and intensity.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.CAPITAL_INTENSIVE)
        if "heavy_capex" in cash_flags:
            if BusinessCharacteristicsFlag.CAPITAL_INTENSIVE not in flags:
                flags.append(BusinessCharacteristicsFlag.CAPITAL_INTENSIVE)

        scale = by_name.get("business_scalability")
        if scale and scale.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.HIGHLY_SCALABLE)

        stab = by_name.get("operational_stability")
        if stab and stab.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.OPERATIONALLY_STABLE)

        res = by_name.get("financial_resilience")
        if res and res.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.RESILIENT_BUSINESS)
        if "healthy_balance_sheet" in balance_flags:
            if BusinessCharacteristicsFlag.RESILIENT_BUSINESS not in flags:
                flags.append(BusinessCharacteristicsFlag.RESILIENT_BUSINESS)

        cyc = by_name.get("cyclicality")
        if cyc and cyc.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.CYCLICAL_BUSINESS)
        trend_class = getattr(
            getattr(income, "revenue", None), "trend_class", None
        )
        if getattr(trend_class, "value", str(trend_class or "")) == "volatile":
            if BusinessCharacteristicsFlag.CYCLICAL_BUSINESS not in flags:
                flags.append(BusinessCharacteristicsFlag.CYCLICAL_BUSINESS)

        cash_a = by_name.get("cash_generation")
        if cash_a and cash_a.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.STRONG_CASH_GENERATOR)
        if "strong_cash_generation" in cash_flags:
            if BusinessCharacteristicsFlag.STRONG_CASH_GENERATOR not in flags:
                flags.append(BusinessCharacteristicsFlag.STRONG_CASH_GENERATOR)

        marg = by_name.get("margin_durability")
        if marg and marg.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.MARGIN_DURABLE)

        ol = by_name.get("operating_leverage")
        if ol and ol.rating in (Rating.STRONG, Rating.EXCELLENT):
            flags.append(BusinessCharacteristicsFlag.HIGH_OPERATING_LEVERAGE)
        if "high_operating_leverage" in income_flags:
            if BusinessCharacteristicsFlag.HIGH_OPERATING_LEVERAGE not in flags:
                flags.append(BusinessCharacteristicsFlag.HIGH_OPERATING_LEVERAGE)

        # overall unused for flags but kept for API symmetry / future use
        _ = overall_01
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


def _ratio_metric(metrics: Any, name: str) -> float | None:
    if metrics is None:
        return None
    for m in metrics:
        if getattr(m, "name", None) == name:
            return getattr(m, "value", None)
    return None


def _normalize_turnover(value: float | None, *, scale: float = 2.0) -> float | None:
    """Map an existing turnover ratio into [0, 1] for scoring (not a new ratio)."""
    if value is None:
        return None
    if scale <= 0:
        return None
    return max(0.0, min(1.0, float(value) / scale))


def _normalize_op_lev(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, abs(float(value)) / 3.0))


def _business_simplicity(income, balance) -> float | None:
    goodwill = getattr(balance.assets, "goodwill_pct", None)
    intangibles = getattr(balance.assets, "intangible_asset_pct", None)
    complexity = _mean([goodwill, intangibles])
    return _mean(
        [
            _invert(getattr(income.consistency, "other_income_dependence", None)),
            _invert(complexity),
            _clip01(getattr(balance.assets, "asset_quality_score", None)),
            _clip01(getattr(balance.working_capital, "asset_quality", None)),
        ]
    )


def _capital_intensity(cash, balance) -> float | None:
    return _mean(
        [
            _clip01(getattr(cash.investing, "capex_intensity", None)),
            _clip01(getattr(balance.assets, "non_current_asset_composition", None)),
        ]
    )


def _asset_light(cash, balance, capital_intensity: float | None) -> float | None:
    return _mean(
        [
            _invert(capital_intensity),
            _invert(getattr(cash.investing, "capex_intensity", None)),
            _clip01(getattr(balance.assets, "current_asset_composition", None)),
            _invert(getattr(balance.assets, "non_current_asset_composition", None)),
        ]
    )


def _operating_leverage(income) -> float | None:
    consistency_ol = getattr(income.consistency, "operating_leverage", None)
    if consistency_ol is not None:
        return _clip01(consistency_ol)
    return _normalize_op_lev(getattr(income.growth, "operating_leverage", None))


def _scalability(income, ratios, op_lev: float | None) -> float | None:
    ato = _normalize_turnover(_ratio_metric(ratios.efficiency, "asset_turnover"))
    fat = _normalize_turnover(
        _ratio_metric(ratios.efficiency, "fixed_asset_turnover"), scale=3.0
    )
    expansion = getattr(income.profitability, "margin_expansion", None)
    expansion_score = None
    if expansion is not None:
        expansion_score = max(0.0, min(1.0, 0.5 + float(expansion)))
    return _mean(
        [
            ato,
            fat,
            op_lev,
            expansion_score,
            _clip01(getattr(income.revenue, "growth_stability", None)),
        ]
    )


def _margin_durability(income) -> float | None:
    return _mean(
        [
            _clip01(getattr(income.profitability, "margin_stability", None)),
            _clip01(getattr(income.consistency, "margin_consistency", None)),
            _invert(getattr(income.profitability, "margin_compression", None)),
        ]
    )


def _cash_generation(cash) -> float | None:
    return _mean(
        [
            _clip01(getattr(cash.quality, "cash_sustainability", None)),
            _clip01(getattr(cash.free_cash_flow, "fcf_stability", None)),
            _clip01(getattr(cash.quality, "operating_cash_quality", None)),
        ]
    )


def _financial_resilience(balance, cash) -> float | None:
    return _mean(
        [
            _clip01(getattr(balance.working_capital, "balance_sheet_strength", None)),
            _clip01(getattr(balance.working_capital, "financial_flexibility", None)),
            _invert(getattr(balance.working_capital, "debt_burden", None)),
            _clip01(getattr(cash.quality, "cash_sustainability", None)),
            _clip01(getattr(cash.quality, "debt_sustainability", None)),
        ]
    )


def _cyclicality(income, trends) -> float | None:
    parts: list[float | None] = [
        _invert(getattr(income.revenue, "growth_stability", None)),
        _invert(getattr(income.consistency, "earnings_stability", None)),
        _invert(getattr(income.consistency, "revenue_consistency", None)),
    ]
    trend_class = getattr(income.revenue, "trend_class", None)
    tc = getattr(trend_class, "value", str(trend_class or ""))
    if tc == "volatile":
        parts.append(0.85)
    elif tc == "declining":
        parts.append(0.65)
    if trends is not None:
        summary = getattr(trends, "trend_summary", None)
        overall = getattr(summary, "overall", None) if summary is not None else None
        ov = getattr(overall, "value", str(overall or ""))
        if ov == "highly_volatile":
            parts.append(0.8)
        tflags = {getattr(f, "value", str(f)) for f in getattr(trends, "quality_flags", ())}
        if "high_volatility" in tflags:
            parts.append(0.75)
    return _mean(parts)


def _operational_stability(income) -> float | None:
    return _mean(
        [
            _clip01(getattr(income.consistency, "earnings_stability", None)),
            _clip01(getattr(income.revenue, "growth_stability", None)),
            _clip01(getattr(income.profitability, "margin_stability", None)),
            _clip01(getattr(income.consistency, "revenue_consistency", None)),
            _clip01(getattr(income.consistency, "margin_consistency", None)),
        ]
    )
