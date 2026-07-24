"""Benjamin Graham Intrinsic Value Engine — research heuristics only.

Original:  IV = EPS × (8.5 + 2G)
Modern:    IV = EPS × (8.5 + 2G) × (Y_ref / Y_aaa)

Integrates Valuation Core without modifying Core or other valuation methods.
"""

from __future__ import annotations

import statistics
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
from valuation.exceptions import ValuationError
from valuation.graham.graham_explainability import explain_many, explain_step
from valuation.graham.graham_models import (
    GRAHAM_VERSION,
    GrahamFormula,
    GrahamInputs,
    GrahamQualityFlag,
    GrahamResult,
)
from valuation.graham.graham_validation import validate_graham_inputs

__all__ = ["GrahamEngine", "GRAHAM_VERSION"]

_METHODOLOGY = (
    "Benjamin Graham intrinsic-value heuristic (research only). "
    "Original: IV = EPS × (8.5 + 2G) where G is expected growth in percent. "
    "Modern: IV = EPS × (8.5 + 2G) × (Y_ref / Y_aaa). "
    "Assumptions: constant growth G, AAA yield adjustment (modern), "
    "no explicit balance-sheet or cash-flow model. Not investment advice."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Heuristic — not a DCF or fundamental cash-flow model",
    "Growth rate G is an assumption, not a forecast guarantee",
    "Does not enable Overall Valuation",
    "Independent of DCF / Reverse DCF / Residual Income / EPV",
)


