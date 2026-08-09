"""Financial Ratio Engine (F2.5).

Composes Income / Balance / Cash Flow Intelligence into canonical ratios.
No forecasting, valuation, market data, or provider I/O.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

from financial.intelligence.balance_engine import BalanceSheetEngine
from financial.intelligence.cashflow_engine import CashFlowEngine
from financial.intelligence.cashflow_validation import _computed_fcf
from financial.intelligence.income_engine import IncomeStatementEngine
from financial.intelligence.income_models import TrendDirection
from financial.intelligence.ratio_explainability import (
    RATIO_RESEARCH_DISCLAIMER,
    MetricExplanation,
    build_explanation,
)
from financial.intelligence.ratio_models import (
    BenchmarkClass,
    CapitalAllocationMetrics,
    FinancialRatioAnalysis,
    RatioAnalysisMetadata,
    RatioMetric,
    RatioQualityFlag,
    RatioTrendSummary,
)
from financial.intelligence.ratio_validation import (
    coerce_ratio_series,
    validate_ratio_inputs,
)
from financial.models import FinancialSnapshot, FinancialStatements

__all__ = ["FinancialRatioEngine", "RATIO_INTELLIGENCE_VERSION"]

RATIO_INTELLIGENCE_VERSION = "0.5.0-ratios"


def _safe_div(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None or denom == 0:
        return None
    result = numer / denom
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _clip01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _avg(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return (a + b) / 2.0


def _equity(bs) -> float | None:
    return bs.total_equity if bs.total_equity is not None else bs.equity


def _total_debt(bs) -> float | None:
    if bs.short_term_debt is None and bs.long_term_debt is None:
        return None
    return (bs.short_term_debt or 0.0) + (bs.long_term_debt or 0.0)


def _current_assets(bs) -> float | None:
    if bs.current_assets is not None:
        return bs.current_assets
    parts = [
        bs.cash,
        bs.short_term_investments,
        bs.accounts_receivable,
        bs.inventory,
        bs.other_current_assets,
    ]
    if all(p is None for p in parts):
        return None
    return sum(p or 0.0 for p in parts)


def _fcf(cf) -> float | None:
    if cf.free_cash_flow is not None:
        return cf.free_cash_flow
    return _computed_fcf(cf)


def _confidence(n: int, *, has_value: bool) -> str:
    if not has_value:
        return "insufficient"
    if n >= 3:
        return "high"
    if n >= 2:
        return "medium"
    return "low"


def _benchmark_margin(value: float | None) -> BenchmarkClass:
    if value is None:
        return BenchmarkClass.INSUFFICIENT
    if value >= 0.25:
        return BenchmarkClass.EXCELLENT
    if value >= 0.15:
        return BenchmarkClass.STRONG
    if value >= 0.08:
        return BenchmarkClass.ADEQUATE
    if value >= 0.0:
        return BenchmarkClass.WEAK
    return BenchmarkClass.POOR


def _benchmark_ratio(
    value: float | None,
    *,
    excellent: float,
    strong: float,
    adequate: float,
    higher_better: bool = True,
) -> BenchmarkClass:
    if value is None:
        return BenchmarkClass.INSUFFICIENT
    if higher_better:
        if value >= excellent:
            return BenchmarkClass.EXCELLENT
        if value >= strong:
            return BenchmarkClass.STRONG
        if value >= adequate:
            return BenchmarkClass.ADEQUATE
        if value >= 0:
            return BenchmarkClass.WEAK
        return BenchmarkClass.POOR
    # lower is better
    if value <= excellent:
        return BenchmarkClass.EXCELLENT
    if value <= strong:
        return BenchmarkClass.STRONG
    if value <= adequate:
        return BenchmarkClass.ADEQUATE
    return BenchmarkClass.WEAK


def _trend(current: float | None, prior: float | None, *, higher_better: bool = True) -> TrendDirection | None:
    if current is None or prior is None:
        return None
    delta = current - prior
    if abs(delta) < 1e-9 or (prior != 0 and abs(delta / abs(prior)) < 0.02):
        return TrendDirection.STABLE
    up = delta > 0
    if higher_better:
        return TrendDirection.IMPROVING if up else TrendDirection.WEAKENING
    return TrendDirection.IMPROVING if not up else TrendDirection.WEAKENING


class FinancialRatioEngine:
    """Compose statement intelligence into canonical financial ratios."""

    def __init__(self) -> None:
        self._income = IncomeStatementEngine()
        self._balance = BalanceSheetEngine()
        self._cash = CashFlowEngine()

    def analyze(
        self,
        source: FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[FinancialStatements],
        *,
        history: Sequence[FinancialStatements] | None = None,
    ) -> FinancialRatioAnalysis:
        """Run Financial Ratio Engine analysis."""
        if history is not None and not isinstance(
            source, (list, tuple, FinancialSnapshot)
        ):
            series: list[Any] = list(history)
            series.append(source)
            stmts, meta = coerce_ratio_series(series)
        else:
            stmts, meta = coerce_ratio_series(source)

        primary = stmts[-1]
        prior = stmts[-2] if len(stmts) >= 2 else None
        validation = validate_ratio_inputs(primary)

        # Compose sibling intelligence (domain composition)
        income_an = self._income.analyze(stmts if len(stmts) > 1 else primary)
        balance_an = self._balance.analyze(stmts if len(stmts) > 1 else primary)
        cash_an = self._cash.analyze(stmts if len(stmts) > 1 else primary)

        explanations: list[MetricExplanation] = []
        profitability = self._profitability(primary, prior, explanations)
        liquidity = self._liquidity(primary, prior, balance_an, explanations)
        leverage = self._leverage(primary, prior, explanations)
        efficiency = self._efficiency(primary, prior, explanations)
        cash_flow = self._cash_ratios(primary, prior, explanations)
        shareholder = self._shareholder(primary, prior, explanations)
        capital = self._capital_allocation(primary, cash_an, explanations)
        flags = self._flags(
            profitability, liquidity, leverage, efficiency, cash_flow, capital, cash_an
        )
        trends = self._trend_summary(
            profitability, liquidity, leverage, efficiency, cash_flow
        )
        metadata = RatioAnalysisMetadata(
            engine_version=RATIO_INTELLIGENCE_VERSION,
            periods_used=len(stmts),
            primary_period_end=meta.get("period_end"),
            company=str(meta.get("company") or ""),
            ticker=str(meta.get("ticker") or ""),
        )
        # Attach sibling summaries into explainability notes (composition proof)
        explanations.append(
            build_explanation(
                name="composed_intelligence",
                formula="compose(income, balance, cash_flow intelligence)",
                inputs={
                    "income_trend": income_an.trend_summary.value,
                    "balance_liquidity_trend": balance_an.trend_summary.liquidity.value,
                    "cash_ocf_trend": cash_an.trend_summary.operating_cash_flow.value,
                },
                intermediates={
                    "income_flags": [f.value for f in income_an.quality_flags],
                    "balance_flags": [f.value for f in balance_an.quality_flags],
                    "cash_flags": [f.value for f in cash_an.quality_flags],
                },
                result=None,
                confidence="high",
                interpretation="Ratio engine composed sibling statement intelligence outputs.",
                limitations="Sibling engines remain independently callable.",
            )
        )
        return FinancialRatioAnalysis(
            profitability=profitability,
            liquidity=liquidity,
            leverage=leverage,
            efficiency=efficiency,
            cash_flow=cash_flow,
            shareholder=shareholder,
            capital_allocation=capital,
            quality_flags=flags,
            trend_summary=trends,
            validation=validation,
            explainability=tuple(explanations),
            metadata=metadata,
            research_disclaimer=RATIO_RESEARCH_DISCLAIMER,
        )

    def _metric(
        self,
        *,
        name: str,
        formula: str,
        value: float | None,
        inputs: dict[str, Any],
        intermediates: dict[str, Any] | None = None,
        benchmark: BenchmarkClass,
        trend: TrendDirection | None,
        periods: int,
        interpretation: str,
        risk_notes: str = "",
        limitations: str = "",
        out: list[MetricExplanation],
    ) -> RatioMetric:
        conf = _confidence(periods, has_value=value is not None)
        out.append(
            build_explanation(
                name=name,
                formula=formula,
                inputs=inputs,
                intermediates=intermediates or {},
                result=value,
                confidence=conf,
                interpretation=interpretation,
                limitations=limitations or "Research heuristic — verify filings.",
            )
        )
        return RatioMetric(
            name=name,
            value=value,
            formula=formula,
            inputs=inputs,
            intermediates=intermediates or {},
            benchmark=benchmark,
            trend=trend,
            confidence=conf,
            interpretation=interpretation,
            risk_notes=risk_notes,
            limitations=limitations or "Research heuristic — verify filings.",
        )

    def _profitability(
        self,
        cur: FinancialStatements,
        prior: FinancialStatements | None,
        out: list[MetricExplanation],
    ) -> tuple[RatioMetric, ...]:
        inc, bs = cur.income_statement, cur.balance_sheet
        rev = inc.revenue
        n = 2 if prior else 1

        def prior_val(fn: Callable[[FinancialStatements], float | None]) -> float | None:
            return fn(prior) if prior else None

        metrics: list[RatioMetric] = []
        pairs = [
            ("gross_margin", "gross_profit / revenue", _safe_div(inc.gross_profit, rev), {"gross_profit": inc.gross_profit, "revenue": rev}),
            ("operating_margin", "ebit / revenue", _safe_div(inc.ebit, rev), {"ebit": inc.ebit, "revenue": rev}),
            ("ebit_margin", "ebit / revenue", _safe_div(inc.ebit, rev), {"ebit": inc.ebit, "revenue": rev}),
            ("ebitda_margin", "ebitda / revenue", _safe_div(inc.ebitda, rev), {"ebitda": inc.ebitda, "revenue": rev}),
            ("net_margin", "net_income / revenue", _safe_div(inc.net_income, rev), {"net_income": inc.net_income, "revenue": rev}),
        ]
        for name, formula, value, inputs in pairs:
            p_map = {
                "gross_margin": lambda s: _safe_div(s.income_statement.gross_profit, s.income_statement.revenue),
                "operating_margin": lambda s: _safe_div(s.income_statement.ebit, s.income_statement.revenue),
                "ebit_margin": lambda s: _safe_div(s.income_statement.ebit, s.income_statement.revenue),
                "ebitda_margin": lambda s: _safe_div(s.income_statement.ebitda, s.income_statement.revenue),
                "net_margin": lambda s: _safe_div(s.income_statement.net_income, s.income_statement.revenue),
            }
            metrics.append(
                self._metric(
                    name=name,
                    formula=formula,
                    value=value,
                    inputs=inputs,
                    benchmark=_benchmark_margin(value),
                    trend=_trend(value, prior_val(p_map[name])),
                    periods=n,
                    interpretation=f"{name} = {value:.4f}." if value is not None else f"{name} unavailable.",
                    out=out,
                )
            )

        roa = _safe_div(inc.net_income, bs.total_assets)
        roe = _safe_div(inc.net_income, _equity(bs))
        capital_employed = None
        if bs.total_assets is not None and bs.current_liabilities is not None:
            capital_employed = bs.total_assets - bs.current_liabilities
        roce = _safe_div(inc.ebit, capital_employed)
        debt = _total_debt(bs)
        invested = None
        eq = _equity(bs)
        if eq is not None:
            invested = eq + (debt or 0.0) - (bs.cash or 0.0)
        tax_rate = _safe_div(inc.tax, inc.pretax_income)
        nopat = None
        # Fail closed — do not invent a statutory tax rate for ROIC.
        if inc.ebit is not None and tax_rate is not None:
            tr = max(0.0, min(0.6, tax_rate))
            nopat = inc.ebit * (1.0 - tr)
        roic = _safe_div(nopat, invested)

        for name, formula, value, inputs, bench_fn in (
            ("roa", "net_income / total_assets", roa, {"net_income": inc.net_income, "total_assets": bs.total_assets}, lambda v: _benchmark_margin(v)),
            ("roe", "net_income / equity", roe, {"net_income": inc.net_income, "equity": eq}, lambda v: _benchmark_margin(v)),
            ("roce", "ebit / (total_assets - current_liabilities)", roce, {"ebit": inc.ebit, "capital_employed": capital_employed}, lambda v: _benchmark_margin(v)),
            ("roic", "nopat / invested_capital", roic, {"nopat": nopat, "invested_capital": invested}, lambda v: _benchmark_margin(v)),
        ):
            prior_v = None
            if prior is not None:
                if name == "roa":
                    prior_v = _safe_div(prior.income_statement.net_income, prior.balance_sheet.total_assets)
                elif name == "roe":
                    prior_v = _safe_div(prior.income_statement.net_income, _equity(prior.balance_sheet))
            metrics.append(
                self._metric(
                    name=name,
                    formula=formula,
                    value=value,
                    inputs=inputs,
                    intermediates={"tax_rate": tax_rate} if name == "roic" else {},
                    benchmark=bench_fn(value),
                    trend=_trend(value, prior_v),
                    periods=n,
                    interpretation=f"{name} = {value:.4f}." if value is not None else f"{name} unavailable.",
                    out=out,
                )
            )
        return tuple(metrics)

    def _liquidity(
        self,
        cur: FinancialStatements,
        prior: FinancialStatements | None,
        balance_an,
        out: list[MetricExplanation],
    ) -> tuple[RatioMetric, ...]:
        bs = cur.balance_sheet
        ca = _current_assets(bs)
        cl = bs.current_liabilities
        current = _safe_div(ca, cl)
        quick = _safe_div((ca - (bs.inventory or 0.0)) if ca is not None else None, cl)
        cash_r = _safe_div(
            (bs.cash or 0.0) + (bs.short_term_investments or 0.0) if bs.cash is not None else None,
            cl,
        )
        # Working capital ratio = current ratio alias research label
        wc_ratio = current
        n = 2 if prior else 1
        prior_cr = None
        if prior is not None:
            pca = _current_assets(prior.balance_sheet)
            prior_cr = _safe_div(pca, prior.balance_sheet.current_liabilities)

        # Prefer sibling balance liquidity trend when available
        _ = balance_an
        metrics = []
        for name, formula, value, inputs in (
            ("current_ratio", "current_assets / current_liabilities", current, {"current_assets": ca, "current_liabilities": cl}),
            ("quick_ratio", "(current_assets - inventory) / current_liabilities", quick, {"current_assets": ca, "inventory": bs.inventory, "current_liabilities": cl}),
            ("cash_ratio", "(cash + STI) / current_liabilities", cash_r, {"cash": bs.cash, "sti": bs.short_term_investments, "current_liabilities": cl}),
            ("working_capital_ratio", "current_assets / current_liabilities", wc_ratio, {"current_assets": ca, "current_liabilities": cl}),
        ):
            metrics.append(
                self._metric(
                    name=name,
                    formula=formula,
                    value=value,
                    inputs=inputs,
                    benchmark=_benchmark_ratio(value, excellent=2.0, strong=1.5, adequate=1.0),
                    trend=_trend(value, prior_cr if name in ("current_ratio", "working_capital_ratio") else None),
                    periods=n,
                    interpretation=f"{name} = {value:.4f}." if value is not None else f"{name} unavailable.",
                    risk_notes="Below 1.0 indicates short-term solvency pressure." if value is not None and value < 1.0 else "",
                    out=out,
                )
            )
        return tuple(metrics)

    def _leverage(
        self,
        cur: FinancialStatements,
        prior: FinancialStatements | None,
        out: list[MetricExplanation],
    ) -> tuple[RatioMetric, ...]:
        bs, inc = cur.balance_sheet, cur.income_statement
        eq = _equity(bs)
        debt = _total_debt(bs)
        dte = _safe_div(debt, eq)
        dta = _safe_div(debt, bs.total_assets)
        equity_ratio = _safe_div(eq, bs.total_assets)
        net_debt = None if debt is None else debt - (bs.cash or 0.0)
        nd_ebitda = _safe_div(net_debt, inc.ebitda)
        interest_cov = _safe_div(inc.ebit, abs(inc.interest_expense) if inc.interest_expense else None)
        fin_lev = _safe_div(bs.total_assets, eq)
        n = 2 if prior else 1
        prior_dte = None
        if prior is not None:
            prior_dte = _safe_div(_total_debt(prior.balance_sheet), _equity(prior.balance_sheet))

        metrics = []
        specs = (
            ("debt_to_equity", "total_debt / equity", dte, {"debt": debt, "equity": eq}, False, 0.3, 0.75, 1.5),
            ("debt_to_assets", "total_debt / total_assets", dta, {"debt": debt, "total_assets": bs.total_assets}, False, 0.2, 0.4, 0.6),
            ("equity_ratio", "equity / total_assets", equity_ratio, {"equity": eq, "total_assets": bs.total_assets}, True, 0.5, 0.4, 0.3),
            ("net_debt", "total_debt - cash", net_debt, {"debt": debt, "cash": bs.cash}, False, -1e18, 0.0, 1e18),  # special
            ("net_debt_to_ebitda", "net_debt / ebitda", nd_ebitda, {"net_debt": net_debt, "ebitda": inc.ebitda}, False, 1.0, 2.0, 3.5),
            ("interest_coverage", "ebit / |interest_expense|", interest_cov, {"ebit": inc.ebit, "interest_expense": inc.interest_expense}, True, 8.0, 4.0, 2.0),
            ("financial_leverage", "total_assets / equity", fin_lev, {"total_assets": bs.total_assets, "equity": eq}, False, 1.5, 2.5, 3.5),
        )
        for name, formula, value, inputs, higher_better, exc, strong, adeq in specs:
            if name == "net_debt":
                bench = (
                    BenchmarkClass.INSUFFICIENT
                    if value is None
                    else BenchmarkClass.STRONG
                    if value <= 0
                    else BenchmarkClass.ADEQUATE
                    if value < (bs.total_assets or value) * 0.3
                    else BenchmarkClass.WEAK
                )
            else:
                bench = _benchmark_ratio(
                    value,
                    excellent=exc,
                    strong=strong,
                    adequate=adeq,
                    higher_better=higher_better,
                )
            metrics.append(
                self._metric(
                    name=name,
                    formula=formula,
                    value=value,
                    inputs=inputs,
                    benchmark=bench,
                    trend=_trend(value, prior_dte if name == "debt_to_equity" else None, higher_better=higher_better),
                    periods=n,
                    interpretation=f"{name} = {value:.4f}." if value is not None else f"{name} unavailable.",
                    out=out,
                )
            )
        return tuple(metrics)

    def _efficiency(
        self,
        cur: FinancialStatements,
        prior: FinancialStatements | None,
        out: list[MetricExplanation],
    ) -> tuple[RatioMetric, ...]:
        inc, bs = cur.income_statement, cur.balance_sheet
        prev_bs = prior.balance_sheet if prior else None
        avg_assets = _avg(bs.total_assets, prev_bs.total_assets if prev_bs else None)
        avg_inv = _avg(bs.inventory, prev_bs.inventory if prev_bs else None)
        avg_ar = _avg(bs.accounts_receivable, prev_bs.accounts_receivable if prev_bs else None)
        avg_ap = _avg(bs.accounts_payable, prev_bs.accounts_payable if prev_bs else None)
        ca = _current_assets(bs)
        wc = (ca - bs.current_liabilities) if ca is not None and bs.current_liabilities is not None else None
        cogs = abs(inc.cogs) if inc.cogs is not None else None

        asset_to = _safe_div(inc.revenue, avg_assets)
        inv_to = _safe_div(cogs, avg_inv)
        ar_to = _safe_div(inc.revenue, avg_ar)
        ap_to = _safe_div(cogs, avg_ap)
        wc_to = _safe_div(inc.revenue, wc)
        fa_to = _safe_div(inc.revenue, bs.ppe)
        n = 2 if prior else 1

        metrics = []
        for name, formula, value, inputs in (
            ("asset_turnover", "revenue / average_total_assets", asset_to, {"revenue": inc.revenue, "avg_assets": avg_assets}),
            ("inventory_turnover", "|cogs| / average_inventory", inv_to, {"cogs": inc.cogs, "avg_inventory": avg_inv}),
            ("receivable_turnover", "revenue / average_receivables", ar_to, {"revenue": inc.revenue, "avg_ar": avg_ar}),
            ("payable_turnover", "|cogs| / average_payables", ap_to, {"cogs": inc.cogs, "avg_ap": avg_ap}),
            ("working_capital_turnover", "revenue / working_capital", wc_to, {"revenue": inc.revenue, "working_capital": wc}),
            ("fixed_asset_turnover", "revenue / ppe", fa_to, {"revenue": inc.revenue, "ppe": bs.ppe}),
        ):
            metrics.append(
                self._metric(
                    name=name,
                    formula=formula,
                    value=value,
                    inputs=inputs,
                    benchmark=_benchmark_ratio(value, excellent=1.5, strong=1.0, adequate=0.5),
                    trend=None,
                    periods=n,
                    interpretation=f"{name} = {value:.4f}." if value is not None else f"{name} unavailable.",
                    limitations="Single-period turnovers use ending balances when averages unavailable.",
                    out=out,
                )
            )
        return tuple(metrics)

    def _cash_ratios(
        self,
        cur: FinancialStatements,
        prior: FinancialStatements | None,
        out: list[MetricExplanation],
    ) -> tuple[RatioMetric, ...]:
        cf, inc, bs = cur.cash_flow, cur.income_statement, cur.balance_sheet
        ocf = cf.operating_cash_flow
        fcf = _fcf(cf)
        cl = bs.current_liabilities
        ocf_ratio = _safe_div(ocf, cl)
        ocf_margin = _safe_div(ocf, inc.revenue)
        fcf_margin = _safe_div(fcf, inc.revenue)
        cash_conv = _safe_div(fcf, ocf)
        capex_ocf = _safe_div(abs(cf.capex) if cf.capex is not None else None, abs(ocf) if ocf is not None else None)
        div_cov = _safe_div(fcf, abs(cf.dividends_paid) if cf.dividends_paid else None)
        debt_cov = _safe_div(ocf, _total_debt(bs))
        cash_int = _safe_div(ocf, abs(inc.interest_expense) if inc.interest_expense else None)
        n = 2 if prior else 1
        prior_ocf_m = None
        if prior is not None:
            prior_ocf_m = _safe_div(
                prior.cash_flow.operating_cash_flow, prior.income_statement.revenue
            )

        metrics = []
        for name, formula, value, inputs, higher_better, exc, strong, adeq in (
            ("operating_cash_flow_ratio", "OCF / current_liabilities", ocf_ratio, {"ocf": ocf, "current_liabilities": cl}, True, 0.5, 0.3, 0.1),
            ("operating_cash_flow_margin", "OCF / revenue", ocf_margin, {"ocf": ocf, "revenue": inc.revenue}, True, 0.2, 0.12, 0.05),
            ("free_cash_flow_margin", "FCF / revenue", fcf_margin, {"fcf": fcf, "revenue": inc.revenue}, True, 0.15, 0.08, 0.03),
            ("cash_conversion_ratio", "FCF / OCF", cash_conv, {"fcf": fcf, "ocf": ocf}, True, 0.8, 0.6, 0.4),
            ("capex_to_ocf", "|capex| / |OCF|", capex_ocf, {"capex": cf.capex, "ocf": ocf}, False, 0.3, 0.5, 0.8),
            ("dividend_coverage", "FCF / |dividends|", div_cov, {"fcf": fcf, "dividends": cf.dividends_paid}, True, 2.0, 1.5, 1.0),
            ("debt_coverage", "OCF / total_debt", debt_cov, {"ocf": ocf, "debt": _total_debt(bs)}, True, 0.5, 0.3, 0.15),
            ("cash_interest_coverage", "OCF / |interest|", cash_int, {"ocf": ocf, "interest": inc.interest_expense}, True, 8.0, 4.0, 2.0),
        ):
            metrics.append(
                self._metric(
                    name=name,
                    formula=formula,
                    value=value,
                    inputs=inputs,
                    benchmark=_benchmark_ratio(
                        value,
                        excellent=exc,
                        strong=strong,
                        adequate=adeq,
                        higher_better=higher_better,
                    ),
                    trend=_trend(value, prior_ocf_m if name == "operating_cash_flow_margin" else None, higher_better=higher_better),
                    periods=n,
                    interpretation=f"{name} = {value:.4f}." if value is not None else f"{name} unavailable.",
                    out=out,
                )
            )
        return tuple(metrics)

    def _shareholder(
        self,
        cur: FinancialStatements,
        prior: FinancialStatements | None,
        out: list[MetricExplanation],
    ) -> tuple[RatioMetric, ...]:
        inc, bs, cf = cur.income_statement, cur.balance_sheet, cur.cash_flow
        shares = inc.weighted_shares
        eq = _equity(bs)
        bvps = _safe_div(eq, shares)
        tangible = None if eq is None else eq - (bs.goodwill or 0.0) - (bs.intangibles or 0.0)
        tbvps = _safe_div(tangible, shares)
        re_ratio = _safe_div(bs.retained_earnings, eq)
        payout = _safe_div(abs(cf.dividends_paid) if cf.dividends_paid is not None else None, abs(inc.net_income) if inc.net_income else None)
        retention = None if payout is None else _clip01(1.0 - payout)
        n = 2 if prior else 1

        metrics = []
        for name, formula, value, inputs in (
            ("book_value_per_share", "equity / weighted_shares", bvps, {"equity": eq, "shares": shares}),
            ("tangible_book_value_per_share", "tangible_equity / weighted_shares", tbvps, {"tangible_equity": tangible, "shares": shares}),
            ("retained_earnings_ratio", "retained_earnings / equity", re_ratio, {"retained_earnings": bs.retained_earnings, "equity": eq}),
            ("dividend_payout_ratio", "|dividends| / |net_income|", payout, {"dividends": cf.dividends_paid, "net_income": inc.net_income}),
            ("dividend_retention_ratio", "1 - payout", retention, {"payout": payout}),
        ):
            metrics.append(
                self._metric(
                    name=name,
                    formula=formula,
                    value=value,
                    inputs=inputs,
                    benchmark=(
                        BenchmarkClass.INSUFFICIENT
                        if value is None
                        else BenchmarkClass.ADEQUATE
                    ),
                    trend=None,
                    periods=n,
                    interpretation=f"{name} = {value:.4f}." if value is not None else f"{name} unavailable.",
                    out=out,
                )
            )
        return tuple(metrics)

    def _capital_allocation(
        self,
        cur: FinancialStatements,
        cash_an,
        out: list[MetricExplanation],
    ) -> CapitalAllocationMetrics:
        cf = cur.cash_flow
        fcf = _fcf(cf)
        ocf = cf.operating_cash_flow
        capex_disc = _clip01(
            1.0
            - min(
                1.0,
                (_safe_div(abs(cf.capex), abs(ocf)) if cf.capex is not None and ocf else None)
                or 1.0,
            )
        ) if cf.capex is not None and ocf is not None else None
        # Prefer sibling cash quality when present — never invent perfect
        # sustainability merely because FCF exists (CV-001 / CV-005).
        div_sust = cash_an.quality.dividend_sustainability
        bb_sust = cash_an.quality.buyback_sustainability

        net_raise = None
        if cf.debt_issued is not None or cf.debt_repaid is not None:
            net_raise = (cf.debt_issued or 0.0) - abs(cf.debt_repaid or 0.0)
        debt_red = None
        if net_raise is not None:
            debt_red = 1.0 if net_raise < 0 else _clip01(1.0 - min(1.0, abs(net_raise) / max(abs(ocf or 1.0), 1.0)))

        parts = [p for p in (capex_disc, div_sust, bb_sust, debt_red) if p is not None]
        score = sum(parts) / len(parts) if parts else None
        out.append(
            build_explanation(
                name="capital_allocation_score",
                formula="mean(capex_discipline, dividend_sust, buyback_sust, debt_reduction)",
                inputs={
                    "capex_discipline": capex_disc,
                    "dividend_sustainability": div_sust,
                    "buyback_sustainability": bb_sust,
                    "debt_reduction_quality": debt_red,
                },
                intermediates={},
                result=score,
                confidence=_confidence(1, has_value=score is not None),
                interpretation=(
                    "Capital allocation score unavailable."
                    if score is None
                    else f"Capital allocation score = {score:.4f}."
                ),
                limitations="Composed from cash-flow intelligence sustainability metrics where available.",
            )
        )
        return CapitalAllocationMetrics(
            capex_discipline=capex_disc,
            dividend_sustainability=div_sust,
            buyback_sustainability=bb_sust,
            debt_reduction_quality=debt_red,
            capital_allocation_score=score,
        )

    def _flags(
        self,
        profitability,
        liquidity,
        leverage,
        efficiency,
        cash_flow,
        capital: CapitalAllocationMetrics,
        cash_an,
    ) -> tuple[RatioQualityFlag, ...]:
        flags: list[RatioQualityFlag] = []

        def _get(group, name: str) -> RatioMetric | None:
            return next((m for m in group if m.name == name), None)

        nm = _get(profitability, "net_margin")
        if nm and nm.value is not None:
            if nm.value >= 0.15:
                flags.append(RatioQualityFlag.EXCELLENT_PROFITABILITY)
            elif nm.value < 0.05:
                flags.append(RatioQualityFlag.WEAK_PROFITABILITY)

        cr = _get(liquidity, "current_ratio")
        if cr and cr.value is not None:
            if cr.value >= 1.5:
                flags.append(RatioQualityFlag.STRONG_LIQUIDITY)
            elif cr.value < 1.0:
                flags.append(RatioQualityFlag.WEAK_LIQUIDITY)

        dte = _get(leverage, "debt_to_equity")
        if dte and dte.value is not None:
            if dte.value >= 2.0:
                flags.append(RatioQualityFlag.HIGH_LEVERAGE)
            elif dte.value <= 0.5:
                flags.append(RatioQualityFlag.LOW_LEVERAGE)

        ato = _get(efficiency, "asset_turnover")
        if ato and ato.value is not None:
            if ato.value >= 1.0:
                flags.append(RatioQualityFlag.EFFICIENT_OPERATIONS)
            elif ato.value < 0.4:
                flags.append(RatioQualityFlag.POOR_EFFICIENCY)

        ocfm = _get(cash_flow, "operating_cash_flow_margin")
        if ocfm and ocfm.value is not None:
            if ocfm.value >= 0.12:
                flags.append(RatioQualityFlag.STRONG_CASH_GENERATION)
            elif ocfm.value < 0.03:
                flags.append(RatioQualityFlag.WEAK_CASH_GENERATION)

        # Sibling cash flags reinforce
        from financial.intelligence.cashflow_models import CashFlowQualityFlag

        if CashFlowQualityFlag.SHAREHOLDER_FRIENDLY in cash_an.quality_flags:
            flags.append(RatioQualityFlag.SHAREHOLDER_FRIENDLY)
        if (capital.capital_allocation_score or 1.0) < 0.55:
            flags.append(RatioQualityFlag.CAPITAL_ALLOCATION_WARNING)

        return tuple(dict.fromkeys(flags))

    def _trend_summary(
        self,
        profitability,
        liquidity,
        leverage,
        efficiency,
        cash_flow,
    ) -> RatioTrendSummary:
        def _first_trend(group) -> TrendDirection:
            for m in group:
                if m.trend is not None:
                    return m.trend
            return TrendDirection.STABLE

        return RatioTrendSummary(
            profitability=_first_trend(profitability),
            liquidity=_first_trend(liquidity),
            leverage=_first_trend(leverage),
            efficiency=_first_trend(efficiency),
            cash_flow=_first_trend(cash_flow),
        )
