"""Cash Flow Intelligence engine (F2.4).

Deterministic domain analysis of normalized CashFlowStatement series.
No forecasting, valuation, market data, or provider I/O.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Sequence

from financial.cash_flow import CashFlowStatement
from financial.intelligence.cashflow_explainability import (
    CASHFLOW_RESEARCH_DISCLAIMER,
    MetricExplanation,
    build_explanation,
)
from financial.intelligence.cashflow_models import (
    CashFlowAnalysis,
    CashFlowAnalysisMetadata,
    CashFlowQualityFlag,
    CashFlowTrendSummary,
    CashQualityMetrics,
    FinancingCashMetrics,
    FreeCashFlowMetrics,
    GrowthInvestmentClass,
    InvestingCashMetrics,
    OperatingCashMetrics,
)
from financial.intelligence.cashflow_validation import (
    _computed_fcf,
    coerce_cashflow_series,
    validate_cashflow_for_analysis,
)
from financial.intelligence.income_models import TrendDirection
from financial.intelligence.quality_signals import fcf_to_earnings_ratio
from financial.models import FinancialSnapshot, FinancialStatements

__all__ = ["CashFlowEngine", "CASHFLOW_INTELLIGENCE_VERSION"]

CASHFLOW_INTELLIGENCE_VERSION = "0.4.0-cashflow"

_STRONG_OCF_GROWTH = 0.05
_WEAK_OCF = 0.0
_HEAVY_CAPEX = 0.80  # |capex| / OCF
_AGGRESSIVE_DEBT = 0.50  # debt_issued / max(|OCF|, 1)


def _safe_div(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None or denom == 0:
        return None
    result = numer / denom
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior)


def _clip01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _stability(values: Sequence[float]) -> float | None:
    clean = [v for v in values if math.isfinite(v)]
    if len(clean) < 2:
        return None
    mean = statistics.fmean(clean)
    if mean == 0:
        return 1.0 if all(v == 0 for v in clean) else 0.0
    cv = abs(statistics.pstdev(clean) / mean)
    return 1.0 / (1.0 + cv)


def _confidence(n: int, *, has_value: bool) -> str:
    if not has_value:
        return "insufficient"
    if n >= 3:
        return "high"
    if n >= 2:
        return "medium"
    return "low"


def _trend_from_delta(delta: float | None, *, improve_when_up: bool = True) -> TrendDirection:
    if delta is None:
        return TrendDirection.STABLE
    if abs(delta) < 0.02:
        return TrendDirection.STABLE
    up = delta > 0
    if improve_when_up:
        return TrendDirection.IMPROVING if up else TrendDirection.WEAKENING
    return TrendDirection.IMPROVING if not up else TrendDirection.WEAKENING


def _resolve_fcf(cf: CashFlowStatement) -> tuple[float | None, str]:
    if cf.free_cash_flow is not None:
        return cf.free_cash_flow, "reported"
    computed = _computed_fcf(cf)
    if computed is not None:
        return computed, "computed_ocf_minus_abs_capex"
    return None, "unavailable"


class CashFlowEngine:
    """Analyze one or more normalized cash-flow statements."""

    def analyze(
        self,
        source: CashFlowStatement
        | FinancialStatements
        | FinancialSnapshot
        | dict
        | Sequence[CashFlowStatement | FinancialStatements],
        *,
        history: Sequence[CashFlowStatement | FinancialStatements] | None = None,
    ) -> CashFlowAnalysis:
        """Run Cash Flow Intelligence."""
        if history is not None and not isinstance(
            source, (list, tuple, FinancialSnapshot)
        ):
            series: list[Any] = list(history)
            series.append(source)
            flows, stmts, meta = coerce_cashflow_series(series)
        else:
            flows, stmts, meta = coerce_cashflow_series(source)

        primary = flows[-1]
        primary_stmt = stmts[-1]
        validation = validate_cashflow_for_analysis(
            primary, statements=primary_stmt
        )
        revenue = meta.get("revenue")
        if revenue is None and primary_stmt is not None:
            revenue = primary_stmt.income_statement.revenue

        explanations: list[MetricExplanation] = []
        operating = self._operating(flows, explanations)
        investing = self._investing(primary, operating, explanations)
        financing = self._financing(primary, operating, explanations)
        net_income = None
        if primary_stmt is not None:
            net_income = primary_stmt.income_statement.net_income
        fcf = self._fcf(flows, revenue, net_income, explanations)
        quality = self._quality(primary, operating, investing, financing, fcf, explanations)
        flags = self._flags(operating, investing, financing, fcf, quality)
        trends = self._trends(flows, operating, financing, fcf)
        metadata = CashFlowAnalysisMetadata(
            engine_version=CASHFLOW_INTELLIGENCE_VERSION,
            periods_used=len(flows),
            primary_period_end=meta.get("period_end"),
            company=str(meta.get("company") or ""),
            ticker=str(meta.get("ticker") or ""),
        )
        return CashFlowAnalysis(
            operating=operating,
            investing=investing,
            financing=financing,
            free_cash_flow=fcf,
            quality=quality,
            quality_flags=flags,
            trend_summary=trends,
            validation=validation,
            explainability=tuple(explanations),
            metadata=metadata,
            research_disclaimer=CASHFLOW_RESEARCH_DISCLAIMER,
        )

    def _operating(
        self,
        flows: Sequence[CashFlowStatement],
        out: list[MetricExplanation],
    ) -> OperatingCashMetrics:
        primary = flows[-1]
        ocf = primary.operating_cash_flow
        prior = flows[-2] if len(flows) >= 2 else None
        growth = _growth(ocf, prior.operating_cash_flow if prior else None)

        ocf_series = [
            f.operating_cash_flow
            for f in flows
            if f.operating_cash_flow is not None
        ]
        stability = _stability(ocf_series) if len(ocf_series) >= 2 else None

        # Cash conversion: FCF / OCF when available
        fcf_val, _ = _resolve_fcf(primary)
        conversion = _safe_div(fcf_val, ocf)

        # Earnings quality proxy without NI: positive stable OCF → higher
        quality = None
        if ocf is not None:
            base = 1.0 if ocf > 0 else 0.0
            if stability is not None:
                quality = _clip01(0.5 * base + 0.5 * stability)
            else:
                quality = base

        gen_trend = None
        if growth is not None:
            gen_trend = _trend_from_delta(growth, improve_when_up=True)

        out.append(
            build_explanation(
                name="operating_cash_flow_growth",
                formula="(OCF_t - OCF_t-1) / |OCF_t-1|",
                inputs={
                    "ocf_t": ocf,
                    "ocf_t-1": prior.operating_cash_flow if prior else None,
                },
                intermediates={"growth": growth},
                result=growth,
                confidence=_confidence(len(flows), has_value=growth is not None),
                interpretation=(
                    "Insufficient history for OCF growth."
                    if growth is None
                    else f"OCF growth is {growth * 100:.2f}%."
                ),
                limitations="Requires a prior period with non-zero OCF.",
            )
        )
        out.append(
            build_explanation(
                name="cash_conversion",
                formula="free_cash_flow / operating_cash_flow",
                inputs={"fcf": fcf_val, "ocf": ocf},
                intermediates={},
                result=conversion,
                confidence=_confidence(1, has_value=conversion is not None),
                interpretation=(
                    "Cash conversion unavailable."
                    if conversion is None
                    else f"Cash conversion = {conversion:.4f}."
                ),
                limitations="Uses reported or computed FCF.",
            )
        )

        return OperatingCashMetrics(
            operating_cash_flow=ocf,
            operating_cash_flow_growth=growth,
            cash_earnings_quality=quality,
            cash_conversion=conversion,
            cash_flow_stability=stability,
            cash_generation_trend=gen_trend,
        )

    def _investing(
        self,
        cf: CashFlowStatement,
        operating: OperatingCashMetrics,
        out: list[MetricExplanation],
    ) -> InvestingCashMetrics:
        ocf = operating.operating_cash_flow
        capex = cf.capex
        capex_intensity = _safe_div(
            abs(capex) if capex is not None else None,
            abs(ocf) if ocf is not None else None,
        )
        inv_activity = cf.investing_cash_flow
        if inv_activity is None:
            parts = [cf.capex, cf.acquisitions, cf.investments, cf.asset_sales]
            if any(p is not None for p in parts):
                inv_activity = sum(p or 0.0 for p in parts)

        # Discipline: lower intensity + limited acquisitions vs OCF
        acq_intensity = _safe_div(
            abs(cf.acquisitions) if cf.acquisitions is not None else None, ocf
        )
        discipline = None
        if capex_intensity is not None:
            discipline = _clip01(1.0 - min(1.0, capex_intensity))
            if acq_intensity is not None:
                discipline = _clip01(
                    0.7 * discipline + 0.3 * (1.0 - min(1.0, acq_intensity))
                )

        gclass = GrowthInvestmentClass.INSUFFICIENT_DATA
        if capex is not None and ocf is not None:
            if inv_activity is not None and inv_activity > 0:
                gclass = GrowthInvestmentClass.NET_DIVESTING
            elif capex_intensity is None:
                gclass = GrowthInvestmentClass.INSUFFICIENT_DATA
            elif capex_intensity < 0.30:
                gclass = GrowthInvestmentClass.MAINTENANCE
            elif capex_intensity < 0.80:
                gclass = GrowthInvestmentClass.GROWTH
            else:
                gclass = GrowthInvestmentClass.AGGRESSIVE_GROWTH

        out.append(
            build_explanation(
                name="capex_intensity",
                formula="|capex| / operating_cash_flow",
                inputs={"capex": capex, "ocf": ocf},
                intermediates={"capex_intensity": capex_intensity},
                result=capex_intensity,
                confidence=_confidence(1, has_value=capex_intensity is not None),
                interpretation=(
                    "Capex intensity unavailable."
                    if capex_intensity is None
                    else f"Capex intensity = {capex_intensity:.4f}; class={gclass.value}."
                ),
                limitations="Sign of capex normalized via absolute value.",
            )
        )

        return InvestingCashMetrics(
            capex=capex,
            capex_intensity=capex_intensity,
            acquisitions=cf.acquisitions,
            investment_activity=inv_activity,
            asset_sales=cf.asset_sales,
            investment_discipline=discipline,
            growth_investment_class=gclass,
        )

    def _financing(
        self,
        cf: CashFlowStatement,
        operating: OperatingCashMetrics,
        out: list[MetricExplanation],
    ) -> FinancingCashMetrics:
        ocf = operating.operating_cash_flow
        debt_issued = cf.debt_issued
        # Dependence: net debt raise / |OCF|
        net_debt_raise = None
        if debt_issued is not None or cf.debt_repaid is not None:
            net_debt_raise = (debt_issued or 0.0) - abs(cf.debt_repaid or 0.0)
        dependence = _safe_div(
            max(0.0, net_debt_raise) if net_debt_raise is not None else None,
            abs(ocf) if ocf is not None else None,
        )

        # Capital allocation quality: prefer FCF funding of dividends/buybacks
        fcf_val, _ = _resolve_fcf(cf)
        shareholder = abs(cf.dividends_paid or 0.0) + abs(cf.share_buybacks or 0.0)
        alloc_q = None
        if fcf_val is not None and fcf_val > 0 and shareholder > 0:
            cover = _safe_div(fcf_val, shareholder)
            alloc_q = _clip01(cover)
        elif fcf_val is not None and fcf_val > 0 and shareholder == 0:
            alloc_q = 0.7  # retained flexibility
        elif fcf_val is not None and fcf_val <= 0 and shareholder > 0:
            alloc_q = 0.2

        out.append(
            build_explanation(
                name="financing_dependence",
                formula="max(debt_issued - |debt_repaid|, 0) / |OCF|",
                inputs={
                    "debt_issued": debt_issued,
                    "debt_repaid": cf.debt_repaid,
                    "ocf": ocf,
                },
                intermediates={"net_debt_raise": net_debt_raise},
                result=dependence,
                confidence=_confidence(1, has_value=dependence is not None),
                interpretation=(
                    "Financing dependence unavailable."
                    if dependence is None
                    else f"Financing dependence = {dependence:.4f}."
                ),
                limitations="Ignores leases and hybrid instruments.",
            )
        )

        return FinancingCashMetrics(
            debt_issued=debt_issued,
            debt_repaid=cf.debt_repaid,
            dividends_paid=cf.dividends_paid,
            share_buybacks=cf.share_buybacks,
            share_issuance=cf.share_issuance,
            financing_dependence=dependence,
            capital_allocation_quality=alloc_q,
        )

    def _fcf(
        self,
        flows: Sequence[CashFlowStatement],
        revenue: float | None,
        net_income: float | None,
        out: list[MetricExplanation],
    ) -> FreeCashFlowMetrics:
        primary = flows[-1]
        fcf, source = _resolve_fcf(primary)
        prior = flows[-2] if len(flows) >= 2 else None
        prior_fcf = _resolve_fcf(prior)[0] if prior else None
        growth = _growth(fcf, prior_fcf)

        fcf_series: list[float] = []
        for f in flows:
            v, _ = _resolve_fcf(f)
            if v is not None:
                fcf_series.append(v)
        stability = _stability(fcf_series) if len(fcf_series) >= 2 else None
        margin = _safe_div(fcf, revenue)
        fcf_to_earn = fcf_to_earnings_ratio(fcf, net_income)

        # Owner earnings: domain placeholder — pass through only
        owner = primary.owner_earnings
        # Cash surplus: FCF after dividends (and optionally buybacks)
        surplus = None
        if fcf is not None:
            surplus = fcf - abs(primary.dividends_paid or 0.0)

        out.append(
            build_explanation(
                name="free_cash_flow",
                formula="reported FCF or OCF - |capex|",
                inputs={
                    "reported_fcf": primary.free_cash_flow,
                    "ocf": primary.operating_cash_flow,
                    "capex": primary.capex,
                },
                intermediates={"fcf_source": source},
                result=fcf,
                confidence=_confidence(1, has_value=fcf is not None),
                interpretation=(
                    "FCF unavailable."
                    if fcf is None
                    else f"FCF = {fcf:.4f} (source={source})."
                ),
                limitations="Computed FCF assumes capex is the maintenance/growth spend proxy.",
            )
        )
        out.append(
            build_explanation(
                name="fcf_to_earnings",
                formula="FCF / net_income (point-in-time; NI > 0 required)",
                inputs={"fcf": fcf, "net_income": net_income},
                intermediates={},
                result=fcf_to_earn,
                confidence=_confidence(1, has_value=fcf_to_earn is not None),
                interpretation=(
                    "FCF-to-earnings unavailable."
                    if fcf_to_earn is None
                    else f"FCF/NI = {fcf_to_earn:.4f}."
                ),
                limitations=(
                    "Distinct from cash_conversion (FCF/OCF). Zero/negative NI → unavailable. "
                    "Does not substitute OCF for FCF or revenue for NI."
                ),
            )
        )
        out.append(
            build_explanation(
                name="owner_earnings",
                formula="domain placeholder (pass-through)",
                inputs={"owner_earnings": owner},
                intermediates={},
                result=owner,
                confidence=_confidence(1, has_value=owner is not None),
                interpretation=(
                    "Owner earnings placeholder not provided."
                    if owner is None
                    else f"Owner earnings placeholder = {owner:.4f}."
                ),
                limitations="F2.4 does not derive owner earnings — uses statement field only.",
            )
        )

        return FreeCashFlowMetrics(
            free_cash_flow=fcf,
            fcf_growth=growth,
            fcf_margin=margin,
            fcf_stability=stability,
            owner_earnings=owner,
            cash_surplus=surplus,
            fcf_source=source,
            fcf_to_earnings=fcf_to_earn,
        )

    def _quality(
        self,
        cf: CashFlowStatement,
        operating: OperatingCashMetrics,
        investing: InvestingCashMetrics,
        financing: FinancingCashMetrics,
        fcf: FreeCashFlowMetrics,
        out: list[MetricExplanation],
    ) -> CashQualityMetrics:
        op_q = operating.cash_earnings_quality
        inv_d = investing.investment_discipline
        fin_q = financing.capital_allocation_quality

        # Sustainability composites
        cash_sust = None
        parts = [p for p in (op_q, fcf.fcf_stability, operating.cash_flow_stability) if p is not None]
        if parts:
            cash_sust = sum(parts) / len(parts)

        div_sust = None
        if fcf.free_cash_flow is not None and cf.dividends_paid is not None:
            if abs(cf.dividends_paid) == 0:
                div_sust = 1.0
            else:
                div_sust = _clip01(_safe_div(fcf.free_cash_flow, abs(cf.dividends_paid)))

        bb_sust = None
        if fcf.free_cash_flow is not None and cf.share_buybacks is not None:
            if abs(cf.share_buybacks) == 0:
                bb_sust = 1.0
            else:
                bb_sust = _clip01(_safe_div(fcf.free_cash_flow, abs(cf.share_buybacks)))

        debt_sust = None
        if financing.financing_dependence is not None:
            debt_sust = _clip01(1.0 - min(1.0, financing.financing_dependence))

        out.append(
            build_explanation(
                name="cash_sustainability",
                formula="mean(operating_quality, fcf_stability, ocf_stability)",
                inputs={
                    "operating_cash_quality": op_q,
                    "fcf_stability": fcf.fcf_stability,
                    "ocf_stability": operating.cash_flow_stability,
                },
                intermediates={},
                result=cash_sust,
                confidence=_confidence(1, has_value=cash_sust is not None),
                interpretation=(
                    "Cash sustainability unavailable."
                    if cash_sust is None
                    else f"Cash sustainability = {cash_sust:.4f}."
                ),
                limitations="Research heuristic — not a liquidity covenant model.",
            )
        )

        return CashQualityMetrics(
            operating_cash_quality=op_q,
            investment_discipline=inv_d,
            financing_quality=fin_q,
            cash_sustainability=cash_sust,
            dividend_sustainability=div_sust,
            buyback_sustainability=bb_sust,
            debt_sustainability=debt_sust,
        )

    def _flags(
        self,
        operating: OperatingCashMetrics,
        investing: InvestingCashMetrics,
        financing: FinancingCashMetrics,
        fcf: FreeCashFlowMetrics,
        quality: CashQualityMetrics,
    ) -> tuple[CashFlowQualityFlag, ...]:
        flags: list[CashFlowQualityFlag] = []
        ocf = operating.operating_cash_flow
        if ocf is not None:
            if ocf > 0 and (
                operating.operating_cash_flow_growth is None
                or operating.operating_cash_flow_growth >= _STRONG_OCF_GROWTH
                or (operating.cash_flow_stability or 0) >= 0.5
            ):
                if ocf > 0 and (
                    operating.operating_cash_flow_growth is None
                    or operating.operating_cash_flow_growth >= 0
                ):
                    flags.append(CashFlowQualityFlag.STRONG_CASH_GENERATION)
            if ocf <= _WEAK_OCF:
                flags.append(CashFlowQualityFlag.WEAK_CASH_GENERATION)

        if fcf.free_cash_flow is not None and fcf.free_cash_flow < 0:
            flags.append(CashFlowQualityFlag.NEGATIVE_FREE_CASH_FLOW)

        if (
            investing.capex_intensity is not None
            and investing.capex_intensity >= _HEAVY_CAPEX
        ):
            flags.append(CashFlowQualityFlag.HEAVY_CAPEX)

        if (
            financing.financing_dependence is not None
            and financing.financing_dependence >= _AGGRESSIVE_DEBT
        ):
            flags.append(CashFlowQualityFlag.AGGRESSIVE_DEBT_FUNDING)

        shareholder = False
        if financing.dividends_paid is not None and abs(financing.dividends_paid) > 0:
            shareholder = True
        if financing.share_buybacks is not None and abs(financing.share_buybacks) > 0:
            shareholder = True
        if (
            shareholder
            and fcf.free_cash_flow is not None
            and fcf.free_cash_flow > 0
            and CashFlowQualityFlag.NEGATIVE_FREE_CASH_FLOW not in flags
        ):
            flags.append(CashFlowQualityFlag.SHAREHOLDER_FRIENDLY)

        if (
            (financing.capital_allocation_quality or 0) >= 0.6
            and (investing.investment_discipline or 0) >= 0.5
            and CashFlowQualityFlag.AGGRESSIVE_DEBT_FUNDING not in flags
        ):
            flags.append(CashFlowQualityFlag.HEALTHY_CAPITAL_ALLOCATION)

        excellent = (
            CashFlowQualityFlag.STRONG_CASH_GENERATION in flags
            and (quality.cash_sustainability or 0) >= 0.7
            and CashFlowQualityFlag.NEGATIVE_FREE_CASH_FLOW not in flags
            and CashFlowQualityFlag.WEAK_CASH_GENERATION not in flags
        )
        if excellent:
            flags.append(CashFlowQualityFlag.EXCELLENT_CASH_QUALITY)

        warning = (
            CashFlowQualityFlag.WEAK_CASH_GENERATION in flags
            or CashFlowQualityFlag.NEGATIVE_FREE_CASH_FLOW in flags
            or CashFlowQualityFlag.AGGRESSIVE_DEBT_FUNDING in flags
            or CashFlowQualityFlag.HEAVY_CAPEX in flags
        )
        if warning and not excellent:
            flags.append(CashFlowQualityFlag.CASH_FLOW_WARNING)

        return tuple(dict.fromkeys(flags))

    def _trends(
        self,
        flows: Sequence[CashFlowStatement],
        operating: OperatingCashMetrics,
        financing: FinancingCashMetrics,
        fcf: FreeCashFlowMetrics,
    ) -> CashFlowTrendSummary:
        if len(flows) < 2:
            return CashFlowTrendSummary(
                operating_cash_flow=operating.cash_generation_trend
                or TrendDirection.STABLE,
            )

        ocf_trend = operating.cash_generation_trend or _trend_from_delta(
            operating.operating_cash_flow_growth
        )
        fcf_trend = _trend_from_delta(fcf.fcf_growth)

        # Capital allocation: improvement if allocation quality rises
        prior = flows[-2]
        prior_fcf, _ = _resolve_fcf(prior)
        prior_shareholder = abs(prior.dividends_paid or 0.0) + abs(
            prior.share_buybacks or 0.0
        )
        cur_shareholder = abs(financing.dividends_paid or 0.0) + abs(
            financing.share_buybacks or 0.0
        )
        prior_alloc = None
        if prior_fcf is not None and prior_fcf > 0 and prior_shareholder > 0:
            prior_alloc = _clip01(_safe_div(prior_fcf, prior_shareholder))
        cur_alloc = financing.capital_allocation_quality
        alloc_delta = None
        if cur_alloc is not None and prior_alloc is not None:
            alloc_delta = cur_alloc - prior_alloc
        elif cur_shareholder > 0 and prior_shareholder == 0 and (fcf.free_cash_flow or 0) > 0:
            alloc_delta = 0.05
        alloc_trend = _trend_from_delta(alloc_delta)

        # Debt activity: improving when net debt raise declines
        def _net_raise(c: CashFlowStatement) -> float | None:
            if c.debt_issued is None and c.debt_repaid is None:
                return None
            return (c.debt_issued or 0.0) - abs(c.debt_repaid or 0.0)

        cur_raise = _net_raise(flows[-1])
        prior_raise = _net_raise(prior)
        debt_delta = None
        if cur_raise is not None and prior_raise is not None:
            # lower raise is better → invert
            debt_delta = prior_raise - cur_raise
        debt_trend = _trend_from_delta(debt_delta, improve_when_up=True)

        return CashFlowTrendSummary(
            operating_cash_flow=ocf_trend,
            free_cash_flow=fcf_trend,
            capital_allocation=alloc_trend,
            debt_activity=debt_trend,
        )
