"""Overall Valuation Aggregator — research-only Phase 1 suite finale.

Consumes completed Consensus + method outputs. Never executes valuation engines.
Research labels only — not investment advice.
"""

from __future__ import annotations

import statistics
import time
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from valuation.consensus.consensus_models import (
    ConsensusResult,
    MethodWeightDetail,
    SensitivitySummary as ConsensusSensitivitySummary,
    StandardizedMethodResult,
    normalize_method_input,
)
from valuation.core.confidence_engine import ConfidenceEngine
from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioOutcome,
    ValuationMetadata,
    ValuationResult,
)
from valuation.overall.overall_explainability import explain_many, explain_step
from valuation.overall.overall_models import (
    OVERALL_VERSION,
    ConsistencySummary,
    MethodSummaryRow,
    MosClassification,
    MosThresholds,
    OverallInputs,
    OverallQualityFlag,
    OverallSensitivitySummary,
    OverallValuationError,
    OverallValuationResult,
    ResearchLabel,
    ScenarioSummary,
)
from valuation.overall.overall_validation import validate_overall_inputs

__all__ = ["OverallEngine", "OVERALL_VERSION"]

_METHODOLOGY = (
    "Overall Valuation Aggregator (research only): assemble completed "
    "method results and Consensus Engine output into a single research "
    "view — intrinsic value, margin of safety, confidence, agreement, "
    "scenarios, and sensitivity. Does not re-run DCF / Relative / etc. "
    "Research labels are educational, not investment recommendations."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Overall Valuation does not execute underlying valuation engines",
    "Quality depends entirely on injected Consensus and method results",
    "Research labels are not buy/sell recommendations",
    "No Decision Engine / Copilot / Research package integration in this sprint",
)


