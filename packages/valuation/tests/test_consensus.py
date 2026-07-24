"""Cross-Method Consensus tests — target 100% module coverage."""

from __future__ import annotations

import math
import time

import pytest

from valuation import ValuationEngine, ValuationError
from valuation.consensus import (
    CONSENSUS_VERSION,
    CompanyProfile,
    ConsensusEngine,
    ConsensusInputs,
    ConsensusQualityFlag,
    ConsensusValidationError,
    MethodCategory,
    OutlierThresholds,
    WeightingMode,
    default_category_for_method,
    explain_many,
    explain_step,
    normalize_method_input,
    to_v2_aggregate_payload,
    validate_consensus_inputs,
)
from valuation.consensus.consensus_models import (
    MethodWeightDetail,
    SensitivitySummary,
    to_valuation_result,
)
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioKind,
    ScenarioOutcome,
    SensitivityCell,
    SensitivityMatrix,
    ValidationSummary,
    ValuationMetadata,
    ValuationResult,
)


def _sens(spread: float = 0.10, name: str = "m") -> SensitivityMatrix:
    base = 100.0
    return SensitivityMatrix(
        grids={
            "x": (
                SensitivityCell("x", 0.9, "ivps", base * (1 - spread), 0, 0),
                SensitivityCell("x", 1.0, "ivps", base, 0, 1),
                SensitivityCell("x", 1.1, "ivps", base * (1 + spread), 0, 2),
            )
        },
        notes=name,
    )


def _vr(
    method: str,
    *,
    iv: float | None = 1000.0,
    ivps: float | None = 10.0,
    confidence_score: float = 5.0,
    confidence_level: str = "medium",
    scenarios: tuple[ScenarioOutcome, ...] | None = None,
    sensitivity: SensitivityMatrix | None = None,
    validation_ok: bool = True,
    quality_flags: tuple[QualityFlag, ...] = (),
) -> ValuationResult:
    if scenarios is None:
        scenarios = (
            ScenarioOutcome(
                ScenarioKind.bear(), iv * 0.9 if iv else 9.0, None, (ivps or 9) * 0.9
            ),
            ScenarioOutcome(
                ScenarioKind.base(), iv, None, ivps
            ),
            ScenarioOutcome(
                ScenarioKind.bull(), iv * 1.1 if iv else 11.0, None, (ivps or 11) * 1.1
            ),
        )
    return ValuationResult(
        model_name=method,
        version="test",
        methodology=f"{method} test",
        intrinsic_value=iv,
        enterprise_value=None,
        equity_value=iv,
        intrinsic_value_per_share=ivps,
        margin_of_safety=0.1,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        quality_flags=quality_flags,
        sensitivity_results=sensitivity if sensitivity is not None else _sens(),
        scenario_results=scenarios,
        validation_summary=ValidationSummary(
            ok=validation_ok, checks=("ok",), warnings=()
        ),
        explainability=(),
        research_disclaimer="research",
        metadata=ValuationMetadata(
            model_name=method, engine_version="t", methodology="t"
        ),
        currency="USD",
        confidence_explanation="test",
    )


def _bundle(**kwargs) -> ConsensusInputs:
    methods = (
        _vr("dcf", ivps=12.0, iv=1200.0, confidence_score=6.0),
        _vr("relative", ivps=10.0, iv=1000.0, confidence_score=5.0),
        _vr("asset_based", ivps=9.0, iv=900.0, confidence_score=4.5),
        _vr("ddm", ivps=11.0, iv=1100.0, confidence_score=5.5),
    )
    data = dict(
        methods=methods,
        weighting_mode=WeightingMode.EQUAL,
        currency="USD",
    )
    data.update(kwargs)
    return ConsensusInputs(**data)


