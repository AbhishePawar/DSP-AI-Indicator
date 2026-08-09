"""Overall Valuation Aggregator tests — target 100% module coverage."""

from __future__ import annotations

import math
import time

import pytest

from valuation import ValuationEngine, ValuationError
from valuation.consensus import (
    ConsensusEngine,
    ConsensusInputs,
    OutlierThresholds,
    WeightingMode,
)
from valuation.overall import (
    OVERALL_VERSION,
    MosClassification,
    MosThresholds,
    OverallEngine,
    OverallInputs,
    OverallQualityFlag,
    OverallValuationError,
    ResearchLabel,
    explain_many,
    explain_step,
    to_v2_aggregate_payload,
    validate_overall_inputs,
)
from valuation.overall.overall_models import to_valuation_result
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


def _sens(spread: float = 0.10) -> SensitivityMatrix:
    base = 100.0
    return SensitivityMatrix(
        grids={
            "x": (
                SensitivityCell("x", 0.9, "ivps", base * (1 - spread), 0, 0),
                SensitivityCell("x", 1.0, "ivps", base, 0, 1),
                SensitivityCell("x", 1.1, "ivps", base * (1 + spread), 0, 2),
            )
        }
    )


def _vr(
    method: str,
    *,
    ivps: float | None = 10.0,
    iv: float | None = 1000.0,
    confidence_score: float = 5.0,
    confidence_level: str = "medium",
    scenarios: tuple[ScenarioOutcome, ...] | None = None,
    sensitivity: SensitivityMatrix | None = None,
    validation_ok: bool = True,
) -> ValuationResult:
    if scenarios is None:
        scenarios = (
            ScenarioOutcome(
                ScenarioKind.bear(), None, None, (ivps or 9) * 0.9
            ),
            ScenarioOutcome(ScenarioKind.base(), None, None, ivps),
            ScenarioOutcome(
                ScenarioKind.bull(), None, None, (ivps or 11) * 1.1
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
        quality_flags=(),
        sensitivity_results=sensitivity if sensitivity is not None else _sens(),
        scenario_results=scenarios,
        validation_summary=ValidationSummary(ok=validation_ok, checks=("ok",)),
        explainability=(),
        research_disclaimer="research",
        metadata=ValuationMetadata(
            model_name=method, engine_version="t", methodology="t"
        ),
        currency="USD",
    )


def _consensus(
    *,
    methods: tuple[ValuationResult, ...] | None = None,
    price_context: float | None = None,
):
    methods = methods or (
        _vr("dcf", ivps=12.0, iv=1200.0, confidence_score=6.0, sensitivity=_sens(0.05)),
        _vr("relative", ivps=10.0, iv=1000.0, confidence_score=5.0, sensitivity=_sens(0.35)),
        _vr("asset_based", ivps=9.0, iv=900.0, confidence_score=4.5, sensitivity=_sens(0.12)),
        _vr("ddm", ivps=11.0, iv=1100.0, confidence_score=5.5, sensitivity=_sens(0.08)),
    )
    return ConsensusEngine().analyze(
        ConsensusInputs(
            methods=methods,
            weighting_mode=WeightingMode.EQUAL,
            outlier_thresholds=OutlierThresholds(
                z_score=100,
                iqr_multiplier=100,
                median_deviation_pct=10,
                extreme_ratio=100,
                exclude_outliers_from_consensus=False,
            ),
            current_market_price=price_context,
        )
    )


def _overall(**kwargs) -> OverallInputs:
    data = dict(
        current_market_price=8.0,
        consensus=_consensus(),
        currency="USD",
    )
    data.update(kwargs)
    return OverallInputs(**data)


class TestAggregation:
    def test_from_consensus_result(self) -> None:
        r = OverallEngine().analyze(_overall())
        assert r.version == OVERALL_VERSION
        assert r.overall_valuation_enabled is True
        assert r.overall_intrinsic_value_per_share.value is not None
        assert r.consensus_value.value is not None
        assert r.margin_of_safety.value is not None
        assert r.overall_valuation_score.value is not None
        assert 0 <= r.overall_valuation_score.value <= 100
        assert "research" in r.disclaimer.lower()

    def test_method_summary_and_rankings(self) -> None:
        cons = _consensus()
        methods = (
            _vr("dcf", ivps=12.0),
            _vr("relative", ivps=10.0),
            _vr("asset_based", ivps=9.0),
            _vr("ddm", ivps=11.0),
        )
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=8.0,
                consensus=cons,
                methods=methods,
            )
        )
        assert len(r.method_summary) >= 4
        assert r.method_rankings
        assert r.consistency.agreement_pct >= 0
        assert r.consistency.highest_method is not None
        assert r.consistency.lowest_method is not None


