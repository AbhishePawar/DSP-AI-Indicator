"""Cross-Method Validation & Consensus Engine — research-only.

Compares standardized valuation results. Never calls valuation engines.
Does **not** enable Overall Valuation.
"""

from __future__ import annotations

import math
import statistics
import time
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from valuation.consensus.consensus_explainability import explain_many, explain_step
from valuation.consensus.consensus_models import (
    CONSENSUS_VERSION,
    CompanyProfile,
    ConsensusInputs,
    ConsensusQualityFlag,
    ConsensusResult,
    ConsensusValidationError,
    DisagreementAnalysis,
    MethodCategory,
    MethodWeightDetail,
    OutlierReport,
    OutlierThresholds,
    SensitivitySummary,
    StandardizedMethodResult,
    WeightingMode,
    normalize_method_input,
)
from valuation.consensus.consensus_validation import validate_consensus_inputs
from valuation.core.confidence_engine import ConfidenceEngine
from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioKind,
    ScenarioOutcome,
    ValuationMetadata,
)
from valuation.core.scenario_engine import ScenarioEngine, ScenarioSpec

__all__ = ["ConsensusEngine", "CONSENSUS_VERSION"]

_METHODOLOGY = (
    "Cross-Method Validation & Consensus (research only): normalize "
    "standardized ValuationResult / V2 payloads across methods, score "
    "applicability, detect outliers, and form weighted consensus. "
    "Does not invoke valuation engines. Does not enable Overall Valuation. "
    "Not investment advice."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Consensus quality depends entirely on injected method results",
    "Does not re-run DCF / Reverse DCF / RIV / EPV / Graham / DDM / Asset / Relative",
    "Does not enable Overall Valuation Aggregator",
    "Outlier exclusion is research heuristic — not a trading signal",
)

# Research prior weights by category (relative scale; normalized later)
_RESEARCH_CATEGORY_WEIGHTS: Mapping[MethodCategory, float] = {
    MethodCategory.INTRINSIC: 1.20,
    MethodCategory.RESIDUAL: 1.10,
    MethodCategory.INCOME: 1.00,
    MethodCategory.DIVIDEND: 0.95,
    MethodCategory.ASSET: 0.90,
    MethodCategory.RELATIVE: 0.85,
    MethodCategory.MARKET: 0.80,
}