class TestCategories:
    def test_known_and_future(self) -> None:
        assert default_category_for_method("dcf") is MethodCategory.INTRINSIC
        assert default_category_for_method("reverse_dcf") is MethodCategory.MARKET
        assert default_category_for_method("residual_income") is MethodCategory.RESIDUAL
        assert default_category_for_method("epv") is MethodCategory.INCOME
        assert default_category_for_method("graham") is MethodCategory.INTRINSIC
        assert default_category_for_method("ddm") is MethodCategory.DIVIDEND
        assert default_category_for_method("asset_based") is MethodCategory.ASSET
        assert default_category_for_method("relative") is MethodCategory.RELATIVE
        assert default_category_for_method("Custom Multiple") is MethodCategory.RELATIVE
        assert default_category_for_method("NAV Liquidation") is MethodCategory.ASSET
        assert default_category_for_method("dividend_model") is MethodCategory.DIVIDEND
        assert default_category_for_method("riv_v2") is MethodCategory.RESIDUAL
        assert default_category_for_method("implied_growth") is MethodCategory.MARKET
        assert default_category_for_method("earnings_power") is MethodCategory.INCOME
        assert default_category_for_method("brand_new_method") is MethodCategory.INTRINSIC


class TestWeightingModes:
    @pytest.mark.parametrize(
        "mode",
        [
            WeightingMode.EQUAL,
            WeightingMode.CONFIDENCE,
            WeightingMode.APPLICABILITY,
            WeightingMode.RESEARCH,
            WeightingMode.AUTOMATIC,
        ],
    )
    def test_modes(self, mode: WeightingMode) -> None:
        r = ConsensusEngine().analyze(_bundle(weighting_mode=mode))
        wsum = sum(d.weight for d in r.method_weights)
        assert wsum == pytest.approx(1.0, abs=1e-9)
        assert r.consensus_intrinsic_value.value is not None
        assert r.version == CONSENSUS_VERSION

    def test_manual(self) -> None:
        r = ConsensusEngine().analyze(
            _bundle(
                weighting_mode=WeightingMode.MANUAL,
                manual_weights={
                    "dcf": 0.4,
                    "relative": 0.2,
                    "asset_based": 0.2,
                    "ddm": 0.2,
                },
            )
        )
        by = {d.method: d.weight for d in r.method_weights}
        assert by["dcf"] == pytest.approx(0.4)
        assert sum(by.values()) == pytest.approx(1.0)

    def test_manual_percent_scale(self) -> None:
        r = ConsensusEngine().analyze(
            _bundle(
                weighting_mode=WeightingMode.MANUAL,
                manual_weights={
                    "dcf": 40.0,
                    "relative": 20.0,
                    "asset_based": 20.0,
                    "ddm": 20.0,
                },
            )
        )
        assert sum(d.weight for d in r.method_weights) == pytest.approx(1.0)


class TestConsensusMath:
    def test_median_and_means(self) -> None:
        r = ConsensusEngine().analyze(_bundle(weighting_mode=WeightingMode.EQUAL))
        # IVPS: 12, 10, 9, 11 → median 10.5, mean 10.5
        assert r.median.value == pytest.approx(10.5)
        assert r.weighted_mean.value == pytest.approx(10.5)
        assert r.trimmed_mean.value is not None
        assert r.weighted_median.value is not None
        assert r.lower_range <= r.upper_range
        assert r.confidence_interval[0] <= r.confidence_interval[1]

    def test_trimmed_mean(self) -> None:
        methods = [
            _vr("dcf", ivps=10.0),
            _vr("relative", ivps=20.0),
            _vr("asset_based", ivps=30.0),
            _vr("ddm", ivps=40.0),
            _vr("epv", ivps=100.0),
        ]
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=methods,
                weighting_mode=WeightingMode.EQUAL,
                trim_fraction=0.2,
                outlier_thresholds=OutlierThresholds(
                    z_score=100,  # disable outlier exclusion for this math check
                    iqr_multiplier=100,
                    median_deviation_pct=10,
                    extreme_ratio=100,
                    exclude_outliers_from_consensus=False,
                ),
            )
        )
        # trim 20% of 5 → k=1 → drop 10 and 100 → mean(20,30,40)=30
        assert r.trimmed_mean.value == pytest.approx(30.0)