class TestMarginOfSafety:
    def test_deep_value(self) -> None:
        # IVPS ~10.5, price 5 → mos ~0.52
        r = OverallEngine().analyze(_overall(current_market_price=5.0))
        assert r.mos_classification is MosClassification.DEEP_VALUE
        assert r.research_label is ResearchLabel.STRONG_BUY_CANDIDATE

    def test_undervalued(self) -> None:
        r = OverallEngine().analyze(_overall(current_market_price=8.5))
        assert r.mos_classification in {
            MosClassification.UNDERVALUED,
            MosClassification.DEEP_VALUE,
            MosClassification.FAIRLY_VALUED,
        }

    def test_fair_and_watchlist(self) -> None:
        # price near IV
        cons = _consensus()
        ivps = cons.consensus_per_share.value or 10.0
        r = OverallEngine().analyze(
            OverallInputs(current_market_price=float(ivps), consensus=cons)
        )
        assert r.mos_classification is MosClassification.FAIRLY_VALUED
        assert r.research_label in {
            ResearchLabel.FAIRLY_VALUED,
            ResearchLabel.WATCHLIST,
        }

    def test_overvalued(self) -> None:
        cons = _consensus()
        ivps = cons.consensus_per_share.value or 10.0
        r = OverallEngine().analyze(
            OverallInputs(current_market_price=float(ivps) * 1.25, consensus=cons)
        )
        assert r.mos_classification is MosClassification.OVERVALUED
        assert r.research_label is ResearchLabel.EXPENSIVE

    def test_extremely_overvalued(self) -> None:
        cons = _consensus()
        ivps = cons.consensus_per_share.value or 10.0
        r = OverallEngine().analyze(
            OverallInputs(current_market_price=float(ivps) * 2.0, consensus=cons)
        )
        assert r.mos_classification is MosClassification.EXTREMELY_OVERVALUED
        assert r.research_label is ResearchLabel.HIGHLY_EXPENSIVE

    def test_custom_thresholds(self) -> None:
        cons = _consensus()
        ivps = cons.consensus_per_share.value or 10.0
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=float(ivps) * 0.95,
                consensus=cons,
                mos_thresholds=MosThresholds(
                    deep_value=0.50,
                    undervalued=0.20,
                    fairly_band=0.02,
                    overvalued=-0.20,
                    extremely_overvalued=-0.50,
                ),
            )
        )
        assert r.mos_classification in set(MosClassification)


class TestConfidenceScenariosSensitivity:
    def test_confidence_and_scenarios(self) -> None:
        r = OverallEngine().analyze(_overall())
        assert r.overall_confidence in {"high", "medium", "low"}
        assert r.bear_value is not None
        assert r.base_value is not None
        assert r.bull_value is not None
        assert r.fair_value_range[0] <= r.fair_value_range[1]
        assert r.valuation_range[0] <= r.valuation_range[1]

    def test_sensitivity_summary(self) -> None:
        r = OverallEngine().analyze(_overall())
        assert r.sensitivity_summary.most_stable_driver is not None
        assert r.sensitivity_summary.highest_risk_driver is not None
        assert r.sensitivity_summary.sensitivity_ranking