class ConsensusEngine:
    """Build research-only cross-method consensus from standardized results."""

    def analyze(self, inputs: ConsensusInputs) -> ConsensusResult:
        """Run consensus analysis over provided method results."""
        t0 = time.perf_counter()
        validation = validate_consensus_inputs(inputs)

        methods = tuple(
            normalize_method_input(m, category_overrides=inputs.category_overrides)
            for m in inputs.methods
        )
        applicability = {
            m.method: self._applicability(m, inputs.company_profile)
            for m in methods
        }
        app_explain = {
            m.method: self._applicability_explanation(m, inputs.company_profile)
            for m in methods
        }

        # Prefer per-share for consensus when available; else total IV
        values = self._pick_values(methods)
        outliers = self._detect_outliers(values, inputs.outlier_thresholds)
        outlier_methods = {o.method for o in outliers}

        weights_map, weight_details = self._compute_weights(
            methods=methods,
            applicability=applicability,
            app_explain=app_explain,
            outlier_methods=outlier_methods,
            inputs=inputs,
            values=values,
        )

        included = [
            m
            for m in methods
            if weights_map.get(m.method, 0.0) > 0
            and values.get(m.method) is not None
            and (
                m.method not in outlier_methods
                or not inputs.outlier_thresholds.exclude_outliers_from_consensus
            )
        ]
        if not included:
            # Fall back to methods with a real intrinsic value only (P1-04).
            included = [m for m in methods if values.get(m.method) is not None]
            if not included:
                raise ConsensusValidationError(
                    "Consensus validation failed: no usable intrinsic values"
                )
            # Equal rescue weights among valid methods only
            weights_map = {m.method: 1.0 / len(included) for m in included}
            weight_details = tuple(
                MethodWeightDetail(
                    method=m.method,
                    category=m.category,
                    weight=weights_map.get(m.method, 0.0),
                    applicability_score=applicability[m.method],
                    confidence_score=m.confidence_score,
                    included_in_consensus=m.method in weights_map,
                    is_outlier=m.method in outlier_methods,
                    explanation=(
                        "Rescue equal weight among methods with valid IV — "
                        "unavailable methods excluded (P1-04)"
                        if m.method in weights_map
                        else "Excluded — unavailable / null intrinsic value (P1-04)"
                    ),
                )
                for m in methods
            )

        series = [
            (m.method, float(values[m.method]), weights_map[m.method])
            for m in included
            if values.get(m.method) is not None
        ]
        if not series:
            raise ConsensusValidationError(
                "Consensus validation failed: no usable intrinsic values"
            )

        w_mean = self._weighted_mean(series)
        w_med = self._weighted_median(series)
        med = statistics.median(v for _, v, _ in series)
        trimmed = self._trimmed_mean([v for _, v, _ in series], inputs.trim_fraction)

        # Primary consensus = weighted mean (research default)
        consensus_value = w_mean
        per_share = self._to_per_share(consensus_value, methods, inputs)

        lo = min(v for _, v, _ in series)
        hi = max(v for _, v, _ in series)
        # Approximate 80% CI via weighted percentile band
        ci_lo, ci_hi = self._weighted_percentile_band(series, 0.10, 0.90)

        consistency = self._consistency_score(series)
        disagreement = self._disagreement(methods, values, series)
        sensitivity = self._sensitivity_summary(methods)
        scenarios = self._scenario_consensus(methods, weights_map)

        confidence = self._confidence(
            methods=methods,
            weights_map=weights_map,
            consistency=consistency,
            outliers=outliers,
            validation_warnings=validation.warnings,
            sensitivity=sensitivity,
        )
        flags, core_flags = self._quality_flags(
            consistency=consistency,
            outliers=outliers,
            methods=methods,
            confidence_level=confidence.level,
            disagreement=disagreement,
        )

        rankings = tuple(
            m
            for m, _ in sorted(
                ((d.method, d.weight) for d in weight_details if d.included_in_consensus),
                key=lambda x: (-x[1], x[0]),
            )
        )

        conf_level = confidence.level
        consensus_exp = explain_step(
            name="consensus_intrinsic_value",
            value=consensus_value,
            formula="Consensus IV = Weighted Mean of included method values",
            inputs={"weighting_mode": inputs.weighting_mode.value},
            intermediates={
                "weighted_mean": w_mean,
                "weighted_median": w_med,
                "median": med,
                "trimmed_mean": trimmed,
            },
            confidence=conf_level,
            notes="Outliers may be excluded per thresholds",
        )
        per_share_exp = explain_step(
            name="consensus_per_share",
            value=per_share,
            formula="Consensus/share = Consensus IV / shares (or mean of IVPS)",
            inputs={"shares": inputs.shares_outstanding},
            intermediates={},
            confidence=conf_level,
        )
        w_mean_exp = explain_step(
            name="weighted_mean",
            value=w_mean,
            formula="Σ(w_i × v_i) / Σ(w_i)",
            inputs={"n": len(series)},
            intermediates={},
            confidence=conf_level,
        )
        w_med_exp = explain_step(
            name="weighted_median",
            value=w_med,
            formula="Value at cumulative weight ≥ 0.5",
            inputs={"n": len(series)},
            intermediates={},
            confidence=conf_level,
        )
        med_exp = explain_step(
            name="median",
            value=med,
            formula="Median of included method values",
            inputs={"n": len(series)},
            intermediates={},
            confidence=conf_level,
        )
        trim_exp = explain_step(
            name="trimmed_mean",
            value=trimmed,
            formula=f"Mean after trimming {inputs.trim_fraction:.0%} each tail",
            inputs={"trim_fraction": inputs.trim_fraction},
            intermediates={},
            confidence=conf_level,
        )
        consistency_exp = explain_step(
            name="consistency_score",
            value=consistency,
            formula="100 × (1 − CV) clipped to [0, 100]; CV = stdev/|mean|",
            inputs={"n": len(series)},
            intermediates={"spread_pct": disagreement.overall_spread_pct},
            confidence=conf_level,
            notes="Higher score → stronger agreement across methods",
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
                    consensus_exp,
                    per_share_exp,
                    w_mean_exp,
                    w_med_exp,
                    med_exp,
                    trim_exp,
                    consistency_exp,
                )
            ]
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        metadata = ValuationMetadata(
            model_name="consensus",
            engine_version=CONSENSUS_VERSION,
            methodology=_METHODOLOGY,
            formula_references=(
                "Weighted mean / median / trimmed mean consensus",
                "Z-score / IQR / median-deviation outlier detection",
            ),
            assumption_summary={
                "weighting_mode": inputs.weighting_mode.value,
                "method_count": len(methods),
                "included_count": len(series),
                "exclude_outliers": inputs.outlier_thresholds.exclude_outliers_from_consensus,
            },
            research_mode=True,
            calculation_timestamp=datetime.now(UTC).isoformat(),
            execution_time_ms=elapsed_ms,
            core_version=VALUATION_CORE_VERSION,
        )

        return ConsensusResult(
            version=CONSENSUS_VERSION,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            methodology=_METHODOLOGY,
            consensus_intrinsic_value=consensus_exp,
            consensus_per_share=per_share_exp,
            consensus_confidence=confidence.level,
            confidence_detail=confidence,
            weighted_mean=w_mean_exp,
            weighted_median=w_med_exp,
            median=med_exp,
            trimmed_mean=trim_exp,
            method_rankings=rankings,
            method_weights=weight_details,
            applicability_scores=applicability,
            outliers=outliers,
            disagreement=disagreement,
            consistency_score=consistency_exp,
            confidence_interval=(ci_lo, ci_hi),
            upper_range=hi,
            lower_range=lo,
            scenario_results=scenarios,
            sensitivity_summary=sensitivity,
            quality_flags=flags,
            core_quality_flags=core_flags,
            validation_summary=validation,
            explainability=explainability,
            limitations=_LIMITATIONS,
            metadata=metadata,
            standardized_methods=methods,
            execution_time_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------ value pick
    def _pick_values(
        self, methods: Sequence[StandardizedMethodResult]
    ) -> dict[str, float | None]:
        """Prefer IVPS when majority have it; else total intrinsic value."""
        with_ivps = sum(1 for m in methods if m.intrinsic_value_per_share is not None)
        use_ivps = with_ivps >= max(1, (len(methods) + 1) // 2)
        out: dict[str, float | None] = {}
        for m in methods:
            if use_ivps and m.intrinsic_value_per_share is not None:
                out[m.method] = m.intrinsic_value_per_share
            elif m.intrinsic_value is not None:
                out[m.method] = m.intrinsic_value
            elif m.intrinsic_value_per_share is not None:
                out[m.method] = m.intrinsic_value_per_share
            else:
                out[m.method] = None
        return out

    def _to_per_share(
        self,
        consensus_value: float,
        methods: Sequence[StandardizedMethodResult],
        inputs: ConsensusInputs,
    ) -> float:
        ivps_vals = [
            m.intrinsic_value_per_share
            for m in methods
            if m.intrinsic_value_per_share is not None
        ]
        # If consensus was already built on IVPS scale, return as-is when
        # majority had IVPS; else convert via shares if provided.
        with_ivps = len(ivps_vals)
        if with_ivps >= max(1, (len(methods) + 1) // 2):
            return consensus_value
        if inputs.shares_outstanding and inputs.shares_outstanding > 0:
            return consensus_value / inputs.shares_outstanding
        if ivps_vals:
            return statistics.mean(ivps_vals)
        return consensus_value

    # ---------------------------------------------------------- applicability
    def _applicability(
        self, method: StandardizedMethodResult, profile: CompanyProfile
    ) -> float:
        score = 0.55
        cat = method.category
        if profile.pays_dividend and cat is MethodCategory.DIVIDEND:
            score += 0.30
        if profile.asset_heavy and cat is MethodCategory.ASSET:
            score += 0.30
        if profile.holding_company and cat is MethodCategory.ASSET:
            score += 0.25
        if profile.growth_company and cat is MethodCategory.INTRINSIC:
            score += 0.25
        if profile.growth_company and cat is MethodCategory.MARKET:
            score += 0.10
        if profile.loss_making and cat is MethodCategory.RELATIVE:
            score += 0.30
        if profile.loss_making and cat is MethodCategory.INTRINSIC:
            score -= 0.15
        if profile.financial_institution and cat is MethodCategory.RELATIVE:
            score += 0.25
        if profile.financial_institution and cat is MethodCategory.ASSET:
            score += 0.10
        if profile.pays_dividend and cat is MethodCategory.INCOME:
            score += 0.05
        if not method.validation_ok:
            score -= 0.20
        return max(0.05, min(1.0, score))

    def _applicability_explanation(
        self, method: StandardizedMethodResult, profile: CompanyProfile
    ) -> str:
        parts: list[str] = [f"base=0.55 category={method.category.value}"]
        if profile.pays_dividend and method.category is MethodCategory.DIVIDEND:
            parts.append("+0.30 dividend payer → DDM")
        if profile.asset_heavy and method.category is MethodCategory.ASSET:
            parts.append("+0.30 asset-heavy → Asset-Based")
        if profile.holding_company and method.category is MethodCategory.ASSET:
            parts.append("+0.25 holding → NAV/Asset")
        if profile.growth_company and method.category is MethodCategory.INTRINSIC:
            parts.append("+0.25 growth → DCF/intrinsic")
        if profile.loss_making and method.category is MethodCategory.RELATIVE:
            parts.append("+0.30 loss-making → Relative")
        if profile.loss_making and method.category is MethodCategory.INTRINSIC:
            parts.append("-0.15 loss-making → lower intrinsic")
        if profile.financial_institution and method.category is MethodCategory.RELATIVE:
            parts.append("+0.25 financial → Relative/P/B")
        if not method.validation_ok:
            parts.append("-0.20 validation not ok")
        return "; ".join(parts)

    # --------------------------------------------------------------- weights
    def _compute_weights(
        self,
        *,
        methods: Sequence[StandardizedMethodResult],
        applicability: Mapping[str, float],
        app_explain: Mapping[str, str],
        outlier_methods: set[str],
        inputs: ConsensusInputs,
        values: Mapping[str, float | None] | None = None,
    ) -> tuple[dict[str, float], tuple[MethodWeightDetail, ...]]:
        mode = inputs.weighting_mode
        raw: dict[str, float] = {}
        explanations: dict[str, str] = {}
        value_map = values or {}

        for m in methods:
            if mode is WeightingMode.EQUAL:
                raw[m.method] = 1.0
                explanations[m.method] = "Equal weighting"
            elif mode is WeightingMode.CONFIDENCE:
                raw[m.method] = max(0.0, m.confidence_score)
                explanations[m.method] = (
                    f"Confidence weighting score={m.confidence_score:.3f}"
                )
            elif mode is WeightingMode.APPLICABILITY:
                raw[m.method] = applicability[m.method]
                explanations[m.method] = (
                    f"Applicability weighting: {app_explain[m.method]}"
                )
            elif mode is WeightingMode.RESEARCH:
                raw[m.method] = float(_RESEARCH_CATEGORY_WEIGHTS.get(m.category, 1.0))
                explanations[m.method] = (
                    f"Research prior for category={m.category.value}"
                )
            elif mode is WeightingMode.MANUAL:
                w = float(inputs.manual_weights.get(m.method, 0.0))
                # Allow percent-scale inputs
                if w > 1.0 and sum(inputs.manual_weights.values()) > 1.5:
                    w = w / 100.0
                raw[m.method] = max(0.0, w)
                explanations[m.method] = f"Manual weight={raw[m.method]:.4f}"
            elif mode is WeightingMode.AUTOMATIC:
                raw[m.method] = max(0.0, m.confidence_score) * applicability[m.method]
                explanations[m.method] = (
                    f"Automatic = confidence×applicability "
                    f"({m.confidence_score:.3f}×{applicability[m.method]:.3f}); "
                    f"{app_explain[m.method]}"
                )
            else:
                raise ConsensusValidationError(f"unknown weighting mode: {mode!r}")

            # P1-04 — unavailable / null IV must never receive consensus weight.
            if value_map.get(m.method) is None:
                raw[m.method] = 0.0
                explanations[m.method] += "; excluded — unavailable intrinsic value"

            if (
                inputs.outlier_thresholds.exclude_outliers_from_consensus
                and m.method in outlier_methods
            ):
                raw[m.method] = 0.0
                explanations[m.method] += "; excluded as outlier"

        total = sum(raw.values())
        if total <= 0:
            # All zero — equal among methods that have a real IV (P1-04).
            candidates = [
                m.method
                for m in methods
                if value_map.get(m.method) is not None
                and (
                    m.method not in outlier_methods
                    or not inputs.outlier_thresholds.exclude_outliers_from_consensus
                )
            ]
            if not candidates:
                candidates = [
                    m.method
                    for m in methods
                    if value_map.get(m.method) is not None
                ]
            raw = {k: (1.0 if k in candidates else 0.0) for k in raw}
            total = sum(raw.values())

        weights = {k: (v / total if total else 0.0) for k, v in raw.items()}

        details = tuple(
            MethodWeightDetail(
                method=m.method,
                category=m.category,
                weight=weights[m.method],
                applicability_score=applicability[m.method],
                confidence_score=m.confidence_score,
                included_in_consensus=(
                    weights[m.method] > 0 and value_map.get(m.method) is not None
                ),
                is_outlier=m.method in outlier_methods,
                explanation=explanations[m.method],
            )
            for m in methods
        )
        return weights, details

    # --------------------------------------------------------------- outliers
    def _detect_outliers(
        self,
        values: Mapping[str, float | None],
        thr: OutlierThresholds,
    ) -> tuple[OutlierReport, ...]:
        usable = [(k, float(v)) for k, v in values.items() if v is not None]
        if len(usable) < 2:
            return ()

        nums = [v for _, v in usable]
        med = statistics.median(nums)
        mean = statistics.fmean(nums)
        stdev = statistics.pstdev(nums) if len(nums) > 1 else 0.0
        q1, q3 = self._quartiles(nums)
        iqr = q3 - q1

        reports: list[OutlierReport] = []
        for method, value in usable:
            reasons: list[str] = []
            z: float | None = None
            if stdev > 0:
                z = (value - mean) / stdev
                if abs(z) >= thr.z_score:
                    reasons.append(f"|z|={abs(z):.2f} ≥ {thr.z_score}")
            iqr_flag = False
            if iqr > 0:
                lo = q1 - thr.iqr_multiplier * iqr
                hi = q3 + thr.iqr_multiplier * iqr
                if value < lo or value > hi:
                    iqr_flag = True
                    reasons.append(f"outside IQR fence [{lo:.4g}, {hi:.4g}]")
            med_dev: float | None = None
            if med != 0:
                med_dev = abs(value - med) / abs(med)
                if med_dev >= thr.median_deviation_pct:
                    reasons.append(
                        f"median deviation {med_dev:.1%} ≥ {thr.median_deviation_pct:.0%}"
                    )
            if med != 0 and abs(value / med) >= thr.extreme_ratio:
                reasons.append(
                    f"extreme ratio |v/median|={abs(value / med):.2f} ≥ {thr.extreme_ratio}"
                )
            if value < 0:
                reasons.append("negative intrinsic value")
            if reasons:
                reports.append(
                    OutlierReport(
                        method=method,
                        value=value,
                        z_score=z,
                        iqr_flag=iqr_flag,
                        median_deviation=med_dev,
                        reasons=tuple(reasons),
                    )
                )
        return tuple(reports)

    def _quartiles(self, nums: Sequence[float]) -> tuple[float, float]:
        s = sorted(nums)
        n = len(s)
        if n == 1:
            return s[0], s[0]

        def _pct(p: float) -> float:
            idx = p * (n - 1)
            lo = int(math.floor(idx))
            hi = int(math.ceil(idx))
            if lo == hi:
                return s[lo]
            frac = idx - lo
            return s[lo] * (1 - frac) + s[hi] * frac

        return _pct(0.25), _pct(0.75)

    # ----------------------------------------------------------------- math
    def _weighted_mean(
        self, series: Sequence[tuple[str, float, float]]
    ) -> float:
        wsum = sum(w for _, _, w in series)
        if wsum <= 0:
            return statistics.fmean(v for _, v, _ in series)
        return sum(v * w for _, v, w in series) / wsum

    def _weighted_median(
        self, series: Sequence[tuple[str, float, float]]
    ) -> float:
        ordered = sorted(series, key=lambda x: x[1])
        wsum = sum(w for _, _, w in ordered)
        if wsum <= 0:
            return statistics.median(v for _, v, _ in ordered)
        cum = 0.0
        result = ordered[-1][1]
        for _, v, w in ordered:
            cum += w
            if cum >= 0.5 * wsum:
                result = v
                break
        return result

    def _trimmed_mean(self, values: Sequence[float], trim: float) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        n = len(s)
        k = int(math.floor(n * trim))
        if n - 2 * k <= 0:
            return statistics.fmean(s)
        return statistics.fmean(s[k : n - k])

    def _weighted_percentile_band(
        self,
        series: Sequence[tuple[str, float, float]],
        lo_p: float,
        hi_p: float,
    ) -> tuple[float, float]:
        ordered = sorted(series, key=lambda x: x[1])
        wsum = sum(w for _, _, w in ordered)
        if wsum <= 0:
            vals = [v for _, v, _ in ordered]
            return vals[0], vals[-1]

        def _at(p: float) -> float:
            target = p * wsum
            cum = 0.0
            result = ordered[-1][1]
            for _, v, w in ordered:
                cum += w
                if cum >= target:
                    result = v
                    break
            return result

        return _at(lo_p), _at(hi_p)

    def _consistency_score(
        self, series: Sequence[tuple[str, float, float]]
    ) -> float:
        vals = [v for _, v, _ in series]
        if len(vals) == 1:
            return 100.0
        mean = statistics.fmean(vals)
        if mean == 0:
            return 0.0 if any(v != 0 for v in vals) else 100.0
        cv = statistics.pstdev(vals) / abs(mean)
        return max(0.0, min(100.0, 100.0 * (1.0 - cv)))

    # ---------------------------------------------------------- disagreement
    def _disagreement(
        self,
        methods: Sequence[StandardizedMethodResult],
        values: Mapping[str, float | None],
        series: Sequence[tuple[str, float, float]],
    ) -> DisagreementAnalysis:
        vals = [v for _, v, _ in series]
        lo, hi = min(vals), max(vals)
        mid = statistics.median(vals)
        spread = ((hi - lo) / abs(mid)) if mid else 0.0
        pairwise = 0.0
        for i, (_, a, _) in enumerate(series):
            for _, b, _ in series[i + 1 :]:
                denom = max(abs(a), abs(b), 1e-12)
                pairwise = max(pairwise, abs(a - b) / denom)

        by_cat: dict[MethodCategory, list[float]] = {}
        for m in methods:
            v = values.get(m.method)
            if v is not None:
                by_cat.setdefault(m.category, []).append(v)

        notes: list[str] = []
        method_notes: dict[str, str] = {}
        if spread >= 0.40:
            notes.append(
                f"Large disagreement: range/median spread={spread:.1%}"
            )
        for m in methods:
            v = values.get(m.method)
            if v is None:
                method_notes[m.method] = "No intrinsic value provided"
                continue
            delta = ((v - mid) / abs(mid)) if mid else 0.0
            cat = m.category
            why = {
                MethodCategory.INTRINSIC: (
                    "DCF/intrinsic depends on forecast growth, WACC, terminal value"
                ),
                MethodCategory.RELATIVE: (
                    "Relative depends on injected peer/industry multiples"
                ),
                MethodCategory.ASSET: (
                    "Asset-based depends on book/NAV/liquidation haircuts"
                ),
                MethodCategory.DIVIDEND: (
                    "DDM depends on payout sustainability and required return"
                ),
                MethodCategory.RESIDUAL: (
                    "Residual income depends on ROE fade and clean-surplus book"
                ),
                MethodCategory.INCOME: (
                    "EPV/income depends on normalized earnings and cost of capital"
                ),
                MethodCategory.MARKET: (
                    "Reverse/market-implied embeds current price expectations"
                ),
            }[cat]
            method_notes[m.method] = (
                f"{why}. Value vs median: {delta:+.1%}."
            )
            if abs(delta) >= 0.25:
                notes.append(
                    f"{m.method} ({cat.value}) differs {delta:+.1%} from median"
                )

        if MethodCategory.INTRINSIC in by_cat and MethodCategory.RELATIVE in by_cat:
            notes.append(
                "Intrinsic vs Relative gap often reflects growth vs multiple assumptions"
            )
        if MethodCategory.ASSET in by_cat and MethodCategory.INTRINSIC in by_cat:
            notes.append(
                "Asset vs Intrinsic gap often reflects hidden franchise value or haircuts"
            )
        if MethodCategory.DIVIDEND in by_cat:
            notes.append(
                "DDM can diverge when payout policy differs from free-cash-flow capacity"
            )

        return DisagreementAnalysis(
            overall_spread_pct=spread,
            pairwise_max_pct=pairwise,
            notes=tuple(dict.fromkeys(notes)),
            method_notes=method_notes,
        )

    # ---------------------------------------------------------- sensitivity
    def _method_sensitivity_score(
        self, method: StandardizedMethodResult
    ) -> float | None:
        sens = method.sensitivity_results
        if sens is None or not sens.grids:
            return None
        spreads: list[float] = []
        for cells in sens.grids.values():
            vals = [c.output_value for c in cells if c.output_value is not None]
            if len(vals) >= 2:
                mid = statistics.median(vals)
                if mid != 0:
                    spreads.append((max(vals) - min(vals)) / abs(mid))
                else:
                    spreads.append(abs(max(vals) - min(vals)))
        if not spreads:
            return None
        return statistics.fmean(spreads)

    def _sensitivity_summary(
        self, methods: Sequence[StandardizedMethodResult]
    ) -> SensitivitySummary:
        scores: dict[str, float] = {}
        for m in methods:
            s = self._method_sensitivity_score(m)
            if s is not None:
                scores[m.method] = s
        if not scores:
            return SensitivitySummary(
                highest_sensitivity=None,
                lowest_sensitivity=None,
                average_sensitivity=None,
                most_stable_method=None,
                least_stable_method=None,
                method_scores={},
            )
        most_stable = min(scores, key=scores.get)  # type: ignore[arg-type]
        least_stable = max(scores, key=scores.get)  # type: ignore[arg-type]
        return SensitivitySummary(
            highest_sensitivity=max(scores.values()),
            lowest_sensitivity=min(scores.values()),
            average_sensitivity=statistics.fmean(scores.values()),
            most_stable_method=most_stable,
            least_stable_method=least_stable,
            method_scores=scores,
        )

    # ------------------------------------------------------------ scenarios
    def _scenario_consensus(
        self,
        methods: Sequence[StandardizedMethodResult],
        weights: Mapping[str, float],
    ) -> tuple[ScenarioOutcome, ...]:
        """Aggregate method scenario IVPS by kind name using method weights."""
        by_kind: dict[str, list[tuple[float, float]]] = {}
        labels: dict[str, str] = {}
        for m in methods:
            w = weights.get(m.method, 0.0)
            if w <= 0:
                continue
            for sc in m.scenario_results:
                val = sc.intrinsic_value_per_share
                if val is None:
                    val = sc.intrinsic_value
                if val is None:
                    continue
                by_kind.setdefault(sc.kind.name, []).append((float(val), w))
                labels[sc.kind.name] = sc.kind.label

        # Ensure bear/base/bull appear when any method has them; also run
        # Core ScenarioEngine for custom research stress on consensus weights.
        outcomes: list[ScenarioOutcome] = []
        for name in ("bear", "base", "bull"):
            if name in by_kind:
                series = by_kind[name]
                wsum = sum(w for _, w in series)
                iv = (
                    sum(v * w for v, w in series) / wsum
                    if wsum
                    else statistics.fmean(v for v, _ in series)
                )
                kind = {
                    "bear": ScenarioKind.bear(),
                    "base": ScenarioKind.base(),
                    "bull": ScenarioKind.bull(),
                }[name]
                outcomes.append(
                    ScenarioOutcome(
                        kind=kind,
                        intrinsic_value=iv,
                        equity_value=iv,
                        intrinsic_value_per_share=iv,
                        notes=f"Weighted consensus of {len(series)} method scenario(s)",
                    )
                )

        for name, series in by_kind.items():
            if name in {"bear", "base", "bull"}:
                continue
            wsum = sum(w for _, w in series)
            iv = (
                sum(v * w for v, w in series) / wsum
                if wsum
                else statistics.fmean(v for v, _ in series)
            )
            outcomes.append(
                ScenarioOutcome(
                    kind=ScenarioKind.custom(name, labels.get(name, name)),
                    intrinsic_value=iv,
                    equity_value=iv,
                    intrinsic_value_per_share=iv,
                    notes=f"Weighted consensus of custom scenario '{name}'",
                )
            )

        # Always attach a Core-driven custom stress if we have any base values
        if by_kind.get("base") or outcomes:
            engine = ScenarioEngine()

            def evaluator(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
                shock = float(ctx.get("shock", 0.0))
                base_iv = (
                    outcomes[0].intrinsic_value_per_share
                    if outcomes and outcomes[0].intrinsic_value_per_share is not None
                    else 0.0
                )
                # Prefer explicit base if present
                for o in outcomes:
                    if o.kind.name == "base" and o.intrinsic_value_per_share is not None:
                        base_iv = o.intrinsic_value_per_share
                        break
                shocked = float(base_iv) * (1.0 + shock)
                return {
                    "intrinsic_value": shocked,
                    "equity_value": shocked,
                    "intrinsic_value_per_share": shocked,
                    "notes": f"consensus shock={shock}",
                }

            custom = engine.scenarios(
                {},
                specs=(
                    ScenarioSpec(
                        ScenarioKind.custom("consensus_stress", "Consensus Stress"),
                        {"shock": -0.15},
                    ),
                ),
                evaluator=evaluator,
            )
            outcomes.extend(custom)

        return tuple(outcomes)

    # ------------------------------------------------------------ confidence
    def _confidence(
        self,
        *,
        methods: Sequence[StandardizedMethodResult],
        weights_map: Mapping[str, float],
        consistency: float,
        outliers: Sequence[OutlierReport],
        validation_warnings: Sequence[str],
        sensitivity: SensitivitySummary,
    ):
        if methods:
            method_conf = sum(
                m.confidence_score * weights_map.get(m.method, 0.0)
                for m in methods
            )
            # Normalize rough 0-8 Core scores to 0-1
            max_c = max(m.confidence_score for m in methods) or 1.0
            method_conf_n = method_conf / max(max_c, 1e-9)
            method_conf_n = max(0.0, min(1.0, method_conf_n))
        else:
            method_conf_n = 0.0

        data_q = min(1.0, len(methods) / 5.0)
        if any(not m.validation_ok for m in methods):
            data_q *= 0.7

        scenario_stability = 0.5
        with_sc = sum(1 for m in methods if m.scenario_results)
        if with_sc:
            scenario_stability = min(1.0, 0.4 + 0.15 * with_sc)

        sens_stability = 0.5
        if sensitivity.average_sensitivity is not None:
            # Lower average sensitivity spread → higher stability
            sens_stability = max(
                0.1, min(1.0, 1.0 - min(1.0, sensitivity.average_sensitivity))
            )

        validation_q = 1.0 if not validation_warnings else 0.7
        hist = consistency / 100.0

        if outliers:
            data_q *= 0.85
            hist *= 0.9

        return ConfidenceEngine().score(
            {
                "accounting_quality": method_conf_n,
                "forecast_reliability": hist,
                "data_completeness": data_q,
                "business_stability": scenario_stability,
                "capital_allocation": sens_stability,
                "model_assumptions": validation_q,
            }
        )

    def _quality_flags(
        self,
        *,
        consistency: float,
        outliers: Sequence[OutlierReport],
        methods: Sequence[StandardizedMethodResult],
        confidence_level: str,
        disagreement: DisagreementAnalysis,
    ) -> tuple[tuple[ConsensusQualityFlag, ...], tuple[QualityFlag, ...]]:
        flags: list[ConsensusQualityFlag] = []
        core: list[QualityFlag] = []

        if consistency >= 80:
            flags.append(ConsensusQualityFlag.HIGH_AGREEMENT)
            flags.append(ConsensusQualityFlag.STRONG_CONSENSUS)
        elif consistency >= 55:
            flags.append(ConsensusQualityFlag.MEDIUM_AGREEMENT)
        else:
            flags.append(ConsensusQualityFlag.LOW_AGREEMENT)

        if outliers:
            flags.append(ConsensusQualityFlag.OUTLIER_PRESENT)

        if len(methods) < 3:
            flags.append(ConsensusQualityFlag.WEAK_DATASET)
            core.append(QualityFlag.LOW_DATA_QUALITY)

        if confidence_level == "low" or consistency < 40:
            flags.append(ConsensusQualityFlag.SPECULATIVE_CONSENSUS)
            core.append(QualityFlag.FORECAST_RISK)

        if disagreement.overall_spread_pct >= 0.50 or disagreement.pairwise_max_pct >= 0.60:
            flags.append(ConsensusQualityFlag.CONFLICTING_METHODS)

        return tuple(dict.fromkeys(flags)), tuple(dict.fromkeys(core))