class TestOutliers:
    def test_detects_extreme(self) -> None:
        methods = [
            _vr("dcf", ivps=10.0),
            _vr("relative", ivps=11.0),
            _vr("asset_based", ivps=10.5),
            _vr("ddm", ivps=100.0),
        ]
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=methods,
                weighting_mode=WeightingMode.EQUAL,
                outlier_thresholds=OutlierThresholds(
                    z_score=1.5,
                    median_deviation_pct=0.30,
                    extreme_ratio=3.0,
                    exclude_outliers_from_consensus=True,
                ),
            )
        )
        assert r.outliers
        assert any(o.method == "ddm" for o in r.outliers)
        assert ConsensusQualityFlag.OUTLIER_PRESENT in r.quality_flags
        ddm_w = next(d for d in r.method_weights if d.method == "ddm")
        assert ddm_w.weight == pytest.approx(0.0)
        assert ddm_w.is_outlier

    def test_negative_value_outlier(self) -> None:
        methods = [
            _vr("dcf", ivps=10.0),
            _vr("relative", ivps=-5.0),
        ]
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=methods,
                weighting_mode=WeightingMode.EQUAL,
                outlier_thresholds=OutlierThresholds(exclude_outliers_from_consensus=False),
            )
        )
        assert any("negative" in " ".join(o.reasons) for o in r.outliers)


class TestApplicability:
    def test_dividend_and_asset_profiles(self) -> None:
        r = ConsensusEngine().analyze(
            _bundle(
                weighting_mode=WeightingMode.APPLICABILITY,
                company_profile=CompanyProfile(
                    pays_dividend=True,
                    asset_heavy=True,
                    growth_company=True,
                    loss_making=False,
                    financial_institution=False,
                    holding_company=True,
                ),
            )
        )
        by = {d.method: d.applicability_score for d in r.method_weights}
        assert by["ddm"] > by["relative"]
        assert by["asset_based"] > by["relative"]
        assert by["dcf"] > 0.5

    def test_loss_making_financial(self) -> None:
        r = ConsensusEngine().analyze(
            _bundle(
                weighting_mode=WeightingMode.APPLICABILITY,
                company_profile=CompanyProfile(
                    loss_making=True,
                    financial_institution=True,
                ),
            )
        )
        by = {d.method: d.applicability_score for d in r.method_weights}
        assert by["relative"] > by["dcf"]


class TestValidation:
    def test_empty(self) -> None:
        with pytest.raises(ConsensusValidationError, match="empty"):
            validate_consensus_inputs(ConsensusInputs(methods=()))

    def test_duplicate(self) -> None:
        with pytest.raises(ConsensusValidationError, match="duplicate"):
            validate_consensus_inputs(
                ConsensusInputs(methods=(_vr("dcf"), _vr("dcf", ivps=11.0)))
            )

    def test_nan(self) -> None:
        with pytest.raises(ConsensusValidationError, match="NaN"):
            validate_consensus_inputs(
                ConsensusInputs(methods=(_vr("dcf", ivps=float("nan")),))
            )

    def test_infinite(self) -> None:
        with pytest.raises(ConsensusValidationError, match="infinite"):
            validate_consensus_inputs(
                ConsensusInputs(methods=(_vr("dcf", ivps=float("inf")),))
            )

    def test_negative_weight(self) -> None:
        with pytest.raises(ConsensusValidationError, match="negative weight"):
            validate_consensus_inputs(
                ConsensusInputs(
                    methods=(_vr("dcf"), _vr("relative")),
                    weighting_mode=WeightingMode.MANUAL,
                    manual_weights={"dcf": -1.0, "relative": 2.0},
                )
            )

    def test_manual_missing(self) -> None:
        with pytest.raises(ConsensusValidationError, match="manual_weights"):
            validate_consensus_inputs(
                ConsensusInputs(
                    methods=(_vr("dcf"),),
                    weighting_mode=WeightingMode.MANUAL,
                )
            )

    def test_manual_zero_sum(self) -> None:
        with pytest.raises(ConsensusValidationError, match="positive total"):
            validate_consensus_inputs(
                ConsensusInputs(
                    methods=(_vr("dcf"),),
                    weighting_mode=WeightingMode.MANUAL,
                    manual_weights={"dcf": 0.0},
                )
            )

    def test_bad_trim(self) -> None:
        with pytest.raises(ConsensusValidationError, match="trim_fraction"):
            validate_consensus_inputs(
                ConsensusInputs(methods=(_vr("dcf"),), trim_fraction=0.6)
            )

    def test_negative_threshold(self) -> None:
        with pytest.raises(ConsensusValidationError, match="non-negative"):
            validate_consensus_inputs(
                ConsensusInputs(
                    methods=(_vr("dcf"),),
                    outlier_thresholds=OutlierThresholds(z_score=-1),
                )
            )

    def test_bad_shares(self) -> None:
        with pytest.raises(ConsensusValidationError, match="shares"):
            validate_consensus_inputs(
                ConsensusInputs(methods=(_vr("dcf"),), shares_outstanding=-1)
            )

    def test_invalid_confidence_payload(self) -> None:
        with pytest.raises(ConsensusValidationError, match="invalid confidence"):
            normalize_method_input({"method": "dcf", "confidence_score": float("nan")})

    def test_missing_method_payload(self) -> None:
        with pytest.raises(ConsensusValidationError, match="missing method"):
            normalize_method_input({"intrinsic_value_per_share": 10})

    def test_unsupported_type(self) -> None:
        with pytest.raises(ConsensusValidationError, match="unsupported"):
            normalize_method_input(123)  # type: ignore[arg-type]

    def test_is_valuation_error(self) -> None:
        assert issubclass(ConsensusValidationError, ValuationError)

    def test_weight_sum_warning(self) -> None:
        summary = validate_consensus_inputs(
            ConsensusInputs(
                methods=(_vr("dcf"), _vr("relative")),
                weighting_mode=WeightingMode.MANUAL,
                manual_weights={"dcf": 0.3, "relative": 0.3},
            )
        )
        assert any("normalized" in w.lower() or "sum" in w.lower() for w in summary.warnings)


