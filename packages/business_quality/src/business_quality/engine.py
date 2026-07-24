"""BusinessQualityEngine — Phase 3 Business Quality Intelligence façade."""

from __future__ import annotations

from typing import Any

from business_quality.capital_allocation_engine import CapitalAllocationEngine
from business_quality.capital_allocation_models import CapitalAllocationAnalysis
from business_quality.earnings_quality_engine import EarningsQualityEngine
from business_quality.earnings_quality_models import EarningsQualityAnalysis
from business_quality.explainability import RESEARCH_DISCLAIMER
from business_quality.metadata import (
    BUSINESS_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    BusinessQualityMetadata,
)
from business_quality.models import (
    BusinessQualityAnalysis,
    BusinessQualityFlag,
    BusinessQualityScore,
    BusinessQualitySummary,
)
from business_quality.scoring import Rating, Score, weighted_mean
from business_quality.earnings_quality_engine import _aggregate_confidence, _rating_from_01
from business_quality.validation import (
    empty_validation,
    merge_validation_results,
)

__all__ = ["BusinessQualityEngine", "BUSINESS_QUALITY_VERSION"]


class BusinessQualityEngine:
    """Façade for Business Quality Intelligence (F3.1+)."""

    def __init__(self) -> None:
        self._version = BUSINESS_QUALITY_VERSION
        self._earnings = EarningsQualityEngine()
        self._capital = CapitalAllocationEngine()

    @property
    def version(self) -> str:
        return self._version

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    def create_shell_analysis(
        self,
        *,
        company: str = "",
        ticker: str = "",
    ) -> BusinessQualityAnalysis:
        """Return an empty immutable analysis shell (framework placeholder)."""
        return BusinessQualityAnalysis(
            metadata=BusinessQualityMetadata(
                engine_version=self._version,
                framework_version=FRAMEWORK_VERSION,
                company=company,
                ticker=ticker,
                modules_composed=("business_quality_framework",),
            ),
            validation=empty_validation(ok=True),
            score=None,
            summary=BusinessQualitySummary(
                headline="Business Quality Framework shell (no full suite yet)",
            ),
            quality_flags=(),
            explainability=(),
            research_disclaimer=RESEARCH_DISCLAIMER,
        )

    def analyze_earnings_quality(
        self, financial_analysis: Any
    ) -> EarningsQualityAnalysis:
        """Run Earnings Quality Intelligence (F3.2)."""
        return self._earnings.analyze(financial_analysis)

    def analyze_capital_allocation(
        self, financial_analysis: Any
    ) -> CapitalAllocationAnalysis:
        """Run Capital Allocation Intelligence (F3.3)."""
        return self._capital.analyze(financial_analysis)

    def analyze(self, financial_analysis: Any) -> BusinessQualityAnalysis:
        """Primary entry: compose Earnings Quality + Capital Allocation."""
        eq = self.analyze_earnings_quality(financial_analysis)
        ca = self.analyze_capital_allocation(financial_analysis)

        parts: list[tuple[float, float]] = []
        if eq.overall_score and eq.overall_score.value is not None:
            parts.append((eq.overall_score.value / 100.0, 1.0))
        if ca.overall_score and ca.overall_score.value is not None:
            parts.append((ca.overall_score.value / 100.0, 1.0))
        overall_01 = weighted_mean(parts)
        overall_score = (
            Score(value=None if overall_01 is None else overall_01 * 100.0)
        )
        overall_rating = _rating_from_01(overall_01)
        confidence = _aggregate_confidence([eq.confidence, ca.confidence])
        bq_flag = _map_rating_to_bq_flag(overall_rating)

        assessments = tuple(eq.assessments) + tuple(ca.assessments)
        validation = merge_validation_results([eq.validation, ca.validation])
        strengths = _strengths(eq, ca)
        weaknesses = _weaknesses(eq, ca)
        observations = tuple(
            dict.fromkeys(list(eq.evidence[:4]) + list(ca.evidence[:4]))
        )

        return BusinessQualityAnalysis(
            metadata=BusinessQualityMetadata(
                engine_version=self._version,
                framework_version=FRAMEWORK_VERSION,
                company=eq.metadata.company or ca.metadata.company,
                ticker=eq.metadata.ticker or ca.metadata.ticker,
                modules_composed=(
                    "business_quality_framework",
                    "earnings_quality_intelligence",
                    "capital_allocation_intelligence",
                ),
            ),
            validation=validation,
            score=BusinessQualityScore(
                overall=overall_score,
                rating=overall_rating,
                confidence=confidence,
                assessments=assessments,
            ),
            summary=BusinessQualitySummary(
                headline=(
                    f"Business quality: {overall_rating.value} "
                    f"(EQ={eq.overall_rating.value}, CA={ca.overall_rating.value})"
                ),
                strengths=strengths,
                weaknesses=weaknesses,
                key_observations=observations,
                flag=bq_flag,
            ),
            quality_flags=(bq_flag,),
            explainability=tuple(eq.explainability) + tuple(ca.explainability),
            research_disclaimer=(
                f"{eq.research_disclaimer} {ca.research_disclaimer}"
            ),
        )


def _map_rating_to_bq_flag(rating: Rating) -> BusinessQualityFlag:
    mapping = {
        Rating.EXCELLENT: BusinessQualityFlag.EXCELLENT,
        Rating.STRONG: BusinessQualityFlag.STRONG,
        Rating.AVERAGE: BusinessQualityFlag.AVERAGE,
        Rating.WEAK: BusinessQualityFlag.WEAK,
        Rating.POOR: BusinessQualityFlag.POOR,
        Rating.UNKNOWN: BusinessQualityFlag.UNKNOWN,
        Rating.INSUFFICIENT_DATA: BusinessQualityFlag.INSUFFICIENT_DATA,
    }
    return mapping.get(rating, BusinessQualityFlag.UNKNOWN)


def _strengths(eq: EarningsQualityAnalysis, ca: CapitalAllocationAnalysis) -> tuple[str, ...]:
    out: list[str] = []
    for f in eq.quality_flags:
        if f.value in {
            "high_earnings_quality",
            "cash_supported_earnings",
            "recurring_earnings",
            "stable_margins",
        }:
            out.append(f"Earnings quality flag: {f.value}")
    for f in ca.quality_flags:
        if f.value in {
            "excellent_capital_allocation",
            "disciplined_reinvestment",
            "shareholder_friendly",
            "healthy_cash_deployment",
        }:
            out.append(f"Capital allocation flag: {f.value}")
    return tuple(out)


def _weaknesses(eq: EarningsQualityAnalysis, ca: CapitalAllocationAnalysis) -> tuple[str, ...]:
    out: list[str] = []
    for f in eq.quality_flags:
        if f.value in {
            "aggressive_accounting_risk",
            "weak_cash_support",
            "volatile_earnings",
            "high_accrual_risk",
        }:
            out.append(f"Earnings quality flag: {f.value}")
    for f in ca.quality_flags:
        if f.value in {
            "excessive_capital_spending",
            "weak_capital_allocation",
            "debt_dependent",
            "dividend_at_risk",
            "inconsistent_allocation",
        }:
            out.append(f"Capital allocation flag: {f.value}")
    return tuple(out)