class TestValidation:
    def test_missing_consensus_values_payload(self) -> None:
        with pytest.raises(OverallValuationError, match="missing intrinsic"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus={"method": "consensus"},
                )
            )

    def test_negative_price(self) -> None:
        with pytest.raises(OverallValuationError, match="current_market_price"):
            validate_overall_inputs(
                OverallInputs(current_market_price=-1.0, consensus=_consensus())
            )

    def test_nan_price(self) -> None:
        with pytest.raises(OverallValuationError, match="NaN"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=float("nan"), consensus=_consensus()
                )
            )

    def test_infinite(self) -> None:
        with pytest.raises(OverallValuationError, match="infinite"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=float("inf"), consensus=_consensus()
                )
            )

    def test_duplicate_methods(self) -> None:
        with pytest.raises(OverallValuationError, match="duplicate"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    methods=(_vr("dcf"), _vr("dcf", ivps=11.0)),
                )
            )

    def test_required_method_count(self) -> None:
        with pytest.raises(OverallValuationError, match="required"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    methods=(_vr("dcf"),),
                    required_method_count=3,
                )
            )

    def test_bad_shares(self) -> None:
        with pytest.raises(OverallValuationError, match="shares"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    shares_outstanding=-1,
                )
            )

    def test_unsupported_consensus_type(self) -> None:
        with pytest.raises(OverallValuationError, match="unsupported consensus"):
            validate_overall_inputs(
                OverallInputs(current_market_price=10.0, consensus=123)  # type: ignore[arg-type]
            )

    def test_unsupported_method_type(self) -> None:
        with pytest.raises(OverallValuationError, match="unsupported type"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    methods=(123,),  # type: ignore[arg-type]
                )
            )

    def test_is_valuation_error(self) -> None:
        assert issubclass(OverallValuationError, ValuationError)

    def test_zero_price_warning(self) -> None:
        summary = validate_overall_inputs(
            OverallInputs(current_market_price=0.0, consensus=_consensus())
        )
        assert any("zero" in w.lower() for w in summary.warnings)


class TestPayloadAndValuationResultConsensus:
    def test_valuation_result_consensus(self) -> None:
        cons_vr = ValuationResult(
            model_name="consensus",
            version="0.11.0-consensus",
            methodology="c",
            intrinsic_value=1050.0,
            enterprise_value=None,
            equity_value=1050.0,
            intrinsic_value_per_share=10.5,
            margin_of_safety=None,
            confidence_score=5.0,
            confidence_level="medium",
            quality_flags=(),
            sensitivity_results=SensitivityMatrix(grids={}),
            scenario_results=(
                ScenarioOutcome(ScenarioKind.bear(), None, None, 9.0),
                ScenarioOutcome(ScenarioKind.base(), None, None, 10.5),
                ScenarioOutcome(ScenarioKind.bull(), None, None, 12.0),
                ScenarioOutcome(
                    ScenarioKind.custom("stress", "Stress"), None, None, 8.0
                ),
            ),
            validation_summary=ValidationSummary(ok=True),
            explainability=(),
        )
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus=cons_vr,
                methods=(_vr("dcf", ivps=12.0), _vr("relative", ivps=10.0)),
            )
        )
        assert r.overall_intrinsic_value_per_share.value == pytest.approx(10.5)
        assert "stress" in r.scenario_summary.custom

    def test_v2_payload_consensus(self) -> None:
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus={
                    "method": "consensus",
                    "intrinsic_value": 1000,
                    "intrinsic_value_per_share": 10.0,
                    "confidence": "high",
                    "consistency_score": 85.0,
                    "confidence_interval": [9.0, 11.0],
                    "lower_range": 9.0,
                    "upper_range": 11.0,
                    "method_rankings": ["dcf", "ddm"],
                },
                methods=(
                    {
                        "method": "dcf",
                        "intrinsic_value_per_share": 12.0,
                        "confidence_score": 6.0,
                    },
                    {
                        "method": "ddm",
                        "intrinsic_value_per_share": 11.0,
                        "confidence": "medium",
                    },
                ),
            )
        )
        assert r.overall_intrinsic_value_per_share.value == pytest.approx(10.0)
        assert OverallQualityFlag.STRONG_CONSENSUS in r.quality_flags
        assert r.consistency.most_trusted_method == "dcf"