class OverallEngine:
    """Aggregate completed valuation outputs into an Overall research result."""

    def analyze(self, inputs: OverallInputs) -> OverallValuationResult:
        """Build Overall Valuation from consensus + optional method results."""
        t0 = time.perf_counter()
        validation = validate_overall_inputs(inputs)

        view = self._resolve_consensus_view(inputs)
        price = float(inputs.current_market_price)
        ivps = view["ivps"]
        iv = view["iv"]
        if ivps is None and iv is not None and inputs.shares_outstanding:
            ivps = iv / inputs.shares_outstanding
        if iv is None and ivps is not None and inputs.shares_outstanding:
            iv = ivps * inputs.shares_outstanding
        if ivps is None and iv is not None:
            ivps = iv
        if iv is None and ivps is not None:
            iv = ivps
        if ivps is None or iv is None:
            raise OverallValuationError(
                "Overall valuation validation failed: unable to resolve intrinsic value"
            )

        mos = (ivps - price) / ivps if ivps != 0 else None
        premium = (price - ivps) / ivps if ivps != 0 else None
        mos_class = self._mos_class(mos, inputs.mos_thresholds)
        label = self._research_label(mos, mos_class)

        method_rows, weights, rankings, applicability = self._method_summary(
            inputs, view, ivps
        )
        consistency = self._consistency(view, method_rows, rankings)
        scenarios = self._scenarios(view)
        sensitivity = self._sensitivity(view)

        ci = view["confidence_interval"]
        fair_lo = min(ci[0], scenarios.bear if scenarios.bear is not None else ci[0])
        fair_hi = max(ci[1], scenarios.bull if scenarios.bull is not None else ci[1])
        val_lo = view["lower_range"]
        val_hi = view["upper_range"]
        if method_rows:
            ivps_vals = [
                r.intrinsic_value_per_share
                for r in method_rows
                if r.intrinsic_value_per_share is not None
            ]
            if ivps_vals:
                val_lo = min(val_lo, min(ivps_vals))
                val_hi = max(val_hi, max(ivps_vals))

        range_pct = ((val_hi - val_lo) / abs(ivps)) if ivps else 0.0
        confidence = self._confidence(view, validation.warnings, sensitivity, method_rows)
        score = self._overall_score(
            mos=mos,
            confidence=confidence,
            agreement=consistency.agreement_pct,
            data_quality=min(1.0, max(0.2, len(method_rows) / 5.0)),
            scenario_stability=self._scenario_stability(scenarios),
            sensitivity_stability=self._sens_stability(sensitivity),
        )
        flags, core_flags = self._quality_flags(
            confidence.level,
            consistency.agreement_pct,
            range_pct,
            inputs,
            method_rows,
            view,
        )
        warnings = tuple(validation.warnings) + tuple(view.get("extra_warnings", ()))

        conf_level = confidence.level
        overall_iv_exp = explain_step(
            name="overall_intrinsic_value",
            value=iv,
            formula="Overall IV = Consensus intrinsic value (injected)",
            inputs={"source": view["source"]},
            intermediates={},
            confidence=conf_level,
            notes="No engine re-execution",
        )
        overall_ivps_exp = explain_step(
            name="overall_intrinsic_value_per_share",
            value=ivps,
            formula="Overall IV/share = Consensus IV/share (injected)",
            inputs={"source": view["source"]},
            intermediates={},
            confidence=conf_level,
        )
        price_exp = explain_step(
            name="current_market_price",
            value=price,
            formula="Observed market price (injected)",
            inputs={},
            intermediates={},
            confidence=conf_level,
        )
        mos_exp = explain_step(
            name="margin_of_safety",
            value=mos,
            formula="MoS = (IV/share − Price) / IV/share",
            inputs={"ivps": ivps, "price": price},
            intermediates={"classification": mos_class.value},
            confidence=conf_level,
            notes="Research classification only — not a recommendation",
            warnings=(
                ("Price is zero — MoS limited",)
                if price == 0
                else ()
            ),
        )
        pd_exp = explain_step(
            name="premium_discount",
            value=premium,
            formula="Premium/Discount = (Price − IV/share) / IV/share",
            inputs={"ivps": ivps, "price": price},
            intermediates={},
            confidence=conf_level,
        )
        consensus_exp = explain_step(
            name="consensus_value",
            value=view["consensus_display"],
            formula="Consensus value from Consensus Engine output",
            inputs={"consensus_confidence": view["consensus_confidence"]},
            intermediates={},
            confidence=view["consensus_confidence"],
        )
        score_exp = explain_step(
            name="overall_valuation_score",
            value=score,
            formula=(
                "0–100 blend of valuation strength, confidence, agreement, "
                "data quality, scenario & sensitivity stability"
            ),
            inputs={
                "agreement_pct": consistency.agreement_pct,
                "confidence": confidence.level,
            },
            intermediates={},
            confidence=conf_level,
        )

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
                    overall_iv_exp,
                    overall_ivps_exp,
                    price_exp,
                    mos_exp,
                    pd_exp,
                    consensus_exp,
                    score_exp,
                )
            ]
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        metadata = ValuationMetadata(
            model_name="overall",
            engine_version=OVERALL_VERSION,
            methodology=_METHODOLOGY,
            formula_references=(
                "Overall IV from Consensus",
                "MoS = (IV − Price) / IV",
                "Overall Score 0–100 research blend",
            ),
            assumption_summary={
                "consensus_source": view["source"],
                "method_count": len(method_rows),
                "mos_classification": mos_class.value,
                "research_label": label.value,
                "overall_valuation_enabled": True,
            },
            research_mode=True,
            calculation_timestamp=datetime.now(UTC).isoformat(),
            execution_time_ms=elapsed_ms,
            core_version=VALUATION_CORE_VERSION,
        )

        return OverallValuationResult(
            version=OVERALL_VERSION,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            methodology=_METHODOLOGY,
            overall_intrinsic_value=overall_iv_exp,
            overall_intrinsic_value_per_share=overall_ivps_exp,
            current_market_price=price_exp,
            margin_of_safety=mos_exp,
            premium_discount=pd_exp,
            mos_classification=mos_class,
            research_label=label,
            consensus_value=consensus_exp,
            consensus_confidence=view["consensus_confidence"],
            overall_confidence=confidence.level,
            confidence_detail=confidence,
            overall_valuation_score=score_exp,
            confidence_interval=ci,
            bull_value=scenarios.bull,
            base_value=scenarios.base,
            bear_value=scenarios.bear,
            fair_value_range=(fair_lo, fair_hi),
            valuation_range=(val_lo, val_hi),
            method_summary=method_rows,
            method_rankings=rankings,
            method_weights=weights,
            method_agreement=consistency.agreement_pct,
            consistency_score=consistency.agreement_pct,
            consistency=consistency,
            applicability_summary=applicability,
            scenario_summary=scenarios,
            sensitivity_summary=sensitivity,
            quality_flags=flags,
            core_quality_flags=core_flags,
            validation_summary=validation,
            explainability=explainability,
            warnings=warnings,
            limitations=_LIMITATIONS,
            metadata=metadata,
            overall_valuation_enabled=True,
            execution_time_ms=elapsed_ms,
        )

    # --------------------------------------------------------- consensus view
    def _resolve_consensus_view(self, inputs: OverallInputs) -> dict[str, Any]:
        c = inputs.consensus
        if isinstance(c, ConsensusResult):
            iv = c.consensus_intrinsic_value.value
            ivps = c.consensus_per_share.value
            return {
                "source": "ConsensusResult",
                "iv": iv,
                "ivps": ivps,
                "consensus_display": ivps if ivps is not None else iv,
                "consensus_confidence": c.consensus_confidence,
                "confidence_score": c.confidence_detail.score,
                "confidence_interval": c.confidence_interval,
                "lower_range": c.lower_range,
                "upper_range": c.upper_range,
                "consistency": (
                    c.consistency_score.value
                    if c.consistency_score.value is not None
                    else 50.0
                ),
                "method_weights": c.method_weights,
                "method_rankings": c.method_rankings,
                "applicability": dict(c.applicability_scores),
                "outliers": {o.method for o in c.outliers},
                "outlier_list": c.outliers,
                "standardized": c.standardized_methods,
                "scenarios": c.scenario_results,
                "sensitivity": c.sensitivity_summary,
                "extra_warnings": (),
            }

        if isinstance(c, ValuationResult):
            return {
                "source": "ValuationResult",
                "iv": c.intrinsic_value,
                "ivps": c.intrinsic_value_per_share,
                "consensus_display": c.intrinsic_value_per_share
                if c.intrinsic_value_per_share is not None
                else c.intrinsic_value,
                "consensus_confidence": c.confidence_level,
                "confidence_score": c.confidence_score,
                "confidence_interval": self._ci_from_scenarios(c.scenario_results, c),
                "lower_range": c.intrinsic_value_per_share
                if c.intrinsic_value_per_share is not None
                else (c.intrinsic_value or 0.0),
                "upper_range": c.intrinsic_value_per_share
                if c.intrinsic_value_per_share is not None
                else (c.intrinsic_value or 0.0),
                "consistency": 50.0,
                "method_weights": (),
                "method_rankings": (),
                "applicability": {},
                "outliers": set(),
                "outlier_list": (),
                "standardized": (),
                "scenarios": c.scenario_results,
                "sensitivity": None,
                "extra_warnings": (),
            }

        if isinstance(c, Mapping):
            iv = c.get("intrinsic_value")
            ivps = c.get("intrinsic_value_per_share")
            conf = str(c.get("confidence") or c.get("confidence_level") or "medium")
            score = c.get("confidence_score")
            if score is None:
                score = {"high": 6.0, "medium": 4.0, "low": 2.0}.get(conf.lower(), 4.0)
            ci = c.get("confidence_interval")
            if isinstance(ci, (list, tuple)) and len(ci) == 2:
                interval = (float(ci[0]), float(ci[1]))
            else:
                base = float(ivps if ivps is not None else iv or 0.0)
                interval = (base * 0.9, base * 1.1)
            consistency = float(c.get("consistency_score") or 50.0)
            return {
                "source": "v2_payload",
                "iv": float(iv) if iv is not None else None,
                "ivps": float(ivps) if ivps is not None else None,
                "consensus_display": float(ivps)
                if ivps is not None
                else (float(iv) if iv is not None else None),
                "consensus_confidence": conf,
                "confidence_score": float(score),
                "confidence_interval": interval,
                "lower_range": float(c.get("lower_range") or interval[0]),
                "upper_range": float(c.get("upper_range") or interval[1]),
                "consistency": consistency,
                "method_weights": (),
                "method_rankings": tuple(c.get("method_rankings") or ()),
                "applicability": {},
                "outliers": set(),
                "outlier_list": (),
                "standardized": (),
                "scenarios": (),
                "sensitivity": None,
                "extra_warnings": (),
            }

        raise OverallValuationError(
            f"Overall valuation validation failed: unsupported consensus type: {type(c)!r}"
        )

    def _ci_from_scenarios(
        self, scenarios: Sequence[ScenarioOutcome], result: ValuationResult
    ) -> tuple[float, float]:
        vals = []
        for s in scenarios:
            v = s.intrinsic_value_per_share
            if v is None:
                v = s.intrinsic_value
            if v is not None:
                vals.append(float(v))
        if len(vals) >= 2:
            return min(vals), max(vals)
        base = result.intrinsic_value_per_share or result.intrinsic_value or 0.0
        return float(base) * 0.9, float(base) * 1.1

    # ------------------------------------------------------------------- MoS
    def _mos_class(
        self, mos: float | None, thr: MosThresholds
    ) -> MosClassification:
        if mos is None:
            return MosClassification.FAIRLY_VALUED
        if mos >= thr.deep_value:
            return MosClassification.DEEP_VALUE
        if mos >= thr.undervalued:
            return MosClassification.UNDERVALUED
        if mos >= -thr.fairly_band:
            return MosClassification.FAIRLY_VALUED
        if mos >= thr.extremely_overvalued:
            return MosClassification.OVERVALUED
        return MosClassification.EXTREMELY_OVERVALUED

    def _research_label(
        self, mos: float | None, mos_class: MosClassification
    ) -> ResearchLabel:
        if mos is None:
            return ResearchLabel.WATCHLIST
        mapping = {
            MosClassification.DEEP_VALUE: ResearchLabel.STRONG_BUY_CANDIDATE,
            MosClassification.UNDERVALUED: ResearchLabel.BUY_CANDIDATE,
            MosClassification.FAIRLY_VALUED: ResearchLabel.FAIRLY_VALUED,
            MosClassification.OVERVALUED: ResearchLabel.EXPENSIVE,
            MosClassification.EXTREMELY_OVERVALUED: ResearchLabel.HIGHLY_EXPENSIVE,
        }
        label = mapping[mos_class]
        # Thin band near fair → watchlist
        if mos_class is MosClassification.FAIRLY_VALUED and mos is not None:
            if abs(mos) < 0.05:
                return ResearchLabel.WATCHLIST
        return label

    # ---------------------------------------------------------- method summary
    def _method_summary(
        self,
        inputs: OverallInputs,
        view: Mapping[str, Any],
        consensus_ivps: float,
    ) -> tuple[
        tuple[MethodSummaryRow, ...],
        tuple[MethodWeightDetail, ...] | tuple[tuple[str, float], ...],
        tuple[str, ...],
        dict[str, float],
    ]:
        weight_details: tuple[MethodWeightDetail, ...] = tuple(
            view.get("method_weights") or ()
        )
        weight_map = {d.method: d.weight for d in weight_details}
        applicability = dict(view.get("applicability") or {})
        outliers = set(view.get("outliers") or ())

        std_methods: tuple[StandardizedMethodResult, ...] = tuple(
            view.get("standardized") or ()
        )
        by_name: dict[str, StandardizedMethodResult] = {m.method: m for m in std_methods}

        for raw in inputs.methods:
            try:
                std = normalize_method_input(raw)
            except Exception:
                continue
            by_name[std.method] = std

        if by_name and not any(weight_map.get(m, 0.0) > 0 for m in by_name):
            eq = 1.0 / len(by_name)
            weight_map = {m: eq for m in by_name}
        else:
            for m in by_name:
                weight_map.setdefault(m, 0.0)

        rows: list[MethodSummaryRow] = []
        for method, std in sorted(by_name.items()):
            ivps = std.intrinsic_value_per_share
            agreement = None
            if ivps is not None and consensus_ivps != 0:
                agreement = max(
                    0.0,
                    min(100.0, 100.0 * (1.0 - abs(ivps - consensus_ivps) / abs(consensus_ivps))),
                )
            status = "included"
            warns: list[str] = list(std.validation_warnings)
            if method in outliers:
                status = "outlier"
                warns.append("flagged as consensus outlier")
            if not std.validation_ok:
                status = "validation_warning"
            w = weight_map.get(method, 0.0)
            if w <= 0 and status == "included":
                status = "zero_weight"
            rows.append(
                MethodSummaryRow(
                    method=method,
                    intrinsic_value=std.intrinsic_value,
                    intrinsic_value_per_share=ivps,
                    confidence=std.confidence_level,
                    confidence_score=std.confidence_score,
                    weight=w,
                    agreement_pct=agreement,
                    status=status,
                    warnings=tuple(warns),
                )
            )

        rankings = tuple(view.get("method_rankings") or ())
        if not rankings:
            rankings = tuple(
                r.method
                for r in sorted(rows, key=lambda x: (-x.weight, x.method))
            )

        if weight_details:
            weights_out: tuple[MethodWeightDetail, ...] | tuple[tuple[str, float], ...] = (
                weight_details
            )
        else:
            weights_out = tuple((r.method, r.weight) for r in rows)

        return tuple(rows), weights_out, rankings, applicability

    def _consistency(
        self,
        view: Mapping[str, Any],
        rows: Sequence[MethodSummaryRow],
        rankings: Sequence[str],
    ) -> ConsistencySummary:
        agreement = float(view.get("consistency") or 50.0)
        vals = [
            (r.method, r.intrinsic_value_per_share)
            for r in rows
            if r.intrinsic_value_per_share is not None
        ]
        highest = lowest = None
        if vals:
            highest = max(vals, key=lambda x: x[1])[0]
            lowest = min(vals, key=lambda x: x[1])[0]
        outliers = list(view.get("outlier_list") or ())
        largest_outlier = None
        if outliers:
            # pick outlier with largest |median deviation| if available
            largest_outlier = max(
                outliers,
                key=lambda o: abs(o.median_deviation or 0.0),
            ).method
        most_trusted = rankings[0] if rankings else (highest if highest else None)
        sens = view.get("sensitivity")
        most_stable = None
        if isinstance(sens, ConsensusSensitivitySummary):
            most_stable = sens.most_stable_method
        return ConsistencySummary(
            agreement_pct=agreement,
            highest_method=highest,
            lowest_method=lowest,
            largest_outlier=largest_outlier,
            most_trusted_method=most_trusted,
            most_stable_method=most_stable,
        )

    # -------------------------------------------------------------- scenarios
    def _scenarios(self, view: Mapping[str, Any]) -> ScenarioSummary:
        outcomes = tuple(view.get("scenarios") or ())
        bear = base = bull = None
        custom: dict[str, float] = {}
        for sc in outcomes:
            val = sc.intrinsic_value_per_share
            if val is None:
                val = sc.intrinsic_value
            if val is None:
                continue
            name = sc.kind.name
            if name == "bear":
                bear = float(val)
            elif name == "base":
                base = float(val)
            elif name == "bull":
                bull = float(val)
            else:
                custom[name] = float(val)
        return ScenarioSummary(
            bear=bear,
            base=base,
            bull=bull,
            custom=custom,
            outcomes=outcomes,
        )

    def _scenario_stability(self, scenarios: ScenarioSummary) -> float:
        vals = [v for v in (scenarios.bear, scenarios.base, scenarios.bull) if v is not None]
        if len(vals) < 2:
            return 0.5
        mid = statistics.median(vals)
        if mid == 0:
            return 0.4
        spread = (max(vals) - min(vals)) / abs(mid)
        return max(0.1, min(1.0, 1.0 - min(1.0, spread)))

    # ------------------------------------------------------------ sensitivity
    def _sensitivity(self, view: Mapping[str, Any]) -> OverallSensitivitySummary:
        sens = view.get("sensitivity")
        if isinstance(sens, ConsensusSensitivitySummary) and sens.method_scores:
            ranking = tuple(
                sorted(sens.method_scores, key=lambda k: sens.method_scores[k])
            )
            return OverallSensitivitySummary(
                highest_risk_driver=sens.least_stable_method,
                most_stable_driver=sens.most_stable_method,
                sensitivity_ranking=ranking,
                average_sensitivity=sens.average_sensitivity,
                method_scores=dict(sens.method_scores),
            )
        return OverallSensitivitySummary(
            highest_risk_driver=None,
            most_stable_driver=None,
            sensitivity_ranking=(),
            average_sensitivity=None,
            method_scores={},
        )

    def _sens_stability(self, summary: OverallSensitivitySummary) -> float:
        if summary.average_sensitivity is None:
            return 0.5
        return max(0.1, min(1.0, 1.0 - min(1.0, summary.average_sensitivity)))

    # ------------------------------------------------------------ confidence
    def _confidence(
        self,
        view: Mapping[str, Any],
        validation_warnings: Sequence[str],
        sensitivity: OverallSensitivitySummary,
        rows: Sequence[MethodSummaryRow],
    ):
        cons_score = float(view.get("confidence_score") or 4.0)
        method_conf_n = max(0.0, min(1.0, cons_score / 8.0))
        validation_q = 1.0 if not validation_warnings else 0.7
        consistency = float(view.get("consistency") or 50.0) / 100.0
        data = min(1.0, max(0.2, len(rows) / 5.0)) if rows else 0.3
        sens_s = self._sens_stability(sensitivity)
        scen_s = 0.6 if view.get("scenarios") else 0.4

        return ConfidenceEngine().score(
            {
                "accounting_quality": method_conf_n,
                "forecast_reliability": consistency,
                "data_completeness": data,
                "business_stability": scen_s,
                "capital_allocation": sens_s,
                "model_assumptions": validation_q,
            }
        )

    def _overall_score(
        self,
        *,
        mos: float | None,
        confidence,
        agreement: float,
        data_quality: float,
        scenario_stability: float,
        sensitivity_stability: float,
    ) -> float:
        # Valuation strength: deeper MoS → higher (clipped)
        if mos is None:
            strength = 0.5
        else:
            strength = max(0.0, min(1.0, 0.5 + mos))  # mos=0 → 0.5; mos=0.4 → 0.9

        conf_n = {
            "high": 1.0,
            "medium": 0.65,
            "low": 0.35,
        }.get(confidence.level, 0.5)

        agreement_n = max(0.0, min(1.0, agreement / 100.0))
        blend = (
            0.25 * strength
            + 0.25 * conf_n
            + 0.20 * agreement_n
            + 0.15 * data_quality
            + 0.10 * scenario_stability
            + 0.05 * sensitivity_stability
        )
        return round(100.0 * blend, 2)

    def _quality_flags(
        self,
        confidence_level: str,
        agreement: float,
        range_pct: float,
        inputs: OverallInputs,
        rows: Sequence[MethodSummaryRow],
        view: Mapping[str, Any],
    ) -> tuple[tuple[OverallQualityFlag, ...], tuple[QualityFlag, ...]]:
        flags: list[OverallQualityFlag] = []
        core: list[QualityFlag] = []

        if confidence_level == "high":
            flags.append(OverallQualityFlag.HIGH_CONFIDENCE)
        elif confidence_level == "low":
            flags.append(OverallQualityFlag.LOW_CONFIDENCE)
            core.append(QualityFlag.FORECAST_RISK)

        if agreement >= 80:
            flags.append(OverallQualityFlag.STRONG_CONSENSUS)
        elif agreement < 55:
            flags.append(OverallQualityFlag.WEAK_CONSENSUS)

        if range_pct >= inputs.wide_range_pct:
            flags.append(OverallQualityFlag.WIDE_VALUATION_RANGE)
        elif range_pct <= inputs.narrow_range_pct and rows:
            flags.append(OverallQualityFlag.NARROW_VALUATION_RANGE)

        if confidence_level == "low" or agreement < 40:
            flags.append(OverallQualityFlag.SPECULATIVE)

        if len(rows) < 3 and not view.get("standardized"):
            flags.append(OverallQualityFlag.INCOMPLETE_DATASET)
            core.append(QualityFlag.LOW_DATA_QUALITY)
        elif len(rows) < 3:
            flags.append(OverallQualityFlag.INCOMPLETE_DATASET)

        return tuple(dict.fromkeys(flags)), tuple(dict.fromkeys(core))