class GrahamEngine:
    """Compute research-only Graham intrinsic value."""

    def analyze(self, inputs: GrahamInputs) -> GrahamResult:
        """Run Graham analysis (base scenario primary)."""
        t0 = time.perf_counter()
        validation = validate_graham_inputs(inputs)
        base = self._value(inputs)

        scenarios = self._scenarios(inputs)
        sensitivity = self._sensitivity(inputs)
        confidence = self._confidence(inputs, base)
        flags, core_flags = self._quality_flags(inputs, base, confidence.level)

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
                for r in (
                    base["eps_exp"],
                    base["growth_exp"],
                    base["ref_yield_exp"],
                    base["cur_yield_exp"],
                    base["ivps_exp"],
                    base["iv_exp"],
                    base["mos_exp"],
                    base["rr_exp"],
                )
            ]
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        metadata = ValuationMetadata(
            model_name="graham",
            engine_version=GRAHAM_VERSION,
            methodology=_METHODOLOGY,
            formula_references=(
                "Graham Intelligent Investor — original IV = EPS×(8.5+2G)",
                "Revised / modern yield adjustment × (Y_ref/Y_aaa)",
            ),
            assumption_summary={
                "formula": inputs.formula.value,
                "growth_rate": inputs.growth_rate,
                "growth_as_decimal": inputs.growth_as_decimal,
                "aaa_bond_yield": inputs.aaa_bond_yield,
                "reference_aaa_yield": inputs.reference_aaa_yield,
            },
            research_mode=True,
            calculation_timestamp=datetime.now(UTC).isoformat(),
            execution_time_ms=elapsed_ms,
            core_version=VALUATION_CORE_VERSION,
        )

        return GrahamResult(
            version=GRAHAM_VERSION,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            methodology=_METHODOLOGY,
            method_used=inputs.formula,
            eps_used=base["eps_exp"],
            growth_assumption=base["growth_exp"],
            reference_yield=base["ref_yield_exp"],
            current_yield=base["cur_yield_exp"],
            intrinsic_value_per_share=base["ivps_exp"],
            intrinsic_value=base["iv_exp"],
            margin_of_safety=base["mos_exp"],
            required_return=base["rr_exp"],
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

    def _growth_percent(self, inputs: GrahamInputs, growth_rate: float | None = None) -> float:
        """Return G in Graham percent units (7 means 7%)."""
        g = inputs.growth_rate if growth_rate is None else growth_rate
        if inputs.growth_as_decimal:
            return g * 100.0
        return g

    def _eps(self, inputs: GrahamInputs) -> float:
        if inputs.normalized_eps is not None:
            return float(inputs.normalized_eps)
        return float(inputs.eps_trailing)

    def _value(self, inputs: GrahamInputs) -> dict[str, Any]:
        eps = self._eps(inputs)
        g_pct = self._growth_percent(inputs)
        multiple = 8.5 + 2.0 * g_pct
        base_ivps = eps * multiple

        if inputs.formula is GrahamFormula.ORIGINAL:
            ivps = base_ivps
            yield_factor = 1.0
            formula_str = "IV = EPS × (8.5 + 2G)"
        elif inputs.formula is GrahamFormula.MODERN:
            if inputs.aaa_bond_yield <= 0:
                raise ValuationError("aaa_bond_yield must be > 0")
            yield_factor = inputs.reference_aaa_yield / inputs.aaa_bond_yield
            ivps = base_ivps * yield_factor
            formula_str = (
                "IV = EPS × (8.5 + 2G) × (Y_ref / Y_aaa)"
            )
        else:
            raise ValuationError(f"unknown Graham formula: {inputs.formula!r}")

        equity_iv = ivps * inputs.shares_outstanding
        mos: float | None = None
        if inputs.current_market_price is not None and ivps != 0:
            mos = (ivps - inputs.current_market_price) / ivps

        conf = "medium"
        eps_exp = explain_step(
            name="eps_used",
            value=eps,
            formula="EPS = normalized_eps if set else eps_trailing",
            inputs={
                "eps_trailing": inputs.eps_trailing,
                "normalized_eps": inputs.normalized_eps,
            },
            intermediates={},
            confidence=conf,
            notes="Normalized EPS preferred for research when available",
        )
        growth_exp = explain_step(
            name="growth_assumption",
            value=g_pct,
            formula="G = growth_rate (percent units in Graham formula)",
            inputs={
                "growth_rate": inputs.growth_rate,
                "growth_as_decimal": inputs.growth_as_decimal,
            },
            intermediates={"multiple_8_5_plus_2G": multiple},
            confidence=conf,
            notes="G is an assumption — not a forecast guarantee",
            warnings=(
                ("High growth assumption increases heuristic uncertainty",)
                if g_pct > 15
                else ()
            ),
        )
        ref_yield_exp = explain_step(
            name="reference_yield",
            value=inputs.reference_aaa_yield,
            formula="Y_ref = configurable reference AAA yield",
            inputs={"reference_aaa_yield": inputs.reference_aaa_yield},
            intermediates={},
            confidence=conf,
        )
        cur_yield_exp = explain_step(
            name="current_yield",
            value=inputs.aaa_bond_yield,
            formula="Y_aaa = current AAA corporate bond yield",
            inputs={"aaa_bond_yield": inputs.aaa_bond_yield},
            intermediates={"yield_factor": yield_factor},
            confidence=conf,
            notes=(
                "Modern formula scales by Y_ref/Y_aaa; original ignores yields"
                if inputs.formula is GrahamFormula.MODERN
                else "Original formula does not adjust for bond yields"
            ),
        )
        ivps_exp = explain_step(
            name="intrinsic_value_per_share",
            value=ivps,
            formula=formula_str,
            inputs={"eps": eps, "G_percent": g_pct, "formula": inputs.formula.value},
            intermediates={
                "base_multiple": multiple,
                "base_ivps": base_ivps,
                "yield_factor": yield_factor,
            },
            confidence=conf,
        )
        iv_exp = explain_step(
            name="intrinsic_value",
            value=equity_iv,
            formula="Equity IV = IV/share × Shares",
            inputs={"ivps": ivps, "shares": inputs.shares_outstanding},
            intermediates={"cash": inputs.cash, "debt": inputs.debt},
            confidence=conf,
            notes="Cash/debt noted for research context; not in classic Graham IV",
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
        rr_exp = explain_step(
            name="required_return",
            value=inputs.required_return,
            formula="Optional research required return (not in Graham IV)",
            inputs={"required_return": inputs.required_return},
            intermediates={},
            confidence="low",
        )

        return {
            "eps": eps,
            "g_pct": g_pct,
            "multiple": multiple,
            "yield_factor": yield_factor,
            "ivps": ivps,
            "intrinsic_value": equity_iv,
            "margin_of_safety": mos,
            "eps_exp": eps_exp,
            "growth_exp": growth_exp,
            "ref_yield_exp": ref_yield_exp,
            "cur_yield_exp": cur_yield_exp,
            "ivps_exp": ivps_exp,
            "iv_exp": iv_exp,
            "mos_exp": mos_exp,
            "rr_exp": rr_exp,
        }

    def _scenarios(self, inputs: GrahamInputs) -> tuple[ScenarioOutcome, ...]:
        engine = ScenarioEngine()
        specs = (
            ScenarioSpec(
                ScenarioKind.bear(),
                {
                    "growth_delta": inputs.bear_growth_delta,
                    "yield_delta": inputs.bear_yield_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.base(),
                {"growth_delta": 0.0, "yield_delta": 0.0},
            ),
            ScenarioSpec(
                ScenarioKind.bull(),
                {
                    "growth_delta": inputs.bull_growth_delta,
                    "yield_delta": inputs.bull_yield_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.custom("stress_growth", "Stress Growth"),
                {
                    "growth_delta": -abs(inputs.bear_growth_delta) * 2,
                    "yield_delta": abs(inputs.bear_yield_delta),
                },
            ),
        )

        def evaluator(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            g_delta = float(ctx.get("growth_delta", 0.0))
            y_delta = float(ctx.get("yield_delta", 0.0))
            adj = replace(
                inputs,
                growth_rate=inputs.growth_rate + g_delta,
                aaa_bond_yield=inputs.aaa_bond_yield + y_delta,
            )
            if adj.aaa_bond_yield <= 0:
                raise ValuationError("scenario aaa_bond_yield must be > 0")
            out = self._value(adj)
            return {
                "intrinsic_value": out["intrinsic_value"],
                "equity_value": out["intrinsic_value"],
                "intrinsic_value_per_share": out["ivps"],
                "notes": f"growth_delta={g_delta}, yield_delta={y_delta}",
                "extras": {"g_pct": out["g_pct"], "yield_factor": out["yield_factor"]},
            }

        return engine.scenarios({}, specs=specs, evaluator=evaluator)

    def _sensitivity(self, inputs: GrahamInputs) -> SensitivityMatrix:
        g = inputs.growth_rate
        y = inputs.aaa_bond_yield
        eps = self._eps(inputs)
        rr = inputs.required_return if inputs.required_return is not None else 0.10

        g_step = 0.01 if inputs.growth_as_decimal else 1.0
        axes = (
            SensitivityAxis("growth_rate", (g - g_step, g, g + g_step)),
            # Low sample may be ≤0 near zero yields — evaluator returns None.
            SensitivityAxis("bond_yield", (y - 0.005, y, y + 0.005)),
            SensitivityAxis("eps", (eps * 0.9, eps, eps * 1.1)),
            SensitivityAxis("required_return", (max(1e-6, rr - 0.01), rr, rr + 0.01)),
        )

        def evaluator(ctx: Mapping[str, Any]) -> float | None:
            adj = inputs
            if "growth_rate" in ctx and ctx["growth_rate"] != g:
                adj = replace(adj, growth_rate=float(ctx["growth_rate"]))
            if "bond_yield" in ctx and ctx["bond_yield"] != y:
                adj = replace(adj, aaa_bond_yield=float(ctx["bond_yield"]))
            if "eps" in ctx and ctx["eps"] != eps:
                adj = replace(adj, normalized_eps=float(ctx["eps"]))
            if "required_return" in ctx and ctx["required_return"] != rr:
                adj = replace(adj, required_return=float(ctx["required_return"]))
            try:
                if adj.aaa_bond_yield <= 0:
                    raise ValuationError("bond yield <= 0")
                return float(self._value(adj)["ivps"])
            except ValuationError:
                return None

        context = {
            "growth_rate": g,
            "bond_yield": y,
            "eps": eps,
            "required_return": rr,
        }
        return SensitivityEngine().sensitivity(
            context,
            axes=axes,
            evaluator=evaluator,
            output_name="intrinsic_value_per_share",
        )

    def _confidence(self, inputs: GrahamInputs, base: Mapping[str, Any]):
        series = [
            v
            for v in (
                inputs.average_eps_3y,
                inputs.average_eps_5y,
                inputs.average_eps_10y,
                inputs.eps_trailing,
            )
            if v is not None
        ]
        earnings_stability = 1.0
        if len(series) >= 2:
            mean = statistics.fmean(series)
            if mean != 0:
                cv = statistics.pstdev(series) / abs(mean)
                earnings_stability = max(0.0, min(1.0, 1.0 - cv))
            if series[-1] < series[0]:
                earnings_stability = min(earnings_stability, 0.5)

        eps_consistency = 1.0
        if inputs.normalized_eps is not None and inputs.eps_trailing != 0:
            gap = abs(inputs.normalized_eps - inputs.eps_trailing) / abs(
                inputs.eps_trailing
            )
            eps_consistency = max(0.0, min(1.0, 1.0 - gap))

        g_pct = float(base["g_pct"])
        growth_stability = max(0.0, min(1.0, 1.0 - abs(g_pct) / 25.0))

        aq = inputs.accounting_quality_score
        if aq is None:
            accounting_quality = 0.6
        else:
            accounting_quality = aq / 100.0 if aq > 1.0 else float(aq)
            accounting_quality = max(0.0, min(1.0, accounting_quality))

        data_completeness = 0.4
        if inputs.normalized_eps is not None:
            data_completeness += 0.15
        if inputs.book_value_per_share is not None:
            data_completeness += 0.15
        if inputs.average_eps_5y is not None or inputs.average_eps_3y is not None:
            data_completeness += 0.15
        if inputs.current_market_price is not None:
            data_completeness += 0.15
        data_completeness = min(1.0, data_completeness)

        return ConfidenceEngine().score(
            {
                "accounting_quality": accounting_quality,
                "forecast_reliability": growth_stability,
                "data_completeness": data_completeness,
                "business_stability": earnings_stability,
                "capital_allocation": eps_consistency,
                "model_assumptions": growth_stability,
            }
        )

    def _quality_flags(
        self,
        inputs: GrahamInputs,
        base: Mapping[str, Any],
        confidence_level: str,
    ) -> tuple[tuple[GrahamQualityFlag, ...], tuple[QualityFlag, ...]]:
        flags: list[GrahamQualityFlag] = []
        core: list[QualityFlag] = []

        series = [
            v
            for v in (
                inputs.average_eps_10y,
                inputs.average_eps_5y,
                inputs.average_eps_3y,
                inputs.eps_trailing,
            )
            if v is not None
        ]
        if len(series) >= 3:
            mean = statistics.fmean(series)
            if mean != 0 and statistics.pstdev(series) / abs(mean) < 0.15:
                flags.append(GrahamQualityFlag.STABLE_EARNINGS)
            if mean != 0 and statistics.pstdev(series) / abs(mean) > 0.40:
                flags.append(GrahamQualityFlag.CYCLICAL_EARNINGS)

        eps = float(base["eps"])
        if eps < 0:
            flags.append(GrahamQualityFlag.NEGATIVE_EPS)

        if (
            inputs.book_value_per_share is not None
            and inputs.book_value_per_share < 1.0
        ):
            flags.append(GrahamQualityFlag.LOW_BOOK_VALUE)

        if float(base["g_pct"]) > 15:
            flags.append(GrahamQualityFlag.HIGH_GROWTH_ASSUMPTION)
            core.append(QualityFlag.OVERLY_OPTIMISTIC_ASSUMPTIONS)

        if inputs.accounting_quality_score is not None:
            aq = inputs.accounting_quality_score
            score = aq / 100.0 if aq > 1.0 else aq
            if score < 0.4:
                flags.append(GrahamQualityFlag.ACCOUNTING_WARNING)
                core.append(QualityFlag.ACCOUNTING_WARNING)

        if confidence_level == "low":
            flags.append(GrahamQualityFlag.LOW_CONFIDENCE)
            core.append(QualityFlag.LOW_DATA_QUALITY)

        return tuple(flags), tuple(core)
