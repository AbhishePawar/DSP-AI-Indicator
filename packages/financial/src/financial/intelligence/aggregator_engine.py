"""Financial Statement Aggregator engine (F2.7).

Pure orchestration over F2.2–F2.6 engines — no duplicated financial math.
"""

from __future__ import annotations

from typing import Sequence

from financial.intelligence.aggregator_explainability import (
    AGGREGATOR_RESEARCH_DISCLAIMER,
    MetricExplanation,
    build_explanation,
)
from financial.intelligence.aggregator_models import (
    AggregatedQualityFlag,
    FinancialAnalysis,
    FinancialAnalysisMetadata,
    OverallFinancialSummary,
)
from financial.intelligence.aggregator_validation import (
    coerce_aggregation_source,
    validate_aggregation_inputs,
)
from financial.intelligence.balance_engine import BalanceSheetEngine
from financial.intelligence.balance_models import BalanceQualityFlag
from financial.intelligence.cashflow_engine import CashFlowEngine
from financial.intelligence.cashflow_models import CashFlowQualityFlag
from financial.intelligence.income_engine import IncomeStatementEngine
from financial.intelligence.income_models import QualityFlag
from financial.intelligence.ratio_engine import FinancialRatioEngine
from financial.intelligence.ratio_models import RatioQualityFlag
from financial.intelligence.trend_engine import TrendEngine
from financial.intelligence.trend_models import (
    FinancialStatementsHistory,
    TrendAnalysis,
    TrendQualityFlag,
)
from financial.models import FinancialStatements
from financial.validation import ValidationResult

__all__ = ["FinancialAggregatorEngine", "AGGREGATOR_VERSION"]

AGGREGATOR_VERSION = "0.7.0-aggregator"


