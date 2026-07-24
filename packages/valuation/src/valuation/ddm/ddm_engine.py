"""Dividend Discount Model Engine — research-only.

Variants: zero-growth, Gordon (single-stage), two-stage, multi-stage.
Integrates Valuation Core without modifying Core or other valuation methods.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Mapping

from valuation.core.confidence_engine import ConfidenceEngine
from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioKind,
    ScenarioOutcome,
    SensitivityMatrix,
    ValuationMetadata,
)
from valuation.core.scenario_engine import ScenarioEngine, ScenarioSpec
from valuation.core.sensitivity_engine import SensitivityAxis, SensitivityEngine
from valuation.ddm.ddm_explainability import explain_many, explain_step
from valuation.ddm.ddm_models import (
    DDM_VERSION,
    DdmInputs,
    DdmMethod,
    DdmQualityFlag,
    DdmResult,
    DividendQuality,
    DividendYear,
)
from valuation.ddm.ddm_validation import validate_ddm_inputs
from valuation.exceptions import ValuationError

__all__ = ["DdmEngine", "DDM_VERSION"]

_METHODOLOGY = (
    "Dividend Discount Model (research only). "
    "Zero-growth: IV = DPS / r. "
    "Gordon: IV = DPS₁ / (r − g). "
    "Two-stage: Σ PV(D_t) + PV(Gordon terminal). "
    "Multi-stage: user growth schedule then Gordon terminal. "
    "Assumes dividends are the sole cash claim; growth and payout are "
    "assumptions. Not investment advice."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Ignores non-dividend cash returns (buybacks) unless folded into DPS",
    "Terminal growth and payout sustainability are judgment-sensitive",
    "Does not enable Overall Valuation",
    "Independent of DCF / Reverse DCF / Residual Income / EPV / Graham",
)


class DdmEngine:
    """Compute research-only Dividend Discount Model valuations."""

    def analyze(self, inputs: DdmInputs) -> DdmResult:
        """Run DDM analysis (base scenario primary)."""
        t0 = time.perf_counter()
        validation = validate_ddm_inputs(inputs)
        base = self._value(inputs)

        scenarios = self._scenarios(inputs)
        sensitivity = self._sensitivity(inputs)
        quality = self._dividend_quality(inputs)
        confidence = self._confidence(inputs, quality)
        flags, core_flags = self._quality_flags(inputs, quality, confidence.level)

        explain_records = [
            base["pv_div_exp"],
            base["term_div_exp"],
            base["tv_exp"],
            base["tv_pv_exp"],
            base["ivps_exp"],
            base["iv_exp"],
            base["mos_exp"],
            base["yield_exp"],
            base["payout_exp"],
        ]
        for yr in base["years"]:
            explain_records.append(yr.explained)

        explainability = explain_many(
            [
                {
                    "name": r.name,
                    "value": r.value,
                    "formula": r.formula,
                    "inputs": dict(r.inputs),
                    "intermediates": dict(r.intermediates),
                    "confidence": r.confidence,
                    "notes": r.notes,
                    "warnings": r.warnings,
                }
                for r in explain_records
            ]
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        metadata = ValuationMetadata(
            model_name="ddm",
            engine_version=DDM_VERSION,
            methodology=_METHODOLOGY,
            formula_references=(
                "Gordon Growth Model",
                "Two-stage / multi-stage DDM (Damodaran-style)",
            ),
            assumption_summary={
                "method": inputs.method.value,
                "cost_of_equity": inputs.cost_of_equity,
                "expected_dividend_growth": inputs.expected_dividend_growth,
                "terminal_growth": inputs.terminal_growth,
                "forecast_years": inputs.forecast_years,
            },
            research_mode=True,
            calculation_timestamp=datetime.now(UTC).isoformat(),
            execution_time_ms=elapsed_ms,
            core_version=VALUATION_CORE_VERSION,
        )

        return DdmResult(
            version=DDM_VERSION,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            methodology=_METHODOLOGY,
            method_used=inputs.method,
            forecast_dividends=base["years"],
            terminal_dividend=base["term_div_exp"],
            present_value_dividends=base["pv_div_exp"],
            terminal_value=base["tv_exp"],
            terminal_value_pv=base["tv_pv_exp"],
            intrinsic_value_per_share=base["ivps_exp"],
            intrinsic_value=base["iv_exp"],
            margin_of_safety=base["mos_exp"],
            dividend_yield=base["yield_exp"],
            payout_ratio=base["payout_exp"],
            dividend_quality=quality,
            confidence=confidence.level,
            confidence_detail=confidence,
            quality_flags=flags,
            core_quality_flags=core_flags,
            validation_summary=validation,
            scenarios=scenarios,
            sensitivity=sensitivity,
            explainability=explainability,
            limitations=_LIMITATIONS,
            metadata=metadata,
            execution_time_ms=elapsed_ms,
        )

    def _growth_path(self, inputs: DdmInputs) -> tuple[float, ...]:
        n = inputs.forecast_years
        if inputs.method is DdmMethod.MULTI_STAGE and inputs.dividend_growth_schedule:
            return tuple(float(g) for g in inputs.dividend_growth_schedule)
        return tuple(inputs.expected_dividend_growth for _ in range(n))

    def _value(self, inputs: DdmInputs) -> dict[str, Any]:
        r = inputs.cost_of_equity
        d0 = inputs.current_dps
        method = inputs.method
        conf = "medium"
        years: list[DividendYear] = []
        pv_explicit = 0.0
        terminal_div = 0.0
        terminal_value = 0.0
        terminal_value_pv = 0.0
        ivps = 0.0

        if method is DdmMethod.ZERO_GROWTH:
            if r <= 0:
                raise ValuationError("cost_of_equity must be > 0")
            ivps = d0 / r
            terminal_div = d0
            formula = "IV = DPS / r"
        elif method is DdmMethod.GORDON:
            g = inputs.expected_dividend_growth
            if g >= r:
                raise ValuationError(f"growth must be < cost_of_equity ({g} >= {r})")
            d1 = d0 * (1.0 + g)
            ivps = d1 / (r - g)
            terminal_div = d1
            formula = "IV = DPS₁ / (r − g)"
            years.append(
                DividendYear(
                    year=1,
                    growth=g,
                    dividend=d1,
                    present_value=d1 / (1.0 + r),
                    explained=explain_step(
                        name="dps_year_1",
                        value=d1,
                        formula="D₁ = D₀ × (1+g)",
                        inputs={"d0": d0, "g": g},
                        intermediates={},
                        confidence=conf,
                    ),
                )
            )
            pv_explicit = years[0].present_value
        elif method in {DdmMethod.TWO_STAGE, DdmMethod.MULTI_STAGE}:
            path = self._growth_path(inputs)
            if len(path) != inputs.forecast_years:
                raise ValuationError("growth path length mismatch")
            d = d0
            for t, g in enumerate(path, start=1):
                d = d * (1.0 + g)
                pv = d / ((1.0 + r) ** t)
                pv_explicit += pv
                years.append(
                    DividendYear(
                        year=t,
                        growth=g,
                        dividend=d,
                        present_value=pv,
                        explained=explain_step(
                            name=f"dividend_year_{t}",
                            value=d,
                            formula=f"D_{t} = D_{t-1} × (1+g_{t}); PV = D_{t}/(1+r)^{t}",
                            inputs={"growth": g, "r": r},
                            intermediates={"pv": pv},
                            confidence=conf,
                        ),
                    )
                )
            tg = inputs.terminal_growth
            if tg >= r:
                raise ValuationError(
                    f"terminal_growth must be < cost_of_equity ({tg} >= {r})"
                )
            terminal_div = d * (1.0 + tg)
            terminal_value = terminal_div / (r - tg)
            n = inputs.forecast_years
            terminal_value_pv = terminal_value / ((1.0 + r) ** n)
            ivps = pv_explicit + terminal_value_pv
            formula = (
                "IV = Σ PV(D_t) + PV(D_{n+1}/(r−g_terminal))"
            )
        else:
            raise ValuationError(f"unknown DDM method: {method!r}")

        equity_iv = ivps * inputs.shares_outstanding
        mos: float | None = None
        if inputs.current_market_price is not None and ivps != 0:
            mos = (ivps - inputs.current_market_price) / ivps

        div_yield: float | None = None
        if inputs.current_market_price is not None and inputs.current_market_price > 0:
            div_yield = d0 / inputs.current_market_price

        payout = inputs.dividend_payout_ratio
        if payout is None and inputs.eps is not None and inputs.eps != 0:
            payout = d0 / inputs.eps

        pv_div_exp = explain_step(
            name="present_value_dividends",
            value=pv_explicit if method is not DdmMethod.ZERO_GROWTH else None,
            formula="Σ D_t / (1+r)^t over explicit horizon",
            inputs={"r": r, "years": len(years)},
            intermediates={"method": method.value},
            confidence=conf,
        )
        term_div_exp = explain_step(
            name="terminal_dividend",
            value=terminal_div,
            formula="D_terminal = last explicit DPS × (1+g_terminal) or D₀ / D₁",
            inputs={"terminal_growth": inputs.terminal_growth},
            intermediates={},
            confidence=conf,
        )
        tv_exp = explain_step(
            name="terminal_value",
            value=(
                terminal_value
                if method in {DdmMethod.TWO_STAGE, DdmMethod.MULTI_STAGE}
                else None
            ),
            formula="TV = D_{n+1} / (r − g_terminal)",
            inputs={"r": r, "g_terminal": inputs.terminal_growth},
            intermediates={"terminal_div": terminal_div},
            confidence=conf,
            notes="Gordon terminal assumes perpetual growth below cost of equity",
        )
        tv_pv_exp = explain_step(
            name="terminal_value_pv",
            value=(
                terminal_value_pv
                if method in {DdmMethod.TWO_STAGE, DdmMethod.MULTI_STAGE}
                else None
            ),
            formula="PV(TV) = TV / (1+r)^n",
            inputs={"n": inputs.forecast_years, "r": r},
            intermediates={"terminal_value": terminal_value},
            confidence=conf,
        )

        if method is DdmMethod.ZERO_GROWTH:
            iv_formula = "IV = DPS / r"
            iv_inputs: dict[str, Any] = {"dps": d0, "r": r}
        elif method is DdmMethod.GORDON:
            iv_formula = "IV = DPS₁ / (r − g)"
            iv_inputs = {
                "d0": d0,
                "g": inputs.expected_dividend_growth,
                "r": r,
            }
        else:
            iv_formula = formula
            iv_inputs = {"d0": d0, "r": r, "method": method.value}

        ivps_exp = explain_step(
            name="intrinsic_value_per_share",
            value=ivps,
            formula=iv_formula,
            inputs=iv_inputs,
            intermediates={
                "pv_explicit": pv_explicit,
                "terminal_value_pv": terminal_value_pv,
            },
            confidence=conf,
            notes="Research heuristic; dividends must be sustainable",
        )
        iv_exp = explain_step(
            name="intrinsic_value",
            value=equity_iv,
            formula="Equity IV = IV/share × Shares",
            inputs={"ivps": ivps, "shares": inputs.shares_outstanding},
            intermediates={},
            confidence=conf,
        )
        mos_exp = explain_step(
            name="margin_of_safety",
            value=mos,
            formula="MoS = (IV/share − Price) / IV/share",
            inputs={"ivps": ivps, "price": inputs.current_market_price},
            intermediates={},
            confidence="low" if mos is None else conf,
            notes="Research posture only — not a recommendation",
        )
        yield_exp = explain_step(
            name="dividend_yield",
            value=div_yield,
            formula="Yield = DPS / Price",
            inputs={"dps": d0, "price": inputs.current_market_price},
            intermediates={},
            confidence=conf,
        )
        payout_exp = explain_step(
            name="payout_ratio",
            value=payout,
            formula="Payout = Div/NI (or supplied dividend_payout_ratio)",
            inputs={
                "dividend_payout_ratio": inputs.dividend_payout_ratio,
                "eps": inputs.eps,
                "dps": d0,
            },
            intermediates={},
            confidence=conf,
        )

        return {
            "years": tuple(years),
            "ivps": ivps,
            "intrinsic_value": equity_iv,
            "margin_of_safety": mos,
            "pv_div_exp": pv_div_exp,
            "term_div_exp": term_div_exp,
            "tv_exp": tv_exp,
            "tv_pv_exp": tv_pv_exp,
            "ivps_exp": ivps_exp,
            "iv_exp": iv_exp,
            "mos_exp": mos_exp,
            "yield_exp": yield_exp,
            "payout_exp": payout_exp,
        }

    def _scenarios(self, inputs: DdmInputs) -> tuple[ScenarioOutcome, ...]:
        engine = ScenarioEngine()
        specs = (
            ScenarioSpec(
                ScenarioKind.bear(),
                {
                    "growth_delta": inputs.bear_growth_delta,
                    "coe_delta": inputs.bear_coe_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.base(),
                {"growth_delta": 0.0, "coe_delta": 0.0},
            ),
            ScenarioSpec(
                ScenarioKind.bull(),
                {
                    "growth_delta": inputs.bull_growth_delta,
                    "coe_delta": inputs.bull_coe_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.custom("stress_payout", "Stress Payout"),
                {
                    "growth_delta": -abs(inputs.bear_growth_delta),
                    "coe_delta": abs(inputs.bear_coe_delta),
                },
            ),
        )

        def evaluator(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            g_delta = float(ctx.get("growth_delta", 0.0))
            coe_delta = float(ctx.get("coe_delta", 0.0))
            adj = replace(
                inputs,
                expected_dividend_growth=inputs.expected_dividend_growth + g_delta,
                terminal_growth=inputs.terminal_growth + g_delta * 0.5,
                cost_of_equity=inputs.cost_of_equity + coe_delta,
            )
            if adj.cost_of_equity <= 0:
                raise ValuationError("scenario cost_of_equity must be > 0")
            # Clamp terminal below r for stage methods
            if adj.method in {
                DdmMethod.GORDON,
                DdmMethod.TWO_STAGE,
                DdmMethod.MULTI_STAGE,
            }:
                if adj.method is DdmMethod.GORDON:
                    if adj.expected_dividend_growth >= adj.cost_of_equity:
                        adj = replace(
                            adj,
                            expected_dividend_growth=adj.cost_of_equity - 1e-6,
                        )
                elif adj.terminal_growth >= adj.cost_of_equity:
                    adj = replace(
                        adj,
                        terminal_growth=adj.cost_of_equity - 1e-6,
                    )
            out = self._value(adj)
            return {
                "intrinsic_value": out["intrinsic_value"],
                "equity_value": out["intrinsic_value"],
                "intrinsic_value_per_share": out["ivps"],
                "notes": f"growth_delta={g_delta}, coe_delta={coe_delta}",
                "extras": {},
            }

        return engine.scenarios({}, specs=specs, evaluator=evaluator)

    def _sensitivity(self, inputs: DdmInputs) -> SensitivityMatrix:
        g = inputs.expected_dividend_growth
        r = inputs.cost_of_equity
        tg = inputs.terminal_growth
        payout = (
            inputs.dividend_payout_ratio
            if inputs.dividend_payout_ratio is not None
            else 0.5
        )
        roe = inputs.roe if inputs.roe is not None else 0.12

        axes = (
            SensitivityAxis("dividend_growth", (g - 0.01, g, g + 0.01)),
            SensitivityAxis("cost_of_equity", (r - 0.01, r, r + 0.01)),
            SensitivityAxis("terminal_growth", (tg - 0.005, tg, tg + 0.005)),
            SensitivityAxis("payout_ratio", (max(0.0, payout - 0.1), payout, min(1.0, payout + 0.1))),
            SensitivityAxis("roe", (roe - 0.02, roe, roe + 0.02)),
        )

        def evaluator(ctx: Mapping[str, Any]) -> float | None:
            adj = inputs
            if "dividend_growth" in ctx and ctx["dividend_growth"] != g:
                adj = replace(
                    adj,
                    expected_dividend_growth=float(ctx["dividend_growth"]),
                )
            if "cost_of_equity" in ctx and ctx["cost_of_equity"] != r:
                adj = replace(adj, cost_of_equity=float(ctx["cost_of_equity"]))
            if "terminal_growth" in ctx and ctx["terminal_growth"] != tg:
                adj = replace(adj, terminal_growth=float(ctx["terminal_growth"]))
            if "payout_ratio" in ctx and ctx["payout_ratio"] != payout:
                adj = replace(
                    adj,
                    dividend_payout_ratio=float(ctx["payout_ratio"]),
                )
            if "roe" in ctx and ctx["roe"] != roe:
                # Implied g = retention × ROE when retention known
                ret = (
                    adj.retention_ratio
                    if adj.retention_ratio is not None
                    else (
                        1.0 - float(adj.dividend_payout_ratio)
                        if adj.dividend_payout_ratio is not None
                        else None
                    )
                )
                new_roe = float(ctx["roe"])
                if ret is not None:
                    adj = replace(
                        adj,
                        roe=new_roe,
                        expected_dividend_growth=ret * new_roe,
                    )
                else:
                    adj = replace(adj, roe=new_roe)
            try:
                if adj.cost_of_equity <= 0:
                    raise ValuationError("r <= 0")
                if adj.method is DdmMethod.GORDON and adj.expected_dividend_growth >= adj.cost_of_equity:
                    raise ValuationError("g >= r")
                if adj.method in {DdmMethod.TWO_STAGE, DdmMethod.MULTI_STAGE}:
                    if adj.terminal_growth >= adj.cost_of_equity:
                        raise ValuationError("tg >= r")
                return float(self._value(adj)["ivps"])
            except ValuationError:
                return None

        context = {
            "dividend_growth": g,
            "cost_of_equity": r,
            "terminal_growth": tg,
            "payout_ratio": payout,
            "roe": roe,
        }
        return SensitivityEngine().sensitivity(
            context,
            axes=axes,
            evaluator=evaluator,
            output_name="intrinsic_value_per_share",
        )

    def _dividend_quality(self, inputs: DdmInputs) -> DividendQuality:
        score = 0.0
        weight = 0.0

        if inputs.dividend_stability_score is not None:
            s = inputs.dividend_stability_score
            s = s / 100.0 if s > 1.0 else float(s)
            score += max(0.0, min(1.0, s)) * 2.0
            weight += 2.0

        if inputs.dividend_coverage_ratio is not None:
            cov = inputs.dividend_coverage_ratio
            score += max(0.0, min(1.0, cov / 2.0)) * 2.0
            weight += 2.0

        if inputs.dividend_payout_ratio is not None:
            p = inputs.dividend_payout_ratio
            # Mid payout preferred
            payout_score = 1.0 - abs(p - 0.5)
            score += max(0.0, payout_score) * 1.5
            weight += 1.5

        if inputs.free_cash_flow_payout_ratio is not None:
            f = inputs.free_cash_flow_payout_ratio
            score += max(0.0, min(1.0, 1.0 - abs(f - 0.5))) * 1.5
            weight += 1.5

        if inputs.years_of_dividend_growth is not None:
            y = inputs.years_of_dividend_growth
            score += max(0.0, min(1.0, y / 25.0)) * 2.0
            weight += 2.0

        if inputs.historical_dividend_cagr is not None:
            c = inputs.historical_dividend_cagr
            if 0 <= c <= 0.12:
                score += 1.0
            elif c > 0.12:
                score += 0.5
            else:
                score += 0.2
            weight += 1.0

        if weight == 0:
            return DividendQuality.AVERAGE

        ratio = score / weight
        if ratio >= 0.75:
            return DividendQuality.EXCELLENT
        if ratio >= 0.55:
            return DividendQuality.GOOD
        if ratio >= 0.35:
            return DividendQuality.AVERAGE
        return DividendQuality.WEAK

    def _confidence(self, inputs: DdmInputs, quality: DividendQuality):
        stability_map = {
            DividendQuality.EXCELLENT: 1.0,
            DividendQuality.GOOD: 0.75,
            DividendQuality.AVERAGE: 0.5,
            DividendQuality.WEAK: 0.25,
        }
        div_stability = stability_map[quality]

        g = abs(inputs.expected_dividend_growth)
        growth_reliability = max(0.0, min(1.0, 1.0 - g / 0.25))

        aq = inputs.accounting_quality_score
        if aq is None:
            accounting_quality = 0.6
        else:
            accounting_quality = aq / 100.0 if aq > 1.0 else float(aq)
            accounting_quality = max(0.0, min(1.0, accounting_quality))

        data_completeness = 0.4
        if inputs.dividend_payout_ratio is not None:
            data_completeness += 0.1
        if inputs.dividend_coverage_ratio is not None:
            data_completeness += 0.15
        if inputs.historical_dividend_cagr is not None:
            data_completeness += 0.1
        if inputs.current_market_price is not None:
            data_completeness += 0.1
        if inputs.eps is not None:
            data_completeness += 0.15
        data_completeness = min(1.0, data_completeness)

        forecast_confidence = 0.7 if inputs.method is DdmMethod.GORDON else 0.55
        if inputs.method is DdmMethod.ZERO_GROWTH:
            forecast_confidence = 0.6
        if inputs.method is DdmMethod.MULTI_STAGE and inputs.dividend_growth_schedule:
            forecast_confidence = 0.65

        return ConfidenceEngine().score(
            {
                "accounting_quality": accounting_quality,
                "forecast_reliability": forecast_confidence,
                "data_completeness": data_completeness,
                "business_stability": div_stability,
                "capital_allocation": growth_reliability,
                "model_assumptions": growth_reliability,
            }
        )

    def _quality_flags(
        self,
        inputs: DdmInputs,
        quality: DividendQuality,
        confidence_level: str,
    ) -> tuple[tuple[DdmQualityFlag, ...], tuple[QualityFlag, ...]]:
        flags: list[DdmQualityFlag] = []
        core: list[QualityFlag] = []

        if (
            inputs.years_of_dividend_growth is not None
            and inputs.years_of_dividend_growth >= 25
        ):
            flags.append(DdmQualityFlag.DIVIDEND_ARISTOCRAT)
            flags.append(DdmQualityFlag.STRONG_DIVIDEND_HISTORY)

        if inputs.years_of_dividend_growth is not None and (
            10 <= inputs.years_of_dividend_growth < 25
        ):
            flags.append(DdmQualityFlag.STRONG_DIVIDEND_HISTORY)

        payout = inputs.dividend_payout_ratio
        if payout is None and inputs.eps is not None and inputs.eps != 0:
            payout = inputs.current_dps / inputs.eps
        if payout is not None and payout > 0.80:
            flags.append(DdmQualityFlag.HIGH_PAYOUT)
        if payout is not None and payout > 1.0:
            flags.append(DdmQualityFlag.UNSUSTAINABLE_DIVIDEND)

        if (
            inputs.dividend_coverage_ratio is not None
            and inputs.dividend_coverage_ratio < 1.2
        ):
            flags.append(DdmQualityFlag.LOW_COVERAGE)
            flags.append(DdmQualityFlag.DIVIDEND_CUT_RISK)

        if inputs.expected_dividend_growth > 0.12:
            flags.append(DdmQualityFlag.HIGH_GROWTH_ASSUMPTION)
            core.append(QualityFlag.OVERLY_OPTIMISTIC_ASSUMPTIONS)

        if inputs.expected_dividend_growth < 0:
            flags.append(DdmQualityFlag.NEGATIVE_GROWTH)

        if (
            inputs.free_cash_flow_payout_ratio is not None
            and inputs.free_cash_flow_payout_ratio > 1.0
        ):
            flags.append(DdmQualityFlag.WEAK_CASH_FLOW)
            core.append(QualityFlag.WEAK_CASH_FLOW)

        if quality is DividendQuality.WEAK or confidence_level == "low":
            if DdmQualityFlag.DIVIDEND_CUT_RISK not in flags:
                flags.append(DdmQualityFlag.DIVIDEND_CUT_RISK)

        return tuple(flags), tuple(core)
