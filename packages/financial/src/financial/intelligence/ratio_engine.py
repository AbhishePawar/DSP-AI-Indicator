"""Financial Ratio Engine (F2.5).

Composes Income / Balance / Cash Flow Intelligence into canonical ratios.
No forecasting, valuation, market data, or provider I/O.

Policy-compliant REPORTED / CALCULATED / UNAVAILABLE derivation lives in
``financial.derivation``.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

from financial.derivation import (
    FORMULA_ASSET_TURNOVER,
    FORMULA_AVERAGE_BALANCE,
    FORMULA_CASH_CONVERSION_CYCLE,
    FORMULA_CASH_CONVERSION_RATIO,
    FORMULA_CASH_RATIO,
    FORMULA_CURRENT_RATIO,
    FORMULA_DAYS_INVENTORY_OUTSTANDING,
    FORMULA_DAYS_PAYABLES_OUTSTANDING,
    FORMULA_DAYS_SALES_OUTSTANDING,
    FORMULA_DEBT_COVERAGE,
    FORMULA_DEBT_TO_ASSETS,
    FORMULA_DEBT_TO_EQUITY,
    FORMULA_DIVIDEND_COVERAGE,
    FORMULA_FCF,
    FORMULA_FCF_MARGIN,
    FORMULA_FIXED_ASSET_TURNOVER,
    FORMULA_GROSS_MARGIN,
    FORMULA_INVENTORY_TURNOVER,
    FORMULA_INVESTED_CAPITAL,
    FORMULA_NET_DEBT,
    FORMULA_NET_DEBT_TO_EBITDA,
    FORMULA_NET_MARGIN,
    FORMULA_NOPAT,
    FORMULA_OPERATING_MARGIN,
    FORMULA_PAYABLE_TURNOVER,
    FORMULA_QUICK_RATIO,
    FORMULA_RECEIVABLE_TURNOVER,
    FORMULA_ROA,
    FORMULA_ROCE,
    FORMULA_ROE,
    FORMULA_ROIC,
    FORMULA_TOTAL_DEBT,
    FORMULA_WORKING_CAPITAL,
    FORMULA_WORKING_CAPITAL_RATIO,
    FORMULA_WORKING_CAPITAL_TURNOVER,
    DerivationInput,
    DerivedFinancialValue,
    FinancialValueStatus,
    as_reported,
    derive,
)
from financial.derivation.formulas import get_formula
from financial.intelligence.balance_engine import BalanceSheetEngine
from financial.intelligence.cashflow_engine import CashFlowEngine
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


def _equity(bs) -> float | None:
    return bs.total_equity if bs.total_equity is not None else bs.equity


def _statement_derivation_input(
    stmt: FinancialStatements,
    field_id: str,
    value: float | None,
) -> DerivationInput:
    """Map a statement line item into a derivation input. Never invent values."""
    period = stmt.period
    meta = stmt.statement_metadata
    reported = value is not None
    return DerivationInput(
        field_id=field_id,
        value=value,
        status=(
            FinancialValueStatus.REPORTED
            if reported
            else FinancialValueStatus.UNAVAILABLE
        ),
        period_type=period.period_type,
        period_end=period.period_end,
        unit_scale=meta.unit_scale,
        currency=period.currency,
        source=meta.source or period.source,
    )


def _phase1_margin(
    stmt: FinancialStatements,
    formula_id: str,
    numerator_id: str,
    numerator: float | None,
) -> DerivedFinancialValue:
    """Same-period margin via the canonical derivation engine.

    Never falls back to an alternate formula. Calculated ratios are never
    labelled reported.
    """
    return derive(
        formula_id,
        {
            numerator_id: _statement_derivation_input(
                stmt, numerator_id, numerator
            ),
            "revenue": _statement_derivation_input(
                stmt, "revenue", stmt.income_statement.revenue
            ),
        },
    )


def _phase1_ratio_status(derived: DerivedFinancialValue) -> str:
    if derived.status is FinancialValueStatus.CALCULATED:
        return FinancialValueStatus.CALCULATED.value
    return FinancialValueStatus.UNAVAILABLE.value


def _phase1_ratio_value(derived: DerivedFinancialValue) -> float | None:
    if derived.status is FinancialValueStatus.CALCULATED:
        return derived.value
    return None


def _unavailable_derived(
    formula_id: str,
    reason: str,
    inputs: tuple[dict, ...] = (),
) -> DerivedFinancialValue:
    spec = get_formula(formula_id)
    return DerivedFinancialValue(
        status=FinancialValueStatus.UNAVAILABLE,
        value=None,
        formula_id=formula_id,
        formula=spec.formula if spec else None,
        inputs=inputs,
        unavailable_reason=reason,
    )


def _derive_roe(
    cur: FinancialStatements,
    prior: FinancialStatements | None,
) -> DerivedFinancialValue:
    """ROE = NI / average equity. Beginning equity is never invented."""
    end_eq = _equity(cur.balance_sheet)
    ni = cur.income_statement.net_income
    if prior is None:
        return _unavailable_derived(
            FORMULA_ROE,
            "missing_input",
            inputs=(
                _statement_derivation_input(cur, "net_income", ni).to_ref(),
                {
                    "field_id": "beginning_equity",
                    "value": None,
                    "status": FinancialValueStatus.UNAVAILABLE.value,
                    "period_type": None,
                    "period_end": None,
                    "fiscal_year": None,
                    "fiscal_quarter": None,
                    "unit_scale": None,
                    "currency": None,
                    "accounting_basis": None,
                    "source": "",
                    "converted_value": None,
                },
                _statement_derivation_input(cur, "ending_equity", end_eq).to_ref(),
            ),
        )
    return derive(
        FORMULA_ROE,
        {
            "net_income": _statement_derivation_input(cur, "net_income", ni),
            "beginning_equity": _statement_derivation_input(
                prior, "beginning_equity", _equity(prior.balance_sheet)
            ),
            "ending_equity": _statement_derivation_input(
                cur, "ending_equity", end_eq
            ),
        },
    )


def _derive_debt_to_equity(stmt: FinancialStatements) -> DerivedFinancialValue:
    """D/E requires both ST and LT debt; missing legs are not zero-filled."""
    bs = stmt.balance_sheet
    total_debt = _derive_total_debt(stmt)
    debt_input = _derived_input(total_debt, stmt, "total_debt")
    return derive(
        FORMULA_DEBT_TO_EQUITY,
        {
            "total_debt": debt_input,
            "equity": _statement_derivation_input(stmt, "equity", _equity(bs)),
        },
    )


def _derived_input(
    derived: DerivedFinancialValue,
    stmt: FinancialStatements,
    field_id: str,
) -> DerivationInput:
    return DerivationInput(
        field_id=field_id,
        value=derived.value,
        status=derived.status,
        period_type=stmt.period.period_type,
        period_end=stmt.period.period_end,
        unit_scale=stmt.statement_metadata.unit_scale,
        currency=stmt.period.currency,
        source=stmt.statement_metadata.source or stmt.period.source,
    )


def _derive_total_debt(stmt: FinancialStatements) -> DerivedFinancialValue:
    bs = stmt.balance_sheet
    return derive(
        FORMULA_TOTAL_DEBT,
        {
            "short_term_debt": _statement_derivation_input(
                stmt, "short_term_debt", bs.short_term_debt
            ),
            "long_term_debt": _statement_derivation_input(
                stmt, "long_term_debt", bs.long_term_debt
            ),
        },
    )


def _derive_fcf(stmt: FinancialStatements) -> DerivedFinancialValue:
    """Reported FCF when present; otherwise OCF − |capex| via FORMULA_FCF."""
    cf = stmt.cash_flow
    if cf.free_cash_flow is not None:
        return as_reported(
            _statement_derivation_input(
                stmt, "free_cash_flow", cf.free_cash_flow
            )
        )
    return derive(
        FORMULA_FCF,
        {
            "operating_cash_flow": _statement_derivation_input(
                stmt, "operating_cash_flow", cf.operating_cash_flow
            ),
            "capex": _statement_derivation_input(stmt, "capex", cf.capex),
        },
    )


def _derive_average_balance(
    cur: FinancialStatements,
    prior: FinancialStatements | None,
    *,
    field_prefix: str,
    beginning: float | None,
    ending: float | None,
) -> DerivedFinancialValue:
    if prior is None:
        return _unavailable_derived(
            FORMULA_AVERAGE_BALANCE,
            "missing_input",
            inputs=(
                {
                    "field_id": "beginning_balance",
                    "value": None,
                    "status": FinancialValueStatus.UNAVAILABLE.value,
                    "period_type": None,
                    "period_end": None,
                    "fiscal_year": None,
                    "fiscal_quarter": None,
                    "unit_scale": None,
                    "currency": None,
                    "accounting_basis": None,
                    "source": "",
                    "converted_value": None,
                },
                _statement_derivation_input(
                    cur, f"ending_{field_prefix}", ending
                ).to_ref(),
            ),
        )
    return derive(
        FORMULA_AVERAGE_BALANCE,
        {
            "beginning_balance": _statement_derivation_input(
                prior, "beginning_balance", beginning
            ),
            "ending_balance": _statement_derivation_input(
                cur, "ending_balance", ending
            ),
        },
    )


def _derive_roic(cur: FinancialStatements) -> DerivedFinancialValue:
    bs, inc = cur.balance_sheet, cur.income_statement
    total_debt = _derive_total_debt(cur)
    invested = derive(
        FORMULA_INVESTED_CAPITAL,
        {
            "equity": _statement_derivation_input(cur, "equity", _equity(bs)),
            "total_debt": _derived_input(total_debt, cur, "total_debt"),
            "cash": _statement_derivation_input(cur, "cash", bs.cash),
        },
    )
    nopat = derive(
        FORMULA_NOPAT,
        {
            "ebit": _statement_derivation_input(cur, "ebit", inc.ebit),
            "tax": _statement_derivation_input(cur, "tax", inc.tax),
            "pretax_income": _statement_derivation_input(
                cur, "pretax_income", inc.pretax_income
            ),
        },
    )
    return derive(
        FORMULA_ROIC,
        {
            "nopat": _derived_input(nopat, cur, "nopat"),
            "invested_capital": _derived_input(invested, cur, "invested_capital"),
        },
    )


def _derive_from_fields(
    stmt: FinancialStatements,
    formula_id: str,
    fields: dict[str, float | None],
) -> DerivedFinancialValue:
    """Same-statement derivation. Missing fields stay unavailable — never 0-filled."""
    return derive(
        formula_id,
        {
            name: _statement_derivation_input(stmt, name, value)
            for name, value in fields.items()
        },
    )


def _derive_working_capital(stmt: FinancialStatements) -> DerivedFinancialValue:
    """Working-capital amount from reported current assets and liabilities."""
    bs = stmt.balance_sheet
    return _derive_from_fields(
        stmt,
        FORMULA_WORKING_CAPITAL,
        {
            "current_assets": bs.current_assets,
            "current_liabilities": bs.current_liabilities,
        },
    )


def _derive_working_capital_turnover(
    stmt: FinancialStatements,
) -> tuple[DerivedFinancialValue, DerivedFinancialValue]:
    """Ending WC turnover: revenue / (CA − CL). Does not average periods."""
    wc = _derive_working_capital(stmt)
    turnover = derive(
        FORMULA_WORKING_CAPITAL_TURNOVER,
        {
            "revenue": _statement_derivation_input(
                stmt, "revenue", stmt.income_statement.revenue
            ),
            "working_capital": _derived_input(wc, stmt, "working_capital"),
        },
    )
    return wc, turnover


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
        capital = self._capital_allocation(primary, cash_an, income_an, explanations)
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
        status: str | None = None,
        formula_id: str | None = None,
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
            status=status,
            formula_id=formula_id,
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

        def _append_phase1(
            name: str,
            formula_id: str,
            numer_id: str,
            numer: float | None,
        ) -> None:
            derived = _phase1_margin(cur, formula_id, numer_id, numer)
            value = _phase1_ratio_value(derived)
            status = _phase1_ratio_status(derived)
            prior_v = None
            if prior is not None:
                prior_derived = _phase1_margin(
                    prior,
                    formula_id,
                    numer_id,
                    getattr(prior.income_statement, numer_id),
                )
                prior_v = _phase1_ratio_value(prior_derived)
            metrics.append(
                self._metric(
                    name=name,
                    formula=derived.formula or "",
                    formula_id=derived.formula_id,
                    value=value,
                    inputs={numer_id: numer, "revenue": rev},
                    intermediates={
                        "formula_id": derived.formula_id,
                        "derivation_inputs": [dict(item) for item in derived.inputs],
                        "unavailable_reason": derived.unavailable_reason,
                    },
                    benchmark=_benchmark_margin(value),
                    trend=_trend(value, prior_v),
                    periods=n,
                    interpretation=(
                        f"{name} = {value:.4f}."
                        if value is not None
                        else f"{name} unavailable."
                    ),
                    status=status,
                    out=out,
                )
            )

        _append_phase1(
            "gross_margin", FORMULA_GROSS_MARGIN, "gross_profit", inc.gross_profit
        )
        _append_phase1(
            "operating_margin", FORMULA_OPERATING_MARGIN, "ebit", inc.ebit
        )

        legacy_pairs = [
            ("ebit_margin", "ebit / revenue", _safe_div(inc.ebit, rev), {"ebit": inc.ebit, "revenue": rev}),
            ("ebitda_margin", "ebitda / revenue", _safe_div(inc.ebitda, rev), {"ebitda": inc.ebitda, "revenue": rev}),
        ]
        for name, formula, value, inputs in legacy_pairs:
            p_map = {
                "ebit_margin": lambda s: _safe_div(s.income_statement.ebit, s.income_statement.revenue),
                "ebitda_margin": lambda s: _safe_div(s.income_statement.ebitda, s.income_statement.revenue),
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

        _append_phase1(
            "net_margin", FORMULA_NET_MARGIN, "net_income", inc.net_income
        )

        roa_derived = _derive_from_fields(
            cur,
            FORMULA_ROA,
            {"net_income": inc.net_income, "total_assets": bs.total_assets},
        )
        roa_value = _phase1_ratio_value(roa_derived)
        prior_roa = None
        if prior is not None:
            prior_roa = _phase1_ratio_value(
                _derive_from_fields(
                    prior,
                    FORMULA_ROA,
                    {
                        "net_income": prior.income_statement.net_income,
                        "total_assets": prior.balance_sheet.total_assets,
                    },
                )
            )
        roce_derived = _derive_from_fields(
            cur,
            FORMULA_ROCE,
            {
                "ebit": inc.ebit,
                "total_assets": bs.total_assets,
                "current_liabilities": bs.current_liabilities,
            },
        )
        roce_value = _phase1_ratio_value(roce_derived)
        roic_derived = _derive_roic(cur)
        roic_value = _phase1_ratio_value(roic_derived)
        roe_derived = _derive_roe(cur, prior)

        metrics.append(
            self._metric(
                name="roa",
                formula=roa_derived.formula or "",
                formula_id=roa_derived.formula_id,
                value=roa_value,
                inputs={
                    "net_income": inc.net_income,
                    "total_assets": bs.total_assets,
                },
                intermediates={
                    "formula_id": roa_derived.formula_id,
                    "derivation_inputs": [dict(item) for item in roa_derived.inputs],
                    "unavailable_reason": roa_derived.unavailable_reason,
                },
                benchmark=_benchmark_margin(roa_value),
                trend=_trend(roa_value, prior_roa),
                periods=n,
                interpretation=(
                    f"roa = {roa_value:.4f}."
                    if roa_value is not None
                    else "roa unavailable."
                ),
                status=_phase1_ratio_status(roa_derived),
                out=out,
            )
        )
        roe_value = _phase1_ratio_value(roe_derived)
        metrics.append(
            self._metric(
                name="roe",
                formula=roe_derived.formula or "",
                formula_id=roe_derived.formula_id,
                value=roe_value,
                inputs={
                    "net_income": inc.net_income,
                    "beginning_equity": (
                        _equity(prior.balance_sheet) if prior is not None else None
                    ),
                    "ending_equity": _equity(bs),
                },
                intermediates={
                    "formula_id": roe_derived.formula_id,
                    "derivation_inputs": [dict(item) for item in roe_derived.inputs],
                    "unavailable_reason": roe_derived.unavailable_reason,
                },
                benchmark=_benchmark_margin(roe_value),
                trend=None,
                periods=n,
                interpretation=(
                    f"roe = {roe_value:.4f}."
                    if roe_value is not None
                    else "roe unavailable."
                ),
                status=_phase1_ratio_status(roe_derived),
                out=out,
            )
        )
        for name, derived, value, inputs in (
            (
                "roce",
                roce_derived,
                roce_value,
                {
                    "ebit": inc.ebit,
                    "total_assets": bs.total_assets,
                    "current_liabilities": bs.current_liabilities,
                },
            ),
            (
                "roic",
                roic_derived,
                roic_value,
                {
                    "ebit": inc.ebit,
                    "tax": inc.tax,
                    "pretax_income": inc.pretax_income,
                    "equity": _equity(bs),
                    "short_term_debt": bs.short_term_debt,
                    "long_term_debt": bs.long_term_debt,
                    "cash": bs.cash,
                },
            ),
        ):
            metrics.append(
                self._metric(
                    name=name,
                    formula=derived.formula or "",
                    formula_id=derived.formula_id,
                    value=value,
                    inputs=inputs,
                    intermediates={
                        "formula_id": derived.formula_id,
                        "derivation_inputs": [dict(item) for item in derived.inputs],
                        "unavailable_reason": derived.unavailable_reason,
                    },
                    benchmark=_benchmark_margin(value),
                    trend=None,
                    periods=n,
                    interpretation=(
                        f"{name} = {value:.4f}."
                        if value is not None
                        else f"{name} unavailable."
                    ),
                    status=_phase1_ratio_status(derived),
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
        n = 2 if prior else 1
        prior_cr = None
        if prior is not None:
            prior_cr = _phase1_ratio_value(
                _derive_from_fields(
                    prior,
                    FORMULA_CURRENT_RATIO,
                    {
                        "current_assets": prior.balance_sheet.current_assets,
                        "current_liabilities": prior.balance_sheet.current_liabilities,
                    },
                )
            )

        _ = balance_an
        specs: tuple[
            tuple[str, str, dict[str, float | None], dict[str, float | None], bool],
            ...,
        ] = (
            (
                "current_ratio",
                FORMULA_CURRENT_RATIO,
                {
                    "current_assets": bs.current_assets,
                    "current_liabilities": bs.current_liabilities,
                },
                {
                    "current_assets": bs.current_assets,
                    "current_liabilities": bs.current_liabilities,
                },
                True,
            ),
            (
                "quick_ratio",
                FORMULA_QUICK_RATIO,
                {
                    "current_assets": bs.current_assets,
                    "inventory": bs.inventory,
                    "current_liabilities": bs.current_liabilities,
                },
                {
                    "current_assets": bs.current_assets,
                    "inventory": bs.inventory,
                    "current_liabilities": bs.current_liabilities,
                },
                False,
            ),
            (
                "cash_ratio",
                FORMULA_CASH_RATIO,
                {
                    "cash": bs.cash,
                    "short_term_investments": bs.short_term_investments,
                    "current_liabilities": bs.current_liabilities,
                },
                {
                    "cash": bs.cash,
                    "sti": bs.short_term_investments,
                    "current_liabilities": bs.current_liabilities,
                },
                False,
            ),
            (
                "working_capital_ratio",
                FORMULA_WORKING_CAPITAL_RATIO,
                {
                    "current_assets": bs.current_assets,
                    "current_liabilities": bs.current_liabilities,
                },
                {
                    "current_assets": bs.current_assets,
                    "current_liabilities": bs.current_liabilities,
                },
                True,
            ),
        )
        metrics = []
        for name, formula_id, derive_fields, inputs, uses_cr_trend in specs:
            derived = _derive_from_fields(cur, formula_id, derive_fields)
            value = _phase1_ratio_value(derived)
            metrics.append(
                self._metric(
                    name=name,
                    formula=derived.formula or "",
                    formula_id=derived.formula_id,
                    value=value,
                    inputs=inputs,
                    intermediates={
                        "formula_id": derived.formula_id,
                        "derivation_inputs": [dict(item) for item in derived.inputs],
                        "unavailable_reason": derived.unavailable_reason,
                    },
                    benchmark=_benchmark_ratio(
                        value, excellent=2.0, strong=1.5, adequate=1.0
                    ),
                    trend=_trend(value, prior_cr if uses_cr_trend else None),
                    periods=n,
                    interpretation=(
                        f"{name} = {value:.4f}."
                        if value is not None
                        else f"{name} unavailable."
                    ),
                    risk_notes=(
                        "Below 1.0 indicates short-term solvency pressure."
                        if value is not None and value < 1.0
                        else ""
                    ),
                    status=_phase1_ratio_status(derived),
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
        total_debt_derived = _derive_total_debt(cur)
        debt = _phase1_ratio_value(total_debt_derived)
        dte_derived = _derive_debt_to_equity(cur)
        dte = _phase1_ratio_value(dte_derived)
        dta_derived = derive(
            FORMULA_DEBT_TO_ASSETS,
            {
                "total_debt": _derived_input(total_debt_derived, cur, "total_debt"),
                "total_assets": _statement_derivation_input(
                    cur, "total_assets", bs.total_assets
                ),
            },
        )
        dta = _phase1_ratio_value(dta_derived)
        net_debt_derived = derive(
            FORMULA_NET_DEBT,
            {
                "total_debt": _derived_input(total_debt_derived, cur, "total_debt"),
                "cash": _statement_derivation_input(cur, "cash", bs.cash),
            },
        )
        net_debt = _phase1_ratio_value(net_debt_derived)
        nd_ebitda_derived = derive(
            FORMULA_NET_DEBT_TO_EBITDA,
            {
                "net_debt": _derived_input(net_debt_derived, cur, "net_debt"),
                "ebitda": _statement_derivation_input(cur, "ebitda", inc.ebitda),
            },
        )
        nd_ebitda = _phase1_ratio_value(nd_ebitda_derived)
        equity_ratio = _safe_div(eq, bs.total_assets)
        interest_cov = _safe_div(inc.ebit, abs(inc.interest_expense) if inc.interest_expense else None)
        fin_lev = _safe_div(bs.total_assets, eq)
        n = 2 if prior else 1
        prior_dte = (
            _phase1_ratio_value(_derive_debt_to_equity(prior)) if prior is not None else None
        )

        metrics = []
        metrics.append(
            self._metric(
                name="debt_to_equity",
                formula=dte_derived.formula or "",
                formula_id=dte_derived.formula_id,
                value=dte,
                inputs={
                    "equity": eq,
                    "short_term_debt": bs.short_term_debt,
                    "long_term_debt": bs.long_term_debt,
                },
                intermediates={
                    "formula_id": dte_derived.formula_id,
                    "derivation_inputs": [dict(item) for item in dte_derived.inputs],
                    "unavailable_reason": dte_derived.unavailable_reason,
                },
                benchmark=_benchmark_ratio(
                    dte,
                    excellent=0.3,
                    strong=0.75,
                    adequate=1.5,
                    higher_better=False,
                ),
                trend=_trend(dte, prior_dte, higher_better=False),
                periods=n,
                interpretation=(
                    f"debt_to_equity = {dte:.4f}."
                    if dte is not None
                    else "debt_to_equity unavailable."
                ),
                status=_phase1_ratio_status(dte_derived),
                out=out,
            )
        )
        derived_specs = (
            (
                "debt_to_assets",
                dta_derived,
                dta,
                {"debt": debt, "total_assets": bs.total_assets},
                False,
                0.2,
                0.4,
                0.6,
            ),
            (
                "net_debt",
                net_debt_derived,
                net_debt,
                {"debt": debt, "cash": bs.cash},
                False,
                -1e18,
                0.0,
                1e18,
            ),
            (
                "net_debt_to_ebitda",
                nd_ebitda_derived,
                nd_ebitda,
                {"net_debt": net_debt, "ebitda": inc.ebitda},
                False,
                1.0,
                2.0,
                3.5,
            ),
        )
        for name, derived, value, inputs, higher_better, exc, strong, adeq in derived_specs:
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
                    formula=derived.formula or "",
                    formula_id=derived.formula_id,
                    value=value,
                    inputs=inputs,
                    intermediates={
                        "formula_id": derived.formula_id,
                        "derivation_inputs": [dict(item) for item in derived.inputs],
                        "unavailable_reason": derived.unavailable_reason,
                    },
                    benchmark=bench,
                    trend=None,
                    periods=n,
                    interpretation=(
                        f"{name} = {value:.4f}."
                        if value is not None
                        else f"{name} unavailable."
                    ),
                    status=_phase1_ratio_status(derived),
                    out=out,
                )
            )
        legacy_specs = (
            ("equity_ratio", "equity / total_assets", equity_ratio, {"equity": eq, "total_assets": bs.total_assets}, True, 0.5, 0.4, 0.3),
            ("interest_coverage", "ebit / |interest_expense|", interest_cov, {"ebit": inc.ebit, "interest_expense": inc.interest_expense}, True, 8.0, 4.0, 2.0),
            ("financial_leverage", "total_assets / equity", fin_lev, {"total_assets": bs.total_assets, "equity": eq}, False, 1.5, 2.5, 3.5),
        )
        for name, formula, value, inputs, higher_better, exc, strong, adeq in legacy_specs:
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
                    trend=None,
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
        n = 2 if prior else 1

        avg_assets_d = _derive_average_balance(
            cur,
            prior,
            field_prefix="total_assets",
            beginning=prev_bs.total_assets if prev_bs else None,
            ending=bs.total_assets,
        )
        asset_to_d = derive(
            FORMULA_ASSET_TURNOVER,
            {
                "revenue": _statement_derivation_input(cur, "revenue", inc.revenue),
                "average_total_assets": _derived_input(
                    avg_assets_d, cur, "average_total_assets"
                ),
            },
        )
        avg_inv_d = _derive_average_balance(
            cur,
            prior,
            field_prefix="inventory",
            beginning=prev_bs.inventory if prev_bs else None,
            ending=bs.inventory,
        )
        inv_to_d = derive(
            FORMULA_INVENTORY_TURNOVER,
            {
                "cogs": _statement_derivation_input(cur, "cogs", inc.cogs),
                "average_inventory": _derived_input(
                    avg_inv_d, cur, "average_inventory"
                ),
            },
        )
        avg_ar_d = _derive_average_balance(
            cur,
            prior,
            field_prefix="accounts_receivable",
            beginning=prev_bs.accounts_receivable if prev_bs else None,
            ending=bs.accounts_receivable,
        )
        ar_to_d = derive(
            FORMULA_RECEIVABLE_TURNOVER,
            {
                "revenue": _statement_derivation_input(cur, "revenue", inc.revenue),
                "average_receivables": _derived_input(
                    avg_ar_d, cur, "average_receivables"
                ),
            },
        )
        avg_ap_d = _derive_average_balance(
            cur,
            prior,
            field_prefix="accounts_payable",
            beginning=prev_bs.accounts_payable if prev_bs else None,
            ending=bs.accounts_payable,
        )
        ap_to_d = derive(
            FORMULA_PAYABLE_TURNOVER,
            {
                "cogs": _statement_derivation_input(cur, "cogs", inc.cogs),
                "average_payables": _derived_input(
                    avg_ap_d, cur, "average_payables"
                ),
            },
        )
        wc_derived, wc_to_derived = _derive_working_capital_turnover(cur)
        wc = _phase1_ratio_value(wc_derived)
        wc_to = _phase1_ratio_value(wc_to_derived)
        fa_to_d = _derive_from_fields(
            cur,
            FORMULA_FIXED_ASSET_TURNOVER,
            {"revenue": inc.revenue, "ppe": bs.ppe},
        )
        dso_d = derive(
            FORMULA_DAYS_SALES_OUTSTANDING,
            {
                "receivable_turnover": _derived_input(
                    ar_to_d, cur, "receivable_turnover"
                ),
            },
        )
        dio_d = derive(
            FORMULA_DAYS_INVENTORY_OUTSTANDING,
            {
                "inventory_turnover": _derived_input(
                    inv_to_d, cur, "inventory_turnover"
                ),
            },
        )
        dpo_d = derive(
            FORMULA_DAYS_PAYABLES_OUTSTANDING,
            {
                "payable_turnover": _derived_input(ap_to_d, cur, "payable_turnover"),
            },
        )
        ccc_d = derive(
            FORMULA_CASH_CONVERSION_CYCLE,
            {
                "days_sales_outstanding": _derived_input(
                    dso_d, cur, "days_sales_outstanding"
                ),
                "days_inventory_outstanding": _derived_input(
                    dio_d, cur, "days_inventory_outstanding"
                ),
                "days_payables_outstanding": _derived_input(
                    dpo_d, cur, "days_payables_outstanding"
                ),
            },
        )

        derived_specs: tuple[
            tuple[
                str,
                DerivedFinancialValue,
                dict[str, float | None],
                str,
                bool,
            ],
            ...,
        ] = (
            (
                "asset_turnover",
                asset_to_d,
                {"revenue": inc.revenue, "avg_assets": _phase1_ratio_value(avg_assets_d)},
                "Average total assets require prior-period balance sheet.",
                False,
            ),
            (
                "inventory_turnover",
                inv_to_d,
                {"cogs": inc.cogs, "avg_inventory": _phase1_ratio_value(avg_inv_d)},
                "Average inventory requires prior-period balance sheet.",
                False,
            ),
            (
                "receivable_turnover",
                ar_to_d,
                {"revenue": inc.revenue, "avg_ar": _phase1_ratio_value(avg_ar_d)},
                "Average receivables require prior-period balance sheet.",
                False,
            ),
            (
                "payable_turnover",
                ap_to_d,
                {"cogs": inc.cogs, "avg_ap": _phase1_ratio_value(avg_ap_d)},
                "Average payables require prior-period balance sheet.",
                False,
            ),
            (
                "fixed_asset_turnover",
                fa_to_d,
                {"revenue": inc.revenue, "ppe": bs.ppe},
                "",
                False,
            ),
            (
                "days_sales_outstanding",
                dso_d,
                {"receivable_turnover": _phase1_ratio_value(ar_to_d)},
                "Days metrics are raw evidence from turnovers — no invented warning thresholds.",
                True,
            ),
            (
                "days_inventory_outstanding",
                dio_d,
                {"inventory_turnover": _phase1_ratio_value(inv_to_d)},
                "Days metrics are raw evidence from turnovers — no invented warning thresholds.",
                True,
            ),
            (
                "days_payables_outstanding",
                dpo_d,
                {"payable_turnover": _phase1_ratio_value(ap_to_d)},
                "Days metrics are raw evidence from turnovers — no invented warning thresholds.",
                True,
            ),
            (
                "cash_conversion_cycle",
                ccc_d,
                {
                    "dso": _phase1_ratio_value(dso_d),
                    "dio": _phase1_ratio_value(dio_d),
                    "dpo": _phase1_ratio_value(dpo_d),
                },
                "Days metrics are raw evidence from turnovers — no invented warning thresholds.",
                True,
            ),
        )

        metrics: list[RatioMetric] = []
        metrics.append(
            self._metric(
                name="working_capital_turnover",
                formula=wc_to_derived.formula or "revenue / working_capital",
                formula_id=wc_to_derived.formula_id,
                value=wc_to,
                inputs={"revenue": inc.revenue, "working_capital": wc},
                intermediates={
                    "formula_id": wc_to_derived.formula_id,
                    "derivation_inputs": [dict(item) for item in wc_to_derived.inputs],
                    "unavailable_reason": wc_to_derived.unavailable_reason,
                },
                benchmark=_benchmark_ratio(wc_to, excellent=1.5, strong=1.0, adequate=0.5),
                trend=None,
                periods=n,
                interpretation=(
                    f"working_capital_turnover = {wc_to:.4f}."
                    if wc_to is not None
                    else "working_capital_turnover unavailable."
                ),
                limitations=(
                    "Ending working capital from reported current assets "
                    "and current liabilities — not an average."
                ),
                status=_phase1_ratio_status(wc_to_derived),
                out=out,
            )
        )
        for name, derived, inputs, limitations, is_days in derived_specs:
            value = _phase1_ratio_value(derived)
            metrics.append(
                self._metric(
                    name=name,
                    formula=derived.formula or "",
                    formula_id=derived.formula_id,
                    value=value,
                    inputs=inputs,
                    intermediates={
                        "formula_id": derived.formula_id,
                        "derivation_inputs": [dict(item) for item in derived.inputs],
                        "unavailable_reason": derived.unavailable_reason,
                    },
                    benchmark=(
                        BenchmarkClass.INSUFFICIENT
                        if is_days
                        else _benchmark_ratio(
                            value, excellent=1.5, strong=1.0, adequate=0.5
                        )
                    ),
                    trend=None,
                    periods=n,
                    interpretation=(
                        f"{name} = {value:.4f}."
                        if value is not None
                        else f"{name} unavailable."
                    ),
                    limitations=limitations,
                    status=_phase1_ratio_status(derived),
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
        fcf_derived = _derive_fcf(cur)
        fcf = _phase1_ratio_value(fcf_derived)
        total_debt_derived = _derive_total_debt(cur)
        debt = _phase1_ratio_value(total_debt_derived)
        cl = bs.current_liabilities
        ocf_ratio = _safe_div(ocf, cl)
        ocf_margin = _safe_div(ocf, inc.revenue)
        fcf_margin_d = derive(
            FORMULA_FCF_MARGIN,
            {
                "fcf": _derived_input(fcf_derived, cur, "fcf"),
                "revenue": _statement_derivation_input(cur, "revenue", inc.revenue),
            },
        )
        fcf_margin = _phase1_ratio_value(fcf_margin_d)
        cash_conv_d = derive(
            FORMULA_CASH_CONVERSION_RATIO,
            {
                "fcf": _derived_input(fcf_derived, cur, "fcf"),
                "operating_cash_flow": _statement_derivation_input(
                    cur, "operating_cash_flow", ocf
                ),
            },
        )
        cash_conv = _phase1_ratio_value(cash_conv_d)
        capex_ocf = _safe_div(abs(cf.capex) if cf.capex is not None else None, abs(ocf) if ocf is not None else None)
        div_cov_d = derive(
            FORMULA_DIVIDEND_COVERAGE,
            {
                "fcf": _derived_input(fcf_derived, cur, "fcf"),
                "dividends_paid": _statement_derivation_input(
                    cur, "dividends_paid", cf.dividends_paid
                ),
            },
        )
        div_cov = _phase1_ratio_value(div_cov_d)
        debt_cov_d = derive(
            FORMULA_DEBT_COVERAGE,
            {
                "operating_cash_flow": _statement_derivation_input(
                    cur, "operating_cash_flow", ocf
                ),
                "total_debt": _derived_input(total_debt_derived, cur, "total_debt"),
            },
        )
        debt_cov = _phase1_ratio_value(debt_cov_d)
        cash_int = _safe_div(ocf, abs(inc.interest_expense) if inc.interest_expense else None)
        n = 2 if prior else 1
        prior_ocf_m = None
        if prior is not None:
            prior_ocf_m = _safe_div(
                prior.cash_flow.operating_cash_flow, prior.income_statement.revenue
            )

        metrics = []
        legacy_specs = (
            ("operating_cash_flow_ratio", "OCF / current_liabilities", ocf_ratio, {"ocf": ocf, "current_liabilities": cl}, True, 0.5, 0.3, 0.1),
            ("operating_cash_flow_margin", "OCF / revenue", ocf_margin, {"ocf": ocf, "revenue": inc.revenue}, True, 0.2, 0.12, 0.05),
            ("capex_to_ocf", "|capex| / |OCF|", capex_ocf, {"capex": cf.capex, "ocf": ocf}, False, 0.3, 0.5, 0.8),
            ("cash_interest_coverage", "OCF / |interest|", cash_int, {"ocf": ocf, "interest": inc.interest_expense}, True, 8.0, 4.0, 2.0),
        )
        derived_specs = (
            (
                "free_cash_flow_margin",
                fcf_margin_d,
                fcf_margin,
                {"fcf": fcf, "revenue": inc.revenue},
                True,
                0.15,
                0.08,
                0.03,
            ),
            (
                "cash_conversion_ratio",
                cash_conv_d,
                cash_conv,
                {"fcf": fcf, "ocf": ocf},
                True,
                0.8,
                0.6,
                0.4,
            ),
            (
                "dividend_coverage",
                div_cov_d,
                div_cov,
                {"fcf": fcf, "dividends": cf.dividends_paid},
                True,
                2.0,
                1.5,
                1.0,
            ),
            (
                "debt_coverage",
                debt_cov_d,
                debt_cov,
                {"ocf": ocf, "debt": debt},
                True,
                0.5,
                0.3,
                0.15,
            ),
        )
        for name, derived, value, inputs, higher_better, exc, strong, adeq in derived_specs:
            metrics.append(
                self._metric(
                    name=name,
                    formula=derived.formula or "",
                    formula_id=derived.formula_id,
                    value=value,
                    inputs=inputs,
                    intermediates={
                        "formula_id": derived.formula_id,
                        "derivation_inputs": [dict(item) for item in derived.inputs],
                        "unavailable_reason": derived.unavailable_reason,
                    },
                    benchmark=_benchmark_ratio(
                        value,
                        excellent=exc,
                        strong=strong,
                        adequate=adeq,
                        higher_better=higher_better,
                    ),
                    trend=None,
                    periods=n,
                    interpretation=(
                        f"{name} = {value:.4f}."
                        if value is not None
                        else f"{name} unavailable."
                    ),
                    status=_phase1_ratio_status(derived),
                    out=out,
                )
            )
        for name, formula, value, inputs, higher_better, exc, strong, adeq in legacy_specs:
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
        income_an,
        out: list[MetricExplanation],
    ) -> CapitalAllocationMetrics:
        cf = cur.cash_flow
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

        # True share dilution from income intelligence (weighted_shares history).
        # Not aliased from buybacks / debt reduction.
        share_dilution = getattr(income_an.profitability, "share_dilution_rate", None)
        dilution_disc = getattr(income_an.profitability, "dilution_discipline", None)

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
                limitations=(
                    "Composed from cash-flow intelligence sustainability metrics where "
                    "available. Share dilution is exposed separately and not folded into "
                    "this mean without an architecture decision."
                ),
            )
        )
        if share_dilution is not None or dilution_disc is not None:
            out.append(
                build_explanation(
                    name="share_dilution_rate",
                    formula="(weighted_shares_end - weighted_shares_start) / start [annual FY]",
                    inputs={
                        "share_dilution_rate": share_dilution,
                        "dilution_discipline": dilution_disc,
                    },
                    intermediates={},
                    result=share_dilution,
                    confidence=_confidence(1, has_value=share_dilution is not None),
                    interpretation=(
                        "Share dilution unavailable."
                        if share_dilution is None
                        else f"Share dilution rate = {share_dilution:.4f}."
                    ),
                    limitations=(
                        "Uses statement weighted_shares as provided; does not invent "
                        "split adjustments. Distinct from buyback activity."
                    ),
                )
            )
        return CapitalAllocationMetrics(
            capex_discipline=capex_disc,
            dividend_sustainability=div_sust,
            buyback_sustainability=bb_sust,
            debt_reduction_quality=debt_red,
            capital_allocation_score=score,
            share_dilution_rate=share_dilution,
            dilution_discipline=dilution_disc,
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
        # Treat 0.0 as a real (weak) score — do not coerce via `or 1.0`.
        if (
            capital.capital_allocation_score is not None
            and capital.capital_allocation_score < 0.55
        ):
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