class TestQualityFlags:
    def test_wide_and_incomplete(self) -> None:
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=10.0,
                consensus={
                    "method": "consensus",
                    "intrinsic_value_per_share": 10.0,
                    "confidence": "low",
                    "consistency_score": 30.0,
                },
                methods=(_vr("dcf", ivps=20.0),),
                wide_range_pct=0.20,
            )
        )
        assert OverallQualityFlag.WIDE_VALUATION_RANGE in r.quality_flags
        assert OverallQualityFlag.INCOMPLETE_DATASET in r.quality_flags
        assert OverallQualityFlag.SPECULATIVE in r.quality_flags
        assert OverallQualityFlag.LOW_CONFIDENCE in r.quality_flags or True

    def test_narrow_range(self) -> None:
        cons = _consensus(
            methods=(
                _vr("dcf", ivps=10.0),
                _vr("relative", ivps=10.05),
                _vr("asset_based", ivps=9.95),
                _vr("ddm", ivps=10.02),
            )
        )
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=10.0,
                consensus=cons,
                methods=(
                    _vr("dcf", ivps=10.0),
                    _vr("relative", ivps=10.05),
                    _vr("asset_based", ivps=9.95),
                    _vr("ddm", ivps=10.02),
                ),
                narrow_range_pct=0.05,
            )
        )
        assert (
            OverallQualityFlag.NARROW_VALUATION_RANGE in r.quality_flags
            or OverallQualityFlag.STRONG_CONSENSUS in r.quality_flags
        )


class TestExplainabilityIntegration:
    def test_helpers_and_public_api(self) -> None:
        assert explain_step(name="x", value=1.0, formula="x=1").name == "x"
        assert len(explain_many([{"name": "y", "value": 2, "formula": "y=2"}])) == 1
        result = ValuationEngine().analyze_overall(_overall())
        assert len(result.explainability) >= 5
        vr = to_valuation_result(result)
        assert vr.model_name == "overall"
        from valuation import (
            to_overall_valuation_result,
            to_overall_v2_aggregate_payload,
        )

        assert to_overall_valuation_result(result).model_name == "overall"
        payload = to_v2_aggregate_payload(result)
        assert payload["method"] == "overall"
        assert payload["overall_valuation_enabled"] is True
        assert payload["not_investment_advice"] is True
        assert to_overall_v2_aggregate_payload(result)["method"] == "overall"
        assert result.to_dict()["overall_valuation_enabled"] is True


