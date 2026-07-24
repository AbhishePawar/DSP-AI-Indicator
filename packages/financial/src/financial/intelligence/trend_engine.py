"""Trend & Time-Series Intelligence engine (F2.6).

Reuses Income / Balance / Cash Flow / Ratio intelligence outputs.
Adds only multi-period trend / consistency math — no duplicated line-item ratios.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Sequence

from financial.intelligence.balance_engine import BalanceSheetEngine
from financial.intelligence.cashflow_engine import CashFlowEngine
from financial.intelligence.income_engine import IncomeStatementEngine
from financial.intelligence.ratio_engine import FinancialRatioEngine
from financial.intelligence.trend_explainability import (
    TREND_RESEARCH_DISCLAIMER,
    MetricExplanation,
    build_explanation,
)
from financial.intelligence.trend_models import (
    FinancialStatementsHistory,
    MetricTrend,
    TrendAnalysis,
    TrendAnalysisMetadata,
    TrendClass,
    TrendConsistencyMetrics,
    TrendQualityFlag,
    TrendSummary,
)
from financial.intelligence.trend_validation import (
    coerce_trend_history,
    validate_trend_history,
)
from financial.models import FinancialSnapshot, FinancialStatements

__all__ = ["TrendEngine", "TREND_INTELLIGENCE_VERSION"]

TREND_INTELLIGENCE_VERSION = "0.6.0-trend"


def _growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior)


def _cagr(start: float | None, end: float | None, periods: int) -> float | None:
    if start is None or end is None or periods <= 0:
        return None
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1.0 / periods) - 1.0


def _stability(values: Sequence[float]) -> float | None:
    clean = [v for v in values if math.isfinite(v)]
    if len(clean) < 2:
        return None
    mean = statistics.fmean(clean)
    if mean == 0:
        return 1.0 if all(v == 0 for v in clean) else 0.0
    cv = abs(statistics.pstdev(clean) / mean)
    return 1.0 / (1.0 + cv)


def _clip01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _confidence(n: int, *, has_value: bool) -> str:
    if not has_value:
        return "insufficient"
    if n >= 5:
        return "high"
    if n >= 3:
        return "medium"
    return "low"


def _growth_rates(series: Sequence[float | None]) -> list[float]:
    rates: list[float] = []
    for i in range(1, len(series)):
        g = _growth(series[i], series[i - 1])
        if g is not None:
            rates.append(g)
    return rates


def _classify(
    series: Sequence[float | None],
    *,
    higher_better: bool = True,
) -> TrendClass:
    rates = _growth_rates(series)
    if not rates:
        return TrendClass.INSUFFICIENT
    stab = _stability(rates)
    if stab is not None and stab < 0.35 and len(rates) >= 3:
        return TrendClass.HIGHLY_VOLATILE
    latest = rates[-1]
    # Flip for lower-is-better series (e.g. debt)
    signed = latest if higher_better else -latest
    if abs(signed) < 0.01:
        return TrendClass.STABLE
    if signed >= 0.08:
        return TrendClass.STRONGLY_IMPROVING
    if signed > 0.02:
        return TrendClass.IMPROVING
    if signed <= -0.08:
        return TrendClass.STRONGLY_WEAKENING
    return TrendClass.WEAKENING


def _ratio_value(analysis, name: str) -> float | None:
    for group in (
        analysis.profitability,
        analysis.liquidity,
        analysis.leverage,
        analysis.efficiency,
        analysis.cash_flow,
        analysis.shareholder,
    ):
        for m in group:
            if m.name == name:
                return m.value
    return None


class TrendEngine:
    """Multi-period trend analysis composed from F2.2–F2.5 engines."""

    def __init__(self) -> None:
        self._income = IncomeStatementEngine()
        self._balance = BalanceSheetEngine()
        self._cash = CashFlowEngine()
        self._ratio = FinancialRatioEngine()

    def analyze(
        self,
        source: FinancialStatementsHistory
        | FinancialSnapshot
        | dict
        | Sequence[FinancialStatements],
    ) -> TrendAnalysis:
        """Run Trend & Time-Series Intelligence."""
        stmts, meta = coerce_trend_history(source)
        validation = validate_trend_history(stmts)

        # Per-period reuse of prior intelligence (absolute metrics).
        # Trend/CAGR/consistency math is owned by this engine — avoids O(n²)
        # expanding-window recompute while still composing F2.2–F2.5 outputs.
        income_series = []
        balance_series = []
        cash_series = []
        ratio_series = []
        for stmt in stmts:
            income_series.append(self._income.analyze(stmt))
            balance_series.append(self._balance.analyze(stmt))
            cash_series.append(self._cash.analyze(stmt))
            ratio_series.append(self._ratio.analyze(stmt))

        explanations: list[MetricExplanation] = []

        revenue_trends = self._build_family(
            {
                "revenue": [a.revenue.revenue for a in income_series],
                "revenue_growth": [a.revenue.revenue_growth for a in income_series],
            },
            explanations,
            higher_better={"revenue": True, "revenue_growth": True},
            cagr_keys={"revenue"},
        )
        revenue_trends = self._enrich_revenue(revenue_trends, income_series, explanations)

        profitability_trends = self._build_family(
            {
                "gross_margin": [a.margins.gross_margin for a in income_series],
                "operating_margin": [a.margins.operating_margin for a in income_series],
                "net_margin": [a.margins.net_margin for a in income_series],
                "ebit": [s.income_statement.ebit for s in stmts],
                "ebitda": [s.income_statement.ebitda for s in stmts],
                "roe": [_ratio_value(r, "roe") for r in ratio_series],
                "roa": [_ratio_value(r, "roa") for r in ratio_series],
                "roic": [_ratio_value(r, "roic") for r in ratio_series],
            },
            explanations,
            higher_better={
                "gross_margin": True,
                "operating_margin": True,
                "net_margin": True,
                "ebit": True,
                "ebitda": True,
                "roe": True,
                "roa": True,
                "roic": True,
            },
            cagr_keys={"ebit", "ebitda"},
        )

        cash_flow_trends = self._build_family(
            {
                "operating_cash_flow": [
                    a.operating.operating_cash_flow for a in cash_series
                ],
                "free_cash_flow": [a.free_cash_flow.free_cash_flow for a in cash_series],
                "cash_conversion": [a.operating.cash_conversion for a in cash_series],
                "capex": [a.investing.capex for a in cash_series],
                "dividends_paid": [a.financing.dividends_paid for a in cash_series],
            },
            explanations,
            higher_better={
                "operating_cash_flow": True,
                "free_cash_flow": True,
                "cash_conversion": True,
                "capex": False,
                "dividends_paid": True,
            },
        )

        asset_series = [s.balance_sheet.total_assets for s in stmts]
        balance_sheet_trends = self._build_family(
            {
                "net_debt": [a.leverage.net_debt for a in balance_series],
                "cash": [a.working_capital.cash_position for a in balance_series],
                "book_value": [a.equity.book_value for a in balance_series],
                "working_capital": [a.liquidity.working_capital for a in balance_series],
                "total_assets": asset_series,
                "equity": [a.equity.book_value for a in balance_series],
            },
            explanations,
            higher_better={
                "net_debt": False,
                "cash": True,
                "book_value": True,
                "working_capital": True,
                "total_assets": True,
                "equity": True,
            },
            cagr_keys={"total_assets", "book_value", "equity"},
        )

        ratio_trends = self._build_family(
            {
                "current_ratio": [_ratio_value(r, "current_ratio") for r in ratio_series],
                "debt_to_equity": [_ratio_value(r, "debt_to_equity") for r in ratio_series],
                "asset_turnover": [_ratio_value(r, "asset_turnover") for r in ratio_series],
                "net_margin": [_ratio_value(r, "net_margin") for r in ratio_series],
                "capital_allocation_score": [
                    r.capital_allocation.capital_allocation_score for r in ratio_series
                ],
            },
            explanations,
            higher_better={
                "current_ratio": True,
                "debt_to_equity": False,
                "asset_turnover": True,
                "net_margin": True,
                "capital_allocation_score": True,
            },
        )

        consistency = self._consistency(
            revenue_trends, profitability_trends, cash_flow_trends, explanations
        )
        flags = self._flags(
            revenue_trends,
            profitability_trends,
            cash_flow_trends,
            balance_sheet_trends,
            consistency,
        )
        summary = self._summary(
            revenue_trends,
            profitability_trends,
            cash_flow_trends,
            balance_sheet_trends,
            ratio_trends,
            stmts,
            explanations,
        )
        metadata = TrendAnalysisMetadata(
            engine_version=TREND_INTELLIGENCE_VERSION,
            periods_used=len(stmts),
            period_ends=tuple(meta.get("period_ends") or ()),
            company=str(meta.get("company") or ""),
            ticker=str(meta.get("ticker") or ""),
        )
        return TrendAnalysis(
            revenue_trends=revenue_trends,
            profitability_trends=profitability_trends,
            cash_flow_trends=cash_flow_trends,
            balance_sheet_trends=balance_sheet_trends,
            ratio_trends=ratio_trends,
            consistency=consistency,
            quality_flags=flags,
            trend_summary=summary,
            validation=validation,
            explainability=tuple(explanations),
            metadata=metadata,
            research_disclaimer=TREND_RESEARCH_DISCLAIMER,
        )

    def _build_family(
        self,
        series_map: dict[str, list[float | None]],
        out: list[MetricExplanation],
        *,
        higher_better: dict[str, bool],
        cagr_keys: set[str] | None = None,
    ) -> tuple[MetricTrend, ...]:
        cagr_keys = cagr_keys or set()
        trends: list[MetricTrend] = []
        for name, series in series_map.items():
            hb = higher_better.get(name, True)
            rates = _growth_rates(series)
            latest_growth = rates[-1] if rates else None
            accel = (rates[-1] - rates[-2]) if len(rates) >= 2 else None
            consistency = _stability(rates) if rates else None
            clean = [v for v in series if v is not None]
            cagr = None
            if name in cagr_keys and len(clean) >= 2:
                cagr = _cagr(clean[0], clean[-1], len(clean) - 1)
            cls = _classify(series, higher_better=hb)
            conf = _confidence(len(series), has_value=latest_growth is not None or len(clean) >= 2)
            interp = (
                f"{name}: {cls.value}"
                if cls is not TrendClass.INSUFFICIENT
                else f"{name}: insufficient history"
            )
            method = (
                "growth/CAGR/stability over per-period F2.2–F2.5 intelligence outputs"
            )
            intermediates = {
                "growth_rates": rates,
                "acceleration": accel,
                "stability": consistency,
            }
            out.append(
                build_explanation(
                    name=f"trend_{name}",
                    formula=method,
                    inputs={"values": list(series)},
                    intermediates=intermediates,
                    result=latest_growth if latest_growth is not None else cagr,
                    confidence=conf,
                    interpretation=interp,
                    limitations="Reuses F2.2–F2.5 outputs; does not recompute statement ratios.",
                )
            )
            trends.append(
                MetricTrend(
                    name=name,
                    values=tuple(series),
                    latest_growth=latest_growth,
                    cagr=cagr,
                    classification=cls,
                    consistency=consistency,
                    acceleration=accel,
                    confidence=conf,
                    interpretation=interp,
                    method=method,
                    intermediates=intermediates,
                    limitations="Reuses prior intelligence outputs only.",
                )
            )
        return tuple(trends)

    def _enrich_revenue(
        self,
        trends: tuple[MetricTrend, ...],
        income_series: list,
        out: list[MetricExplanation],
    ) -> tuple[MetricTrend, ...]:
        # Growth consistency / acceleration from trend-owned revenue growth series
        rev_values = [a.revenue.revenue for a in income_series]
        growth_series: list[float | None] = [None]
        for i in range(1, len(rev_values)):
            growth_series.append(_growth(rev_values[i], rev_values[i - 1]))
        rates = [g for g in growth_series if g is not None]
        consistency = _stability(rates) if len(rates) >= 2 else None
        accel = None
        if len(rates) >= 2:
            accel = rates[-1] - rates[-2]
        # Attach as additional MetricTrend entries
        n = len(income_series)
        accel_series: list[float | None] = [None] * n
        for i in range(1, n):
            if growth_series[i] is None or growth_series[i - 1] is None:
                accel_series[i] = None
            else:
                accel_series[i] = growth_series[i] - growth_series[i - 1]
        stability_series: list[float | None] = [None] * n
        for i in range(1, n):
            partial = [g for g in growth_series[1 : i + 1] if g is not None]
            stability_series[i] = (
                _stability(partial) if len(partial) >= 2 else None
            )
        extra = self._build_family(
            {
                "growth_consistency": growth_series,
                "revenue_stability": stability_series,
                "growth_acceleration": accel_series,
            },
            out,
            higher_better={
                "growth_consistency": True,
                "revenue_stability": True,
                "growth_acceleration": True,
            },
        )
        # Patch revenue trend with acceleration annotation
        patched: list[MetricTrend] = []
        for t in trends:
            if t.name == "revenue":
                patched.append(
                    MetricTrend(
                        name=t.name,
                        values=t.values,
                        latest_growth=t.latest_growth,
                        cagr=t.cagr,
                        classification=t.classification,
                        consistency=consistency if consistency is not None else t.consistency,
                        acceleration=accel if accel is not None else t.acceleration,
                        confidence=t.confidence,
                        interpretation=t.interpretation
                        + (
                            f"; acceleration={accel:.4f}"
                            if accel is not None
                            else ""
                        ),
                        method=t.method,
                        intermediates={**dict(t.intermediates), "growth_consistency": consistency},
                        limitations=t.limitations,
                    )
                )
            else:
                patched.append(t)
        return tuple(list(patched) + list(extra))

    def _consistency(
        self,
        revenue: tuple[MetricTrend, ...],
        profitability: tuple[MetricTrend, ...],
        cash: tuple[MetricTrend, ...],
        out: list[MetricExplanation],
    ) -> TrendConsistencyMetrics:
        cons_vals = [
            t.consistency
            for group in (revenue, profitability, cash)
            for t in group
            if t.consistency is not None
        ]
        consistency_score = (
            sum(cons_vals) / len(cons_vals) if cons_vals else None
        )
        volatility_score = (
            _clip01(1.0 - consistency_score) if consistency_score is not None else None
        )
        # Stability: share of STABLE/IMPROVING classifications
        classes = [
            t.classification
            for group in (revenue, profitability, cash)
            for t in group
        ]
        if classes:
            stable_like = sum(
                1
                for c in classes
                if c
                in (
                    TrendClass.STABLE,
                    TrendClass.IMPROVING,
                    TrendClass.STRONGLY_IMPROVING,
                )
            )
            stability_score = stable_like / len(classes)
        else:
            stability_score = None
        # Persistence: consecutive same-direction growth signs
        rev = next((t for t in revenue if t.name == "revenue"), None)
        persistence = None
        if rev is not None:
            rates = _growth_rates(rev.values)
            if rates:
                sign = 1 if rates[0] >= 0 else -1
                run = 1
                for r in rates[1:]:
                    s = 1 if r >= 0 else -1
                    if s == sign:
                        run += 1
                    else:
                        break
                persistence = run / len(rates)
        predictability = None
        parts = [p for p in (consistency_score, stability_score, persistence) if p is not None]
        if parts:
            predictability = sum(parts) / len(parts)
        out.append(
            build_explanation(
                name="consistency_metrics",
                formula="mean(metric consistencies); volatility=1-consistency",
                inputs={"consistency_samples": cons_vals},
                intermediates={
                    "stability_score": stability_score,
                    "persistence": persistence,
                },
                result=consistency_score,
                confidence=_confidence(len(cons_vals), has_value=consistency_score is not None),
                interpretation=(
                    "Consistency unavailable."
                    if consistency_score is None
                    else f"Consistency score = {consistency_score:.4f}."
                ),
                limitations="Research heuristic over reused intelligence series.",
            )
        )
        return TrendConsistencyMetrics(
            consistency_score=consistency_score,
            volatility_score=volatility_score,
            stability_score=stability_score,
            persistence_score=persistence,
            financial_predictability=predictability,
        )

    def _flags(
        self,
        revenue: tuple[MetricTrend, ...],
        profitability: tuple[MetricTrend, ...],
        cash: tuple[MetricTrend, ...],
        balance: tuple[MetricTrend, ...],
        consistency: TrendConsistencyMetrics,
    ) -> tuple[TrendQualityFlag, ...]:
        flags: list[TrendQualityFlag] = []
        rev = next((t for t in revenue if t.name == "revenue"), None)
        nm = next((t for t in profitability if t.name == "net_margin"), None)
        fcf = next((t for t in cash if t.name == "free_cash_flow"), None)
        debt = next((t for t in balance if t.name == "net_debt"), None)

        if rev and rev.classification in (
            TrendClass.IMPROVING,
            TrendClass.STRONGLY_IMPROVING,
        ):
            if (rev.consistency or 0) >= 0.55 and (rev.cagr or 0) > 0:
                flags.append(TrendQualityFlag.CONSISTENT_COMPOUNDER)
                flags.append(TrendQualityFlag.STABLE_COMPOUND_GROWTH)
            flags.append(TrendQualityFlag.IMPROVING_BUSINESS)
        if rev and rev.classification in (
            TrendClass.WEAKENING,
            TrendClass.STRONGLY_WEAKENING,
        ):
            flags.append(TrendQualityFlag.DETERIORATING_BUSINESS)

        if nm and nm.latest_growth is not None:
            if nm.latest_growth > 0.01:
                flags.append(TrendQualityFlag.MARGIN_EXPANSION)
            elif nm.latest_growth < -0.01:
                flags.append(TrendQualityFlag.MARGIN_COMPRESSION)

        if fcf and fcf.classification in (
            TrendClass.IMPROVING,
            TrendClass.STRONGLY_IMPROVING,
        ):
            flags.append(TrendQualityFlag.CASH_FLOW_IMPROVING)

        if debt and debt.latest_growth is not None:
            # net_debt higher_better=False → positive growth means debt rising
            if debt.latest_growth > 0.02:
                flags.append(TrendQualityFlag.DEBT_INCREASING)
            elif debt.latest_growth < -0.02:
                flags.append(TrendQualityFlag.DEBT_REDUCING)

        if (consistency.volatility_score or 0) >= 0.55:
            flags.append(TrendQualityFlag.HIGH_VOLATILITY)
        for group in (revenue, profitability, cash, balance):
            if any(t.classification is TrendClass.HIGHLY_VOLATILE for t in group):
                flags.append(TrendQualityFlag.HIGH_VOLATILITY)
                break

        return tuple(dict.fromkeys(flags))

    def _summary(
        self,
        revenue: tuple[MetricTrend, ...],
        profitability: tuple[MetricTrend, ...],
        cash: tuple[MetricTrend, ...],
        balance: tuple[MetricTrend, ...],
        ratios: tuple[MetricTrend, ...],
        stmts: Sequence[FinancialStatements],
        out: list[MetricExplanation],
    ) -> TrendSummary:
        def _dom(group: tuple[MetricTrend, ...]) -> TrendClass:
            if not group:
                return TrendClass.INSUFFICIENT
            # Prefer primary metric when present
            return group[0].classification

        rev_c = _dom(tuple(t for t in revenue if t.name == "revenue") or revenue)
        prof_c = _dom(tuple(t for t in profitability if t.name == "net_margin") or profitability)
        cash_c = _dom(tuple(t for t in cash if t.name == "free_cash_flow") or cash)
        bal_c = _dom(tuple(t for t in balance if t.name == "book_value") or balance)
        ratio_c = _dom(tuple(t for t in ratios if t.name == "net_margin") or ratios)

        score_map = {
            TrendClass.STRONGLY_IMPROVING: 2,
            TrendClass.IMPROVING: 1,
            TrendClass.STABLE: 0,
            TrendClass.WEAKENING: -1,
            TrendClass.STRONGLY_WEAKENING: -2,
            TrendClass.HIGHLY_VOLATILE: -1,
            TrendClass.INSUFFICIENT: 0,
        }
        avg = statistics.fmean(
            [score_map[c] for c in (rev_c, prof_c, cash_c, bal_c, ratio_c)]
        )
        if avg >= 1.2:
            overall = TrendClass.STRONGLY_IMPROVING
        elif avg >= 0.4:
            overall = TrendClass.IMPROVING
        elif avg <= -1.2:
            overall = TrendClass.STRONGLY_WEAKENING
        elif avg <= -0.4:
            overall = TrendClass.WEAKENING
        else:
            overall = TrendClass.STABLE

        n = len(stmts)
        insights: list[str] = []
        rev = next((t for t in revenue if t.name == "revenue"), None)
        if rev and rev.classification in (
            TrendClass.IMPROVING,
            TrendClass.STRONGLY_IMPROVING,
        ):
            insights.append(
                f"Revenue has grown consistently across {n} periods."
                if (rev.consistency or 0) >= 0.5
                else f"Revenue trend is {rev.classification.value} over {n} periods."
            )
        nm = next((t for t in profitability if t.name == "net_margin"), None)
        if nm and nm.values:
            expands = 0
            vals = [v for v in nm.values if v is not None]
            for i in range(1, len(vals)):
                if vals[i] > vals[i - 1]:
                    expands += 1
            if len(vals) >= 2:
                insights.append(
                    f"Operating/net margins expanded in {expands} of the last "
                    f"{len(vals) - 1} period transitions."
                )
        debt = next((t for t in balance if t.name == "net_debt"), None)
        if debt and debt.classification in (
            TrendClass.IMPROVING,
            TrendClass.STRONGLY_IMPROVING,
        ):
            insights.append("Debt has declined over multiple reporting cycles.")
        fcf = next((t for t in cash if t.name == "free_cash_flow"), None)
        if fcf and (fcf.consistency or 0) >= 0.55:
            insights.append("Free cash flow has become more stable.")
        alloc = next((t for t in ratios if t.name == "capital_allocation_score"), None)
        if alloc and alloc.classification in (
            TrendClass.IMPROVING,
            TrendClass.STRONGLY_IMPROVING,
        ):
            insights.append("Capital allocation quality has improved.")

        out.append(
            build_explanation(
                name="trend_summary",
                formula="aggregate family classifications + insight templates",
                inputs={
                    "revenue": rev_c.value,
                    "profitability": prof_c.value,
                    "cash_flow": cash_c.value,
                    "balance_sheet": bal_c.value,
                    "ratios": ratio_c.value,
                },
                intermediates={"score_avg": avg},
                result=None,
                confidence=_confidence(n, has_value=True),
                interpretation=f"Overall trend: {overall.value}.",
                limitations="Insights are template-based research narratives.",
            )
        )
        return TrendSummary(
            revenue=rev_c,
            profitability=prof_c,
            cash_flow=cash_c,
            balance_sheet=bal_c,
            ratios=ratio_c,
            overall=overall,
            insights=tuple(insights),
        )