class FinancialAggregatorEngine:
    """Compose F2.2–F2.6 analyses into one ``FinancialAnalysis``."""

    def __init__(self) -> None:
        self._income = IncomeStatementEngine()
        self._balance = BalanceSheetEngine()
        self._cash = CashFlowEngine()
        self._ratio = FinancialRatioEngine()
        self._trend = TrendEngine()

    def analyze(
        self,
        source: FinancialStatements
        | FinancialStatementsHistory
        | Sequence[FinancialStatements],
    ) -> FinancialAnalysis:
        """Run full financial statement aggregation."""
        stmts, meta = coerce_aggregation_source(source)
        validation = validate_aggregation_inputs(stmts)

        primary = stmts[-1]
        history = stmts[:-1] if len(stmts) > 1 else None

        income = self._income.analyze(
            primary, history=history if history else None
        )
        balance = self._balance.analyze(
            primary, history=history if history else None
        )
        cash = self._cash.analyze(
            primary, history=history if history else None
        )
        ratios = self._ratio.analyze(
            primary, history=history if history else None
        )

        trends: TrendAnalysis | None = None
        if len(stmts) >= 2:
            trends = self._trend.analyze(
                FinancialStatementsHistory(statements=tuple(stmts))
            )

        flags = self._aggregate_flags(income, balance, cash, ratios, trends)
        summary = self._summary(
            income, balance, cash, ratios, trends, validation, flags
        )
        explainability = self._compose_explainability(
            income, balance, cash, ratios, trends, flags, summary
        )

        modules = [
            "income_statement_intelligence",
            "balance_sheet_intelligence",
            "cash_flow_intelligence",
            "financial_ratio_engine",
        ]
        if trends is not None:
            modules.append("trend_time_series_intelligence")

        metadata = FinancialAnalysisMetadata(
            engine_version=AGGREGATOR_VERSION,
            periods_used=len(stmts),
            period_ends=tuple(meta.get("period_ends") or ()),
            company=str(meta.get("company") or ""),
            ticker=str(meta.get("ticker") or ""),
            modules_composed=tuple(modules),
            trend_included=trends is not None,
        )
        return FinancialAnalysis(
            metadata=metadata,
            validation=validation,
            income=income,
            balance_sheet=balance,
            cash_flow=cash,
            ratios=ratios,
            trends=trends,
            overall_summary=summary,
            quality_flags=flags,
            explainability=explainability,
            research_disclaimer=AGGREGATOR_RESEARCH_DISCLAIMER,
        )

    def _aggregate_flags(
        self,
        income,
        balance,
        cash,
        ratios,
        trends: TrendAnalysis | None,
    ) -> tuple[AggregatedQualityFlag, ...]:
        """Map existing module flags → aggregated summaries (no new math)."""
        inc = set(income.quality_flags)
        bal = set(balance.quality_flags)
        cf = set(cash.quality_flags)
        rat = set(ratios.quality_flags)
        tr = set(trends.quality_flags) if trends is not None else set()

        out: list[AggregatedQualityFlag] = []

        liquidity_concern = (
            BalanceQualityFlag.WEAK_LIQUIDITY in bal
            or RatioQualityFlag.WEAK_LIQUIDITY in rat
            or BalanceQualityFlag.WORKING_CAPITAL_PRESSURE in bal
        )
        leverage_concern = (
            BalanceQualityFlag.EXCESSIVE_LEVERAGE in bal
            or RatioQualityFlag.HIGH_LEVERAGE in rat
            or TrendQualityFlag.DEBT_INCREASING in tr
        )
        cash_concern = (
            CashFlowQualityFlag.WEAK_CASH_GENERATION in cf
            or CashFlowQualityFlag.CASH_FLOW_WARNING in cf
            or CashFlowQualityFlag.NEGATIVE_FREE_CASH_FLOW in cf
            or RatioQualityFlag.WEAK_CASH_GENERATION in rat
        )
        deterioration = (
            TrendQualityFlag.DETERIORATING_BUSINESS in tr
            or QualityFlag.DECLINING_REVENUE in inc
            or TrendQualityFlag.MARGIN_COMPRESSION in tr
            or QualityFlag.MARGIN_COMPRESSION in inc
        )
        improving = (
            TrendQualityFlag.IMPROVING_BUSINESS in tr
            or QualityFlag.HEALTHY_GROWTH in inc
            or TrendQualityFlag.MARGIN_EXPANSION in tr
            or QualityFlag.MARGIN_EXPANSION in inc
            or TrendQualityFlag.CASH_FLOW_IMPROVING in tr
        )
        compounder = TrendQualityFlag.CONSISTENT_COMPOUNDER in tr or (
            TrendQualityFlag.STABLE_COMPOUND_GROWTH in tr
        )

        positive_core = (
            (
                BalanceQualityFlag.HEALTHY_BALANCE_SHEET in bal
                or BalanceQualityFlag.STRONG_LIQUIDITY in bal
                or RatioQualityFlag.STRONG_LIQUIDITY in rat
            )
            and (
                CashFlowQualityFlag.STRONG_CASH_GENERATION in cf
                or CashFlowQualityFlag.EXCELLENT_CASH_QUALITY in cf
                or RatioQualityFlag.STRONG_CASH_GENERATION in rat
            )
            and (
                RatioQualityFlag.EXCELLENT_PROFITABILITY in rat
                or QualityFlag.STRONG_EARNINGS_QUALITY in inc
            )
        )
        healthy = (
            BalanceQualityFlag.HEALTHY_BALANCE_SHEET in bal
            or BalanceQualityFlag.STRONG_EQUITY_BASE in bal
            or RatioQualityFlag.LOW_LEVERAGE in rat
            or CashFlowQualityFlag.HEALTHY_CAPITAL_ALLOCATION in cf
        ) and not (liquidity_concern or leverage_concern or cash_concern)

        if liquidity_concern:
            out.append(AggregatedQualityFlag.LIQUIDITY_CONCERN)
        if leverage_concern:
            out.append(AggregatedQualityFlag.LEVERAGE_CONCERN)
        if cash_concern:
            out.append(AggregatedQualityFlag.CASH_FLOW_CONCERN)
        if deterioration:
            out.append(AggregatedQualityFlag.FINANCIAL_DETERIORATION)
        if improving and not deterioration:
            out.append(AggregatedQualityFlag.IMPROVING_FUNDAMENTALS)
        if compounder:
            out.append(AggregatedQualityFlag.CONSISTENT_COMPOUNDER)

        if positive_core and not (
            liquidity_concern or leverage_concern or cash_concern or deterioration
        ):
            out.append(AggregatedQualityFlag.EXCELLENT_FINANCIAL_HEALTH)
        elif healthy and not deterioration:
            out.append(AggregatedQualityFlag.HEALTHY_FINANCIAL_POSITION)

        attention = (
            liquidity_concern
            or leverage_concern
            or cash_concern
            or deterioration
            or BalanceQualityFlag.BALANCE_SHEET_WARNING in bal
            or RatioQualityFlag.CAPITAL_ALLOCATION_WARNING in rat
            or RatioQualityFlag.WEAK_PROFITABILITY in rat
            or QualityFlag.WEAK_EARNINGS_QUALITY in inc
        )
        if attention:
            out.append(AggregatedQualityFlag.NEEDS_ATTENTION)

        return tuple(dict.fromkeys(out))

    def _summary(
        self,
        income,
        balance,
        cash,
        ratios,
        trends: TrendAnalysis | None,
        validation: ValidationResult,
        flags: tuple[AggregatedQualityFlag, ...],
    ) -> OverallFinancialSummary:
        strengths: list[str] = []
        weaknesses: list[str] = []
        observations: list[str] = []

        flag_set = set(flags)
        strength_map = {
            AggregatedQualityFlag.EXCELLENT_FINANCIAL_HEALTH: (
                "Cross-module signals indicate excellent financial health."
            ),
            AggregatedQualityFlag.HEALTHY_FINANCIAL_POSITION: (
                "Balance sheet / capital structure signals are healthy."
            ),
            AggregatedQualityFlag.CONSISTENT_COMPOUNDER: (
                "Trend intelligence flags consistent compound growth."
            ),
            AggregatedQualityFlag.IMPROVING_FUNDAMENTALS: (
                "Fundamentals show improving directional signals."
            ),
        }
        weakness_map = {
            AggregatedQualityFlag.LIQUIDITY_CONCERN: (
                "Liquidity concern raised by balance/ratio flags."
            ),
            AggregatedQualityFlag.LEVERAGE_CONCERN: (
                "Leverage concern raised by balance/ratio/trend flags."
            ),
            AggregatedQualityFlag.CASH_FLOW_CONCERN: (
                "Cash flow concern raised by cash-flow/ratio flags."
            ),
            AggregatedQualityFlag.FINANCIAL_DETERIORATION: (
                "Deterioration signals present in income/trend flags."
            ),
            AggregatedQualityFlag.NEEDS_ATTENTION: (
                "One or more module warning flags require attention."
            ),
        }
        for flag, text in strength_map.items():
            if flag in flag_set:
                strengths.append(text)
        for flag, text in weakness_map.items():
            if flag in flag_set:
                weaknesses.append(text)

        if trends is not None and trends.trend_summary.insights:
            observations.extend(trends.trend_summary.insights)
        observations.append(
            f"Revenue trend class: {income.revenue.trend_class.value}."
        )
        observations.append(
            f"Balance liquidity trend: {balance.trend_summary.liquidity.value}."
        )
        if cash.quality_flags:
            observations.append(
                "Cash-flow quality flags: "
                + ", ".join(f.value for f in cash.quality_flags[:5])
                + "."
            )
        if ratios.quality_flags:
            observations.append(
                "Ratio quality flags: "
                + ", ".join(f.value for f in ratios.quality_flags[:5])
                + "."
            )

        warn_n = len(validation.warnings)
        if warn_n == 0:
            completeness = "complete"
        elif warn_n <= 2:
            completeness = "mostly_complete"
        else:
            completeness = "partial"

        confidences: list[str] = []
        for block in (
            getattr(income.metadata, "confidence", None),
            getattr(balance.metadata, "confidence", None),
            getattr(cash.metadata, "confidence", None),
            getattr(ratios.metadata, "confidence", None),
        ):
            if isinstance(block, str):
                confidences.append(block)
        if trends is not None:
            rev = next(
                (t for t in trends.revenue_trends if t.name == "revenue"),
                None,
            )
            if rev is not None:
                confidences.append(rev.confidence)
        rank = {"high": 3, "medium": 2, "low": 1, "insufficient": 0}
        if confidences:
            avg = sum(rank.get(c, 0) for c in confidences) / len(confidences)
            if avg >= 2.5:
                confidence_summary = "high"
            elif avg >= 1.5:
                confidence_summary = "medium"
            elif avg >= 0.5:
                confidence_summary = "low"
            else:
                confidence_summary = "insufficient"
        else:
            confidence_summary = "medium" if warn_n == 0 else "low"

        if AggregatedQualityFlag.EXCELLENT_FINANCIAL_HEALTH in flag_set:
            health = "excellent_financial_health"
        elif AggregatedQualityFlag.HEALTHY_FINANCIAL_POSITION in flag_set:
            health = "healthy_financial_position"
        elif AggregatedQualityFlag.FINANCIAL_DETERIORATION in flag_set:
            health = "financial_deterioration"
        else:
            health = "needs_attention"

        return OverallFinancialSummary(
            strengths=tuple(strengths),
            weaknesses=tuple(weaknesses),
            key_observations=tuple(dict.fromkeys(observations)),
            data_completeness=completeness,
            confidence_summary=confidence_summary,
            health_label=health,
        )

    def _compose_explainability(
        self,
        income,
        balance,
        cash,
        ratios,
        trends: TrendAnalysis | None,
        flags: tuple[AggregatedQualityFlag, ...],
        summary: OverallFinancialSummary,
    ) -> tuple[MetricExplanation, ...]:
        """Preserve module explainability + aggregator composition record."""
        records: list[MetricExplanation] = []
        records.extend(income.explainability)
        records.extend(balance.explainability)
        records.extend(cash.explainability)
        records.extend(ratios.explainability)
        if trends is not None:
            records.extend(trends.explainability)

        records.append(
            build_explanation(
                name="aggregated_quality_flags",
                formula="boolean composition of F2.2–F2.6 quality flags",
                inputs={
                    "income_flags": [f.value for f in income.quality_flags],
                    "balance_flags": [f.value for f in balance.quality_flags],
                    "cash_flow_flags": [f.value for f in cash.quality_flags],
                    "ratio_flags": [f.value for f in ratios.quality_flags],
                    "trend_flags": (
                        [f.value for f in trends.quality_flags]
                        if trends is not None
                        else []
                    ),
                },
                intermediates={},
                result=None,
                confidence=summary.confidence_summary,
                interpretation=(
                    "Aggregated flags: "
                    + (", ".join(f.value for f in flags) if flags else "none")
                ),
                limitations=(
                    "Aggregator does not invent new metrics; flags are "
                    "derived solely from existing module outputs."
                ),
            )
        )
        records.append(
            build_explanation(
                name="overall_financial_summary",
                formula="template composition from module flags + insights",
                inputs={
                    "strengths": list(summary.strengths),
                    "weaknesses": list(summary.weaknesses),
                },
                intermediates={
                    "data_completeness": summary.data_completeness,
                    "health_label": summary.health_label,
                },
                result=None,
                confidence=summary.confidence_summary,
                interpretation=(
                    f"Health label={summary.health_label}; "
                    f"completeness={summary.data_completeness}."
                ),
                limitations="Narrative only; not a scoring model or forecast.",
            )
        )
        return tuple(records)
