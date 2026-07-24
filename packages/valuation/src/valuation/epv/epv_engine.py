"""Earnings Power Value Engine — zero-growth capitalization (research-only).

Integrates shared Valuation Core engines without modifying Core APIs.
Independent of DCF Intelligence, Reverse DCF, and Residual Income.

References
    Greenwald earnings power value: capitalize normalized owner earnings
    at the cost of capital assuming no growth.
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
from valuation.epv.epv_explainability import explain_many, explain_step
from valuation.epv.epv_models import (
    EPV_VERSION,
    EpvInputs,
    EpvQualityFlag,
    EpvResult,
    NormalizationDetail,
    NormalizationMethod,
)
from valuation.epv.epv_validation import validate_epv_inputs
from valuation.exceptions import ValuationError

__all__ = ["EpvEngine", "EPV_VERSION"]

_METHODOLOGY = (
    "Earnings Power Value (zero growth): "
    "Normalize EBIT (strip one-offs / distortions); "
    "Tax-Adjusted EBIT = EBIT_n × (1 − t); "
    "Owner Earnings = Tax-Adjusted EBIT + Depreciation − Maintenance CapEx "
    "− Working Capital Adjustment; "
    "Enterprise EPV = Owner Earnings / Cost of Capital; "
    "Equity = Enterprise EPV + Cash − Debt − Minority Interest + Investments; "
    "IV/share = Equity / Shares. Research / educational only."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Assumes no growth in earnings power",
    "Maintenance CapEx and normalization are judgment-sensitive",
    "Does not enable Overall Valuation",
    "Independent of DCF / Reverse DCF / Residual Income engines",
)


class EpvEngine:
    """Compute research-only Earnings Power Value."""

    def analyze(self, inputs: EpvInputs) -> EpvResult:
        """Run full EPV analysis (base scenario primary)."""
        t0 = time.perf_counter()
        validation = validate_epv_inputs(inputs)
        base = self._value(inputs)
        if base["enterprise_epv"] is not None and base["enterprise_epv"] < 0:
            raise ValuationError(
                f"impossible enterprise EPV: {base['enterprise_epv']}"
            )

        scenarios = self._scenarios(inputs)
        sensitivity = self._sensitivity(inputs)
        confidence = self._confidence(inputs, base)
        flags, core_flags = self._quality_flags(inputs, base)

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
                    base["normalized_ebit_exp"],
                    base["tax_adjusted_exp"],
                    base["maint_exp"],
                    base["owner_exp"],
                    base["nfe_exp"],
                    base["ev_exp"],
                    base["equity_exp"],
                    base["iv_exp"],
                    base["ivps_exp"],
                    base["mos_exp"],
                )
            ]
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        metadata = ValuationMetadata(
            model_name="epv",
            engine_version=EPV_VERSION,
            methodology=_METHODOLOGY,
            formula_references=(
                "Greenwald Earnings Power Value",
                "Owner Earnings = NOPAT + D&A − MaintCapEx − ΔNWC",
            ),
            assumption_summary={
                "normalization": inputs.normalization_method.value,
                "cost_of_capital": inputs.cost_of_capital,
                "tax_rate": inputs.tax_rate,
                "zero_growth": True,
            },
            research_mode=True,
            calculation_timestamp=datetime.now(UTC).isoformat(),
            execution_time_ms=elapsed_ms,
            core_version=VALUATION_CORE_VERSION,
        )

        return EpvResult(
            version=EPV_VERSION,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            methodology=_METHODOLOGY,
            normalization=base["normalization"],
            normalized_ebit=base["normalized_ebit_exp"],
            tax_adjusted_ebit=base["tax_adjusted_exp"],
            maintenance_capex=base["maint_exp"],
            owner_earnings=base["owner_exp"],
            normalized_free_earnings=base["nfe_exp"],
            enterprise_epv=base["ev_exp"],
            equity_value=base["equity_exp"],
            intrinsic_value=base["iv_exp"],
            intrinsic_value_per_share=base["ivps_exp"],
            margin_of_safety=base["mos_exp"],
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

    def _normalize_ebit(
        self, inputs: EpvInputs
    ) -> tuple[float, NormalizationDetail]:
        method = inputs.normalization_method
        raw = inputs.ebit

        if method is NormalizationMethod.MANUAL_OVERRIDE:
            if inputs.normalized_operating_margin is not None:
                if inputs.revenue <= 0:
                    raise ValuationError(
                        "normalized_operating_margin requires positive revenue"
                    )
                base_ebit = inputs.revenue * inputs.normalized_operating_margin
            elif inputs.average_ebit is not None:
                base_ebit = inputs.average_ebit
            else:
                base_ebit = raw
        elif method is NormalizationMethod.HISTORICAL_AVERAGE:
            if inputs.average_ebit is not None:
                base_ebit = inputs.average_ebit
            elif inputs.historical_ebit:
                base_ebit = statistics.fmean(inputs.historical_ebit)
            elif inputs.normalized_operating_margin is not None:
                base_ebit = inputs.revenue * inputs.normalized_operating_margin
            else:
                raise ValuationError("historical_average requires history or average_ebit")
        elif method is NormalizationMethod.MEDIAN:
            if inputs.historical_ebit:
                base_ebit = float(statistics.median(inputs.historical_ebit))
            elif inputs.average_ebit is not None:
                base_ebit = inputs.average_ebit
            else:
                raise ValuationError("median normalization requires historical_ebit")
        elif method is NormalizationMethod.BUSINESS_CYCLE_ADJUSTMENT:
            if inputs.historical_ebit:
                cycle_base = statistics.fmean(inputs.historical_ebit)
            elif inputs.average_ebit is not None:
                cycle_base = inputs.average_ebit
            elif inputs.normalized_operating_margin is not None:
                cycle_base = inputs.revenue * inputs.normalized_operating_margin
            else:
                raise ValuationError(
                    "business_cycle_adjustment requires history or average_ebit"
                )
            base_ebit = cycle_base * inputs.cycle_adjustment_factor
        else:
            raise ValuationError(f"unknown normalization method: {method!r}")

        # Strip one-time / exceptional / distortion items
        adjustments = {
            "one_time_gains_removed": -abs(inputs.one_time_gains),
            "one_time_losses_added_back": abs(inputs.one_time_losses),
            "asset_sales_removed": -abs(inputs.asset_sales),
            "exceptional_items_removed": -inputs.exceptional_items,
            "accounting_distortions_reversed": -inputs.accounting_distortions,
        }
        normalized = base_ebit + sum(adjustments.values())

        # Optional margin cross-check warning path handled in quality flags
        detail = NormalizationDetail(
            method=method,
            raw_ebit=raw,
            normalized_ebit=normalized,
            adjustments=adjustments,
            notes=(
                f"method={method.value}; "
                f"cycle_factor={inputs.cycle_adjustment_factor}"
            ),
        )
        return normalized, detail

    def _value(self, inputs: EpvInputs) -> dict[str, Any]:
        """Core deterministic EPV math for one assumption set."""
        normalized_ebit, norm_detail = self._normalize_ebit(inputs)
        tax_adjusted = normalized_ebit * (1.0 - inputs.tax_rate)

        # Owner earnings / normalized free earnings (zero growth)
        if inputs.normalized_earnings is not None:
            owner = float(inputs.normalized_earnings)
            nfe = owner
            nfe_note = "manual normalized_earnings override"
        else:
            owner = (
                tax_adjusted
                + inputs.depreciation
                - inputs.maintenance_capex
                - inputs.working_capital_adjustment
            )
            nfe = owner
            nfe_note = "Owner Earnings = TaxAdjEBIT + D&A − MaintCapEx − ΔNWC"

        if inputs.cost_of_capital <= 0:
            raise ValuationError("cost_of_capital must be > 0")

        enterprise = nfe / inputs.cost_of_capital
        equity = (
            enterprise
            + inputs.cash
            - inputs.debt
            - inputs.minority_interest
            + inputs.investments
        )
        iv = equity
        ivps = equity / inputs.shares_outstanding

        mos: float | None = None
        if inputs.current_market_price is not None and ivps != 0:
            mos = (ivps - inputs.current_market_price) / ivps

        conf = "medium"
        normalized_ebit_exp = explain_step(
            name="normalized_ebit",
            value=normalized_ebit,
            formula="Normalize EBIT; strip one-offs / distortions",
            inputs={
                "raw_ebit": inputs.ebit,
                "method": inputs.normalization_method.value,
            },
            intermediates=dict(norm_detail.adjustments),
            confidence=conf,
            notes=norm_detail.notes,
        )
        tax_adjusted_exp = explain_step(
            name="tax_adjusted_ebit",
            value=tax_adjusted,
            formula="TaxAdjEBIT = EBIT_n × (1 − t)",
            inputs={"normalized_ebit": normalized_ebit, "tax_rate": inputs.tax_rate},
            intermediates={},
            confidence=conf,
        )
        maint_exp = explain_step(
            name="maintenance_capex",
            value=inputs.maintenance_capex,
            formula="MaintCapEx = CapEx required to sustain earnings power",
            inputs={"maintenance_capex": inputs.maintenance_capex},
            intermediates={"depreciation": inputs.depreciation},
            confidence=conf,
            notes="Growth CapEx is excluded under zero-growth EPV",
        )
        owner_exp = explain_step(
            name="owner_earnings",
            value=owner,
            formula=(
                "OE = TaxAdjEBIT + Depreciation − MaintCapEx − WC Adj"
                if inputs.normalized_earnings is None
                else "OE = normalized_earnings (override)"
            ),
            inputs={
                "tax_adjusted_ebit": tax_adjusted,
                "depreciation": inputs.depreciation,
                "maintenance_capex": inputs.maintenance_capex,
                "working_capital_adjustment": inputs.working_capital_adjustment,
            },
            intermediates={},
            confidence=conf,
            notes=nfe_note,
        )
        nfe_exp = explain_step(
            name="normalized_free_earnings",
            value=nfe,
            formula="NFE ≡ Owner Earnings under zero-growth EPV",
            inputs={"owner_earnings": owner},
            intermediates={},
            confidence=conf,
        )
        ev_exp = explain_step(
            name="enterprise_epv",
            value=enterprise,
            formula="Enterprise EPV = NFE / Cost of Capital",
            inputs={"normalized_free_earnings": nfe, "cost_of_capital": inputs.cost_of_capital},
            intermediates={},
            confidence=conf,
        )
        equity_exp = explain_step(
            name="equity_value",
            value=equity,
            formula="Equity = EV + Cash − Debt − MI + Investments",
            inputs={
                "enterprise_epv": enterprise,
                "cash": inputs.cash,
                "debt": inputs.debt,
                "minority_interest": inputs.minority_interest,
                "investments": inputs.investments,
            },
            intermediates={},
            confidence=conf,
        )
        iv_exp = explain_step(
            name="intrinsic_value",
            value=iv,
            formula="Intrinsic Value = Equity Value (firm claim on equity)",
            inputs={"equity_value": equity},
            intermediates={},
            confidence=conf,
        )
        ivps_exp = explain_step(
            name="intrinsic_value_per_share",
            value=ivps,
            formula="IV/share = Equity / Shares",
            inputs={"equity_value": equity, "shares": inputs.shares_outstanding},
            intermediates={},
            confidence=conf,
        )
        mos_exp = explain_step(
            name="margin_of_safety",
            value=mos,
            formula="MoS = (IV/share − Price) / IV/share",
            inputs={
                "ivps": ivps,
                "price": inputs.current_market_price,
            },
            intermediates={},
            confidence="low" if mos is None else conf,
            notes="Research posture only — not a recommendation",
        )

        return {
            "normalization": norm_detail,
            "normalized_ebit": normalized_ebit,
            "tax_adjusted": tax_adjusted,
            "owner_earnings": owner,
            "normalized_free_earnings": nfe,
            "enterprise_epv": enterprise,
            "equity_value": equity,
            "intrinsic_value": iv,
            "intrinsic_value_per_share": ivps,
            "margin_of_safety": mos,
            "normalized_ebit_exp": normalized_ebit_exp,
            "tax_adjusted_exp": tax_adjusted_exp,
            "maint_exp": maint_exp,
            "owner_exp": owner_exp,
            "nfe_exp": nfe_exp,
            "ev_exp": ev_exp,
            "equity_exp": equity_exp,
            "iv_exp": iv_exp,
            "ivps_exp": ivps_exp,
            "mos_exp": mos_exp,
        }

    def _scenarios(self, inputs: EpvInputs) -> tuple[ScenarioOutcome, ...]:
        engine = ScenarioEngine()
        specs = (
            ScenarioSpec(
                ScenarioKind.bear(),
                {
                    "earnings_delta": inputs.bear_earnings_delta,
                    "wacc_delta": inputs.bear_wacc_delta,
                },
            ),
            ScenarioSpec(ScenarioKind.base(), {"earnings_delta": 0.0, "wacc_delta": 0.0}),
            ScenarioSpec(
                ScenarioKind.bull(),
                {
                    "earnings_delta": inputs.bull_earnings_delta,
                    "wacc_delta": inputs.bull_wacc_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.custom("stress_margin", "Stress Margin"),
                {"earnings_delta": -abs(inputs.ebit) * 0.05, "wacc_delta": 0.005},
            ),
        )

        def evaluator(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            earnings_delta = float(ctx.get("earnings_delta", 0.0))
            wacc_delta = float(ctx.get("wacc_delta", 0.0))
            # Apply deltas via normalized_earnings override path after base OE
            base_val = self._value(inputs)
            base_oe = float(base_val["owner_earnings"])
            wacc = inputs.cost_of_capital + wacc_delta
            if wacc <= 0:
                raise ValuationError("scenario cost_of_capital must be > 0")
            nfe = base_oe + earnings_delta
            # Rebuild with override
            adj = replace(
                inputs,
                normalized_earnings=nfe,
                cost_of_capital=wacc,
            )
            out = self._value(adj)
            return {
                "intrinsic_value": out["intrinsic_value"],
                "equity_value": out["equity_value"],
                "intrinsic_value_per_share": out["intrinsic_value_per_share"],
                "notes": f"earnings_delta={earnings_delta}, wacc_delta={wacc_delta}",
                "extras": {
                    "enterprise_epv": out["enterprise_epv"],
                    "owner_earnings": out["owner_earnings"],
                },
            }

        return engine.scenarios({}, specs=specs, evaluator=evaluator)

    def _sensitivity(self, inputs: EpvInputs) -> SensitivityMatrix:
        base = self._value(inputs)
        base_oe = float(base["owner_earnings"])
        wacc = inputs.cost_of_capital
        margin = (
            inputs.normalized_operating_margin
            if inputs.normalized_operating_margin is not None
            else (inputs.ebit / inputs.revenue if inputs.revenue else 0.0)
        )
        maint = inputs.maintenance_capex
        tax = inputs.tax_rate

        axes = (
            SensitivityAxis(
                "cost_of_capital",
                (wacc - 0.01, wacc, wacc + 0.01),
            ),
            SensitivityAxis(
                "normalized_margin",
                (margin - 0.02, margin, margin + 0.02),
            ),
            SensitivityAxis(
                "maintenance_capex",
                (max(0.0, maint * 0.8), maint, maint * 1.2),
            ),
            SensitivityAxis(
                "tax_rate",
                (max(0.0, tax - 0.05), tax, min(0.99, tax + 0.05)),
            ),
            SensitivityAxis(
                "owner_earnings",
                (base_oe * 0.9, base_oe, base_oe * 1.1),
            ),
        )

        def evaluator(ctx: Mapping[str, Any]) -> float | None:
            # Detect which axis was overridden by comparing to base context keys
            adj = inputs
            if "cost_of_capital" in ctx and ctx["cost_of_capital"] != wacc:
                adj = replace(adj, cost_of_capital=float(ctx["cost_of_capital"]))
            if "normalized_margin" in ctx and ctx["normalized_margin"] != margin:
                if adj.revenue <= 0:
                    return None
                adj = replace(
                    adj,
                    normalization_method=NormalizationMethod.MANUAL_OVERRIDE,
                    normalized_operating_margin=float(ctx["normalized_margin"]),
                    normalized_earnings=None,
                )
            if "maintenance_capex" in ctx and ctx["maintenance_capex"] != maint:
                adj = replace(
                    adj,
                    maintenance_capex=float(ctx["maintenance_capex"]),
                    normalized_earnings=None,
                )
            if "tax_rate" in ctx and ctx["tax_rate"] != tax:
                adj = replace(
                    adj,
                    tax_rate=float(ctx["tax_rate"]),
                    normalized_earnings=None,
                )
            if "owner_earnings" in ctx and ctx["owner_earnings"] != base_oe:
                adj = replace(
                    adj,
                    normalized_earnings=float(ctx["owner_earnings"]),
                )
            try:
                return float(self._value(adj)["intrinsic_value_per_share"])
            except ValuationError:
                return None

        # SensitivityEngine OTAT: each axis evaluated with context containing
        # only that axis key when we pass empty base and set keys in evaluator
        # via merged context. Pass full base so comparisons work.
        context = {
            "cost_of_capital": wacc,
            "normalized_margin": margin,
            "maintenance_capex": maint,
            "tax_rate": tax,
            "owner_earnings": base_oe,
        }
        return SensitivityEngine().sensitivity(
            context,
            axes=axes,
            evaluator=evaluator,
            output_name="intrinsic_value_per_share",
        )

    def _confidence(
        self, inputs: EpvInputs, base: Mapping[str, Any]
    ):
        hist = inputs.historical_ebit
        earnings_stability = 1.0
        if len(hist) >= 2:
            mean = statistics.fmean(hist)
            if mean != 0:
                cv = statistics.pstdev(hist) / abs(mean)
                earnings_stability = max(0.0, min(1.0, 1.0 - cv))
            if hist[-1] < hist[0]:
                earnings_stability = min(earnings_stability, 0.5)

        margin_stability = 1.0
        margins = inputs.historical_ebit_margin
        if len(margins) >= 2:
            mmean = statistics.fmean(margins)
            if mmean != 0:
                mcv = statistics.pstdev(margins) / abs(mmean)
                margin_stability = max(0.0, min(1.0, 1.0 - mcv))
            if margins[-1] < margins[0]:
                margin_stability *= 0.7

        aq = inputs.accounting_quality_score
        if aq is None:
            accounting_quality = 0.6
        else:
            accounting_quality = aq / 100.0 if aq > 1.0 else float(aq)
            accounting_quality = max(0.0, min(1.0, accounting_quality))

        data_completeness = 0.5
        if inputs.historical_ebit:
            data_completeness += 0.2
        if inputs.maintenance_capex >= 0:
            data_completeness += 0.15
        if inputs.current_market_price is not None:
            data_completeness += 0.15
        data_completeness = min(1.0, data_completeness)

        business_stability = earnings_stability
        # Capital allocation: maint capex vs depreciation
        if inputs.depreciation > 0:
            ratio = inputs.maintenance_capex / inputs.depreciation
            capital_allocation = max(0.0, min(1.0, 1.0 - abs(ratio - 1.0)))
        else:
            capital_allocation = 0.5

        return ConfidenceEngine().score(
            {
                "accounting_quality": accounting_quality,
                "forecast_reliability": earnings_stability,  # proxy: stability
                "data_completeness": data_completeness,
                "business_stability": business_stability,
                "capital_allocation": capital_allocation,
                "model_assumptions": margin_stability,
            }
        )

    def _quality_flags(
        self, inputs: EpvInputs, base: Mapping[str, Any]
    ) -> tuple[tuple[EpvQualityFlag, ...], tuple[QualityFlag, ...]]:
        flags: list[EpvQualityFlag] = []
        core: list[QualityFlag] = []
        hist = inputs.historical_ebit

        if len(hist) >= 3:
            mean = statistics.fmean(hist)
            if mean != 0 and statistics.pstdev(hist) / abs(mean) < 0.15:
                flags.append(EpvQualityFlag.STABLE_EARNINGS)
            if mean != 0 and statistics.pstdev(hist) / abs(mean) > 0.40:
                flags.append(EpvQualityFlag.HIGH_CYCLICALITY)
            if hist[-1] < hist[0] * 0.9:
                flags.append(EpvQualityFlag.DECLINING_EARNINGS)

        margins = inputs.historical_ebit_margin
        if len(margins) >= 2 and margins[-1] < margins[0] - 0.02:
            flags.append(EpvQualityFlag.MARGIN_COMPRESSION)
            core.append(QualityFlag.MARGIN_COMPRESSION)

        if abs(inputs.exceptional_items) > 0 or abs(inputs.accounting_distortions) > 0:
            flags.append(EpvQualityFlag.ACCOUNTING_WARNING)
            core.append(QualityFlag.ACCOUNTING_WARNING)

        if inputs.depreciation > 0 and inputs.maintenance_capex > 1.25 * inputs.depreciation:
            flags.append(EpvQualityFlag.HIGH_MAINTENANCE_CAPEX)

        oe = float(base["owner_earnings"])
        tax_adj = float(base["tax_adjusted"])
        if tax_adj != 0 and oe / tax_adj >= 0.85:
            flags.append(EpvQualityFlag.STRONG_OWNER_EARNINGS)
        if tax_adj != 0 and oe / tax_adj < 0.5:
            flags.append(EpvQualityFlag.WEAK_OWNER_EARNINGS)

        return tuple(flags), tuple(core)