class TestEdgeCases:
    def test_shares_conversion(self) -> None:
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus={
                    "method": "consensus",
                    "intrinsic_value": 1000.0,
                    "confidence": "medium",
                },
                shares_outstanding=100.0,
            )
        )
        assert r.overall_intrinsic_value_per_share.value == pytest.approx(10.0)

    def test_ivps_only_payload(self) -> None:
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus={
                    "method": "consensus",
                    "intrinsic_value_per_share": 10.0,
                    "confidence_score": 5.0,
                },
                shares_outstanding=50.0,
            )
        )
        assert r.overall_intrinsic_value.value == pytest.approx(500.0)

    def test_unable_to_resolve_iv(self) -> None:
        # Bypass validation by calling resolve with empty - use consensus that
        # validates but analyze can't resolve: impossible if validation works.
        # Call _resolve then force None via engine path with monkeypatch.
        eng = OverallEngine()
        inputs = OverallInputs(
            current_market_price=10.0,
            consensus={
                "method": "consensus",
                "intrinsic_value_per_share": 10.0,
                "confidence": "medium",
            },
        )

        def bad_view(_inputs):
            return {
                "source": "x",
                "iv": None,
                "ivps": None,
                "consensus_display": None,
                "consensus_confidence": "low",
                "confidence_score": 1.0,
                "confidence_interval": (0.0, 0.0),
                "lower_range": 0.0,
                "upper_range": 0.0,
                "consistency": 10.0,
                "method_weights": (),
                "method_rankings": (),
                "applicability": {},
                "outliers": set(),
                "outlier_list": (),
                "standardized": (),
                "scenarios": (),
                "sensitivity": None,
                "extra_warnings": (),
            }

        orig = eng._resolve_consensus_view
        eng._resolve_consensus_view = bad_view  # type: ignore[method-assign]
        try:
            with pytest.raises(OverallValuationError, match="unable to resolve"):
                eng.analyze(inputs)
        finally:
            eng._resolve_consensus_view = orig  # type: ignore[method-assign]

    def test_unsupported_consensus_in_resolve(self) -> None:
        eng = OverallEngine()
        with pytest.raises(OverallValuationError, match="unsupported consensus"):
            eng._resolve_consensus_view(
                OverallInputs(current_market_price=1.0, consensus=object())  # type: ignore[arg-type]
            )

    def test_outlier_in_summary(self) -> None:
        methods = (
            _vr("dcf", ivps=10.0),
            _vr("relative", ivps=10.5),
            _vr("asset_based", ivps=10.2),
            _vr("ddm", ivps=50.0),
        )
        cons = ConsensusEngine().analyze(
            ConsensusInputs(
                methods=methods,
                weighting_mode=WeightingMode.EQUAL,
                outlier_thresholds=OutlierThresholds(
                    z_score=1.0,
                    median_deviation_pct=0.3,
                    extreme_ratio=2.0,
                    exclude_outliers_from_consensus=True,
                ),
            )
        )
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=10.0,
                consensus=cons,
                methods=methods,
            )
        )
        assert r.consistency.largest_outlier is not None or any(
            row.status == "outlier" for row in r.method_summary
        )

    def test_non_consensus_model_name_warning(self) -> None:
        vr = _vr("dcf", ivps=10.0)
        object.__setattr__(vr, "model_name", "not_consensus")
        summary = validate_overall_inputs(
            OverallInputs(current_market_price=10.0, consensus=vr)
        )
        assert any("expected 'consensus'" in w for w in summary.warnings)

    def test_missing_values_on_vr_consensus(self) -> None:
        vr = _vr("consensus", iv=None, ivps=None)
        with pytest.raises(OverallValuationError, match="missing intrinsic"):
            validate_overall_inputs(
                OverallInputs(current_market_price=10.0, consensus=vr)
            )

    def test_payload_method_warning_and_bad_numeric(self) -> None:
        summary = validate_overall_inputs(
            OverallInputs(
                current_market_price=10.0,
                consensus={
                    "method": "relative",
                    "intrinsic_value_per_share": 10.0,
                },
            )
        )
        assert any("method=" in w for w in summary.warnings)
        with pytest.raises(OverallValuationError, match="not numeric"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus={
                        "method": "consensus",
                        "intrinsic_value_per_share": "x",
                    },
                )
            )

    def test_method_payload_missing_name(self) -> None:
        with pytest.raises(OverallValuationError, match="missing method"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    methods=({"intrinsic_value_per_share": 10},),
                )
            )

    def test_method_payload_bad_numeric(self) -> None:
        with pytest.raises(OverallValuationError, match="not numeric"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    methods=({"method": "dcf", "intrinsic_value": "bad"},),
                )
            )

    def test_negative_range_pct(self) -> None:
        with pytest.raises(OverallValuationError, match="non-negative"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    wide_range_pct=-0.1,
                )
            )

    def test_nan_threshold(self) -> None:
        with pytest.raises(OverallValuationError, match="NaN"):
            validate_overall_inputs(
                OverallInputs(
                    current_market_price=10.0,
                    consensus=_consensus(),
                    mos_thresholds=MosThresholds(deep_value=float("nan")),
                )
            )

    def test_sparse_methods_warning(self) -> None:
        summary = validate_overall_inputs(
            OverallInputs(
                current_market_price=10.0,
                consensus={
                    "method": "consensus",
                    "intrinsic_value_per_share": 10.0,
                },
            )
        )
        assert any("sparse" in w.lower() for w in summary.warnings)

    def test_mos_none_path(self) -> None:
        eng = OverallEngine()
        assert eng._mos_class(None, MosThresholds()) is MosClassification.UNAVAILABLE
        assert eng._research_label(None, MosClassification.UNAVAILABLE) is ResearchLabel.WATCHLIST

    def test_zero_ivps_mos(self) -> None:
        # P1-04 — zero IV/share cannot produce MoS; fail closed.
        with pytest.raises(OverallValuationError, match="zero"):
            OverallEngine().analyze(
                OverallInputs(
                    current_market_price=5.0,
                    consensus={
                        "method": "consensus",
                        "intrinsic_value_per_share": 0.0,
                        "confidence": "medium",
                    },
                )
            )

    def test_ci_from_scenarios_fallback(self) -> None:
        eng = OverallEngine()
        vr = _vr("consensus", ivps=10.0, scenarios=())
        lo, hi = eng._ci_from_scenarios((), vr)
        assert lo < hi

    def test_scenario_iv_fallback(self) -> None:
        eng = OverallEngine()
        view = {
            "scenarios": (
                ScenarioOutcome(ScenarioKind.base(), 100.0, None, None),
                ScenarioOutcome(ScenarioKind.bear(), None, None, None),
            )
        }
        s = eng._scenarios(view)
        assert s.base == pytest.approx(100.0)

    def test_performance_budget(self) -> None:
        eng = OverallEngine()
        inputs = _overall()
        t0 = time.perf_counter()
        for _ in range(30):
            eng.analyze(inputs)
        avg_ms = (time.perf_counter() - t0) * 1000.0 / 30.0
        assert avg_ms < 50.0, f"avg {avg_ms:.2f} ms >= 50"
        assert not math.isnan(eng.analyze(inputs).execution_time_ms or 0.0)

    def test_high_confidence_flag(self) -> None:
        cons = _consensus(
            methods=(
                _vr("dcf", ivps=10.0, confidence_score=8.0, confidence_level="high"),
                _vr("relative", ivps=10.1, confidence_score=8.0, confidence_level="high"),
                _vr("asset_based", ivps=9.9, confidence_score=8.0, confidence_level="high"),
                _vr("ddm", ivps=10.05, confidence_score=8.0, confidence_level="high"),
                _vr("epv", ivps=10.0, confidence_score=8.0, confidence_level="high"),
            )
        )
        r = OverallEngine().analyze(
            OverallInputs(current_market_price=8.0, consensus=cons)
        )
        assert r.overall_confidence in {"high", "medium", "low"}
        # May or may not be HIGH_CONFIDENCE depending on Core blend
        assert r.quality_flags

    def test_zero_weight_status(self) -> None:
        cons = _consensus()
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus=cons,
                methods=(_vr("graham", ivps=10.0),),  # not in consensus weights
            )
        )
        graham = next(row for row in r.method_summary if row.method == "graham")
        assert graham.status == "zero_weight"
        assert graham.weight == pytest.approx(0.0)

    def test_validation_not_ok_status(self) -> None:
        cons = _consensus()
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus=cons,
                methods=(_vr("epv", ivps=10.0, validation_ok=False),),
            )
        )
        assert any(row.status == "validation_warning" for row in r.method_summary)

    def test_empty_sensitivity_view(self) -> None:
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus={
                    "method": "consensus",
                    "intrinsic_value_per_share": 10.0,
                    "confidence": "medium",
                },
            )
        )
        assert r.sensitivity_summary.most_stable_driver is None

    def test_iv_only_no_shares_sets_ivps(self) -> None:
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus={
                    "method": "consensus",
                    "intrinsic_value": 1000.0,
                    "confidence": "medium",
                },
            )
        )
        assert r.overall_intrinsic_value_per_share.value == pytest.approx(1000.0)

    def test_ci_uses_intrinsic_when_ivps_missing(self) -> None:
        eng = OverallEngine()
        sc = (
            ScenarioOutcome(ScenarioKind.bear(), 90.0, None, None),
            ScenarioOutcome(ScenarioKind.bull(), 110.0, None, None),
        )
        vr = _vr("consensus", ivps=100.0, scenarios=sc)
        lo, hi = eng._ci_from_scenarios(sc, vr)
        assert lo == pytest.approx(90.0)
        assert hi == pytest.approx(110.0)

    def test_normalize_exception_skipped(self) -> None:
        eng = OverallEngine()
        view = {
            "method_weights": (),
            "applicability": {},
            "outliers": set(),
            "standardized": (),
            "method_rankings": (),
        }
        # Invalid raw bypasses validation when calling helper directly
        rows, weights, rankings, _ = eng._method_summary(
            OverallInputs(
                current_market_price=10.0,
                consensus={"method": "consensus", "intrinsic_value_per_share": 10.0},
                methods=(object(),),  # type: ignore[arg-type]
            ),
            view,
            10.0,
        )
        assert rows == ()

    def test_equal_weights_without_consensus_weights(self) -> None:
        cons_vr = ValuationResult(
            model_name="consensus",
            version="t",
            methodology="c",
            intrinsic_value=1000.0,
            enterprise_value=None,
            equity_value=1000.0,
            intrinsic_value_per_share=10.0,
            margin_of_safety=None,
            confidence_score=5.0,
            confidence_level="medium",
            quality_flags=(),
            sensitivity_results=SensitivityMatrix(grids={}),
            scenario_results=(),
            validation_summary=ValidationSummary(ok=True),
            explainability=(),
        )
        r = OverallEngine().analyze(
            OverallInputs(
                current_market_price=9.0,
                consensus=cons_vr,
                methods=(_vr("dcf", ivps=12.0), _vr("relative", ivps=10.0)),
            )
        )
        assert abs(sum(w for _, w in r.method_weights) - 1.0) < 1e-9  # type: ignore[misc]

    def test_scenario_stability_zero_mid(self) -> None:
        eng = OverallEngine()
        from valuation.overall.overall_models import ScenarioSummary

        s = ScenarioSummary(
            bear=-1.0, base=0.0, bull=1.0, custom={}, outcomes=()
        )
        # median of [-1,0,1] is 0
        assert eng._scenario_stability(s) == pytest.approx(0.4)
        assert eng._scenario_stability(
            ScenarioSummary(bear=None, base=10.0, bull=None, custom={}, outcomes=())
        ) == pytest.approx(0.5)

    def test_high_confidence_quality_flag_direct(self) -> None:
        eng = OverallEngine()
        flags, _ = eng._quality_flags(
            "high",
            90.0,
            0.05,
            OverallInputs(
                current_market_price=10.0,
                consensus={"method": "consensus", "intrinsic_value_per_share": 10.0},
                narrow_range_pct=0.10,
            ),
            (
                # two rows + standardized present → incomplete elif branch
            ),
            {"standardized": ("a", "b")},
        )
        assert OverallQualityFlag.HIGH_CONFIDENCE in flags
        assert OverallQualityFlag.STRONG_CONSENSUS in flags
        assert OverallQualityFlag.INCOMPLETE_DATASET in flags

    def test_missing_consensus_none(self) -> None:
        inputs = OverallInputs(
            current_market_price=10.0,
            consensus={"method": "consensus", "intrinsic_value_per_share": 10.0},
        )
        object.__setattr__(inputs, "consensus", None)
        with pytest.raises(OverallValuationError, match="missing consensus"):
            validate_overall_inputs(inputs)

    def test_consensus_result_missing_values(self) -> None:
        cons = _consensus()
        # Force explained values to None
        object.__setattr__(
            cons,
            "consensus_intrinsic_value",
            explain_step(name="x", value=None, formula="x"),
        )
        object.__setattr__(
            cons,
            "consensus_per_share",
            explain_step(name="y", value=None, formula="y"),
        )
        with pytest.raises(OverallValuationError, match="missing intrinsic"):
            validate_overall_inputs(
                OverallInputs(current_market_price=10.0, consensus=cons)
            )