class TestNormalize:
    def test_payload(self) -> None:
        std = normalize_method_input(
            {
                "method": "graham",
                "intrinsic_value": 500,
                "intrinsic_value_per_share": 5,
                "confidence": "high",
                "quality_flags": ["x"],
                "currency": "USD",
                "version": "0.7.0",
            }
        )
        assert std.method == "graham"
        assert std.category is MethodCategory.INTRINSIC
        assert std.confidence_score == pytest.approx(6.0)
        assert std.source == "v2_payload"

    def test_payload_equity_fallback(self) -> None:
        std = normalize_method_input(
            {"method": "epv", "equity_value": 800, "confidence_score": 4.0}
        )
        assert std.intrinsic_value == pytest.approx(800.0)

    def test_result_bad_confidence(self) -> None:
        bad = _vr("dcf")
        object.__setattr__(bad, "confidence_score", float("inf"))
        with pytest.raises(ConsensusValidationError, match="invalid confidence"):
            normalize_method_input(bad)

    def test_category_override(self) -> None:
        std = normalize_method_input(
            _vr("custom_x"),
            category_overrides={"custom_x": MethodCategory.MARKET},
        )
        assert std.category is MethodCategory.MARKET


class TestConfidenceFlagsScenarios:
    def test_confidence_and_flags(self) -> None:
        r = ConsensusEngine().analyze(_bundle())
        assert r.consensus_confidence in {"high", "medium", "low"}
        assert r.consistency_score.value is not None
        assert 0 <= r.consistency_score.value <= 100
        assert r.quality_flags
        assert r.disagreement.method_notes

    def test_weak_dataset(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(methods=(_vr("dcf"), _vr("relative", ivps=10.5)))
        )
        assert ConsensusQualityFlag.WEAK_DATASET in r.quality_flags

    def test_high_agreement(self) -> None:
        methods = [
            _vr("dcf", ivps=10.0),
            _vr("relative", ivps=10.1),
            _vr("asset_based", ivps=9.9),
            _vr("ddm", ivps=10.05),
            _vr("epv", ivps=10.0),
        ]
        r = ConsensusEngine().analyze(
            ConsensusInputs(methods=methods, weighting_mode=WeightingMode.EQUAL)
        )
        assert ConsensusQualityFlag.HIGH_AGREEMENT in r.quality_flags
        assert ConsensusQualityFlag.STRONG_CONSENSUS in r.quality_flags

    def test_scenarios_and_sensitivity(self) -> None:
        r = ConsensusEngine().analyze(
            _bundle(
                methods=(
                    _vr("dcf", ivps=12.0, sensitivity=_sens(0.05)),
                    _vr("relative", ivps=10.0, sensitivity=_sens(0.40)),
                    _vr("asset_based", ivps=9.0, sensitivity=_sens(0.10)),
                )
            )
        )
        kinds = {s.kind.name for s in r.scenario_results}
        assert "bear" in kinds and "base" in kinds and "bull" in kinds
        assert r.sensitivity_summary.most_stable_method == "dcf"
        assert r.sensitivity_summary.least_stable_method == "relative"
        assert r.sensitivity_summary.average_sensitivity is not None


