"""Income Statement Intelligence engine (F2.2).

Deterministic domain analysis of normalized IncomeStatement series.
No forecasting, valuation, or provider I/O.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Sequence

from financial.income_statement import IncomeStatement
from financial.intelligence.income_explainability import (
    RESEARCH_DISCLAIMER,
    MetricExplanation,
    build_explanation,
)
from financial.intelligence.income_models import (
    ConsistencyMetrics,
    ExpenseMetrics,
    GrowthMetrics,
    IncomeAnalysisMetadata,
    IncomeStatementAnalysis,
    MarginMetrics,
    ProfitabilityMetrics,
    QualityFlag,
    RevenueMetrics,
    RevenueTrendClass,
    TrendDirection,
)
from financial.intelligence.income_validation import (
    coerce_income_series,
    validate_income_for_analysis,
)
from financial.intelligence.quality_signals import (
    dilution_discipline_01,
    eps_cagr_from_series,
    share_dilution_rate,
)
from financial.models import FinancialSnapshot, FinancialStatements
from financial.period import PeriodType

__all__ = ["IncomeStatementEngine", "INCOME_INTELLIGENCE_VERSION"]

INCOME_INTELLIGENCE_VERSION = "0.2.0-income"

# Research thresholds (deterministic; not calibrated trading rules)
_HEALTHY_GROWTH = 0.05
_DECLINE_GROWTH = -0.02
_HIGH_OP_LEVERAGE = 1.5
_HIGH_TAX_BURDEN = 0.35
_HIGH_INTEREST_BURDEN = 0.15
_OTHER_INCOME_DEPENDENCE = 0.20
_MARGIN_EXPAND = 0.01


def _safe_div(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None:
        return None
    if denom == 0:
        return None
    result = numer / denom
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None:
        return None
    if prior == 0:
        return None
    return (current - prior) / abs(prior)


def _cagr(start: float | None, end: float | None, periods: int) -> float | None:
    if start is None or end is None or periods <= 0:
        return None
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1.0 / periods) - 1.0


def _stability(values: Sequence[float]) -> float | None:
    """Return 1 / (1 + CV) in (0, 1]; higher = more stable."""
    clean = [v for v in values if math.isfinite(v)]
    if len(clean) < 2:
        return None
    mean = statistics.fmean(clean)
    if mean == 0:
        # All-zero series is perfectly stable; mixed-sign around zero → unstable
        if all(v == 0 for v in clean):
            return 1.0
        return 0.0
    stdev = statistics.pstdev(clean)
    cv = abs(stdev / mean)
    return 1.0 / (1.0 + cv)


def _confidence_from_history(n: int, *, has_value: bool) -> str:
    if not has_value:
        return "insufficient"
    if n >= 4:
        return "high"
    if n >= 2:
        return "medium"
    return "low"


class IncomeStatementEngine:
    """Analyze one or more normalized income statements."""

    def analyze(
        self,
        source: IncomeStatement
        | FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[IncomeStatement | FinancialStatements],
        *,
        history: Sequence[IncomeStatement | FinancialStatements] | None = None,
    ) -> IncomeStatementAnalysis:
        """Run Income Statement Intelligence.

        Accepts ``IncomeStatement``, ``FinancialStatements``,
        ``FinancialSnapshot``, a normalized dict payload, or a sequence of
        periods. Optional ``history`` is prepended when ``source`` is a single
        statement.
        """
        if history is not None and not isinstance(
            source, (list, tuple, FinancialSnapshot)
        ):
            series: list[Any] = list(history)
            series.append(source)
            incomes, stmts, meta = coerce_income_series(series)
        else:
            incomes, stmts, meta = coerce_income_series(source)

        primary = incomes[-1]
        primary_stmt = stmts[-1]
        validation = validate_income_for_analysis(
            primary, statements=primary_stmt, require_revenue=True
        )

        explanations: list[MetricExplanation] = []

        margins = self._margins(primary, explanations)
        expenses = self._expenses(primary, incomes, explanations)
        revenue = self._revenue(incomes, stmts, explanations)
        profitability = self._profitability(incomes, stmts, margins, explanations)
        growth = self._growth_block(incomes, explanations)
        consistency = self._consistency(incomes, margins, growth, explanations)
        flags = self._flags(revenue, margins, growth, consistency, incomes)
        trend = self._trend_summary(revenue, margins, growth)
        metadata = IncomeAnalysisMetadata(
            engine_version=INCOME_INTELLIGENCE_VERSION,
            periods_used=len(incomes),
            primary_period_end=meta.get("period_end"),
            company=str(meta.get("company") or ""),
            ticker=str(meta.get("ticker") or ""),
        )

        return IncomeStatementAnalysis(
            revenue=revenue,
            margins=margins,
            expenses=expenses,
            profitability=profitability,
            growth=growth,
            consistency=consistency,
            quality_flags=flags,
            trend_summary=trend,
            validation=validation,
            explainability=tuple(explanations),
            metadata=metadata,
            research_disclaimer=RESEARCH_DISCLAIMER,
        )

    def _margins(
        self, income: IncomeStatement, out: list[MetricExplanation]
    ) -> MarginMetrics:
        rev = income.revenue
        # Operating margin prefers EBIT; falls back to revenue - opex when both set
        operating = income.ebit
        if operating is None and income.operating_expenses is not None and rev is not None:
            operating = rev - income.operating_expenses

        pairs = (
            ("gross_margin", "gross_profit / revenue", income.gross_profit),
            ("ebitda_margin", "ebitda / revenue", income.ebitda),
            ("ebit_margin", "ebit / revenue", income.ebit),
            ("operating_margin", "operating_profit / revenue", operating),
            ("pretax_margin", "pretax_income / revenue", income.pretax_income),
            ("net_margin", "net_income / revenue", income.net_income),
        )
        values: dict[str, float | None] = {}
        for name, formula, numer in pairs:
            result = _safe_div(numer, rev)
            values[name] = result
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs={"numerator": numer, "revenue": rev},
                    intermediates={"ratio": result},
                    result=result,
                    confidence=_confidence_from_history(1, has_value=result is not None),
                    interpretation=self._margin_interp(name, result),
                    limitations="Undefined when revenue is missing or zero.",
                )
            )
        return MarginMetrics(**values)

    @staticmethod
    def _margin_interp(name: str, value: float | None) -> str:
        if value is None:
            return f"{name} unavailable — insufficient inputs."
        pct = value * 100.0
        return f"{name} is {pct:.2f}% of revenue."

    def _expenses(
        self,
        income: IncomeStatement,
        incomes: Sequence[IncomeStatement],
        out: list[MetricExplanation],
    ) -> ExpenseMetrics:
        rev = income.revenue
        fields = (
            ("cogs_pct", "cogs / revenue", income.cogs),
            ("rd_pct", "rd / revenue", income.rd),
            ("sga_pct", "sga / revenue", income.sga),
            ("operating_expense_pct", "operating_expenses / revenue", income.operating_expenses),
            ("interest_pct", "interest_expense / revenue", income.interest_expense),
            ("tax_pct", "tax / revenue", income.tax),
            ("other_income_pct", "other_income / revenue", income.other_income),
        )
        values: dict[str, float | None] = {}
        for name, formula, numer in fields:
            result = _safe_div(numer, rev)
            values[name] = result
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs={"numerator": numer, "revenue": rev},
                    intermediates={"ratio": result},
                    result=result,
                    confidence=_confidence_from_history(1, has_value=result is not None),
                    interpretation=(
                        f"{name} unavailable."
                        if result is None
                        else f"{name} is {result * 100:.2f}% of revenue."
                    ),
                    limitations="Ratio undefined without revenue.",
                )
            )

        expense_trend: TrendDirection | None = None
        if len(incomes) >= 2:
            prev = incomes[-2]
            cur_opex = _safe_div(income.operating_expenses, rev)
            prev_opex = _safe_div(prev.operating_expenses, prev.revenue)
            if cur_opex is not None and prev_opex is not None:
                delta = cur_opex - prev_opex
                if delta <= -0.01:
                    expense_trend = TrendDirection.IMPROVING
                elif delta >= 0.01:
                    expense_trend = TrendDirection.WEAKENING
                else:
                    expense_trend = TrendDirection.STABLE
                out.append(
                    build_explanation(
                        name="expense_trend",
                        formula="Δ(operating_expenses/revenue)",
                        inputs={
                            "current_opex_pct": cur_opex,
                            "prior_opex_pct": prev_opex,
                        },
                        intermediates={"delta": delta},
                        result=delta,
                        confidence="medium",
                        interpretation=f"Expense trend classified as {expense_trend.value}.",
                        limitations="Uses operating expense ratio when available.",
                    )
                )

        return ExpenseMetrics(expense_trend=expense_trend, **values)

    def _revenue(
        self,
        incomes: Sequence[IncomeStatement],
        stmts: Sequence[FinancialStatements | None],
        out: list[MetricExplanation],
    ) -> RevenueMetrics:
        primary = incomes[-1]
        rev = primary.revenue
        prior = incomes[-2] if len(incomes) >= 2 else None
        revenue_growth = _growth(rev, prior.revenue if prior else None)

        qoq = None
        yoy = None
        if prior is not None and stmts[-1] is not None and stmts[-2] is not None:
            cur_p = stmts[-1].period
            prev_p = stmts[-2].period
            g = _growth(rev, prior.revenue)
            if (
                cur_p.period_type is PeriodType.QUARTERLY
                and prev_p.period_type is PeriodType.QUARTERLY
            ):
                qoq = g
            # YoY: same quarter prior year or annual vs annual
            for i in range(len(incomes) - 2, -1, -1):
                s = stmts[i]
                if s is None:
                    continue
                if cur_p.period_type is PeriodType.ANNUAL and s.period.period_type is PeriodType.ANNUAL:
                    if cur_p.fiscal_year and s.period.fiscal_year:
                        if cur_p.fiscal_year - s.period.fiscal_year == 1:
                            yoy = _growth(rev, incomes[i].revenue)
                            break
                if (
                    cur_p.period_type is PeriodType.QUARTERLY
                    and s.period.period_type is PeriodType.QUARTERLY
                    and cur_p.fiscal_quarter is not None
                    and s.period.fiscal_quarter == cur_p.fiscal_quarter
                    and cur_p.fiscal_year
                    and s.period.fiscal_year
                    and cur_p.fiscal_year - s.period.fiscal_year == 1
                ):
                    yoy = _growth(rev, incomes[i].revenue)
                    break

        # CAGR only over annual statements with fiscal-year span (never quarterly
        # period-count-as-years — that invents annualised growth).
        cagr = None
        annual_points: list[tuple[int, float]] = []
        for income, stmt in zip(incomes, stmts, strict=False):
            if stmt is None or stmt.period.period_type is not PeriodType.ANNUAL:
                continue
            fy = stmt.period.fiscal_year
            if fy is None or income.revenue is None or income.revenue <= 0:
                continue
            annual_points.append((int(fy), float(income.revenue)))
        if len(annual_points) >= 2:
            annual_points.sort(key=lambda item: item[0])
            start_fy, start_rev = annual_points[0]
            end_fy, end_rev = annual_points[-1]
            years = end_fy - start_fy
            if years >= 1:
                cagr = _cagr(start_rev, end_rev, years)

        rev_series = [i.revenue for i in incomes if i.revenue is not None]
        growth_rates: list[float] = []
        for i in range(1, len(incomes)):
            g = _growth(incomes[i].revenue, incomes[i - 1].revenue)
            if g is not None:
                growth_rates.append(g)
        growth_stability = _stability(growth_rates) if growth_rates else None
        trend_class = self._classify_revenue_trend(growth_rates, revenue_growth)

        out.append(
            build_explanation(
                name="revenue_growth",
                formula="(revenue_t - revenue_t-1) / |revenue_t-1|",
                inputs={
                    "revenue_t": rev,
                    "revenue_t-1": prior.revenue if prior else None,
                },
                intermediates={"growth": revenue_growth},
                result=revenue_growth,
                confidence=_confidence_from_history(
                    len(incomes), has_value=revenue_growth is not None
                ),
                interpretation=(
                    "Insufficient history for growth."
                    if revenue_growth is None
                    else f"Period revenue growth is {revenue_growth * 100:.2f}%."
                ),
                limitations="Requires a prior period with non-zero revenue.",
            )
        )
        if cagr is not None:
            out.append(
                build_explanation(
                    name="cagr",
                    formula="(end/start)^(1/n) - 1 using annual fiscal years",
                    inputs={
                        "start": annual_points[0][1],
                        "end": annual_points[-1][1],
                        "years": annual_points[-1][0] - annual_points[0][0],
                    },
                    intermediates={"cagr": cagr},
                    result=cagr,
                    confidence=_confidence_from_history(
                        len(annual_points), has_value=True
                    ),
                    interpretation=(
                        f"Revenue CAGR over "
                        f"{annual_points[-1][0] - annual_points[0][0]} "
                        f"fiscal years is {cagr * 100:.2f}%."
                    ),
                    limitations=(
                        "Annual statements only; quarterly histories do not "
                        "produce CAGR. Negative revenues unsupported."
                    ),
                )
            )

        return RevenueMetrics(
            revenue=rev,
            revenue_growth=revenue_growth,
            qoq_growth=qoq,
            # YoY must not silently fall back to sequential period growth.
            yoy_growth=yoy,
            cagr=cagr,
            growth_stability=growth_stability,
            trend_class=trend_class,
        )

    @staticmethod
    def _classify_revenue_trend(
        growth_rates: Sequence[float], latest: float | None
    ) -> RevenueTrendClass:
        if not growth_rates:
            return RevenueTrendClass.INSUFFICIENT_HISTORY
        if _stability(list(growth_rates)) is not None:
            stab = _stability(list(growth_rates))
            if stab is not None and stab < 0.4 and len(growth_rates) >= 3:
                return RevenueTrendClass.VOLATILE
        if latest is None:
            return RevenueTrendClass.INSUFFICIENT_HISTORY
        if abs(latest) < 0.01:
            return RevenueTrendClass.FLAT
        if latest < _DECLINE_GROWTH:
            return RevenueTrendClass.DECLINING
        if len(growth_rates) >= 2:
            delta = growth_rates[-1] - growth_rates[-2]
            if delta > 0.02 and latest > 0:
                return RevenueTrendClass.ACCELERATING
            if delta < -0.02 and latest > 0:
                return RevenueTrendClass.DECELERATING
        if latest > 0:
            return RevenueTrendClass.STEADY_GROWTH
        return RevenueTrendClass.DECLINING

    def _profitability(
        self,
        incomes: Sequence[IncomeStatement],
        stmts: Sequence[FinancialStatements | None],
        margins: MarginMetrics,
        out: list[MetricExplanation],
    ) -> ProfitabilityMetrics:
        primary = incomes[-1]
        # Quality: margin level clipped to [0, 1] contribution
        def _q(m: float | None) -> float | None:
            if m is None:
                return None
            return max(0.0, min(1.0, m))

        gpq = _q(margins.gross_margin)
        opq = _q(margins.operating_margin if margins.operating_margin is not None else margins.ebit_margin)
        niq = _q(margins.net_margin)

        net_margins: list[float] = []
        for inc in incomes:
            m = _safe_div(inc.net_income, inc.revenue)
            if m is not None:
                net_margins.append(m)
        margin_stability = _stability(net_margins)

        margin_expansion = None
        margin_compression = None
        if len(net_margins) >= 2:
            delta = net_margins[-1] - net_margins[-2]
            if delta >= _MARGIN_EXPAND:
                margin_expansion = delta
            elif delta <= -_MARGIN_EXPAND:
                margin_compression = abs(delta)
            out.append(
                build_explanation(
                    name="net_margin_change",
                    formula="net_margin_t - net_margin_t-1",
                    inputs={
                        "current": net_margins[-1],
                        "prior": net_margins[-2],
                    },
                    intermediates={"delta": delta},
                    result=delta,
                    confidence="medium",
                    interpretation=(
                        "Net margin expanded."
                        if delta >= _MARGIN_EXPAND
                        else "Net margin compressed."
                        if delta <= -_MARGIN_EXPAND
                        else "Net margin roughly stable."
                    ),
                    limitations="Requires two periods with computable net margins.",
                )
            )

        eps_growth = None
        if len(incomes) >= 2:
            eps_growth = _growth(primary.eps, incomes[-2].eps)

        eps_vals = [i.eps for i in incomes if i.eps is not None]
        eps_stability = _stability(eps_vals) if len(eps_vals) >= 2 else None
        ni_vals = [i.net_income for i in incomes if i.net_income is not None]
        earnings_consistency = _stability(ni_vals) if len(ni_vals) >= 2 else None

        eps_cagr, eps_cagr_basis = eps_cagr_from_series(incomes, stmts)
        dilution_rate = share_dilution_rate(incomes, stmts)
        dilution_disc = dilution_discipline_01(dilution_rate)

        for name, result, formula, inputs in (
            (
                "gross_profit_quality",
                gpq,
                "clip(gross_margin, 0, 1)",
                {"gross_margin": margins.gross_margin},
            ),
            (
                "operating_profit_quality",
                opq,
                "clip(operating_margin, 0, 1)",
                {"operating_margin": margins.operating_margin},
            ),
            (
                "net_income_quality",
                niq,
                "clip(net_margin, 0, 1)",
                {"net_margin": margins.net_margin},
            ),
            (
                "eps_growth",
                eps_growth,
                "(eps_t - eps_t-1) / |eps_t-1|",
                {
                    "eps_t": primary.eps,
                    "eps_t-1": incomes[-2].eps if len(incomes) >= 2 else None,
                },
            ),
            (
                "eps_cagr",
                eps_cagr,
                "(eps_end / eps_start)^(1/years) - 1 [annual FY; diluted preferred]",
                {"eps_cagr_basis": eps_cagr_basis},
            ),
            (
                "share_dilution_rate",
                dilution_rate,
                "(weighted_shares_end - weighted_shares_start) / weighted_shares_start",
                {"share_field": "weighted_shares"},
            ),
        ):
            out.append(
                build_explanation(
                    name=name,
                    formula=formula,
                    inputs=inputs,
                    intermediates={},
                    result=result,
                    confidence=_confidence_from_history(
                        len(incomes), has_value=result is not None
                    ),
                    interpretation=(
                        f"{name} unavailable."
                        if result is None
                        else f"{name} = {result:.4f}."
                    ),
                    limitations="Research heuristic — not an accounting audit.",
                )
            )

        return ProfitabilityMetrics(
            gross_profit_quality=gpq,
            operating_profit_quality=opq,
            net_income_quality=niq,
            margin_stability=margin_stability,
            margin_expansion=margin_expansion,
            margin_compression=margin_compression,
            eps=primary.eps,
            diluted_eps=primary.diluted_eps,
            eps_growth=eps_growth,
            eps_stability=eps_stability,
            earnings_consistency=earnings_consistency,
            eps_cagr=eps_cagr,
            eps_cagr_basis=eps_cagr_basis,
            share_dilution_rate=dilution_rate,
            dilution_discipline=dilution_disc,
        )

    def _growth_block(
        self,
        incomes: Sequence[IncomeStatement],
        out: list[MetricExplanation],
    ) -> GrowthMetrics:
        if len(incomes) < 2:
            return GrowthMetrics(
                revenue_growth=None,
                ebit_growth=None,
                net_income_growth=None,
                eps_growth=None,
                operating_leverage=None,
            )
        cur, prev = incomes[-1], incomes[-2]
        rg = _growth(cur.revenue, prev.revenue)
        eg = _growth(cur.ebit, prev.ebit)
        ng = _growth(cur.net_income, prev.net_income)
        epg = _growth(cur.eps, prev.eps)
        op_lev = None
        if rg is not None and eg is not None and abs(rg) > 1e-12:
            op_lev = eg / rg
            out.append(
                build_explanation(
                    name="operating_leverage",
                    formula="ebit_growth / revenue_growth",
                    inputs={"ebit_growth": eg, "revenue_growth": rg},
                    intermediates={"operating_leverage": op_lev},
                    result=op_lev,
                    confidence="medium",
                    interpretation=f"Operating leverage ≈ {op_lev:.2f}x.",
                    limitations="Sensitive when revenue growth is near zero.",
                )
            )
        return GrowthMetrics(
            revenue_growth=rg,
            ebit_growth=eg,
            net_income_growth=ng,
            eps_growth=epg,
            operating_leverage=op_lev,
        )

    def _consistency(
        self,
        incomes: Sequence[IncomeStatement],
        margins: MarginMetrics,
        growth: GrowthMetrics,
        out: list[MetricExplanation],
    ) -> ConsistencyMetrics:
        primary = incomes[-1]
        rev_vals = [i.revenue for i in incomes if i.revenue is not None]
        revenue_consistency = _stability(rev_vals) if len(rev_vals) >= 2 else None

        net_m = [
            m
            for m in (
                _safe_div(i.net_income, i.revenue) for i in incomes
            )
            if m is not None
        ]
        margin_consistency = _stability(net_m) if len(net_m) >= 2 else None

        ni_vals = [i.net_income for i in incomes if i.net_income is not None]
        earnings_stability = _stability(ni_vals) if len(ni_vals) >= 2 else None

        interest_burden = _safe_div(primary.interest_expense, primary.ebit)
        if interest_burden is None:
            interest_burden = _safe_div(primary.interest_expense, primary.revenue)

        tax_burden = _safe_div(primary.tax, primary.pretax_income)
        if tax_burden is None:
            tax_burden = _safe_div(primary.tax, primary.revenue)

        other_dep = None
        if primary.other_income is not None and primary.pretax_income:
            other_dep = abs(primary.other_income) / abs(primary.pretax_income)
        elif primary.other_income is not None and primary.revenue:
            other_dep = abs(primary.other_income) / abs(primary.revenue)

        # Recurring earnings proxy: 1 - other_income dependence
        recurring = None
        if other_dep is not None:
            recurring = max(0.0, min(1.0, 1.0 - other_dep))

        # One-time heuristic: other_income large vs pretax OR tax rate extreme
        one_time = False
        if other_dep is not None and other_dep >= _OTHER_INCOME_DEPENDENCE:
            one_time = True
        if tax_burden is not None and (tax_burden < 0 or tax_burden > 0.6):
            one_time = True

        out.append(
            build_explanation(
                name="interest_burden",
                formula="interest_expense / ebit (fallback: / revenue)",
                inputs={
                    "interest_expense": primary.interest_expense,
                    "ebit": primary.ebit,
                    "revenue": primary.revenue,
                },
                intermediates={"interest_burden": interest_burden},
                result=interest_burden,
                confidence=_confidence_from_history(
                    1, has_value=interest_burden is not None
                ),
                interpretation=(
                    "Interest burden unavailable."
                    if interest_burden is None
                    else f"Interest burden is {interest_burden * 100:.2f}%."
                ),
                limitations="Heuristic ratio — lease/interest classification varies.",
            )
        )
        out.append(
            build_explanation(
                name="tax_burden",
                formula="tax / pretax_income (fallback: / revenue)",
                inputs={
                    "tax": primary.tax,
                    "pretax_income": primary.pretax_income,
                    "revenue": primary.revenue,
                },
                intermediates={"tax_burden": tax_burden},
                result=tax_burden,
                confidence=_confidence_from_history(1, has_value=tax_burden is not None),
                interpretation=(
                    "Tax burden unavailable."
                    if tax_burden is None
                    else f"Tax burden is {tax_burden * 100:.2f}%."
                ),
                limitations="Statutory vs effective rate differences not modeled.",
            )
        )

        return ConsistencyMetrics(
            revenue_consistency=revenue_consistency,
            margin_consistency=margin_consistency,
            earnings_stability=earnings_stability,
            operating_leverage=growth.operating_leverage,
            interest_burden=interest_burden,
            tax_burden=tax_burden,
            other_income_dependence=other_dep,
            recurring_earnings=recurring,
            one_time_items_detected=one_time,
        )

    def _flags(
        self,
        revenue: RevenueMetrics,
        margins: MarginMetrics,
        growth: GrowthMetrics,
        consistency: ConsistencyMetrics,
        incomes: Sequence[IncomeStatement],
    ) -> tuple[QualityFlag, ...]:
        flags: list[QualityFlag] = []
        g = revenue.revenue_growth
        if g is not None:
            if g >= _HEALTHY_GROWTH and (
                revenue.growth_stability is None or revenue.growth_stability >= 0.5
            ):
                flags.append(QualityFlag.HEALTHY_GROWTH)
            if g <= _DECLINE_GROWTH:
                flags.append(QualityFlag.DECLINING_REVENUE)

        if consistency.margin_consistency is not None or len(incomes) >= 2:
            # Expansion / compression from profitability deltas via growth net margin
            if len(incomes) >= 2:
                cur_m = _safe_div(incomes[-1].net_income, incomes[-1].revenue)
                prev_m = _safe_div(incomes[-2].net_income, incomes[-2].revenue)
                if cur_m is not None and prev_m is not None:
                    delta = cur_m - prev_m
                    if delta >= _MARGIN_EXPAND:
                        flags.append(QualityFlag.MARGIN_EXPANSION)
                    elif delta <= -_MARGIN_EXPAND:
                        flags.append(QualityFlag.MARGIN_COMPRESSION)

        if (
            growth.operating_leverage is not None
            and growth.operating_leverage >= _HIGH_OP_LEVERAGE
            and (g or 0) > 0
        ):
            flags.append(QualityFlag.HIGH_OPERATING_LEVERAGE)

        if consistency.tax_burden is not None and consistency.tax_burden >= _HIGH_TAX_BURDEN:
            flags.append(QualityFlag.HIGH_TAX_BURDEN)
        if (
            consistency.interest_burden is not None
            and consistency.interest_burden >= _HIGH_INTEREST_BURDEN
        ):
            flags.append(QualityFlag.HIGH_INTEREST_BURDEN)

        # Earnings quality
        strong = (
            (margins.net_margin is not None and margins.net_margin > 0)
            and (consistency.other_income_dependence is None or consistency.other_income_dependence < 0.1)
            and not consistency.one_time_items_detected
            and (consistency.earnings_stability is None or consistency.earnings_stability >= 0.5)
        )
        weak = (
            consistency.one_time_items_detected
            or (
                consistency.other_income_dependence is not None
                and consistency.other_income_dependence >= _OTHER_INCOME_DEPENDENCE
            )
            or (margins.net_margin is not None and margins.net_margin < 0)
        )
        if strong:
            flags.append(QualityFlag.STRONG_EARNINGS_QUALITY)
        elif weak:
            flags.append(QualityFlag.WEAK_EARNINGS_QUALITY)

        # Deduplicate while preserving order
        return tuple(dict.fromkeys(flags))

    @staticmethod
    def _trend_summary(
        revenue: RevenueMetrics,
        margins: MarginMetrics,
        growth: GrowthMetrics,
    ) -> TrendDirection:
        score = 0
        if revenue.revenue_growth is not None:
            if revenue.revenue_growth > 0.02:
                score += 1
            elif revenue.revenue_growth < -0.02:
                score -= 1
        if growth.net_income_growth is not None:
            if growth.net_income_growth > 0.02:
                score += 1
            elif growth.net_income_growth < -0.02:
                score -= 1
        if revenue.trend_class in (
            RevenueTrendClass.ACCELERATING,
            RevenueTrendClass.STEADY_GROWTH,
        ):
            score += 1
        elif revenue.trend_class in (
            RevenueTrendClass.DECLINING,
            RevenueTrendClass.DECELERATING,
        ):
            score -= 1

        if score >= 1:
            return TrendDirection.IMPROVING
        if score <= -1:
            return TrendDirection.WEAKENING
        return TrendDirection.STABLE