class TestExplainabilityIntegration:
    def test_helpers_and_payloads(self) -> None:
        assert explain_step(name="x", value=1.0, formula="x=1").name == "x"
        assert len(explain_many([{"name": "y", "value": 2, "formula": "y=2"}])) == 1
        result = ValuationEngine().analyze_consensus(_bundle())
        assert len(result.explainability) >= 5
        assert "research" in result.disclaimer.lower()
        vr = to_valuation_result(result)
        assert vr.model_name == "consensus"
        from valuation import (
            to_consensus_valuation_result,
            to_consensus_v2_aggregate_payload,
        )

        assert to_consensus_valuation_result(result).model_name == "consensus"
        payload = to_v2_aggregate_payload(result)
        assert payload["method"] == "consensus"
        assert payload["overall_valuation_enabled"] is False
        assert to_consensus_v2_aggregate_payload(result)["method"] == "consensus"
        assert result.to_dict()["version"] == CONSENSUS_VERSION


class TestEdgeCases:
    def test_single_method(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(methods=(_vr("dcf", ivps=15.0),))
        )
        assert r.consensus_per_share.value == pytest.approx(15.0)
        assert r.consistency_score.value == pytest.approx(100.0)

    def test_iv_only_no_ivps(self) -> None:
        methods = [
            _vr("dcf", iv=1000.0, ivps=None),
            _vr("relative", iv=900.0, ivps=None),
        ]
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=methods,
                shares_outstanding=100.0,
                weighting_mode=WeightingMode.EQUAL,
            )
        )
        assert r.consensus_intrinsic_value.value == pytest.approx(950.0)
        assert r.consensus_per_share.value == pytest.approx(9.5)

    def test_no_usable_values(self) -> None:
        with pytest.raises(ConsensusValidationError, match="no usable"):
            ConsensusEngine().analyze(
                ConsensusInputs(
                    methods=(
                        _vr("dcf", iv=None, ivps=None),
                        _vr("relative", iv=None, ivps=None),
                    )
                )
            )

    def test_all_outliers_rescue(self) -> None:
        methods = [
            _vr("dcf", ivps=10.0),
            _vr("relative", ivps=1000.0),
        ]
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=methods,
                weighting_mode=WeightingMode.EQUAL,
                outlier_thresholds=OutlierThresholds(
                    z_score=0.01,
                    median_deviation_pct=0.01,
                    extreme_ratio=1.01,
                    exclude_outliers_from_consensus=True,
                ),
            )
        )
        # Rescue path should still produce a consensus
        assert r.consensus_intrinsic_value.value is not None

    def test_unknown_weighting_mode(self) -> None:
        inputs = _bundle()
        object.__setattr__(inputs, "weighting_mode", "bogus")  # type: ignore[arg-type]
        with pytest.raises(ConsensusValidationError, match="unknown weighting"):
            ConsensusEngine()._compute_weights(
                methods=tuple(
                    normalize_method_input(m) for m in inputs.methods
                ),
                applicability={"dcf": 1, "relative": 1, "asset_based": 1, "ddm": 1},
                app_explain={
                    "dcf": "",
                    "relative": "",
                    "asset_based": "",
                    "ddm": "",
                },
                outlier_methods=set(),
                inputs=inputs,
            )

    def test_validation_not_ok_lowers_applicability(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=10.0, validation_ok=False),
                    _vr("relative", ivps=10.0, validation_ok=True),
                ),
                weighting_mode=WeightingMode.APPLICABILITY,
            )
        )
        by = {d.method: d.applicability_score for d in r.method_weights}
        assert by["dcf"] < by["relative"]

    def test_custom_scenario_in_methods(self) -> None:
        sc = (
            ScenarioOutcome(ScenarioKind.base(), 100, 100, 10),
            ScenarioOutcome(
                ScenarioKind.custom("stress", "Stress"), 80, 80, 8
            ),
        )
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=10.0, scenarios=sc),
                    _vr("relative", ivps=10.0, scenarios=sc),
                )
            )
        )
        names = {s.kind.name for s in r.scenario_results}
        assert "stress" in names or "consensus_stress" in names

    def test_empty_sensitivity(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=10.0, sensitivity=SensitivityMatrix(grids={})),
                    _vr("relative", ivps=10.5, sensitivity=SensitivityMatrix(grids={})),
                )
            )
        )
        assert r.sensitivity_summary.most_stable_method is None

    def test_zero_mean_consistency(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=0.0, iv=0.0),
                    _vr("relative", ivps=0.0, iv=0.0),
                ),
                outlier_thresholds=OutlierThresholds(
                    exclude_outliers_from_consensus=False
                ),
            )
        )
        assert r.consistency_score.value == pytest.approx(100.0)

    def test_finite_validation_edges(self) -> None:
        with pytest.raises(ConsensusValidationError, match="NaN"):
            validate_consensus_inputs(
                ConsensusInputs(methods=(_vr("dcf"),), trim_fraction=float("nan"))
            )
        with pytest.raises(ConsensusValidationError, match="infinite"):
            validate_consensus_inputs(
                ConsensusInputs(
                    methods=(_vr("dcf"),),
                    outlier_thresholds=OutlierThresholds(iqr_multiplier=float("inf")),
                )
            )
        with pytest.raises(ConsensusValidationError, match="NaN"):
            validate_consensus_inputs(
                ConsensusInputs(
                    methods=(_vr("dcf"),),
                    current_market_price=float("nan"),
                )
            )

    def test_normalize_error_collected(self) -> None:
        with pytest.raises(ConsensusValidationError, match="missing method"):
            validate_consensus_inputs(
                ConsensusInputs(methods=({"intrinsic_value_per_share": 10},))
            )

    def test_helper_math_edges(self) -> None:
        eng = ConsensusEngine()
        assert eng._quartiles([7.0]) == (7.0, 7.0)
        assert eng._weighted_mean([("a", 10.0, 0.0), ("b", 20.0, 0.0)]) == pytest.approx(
            15.0
        )
        assert eng._weighted_median(
            [("a", 10.0, 0.0), ("b", 20.0, 0.0)]
        ) == pytest.approx(15.0)
        assert eng._trimmed_mean([], 0.1) == 0.0
        assert eng._trimmed_mean([1.0, 2.0], 0.5) == pytest.approx(1.5)
        lo, hi = eng._weighted_percentile_band(
            [("a", 10.0, 0.0), ("b", 30.0, 0.0)], 0.1, 0.9
        )
        assert lo == pytest.approx(10.0)
        assert hi == pytest.approx(30.0)
        # Force _at fallthrough by using weights that never reach target early... 
        # last element path when cum never hits — use empty weight after sort edge
        band = eng._weighted_percentile_band([("a", 5.0, 1.0)], 0.0, 1.0)
        assert band[0] == pytest.approx(5.0)

    def test_pick_values_ivps_fallback(self) -> None:
        eng = ConsensusEngine()
        # Majority lack IVPS → use IV; one has only IVPS
        m1 = normalize_method_input(_vr("dcf", iv=1000.0, ivps=None))
        m2 = normalize_method_input(_vr("relative", iv=900.0, ivps=None))
        m3 = normalize_method_input(_vr("epv", iv=None, ivps=8.0))
        vals = eng._pick_values((m1, m2, m3))
        assert vals["dcf"] == pytest.approx(1000.0)
        assert vals["epv"] == pytest.approx(8.0)

    def test_to_per_share_mean_fallback(self) -> None:
        eng = ConsensusEngine()
        # Minority IVPS + no shares → mean of available IVPS
        methods = (
            normalize_method_input(_vr("dcf", iv=1000.0, ivps=None)),
            normalize_method_input(_vr("relative", iv=900.0, ivps=None)),
            normalize_method_input(_vr("epv", iv=800.0, ivps=8.0)),
        )
        inputs = ConsensusInputs(methods=(_vr("dcf"),), shares_outstanding=None)
        assert eng._to_per_share(950.0, methods, inputs) == pytest.approx(8.0)
        # No IVPS at all → return consensus value
        methods2 = (
            normalize_method_input(_vr("dcf", iv=1000.0, ivps=None)),
            normalize_method_input(_vr("relative", iv=900.0, ivps=None)),
        )
        assert eng._to_per_share(950.0, methods2, inputs) == pytest.approx(950.0)

    def test_sensitivity_zero_mid_and_sparse(self) -> None:
        eng = ConsensusEngine()
        sens = SensitivityMatrix(
            grids={
                "x": (
                    SensitivityCell("x", 1.0, "ivps", 0.0, 0, 0),
                    SensitivityCell("x", 2.0, "ivps", 0.0, 0, 1),
                )
            }
        )
        m = normalize_method_input(_vr("dcf", sensitivity=sens))
        assert eng._method_sensitivity_score(m) == pytest.approx(0.0)
        sparse = SensitivityMatrix(
            grids={"x": (SensitivityCell("x", 1.0, "ivps", None, 0, 0),)}
        )
        m2 = normalize_method_input(_vr("relative", sensitivity=sparse))
        assert eng._method_sensitivity_score(m2) is None

    def test_disagreement_none_value_note(self) -> None:
        eng = ConsensusEngine()
        methods = (
            normalize_method_input(_vr("dcf", ivps=10.0)),
            normalize_method_input(_vr("relative", iv=None, ivps=None)),
        )
        values = {"dcf": 10.0, "relative": None}
        series = [("dcf", 10.0, 1.0)]
        d = eng._disagreement(methods, values, series)
        assert "No intrinsic value" in d.method_notes["relative"]

    def test_scenario_iv_fallback_and_zero_weight(self) -> None:
        eng = ConsensusEngine()
        sc = (
            ScenarioOutcome(ScenarioKind.base(), 100.0, 100.0, None),
            ScenarioOutcome(ScenarioKind.bear(), None, None, None),
        )
        m = normalize_method_input(_vr("dcf", ivps=10.0, scenarios=sc))
        outs = eng._scenario_consensus((m,), {"dcf": 1.0})
        assert any(o.kind.name == "base" for o in outs)
        outs2 = eng._scenario_consensus((m,), {"dcf": 0.0})
        # zero weight skipped — may still get consensus_stress only if outcomes empty
        assert isinstance(outs2, tuple)

    def test_confidence_empty_methods(self) -> None:
        eng = ConsensusEngine()
        detail = eng._confidence(
            methods=(),
            weights_map={},
            consistency=50.0,
            outliers=(),
            validation_warnings=("w",),
            sensitivity=SensitivitySummary(
                highest_sensitivity=None,
                lowest_sensitivity=None,
                average_sensitivity=None,
                most_stable_method=None,
                least_stable_method=None,
                method_scores={},
            ),
        )
        assert detail.level in {"high", "medium", "low"}

    def test_medium_agreement_flag(self) -> None:
        # pstdev/mean ≈ 0.27 → consistency ≈ 73 → medium band
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=10.0),
                    _vr("relative", ivps=15.0),
                    _vr("asset_based", ivps=20.0),
                ),
                outlier_thresholds=OutlierThresholds(
                    z_score=100,
                    iqr_multiplier=100,
                    median_deviation_pct=10,
                    extreme_ratio=100,
                    exclude_outliers_from_consensus=False,
                ),
            )
        )
        assert ConsensusQualityFlag.MEDIUM_AGREEMENT in r.quality_flags
        assert r.consistency_score.value == pytest.approx(72.78344730240913, rel=1e-3)

    def test_rescue_when_included_empty_no_values(self) -> None:
        # Force empty included + empty rescue via monkeypatch of _compute_weights
        eng = ConsensusEngine()
        methods = (_vr("dcf", iv=None, ivps=None),)

        def zero_weights(**kwargs):
            ms = kwargs["methods"]
            details = tuple(
                MethodWeightDetail(
                    method=m.method,
                    category=m.category,
                    weight=0.0,
                    applicability_score=0.5,
                    confidence_score=m.confidence_score,
                    included_in_consensus=False,
                    is_outlier=False,
                    explanation="zero",
                )
                for m in ms
            )
            return {m.method: 0.0 for m in ms}, details

        import valuation.consensus.consensus_engine as mod

        orig = eng._compute_weights
        eng._compute_weights = zero_weights  # type: ignore[method-assign]
        try:
            with pytest.raises(ConsensusValidationError, match="no usable"):
                eng.analyze(ConsensusInputs(methods=methods))
        finally:
            eng._compute_weights = orig  # type: ignore[method-assign]

    def test_weighted_median_last_element(self) -> None:
        eng = ConsensusEngine()
        # All weight on last after sort — first cum never reaches 0.5 until last
        # Actually if first has tiny weight and second has rest...
        assert eng._weighted_median(
            [("a", 1.0, 0.1), ("b", 2.0, 0.9)]
        ) == pytest.approx(2.0)

    def test_speculative_low_confidence(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=10.0, confidence_score=0.5, confidence_level="low"),
                    _vr(
                        "relative",
                        ivps=40.0,
                        confidence_score=0.5,
                        confidence_level="low",
                    ),
                ),
                outlier_thresholds=OutlierThresholds(
                    exclude_outliers_from_consensus=False,
                    z_score=100,
                    median_deviation_pct=10,
                    extreme_ratio=100,
                ),
            )
        )
        assert (
            ConsensusQualityFlag.SPECULATIVE_CONSENSUS in r.quality_flags
            or ConsensusQualityFlag.LOW_AGREEMENT in r.quality_flags
        )

    def test_conflicting_flag(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=10.0),
                    _vr("relative", ivps=50.0),
                    _vr("asset_based", ivps=12.0),
                ),
                outlier_thresholds=OutlierThresholds(
                    z_score=100,
                    iqr_multiplier=100,
                    median_deviation_pct=10,
                    extreme_ratio=100,
                    exclude_outliers_from_consensus=False,
                ),
            )
        )
        assert (
            ConsensusQualityFlag.CONFLICTING_METHODS in r.quality_flags
            or ConsensusQualityFlag.LOW_AGREEMENT in r.quality_flags
        )

    def test_performance_budget(self) -> None:
        engine = ConsensusEngine()
        inputs = _bundle()
        t0 = time.perf_counter()
        for _ in range(30):
            engine.analyze(inputs)
        avg_ms = (time.perf_counter() - t0) * 1000.0 / 30.0
        assert avg_ms < 50.0, f"avg {avg_ms:.2f} ms >= 50"
        assert not math.isnan(engine.analyze(inputs).execution_time_ms or 0.0)

    def test_growth_market_applicability_branch(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("reverse_dcf", ivps=10.0),
                    _vr("residual_income", ivps=11.0),
                    _vr("epv", ivps=10.5),
                ),
                weighting_mode=WeightingMode.APPLICABILITY,
                company_profile=CompanyProfile(
                    growth_company=True, pays_dividend=True
                ),
            )
        )
        assert r.applicability_scores["reverse_dcf"] >= 0.55

    def test_payload_mix_with_results(self) -> None:
        r = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(
                    _vr("dcf", ivps=10.0),
                    {
                        "method": "relative",
                        "intrinsic_value_per_share": 11.0,
                        "confidence_score": 4.0,
                        "currency": "USD",
                    },
                    {
                        "method": "graham",
                        "equity_value": 1050,
                        "intrinsic_value_per_share": 10.5,
                        "confidence": "medium",
                    },
                )
            )
        )
        assert len(r.standardized_methods) == 3
        assert r.consensus_intrinsic_value.value is not None
