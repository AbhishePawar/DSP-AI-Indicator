"""Valuation Core Framework tests — confidence, validation, sensitivity, etc."""

from __future__ import annotations

import math
import time
from typing import Any, Mapping, Sequence

import pytest

from valuation.core import (
    RESEARCH_DISCLAIMER,
    VALUATION_CORE_VERSION,
    ConfidenceEngine,
    ConfidenceProvider,
    ConvergenceError,
    ExplainabilityEngine,
    ExplainabilityError,
    ExplainabilityProvider,
    ForecastError,
    MetadataError,
    QualityFlag,
    ScenarioEngine,
    ScenarioError,
    ScenarioKind,
    ScenarioOutcome,
    ScenarioProvider,
    ScenarioSpec,
    SensitivityAxis,
    SensitivityCell,
    SensitivityEngine,
    SensitivityError,
    SensitivityMatrix,
    SensitivityProvider,
    ValidationEngine,
    ValidationError,
    ValidationProvider,
    ValidationSummary,
    ValuationError,
    ValuationMetadata,
    ValuationMethod,
    ValuationResult,
)
from valuation.core.result_models import ExplainabilityRecord
from valuation.exceptions import ValuationError as PackageValuationError


class TestErrors:
    def test_hierarchy(self) -> None:
        assert issubclass(ValidationError, ValuationError)
        assert issubclass(ForecastError, ValuationError)
        assert issubclass(ConvergenceError, ValuationError)
        assert issubclass(SensitivityError, ValuationError)
        assert issubclass(ScenarioError, ValuationError)
        assert issubclass(MetadataError, ValuationError)
        assert issubclass(ExplainabilityError, ValuationError)
        assert ValuationError is PackageValuationError

    def test_raise_each(self) -> None:
        for exc in (
            ValidationError,
            ForecastError,
            ConvergenceError,
            SensitivityError,
            ScenarioError,
            MetadataError,
            ExplainabilityError,
        ):
            with pytest.raises(exc):
                raise exc("x")


class TestQualityFlags:
    def test_all_flags_present(self) -> None:
        expected = {
            "high_roe",
            "declining_roe",
            "negative_residual_income",
            "high_debt",
            "weak_cash_flow",
            "weak_book_value_growth",
            "accounting_warning",
            "capital_efficient",
            "low_data_quality",
            "forecast_risk",
            "margin_compression",
            "terminal_value_dominance",
            "overly_optimistic_assumptions",
        }
        assert {f.value for f in QualityFlag} == expected


class TestConfidenceEngine:
    def test_high_confidence(self) -> None:
        detail = ConfidenceEngine().score(
            {
                "accounting_quality": 1.0,
                "forecast_reliability": 1.0,
                "data_completeness": 1.0,
                "business_stability": 1.0,
                "capital_allocation": 1.0,
                "model_assumptions": 1.0,
                "clean_surplus_compliance": 1.0,
                "solver_accuracy": 1.0,
            }
        )
        assert detail.level == "high"
        assert detail.score == detail.max_score
        assert "high" in detail.explanation
        d = detail.to_dict()
        assert d["level"] == "high"

    def test_empty_weights_defensive(self) -> None:
        eng = ConfidenceEngine()
        original = ConfidenceEngine.FACTOR_WEIGHTS
        try:
            ConfidenceEngine.FACTOR_WEIGHTS = {}
            detail = eng.score({"accounting_quality": 1.0})
            assert detail.level == "low"
            assert detail.max_score == 0.0
        finally:
            ConfidenceEngine.FACTOR_WEIGHTS = original

    def test_medium_and_low_and_bool_and_scaled(self) -> None:
        eng = ConfidenceEngine()
        mid = eng.score(
            {
                "accounting_quality": True,
                "forecast_reliability": True,
                "data_completeness": True,
                "business_stability": True,
                "capital_allocation": False,
                "model_assumptions": None,
            }
        )
        assert mid.level == "medium"  # 4/8 = 0.5
        low = eng.score({"accounting_quality": 0.1})
        assert low.level == "low"
        scaled = eng.score({"accounting_quality": 80})  # percent-like >10
        assert scaled.factors["accounting_quality"] == pytest.approx(0.8)
        capped = eng.score({"accounting_quality": 5})  # >1 but <=10
        assert capped.factors["accounting_quality"] == 1.0
        neg = eng.score({"accounting_quality": -2})
        assert neg.factors["accounting_quality"] == 0.0


class TestValidationEngine:
    def test_ok_path(self) -> None:
        summary = ValidationEngine().validate(
            {
                "shares_outstanding": 100,
                "wacc": 0.09,
                "terminal_growth": 0.02,
                "tax_rate": 0.25,
                "book_value": 1000,
                "debt": 50,
                "cash": 20,
                "revenue": 500,
                "growth": 0.05,
                "forecast_years": 10,
            }
        )
        assert summary.ok is True
        assert summary.to_dict()["ok"] is True

    def test_share_count_and_discount_fallbacks(self) -> None:
        s = ValidationEngine().validate(
            {
                "share_count": 10,
                "cost_of_equity": 0.1,
                "terminal_growth": 0.02,
            }
        )
        assert s.ok
        s2 = ValidationEngine().validate(
            {"discount_rate": 0.08, "terminal_growth": 0.02}
        )
        assert s2.ok

    def test_summarize_errors_and_warnings(self) -> None:
        eng = ValidationEngine()
        bad = eng.summarize(
            {
                "shares_outstanding": -1,
                "wacc": 0,
                "tax_rate": 1.5,
                "book_value": -1,
                "debt": -1,
                "growth": 0.9,
                "forecast_years": 99,
                "terminal_growth": 0.2,
            }
        )
        assert bad.ok is False
        assert bad.errors
        assert bad.warnings
        with pytest.raises(ValidationError):
            eng.validate({"shares_outstanding": 0})

    def test_nan_inf_and_helpers(self) -> None:
        eng = ValidationEngine()
        assert eng.summarize({"wacc": float("nan")}).ok is False
        assert eng.summarize({"cash": float("inf")}).ok is False
        eng.require_positive(1.0, "x")
        eng.require_non_negative(0.0, "y")
        with pytest.raises(ValidationError):
            eng.require_positive(0.0, "x")
        with pytest.raises(ValidationError):
            eng.require_non_negative(-1.0, "y")
        with pytest.raises(ValidationError):
            eng.require_positive(float("nan"), "x")
        with pytest.raises(ValidationError):
            eng.require_non_negative(float("inf"), "y")


class TestSensitivityEngine:
    def test_without_evaluator(self) -> None:
        matrix = SensitivityEngine().sensitivity({})
        assert "growth" in matrix.grids
        assert matrix.to_dict()["heatmap_ready"] is True
        cell = matrix.grids["growth"][0]
        assert isinstance(cell, SensitivityCell)
        assert cell.to_dict()["output_value"] is None

    def test_with_evaluator_and_context_key(self) -> None:
        def ev(ctx: Mapping[str, Any]) -> float:
            return float(ctx["growth"]) * 100.0

        matrix = SensitivityEngine().sensitivity(
            {"growth": 0.05},
            axes=[SensitivityAxis("growth", (0.01, 0.05, 0.10))],
            evaluator=ev,
            output_name="iv",
        )
        assert matrix.grids["growth"][1].output_value == pytest.approx(5.0)

    def test_evaluator_failure(self) -> None:
        def boom(_ctx: Mapping[str, Any]) -> float:
            raise RuntimeError("fail")

        with pytest.raises(SensitivityError):
            SensitivityEngine().sensitivity(
                {},
                axes=[SensitivityAxis("wacc", (0.08,))],
                evaluator=boom,
            )


class TestScenarioEngine:
    def test_default_no_evaluator(self) -> None:
        outcomes = ScenarioEngine().scenarios({})
        assert len(outcomes) == 3
        assert outcomes[0].kind.name == "bear"
        assert outcomes[0].to_dict()["kind"] == "bear"

    def test_custom_and_evaluator(self) -> None:
        specs = (
            ScenarioSpec(ScenarioKind.custom("stress", "Stress"), {"g": -0.05}),
            ScenarioSpec(ScenarioKind.base(), {"g": 0.0}),
        )

        def ev(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            return {
                "intrinsic_value": 100 + float(ctx.get("g", 0)) * 1000,
                "equity_value": 90,
                "intrinsic_value_per_share": 1.0,
                "notes": "ok",
                "extras": {"g": ctx.get("g")},
            }

        outs = ScenarioEngine().scenarios({}, specs=specs, evaluator=ev)
        assert outs[0].intrinsic_value == pytest.approx(50.0)
        assert outs[1].extras["g"] == 0.0

        # Cover non-None coercion path in _opt_float via string numerics
        def ev_str(_ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            return {
                "intrinsic_value": "12.5",
                "equity_value": "10",
                "intrinsic_value_per_share": "0.5",
            }

        coerced = ScenarioEngine().scenarios(
            {},
            specs=[ScenarioSpec(ScenarioKind.base())],
            evaluator=ev_str,
        )
        assert coerced[0].intrinsic_value == pytest.approx(12.5)

        from valuation.core.scenario_engine import _opt_float

        assert _opt_float(None) is None
        assert _opt_float(7) == 7.0
        assert _opt_float("3.25") == pytest.approx(3.25)

    def test_scenario_failure(self) -> None:
        def boom(_ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            raise ValueError("nope")

        with pytest.raises(ScenarioError):
            ScenarioEngine().scenarios(
                {},
                specs=[ScenarioSpec(ScenarioKind.bull())],
                evaluator=boom,
            )

    def test_default_specs(self) -> None:
        specs = ScenarioEngine().default_specs(bear={"a": 1}, base={}, bull={"b": 2})
        assert specs[0].overrides["a"] == 1


class TestExplainabilityEngine:
    def test_explain_and_single(self) -> None:
        eng = ExplainabilityEngine()
        records = eng.explain(
            [
                {
                    "name": "IV",
                    "value": 10.0,
                    "formula": "IV = BV + PV(RI)",
                    "inputs": {"bv": 5},
                    "intermediates": {"pv": 5},
                    "confidence": "high",
                    "warnings": "watch",
                }
            ]
        )
        assert len(records) == 1
        assert RESEARCH_DISCLAIMER in records[0].notes
        assert records[0].to_dict()["name"] == "IV"
        one = eng.single(
            name="WACC",
            value=0.09,
            formula="WACC = …",
            confidence="medium",
            notes="n",
            warnings=("w",),
        )
        assert isinstance(one, ExplainabilityRecord)

    def test_errors(self) -> None:
        eng = ExplainabilityEngine()
        with pytest.raises(ExplainabilityError):
            eng.explain([{"formula": "x"}])
        with pytest.raises(ExplainabilityError):
            eng.explain([{"name": "a"}])
        with pytest.raises(ExplainabilityError):
            eng.explain(
                [{"name": "a", "formula": "f", "confidence": "bogus"}]
            )


class TestResultModelsAndMetadata:
    def test_valuation_result_serialization(self) -> None:
        meta = ValuationMetadata(
            model_name="core_demo",
            engine_version="0.5.0",
            methodology="infrastructure",
            formula_references=("n/a",),
            assumption_summary={"note": "demo"},
            calculation_timestamp="2026-07-24T00:00:00Z",
            execution_time_ms=1.2,
        )
        assert meta.to_dict()["core_version"] == VALUATION_CORE_VERSION
        assert ScenarioKind.bear().label == "Bear"
        assert ScenarioKind.base().name == "base"
        assert ScenarioKind.bull().name == "bull"

        result = ValuationResult(
            model_name="core_demo",
            version="0.5.0",
            methodology="infrastructure",
            intrinsic_value=100.0,
            enterprise_value=110.0,
            equity_value=100.0,
            intrinsic_value_per_share=1.0,
            margin_of_safety=0.2,
            confidence_score=6.0,
            confidence_level="high",
            quality_flags=(QualityFlag.HIGH_ROE, QualityFlag.CAPITAL_EFFICIENT),
            sensitivity_results=SensitivityMatrix(grids={}),
            scenario_results=(
                ScenarioOutcome(
                    kind=ScenarioKind.base(),
                    intrinsic_value=100.0,
                    equity_value=100.0,
                    intrinsic_value_per_share=1.0,
                ),
            ),
            validation_summary=ValidationSummary(ok=True, checks=("shares > 0",)),
            explainability=(),
            execution_time_ms=1.2,
            metadata=meta,
            confidence_explanation="demo",
        )
        d = result.to_dict()
        assert d["model_name"] == "core_demo"
        assert d["quality_flags"] == ["high_roe", "capital_efficient"]
        agg = result.to_aggregate_payload()
        result_no_meta = ValuationResult(
            model_name="x",
            version="0.5.0",
            methodology="infra",
            intrinsic_value=None,
            enterprise_value=None,
            equity_value=None,
            intrinsic_value_per_share=None,
            margin_of_safety=None,
            confidence_score=0.0,
            confidence_level="low",
            quality_flags=(),
            sensitivity_results=SensitivityMatrix(grids={}),
            scenario_results=(),
            validation_summary=ValidationSummary(ok=True),
            explainability=(),
            metadata=None,
        )
        assert result_no_meta.to_dict()["metadata"] is None

        from valuation.core.validation_engine import FieldRule

        assert FieldRule.POSITIVE == "positive"
        assert FieldRule.SHARES == "shares"


class TestInterfaces:
    def test_concrete_providers(self) -> None:
        class M(ValuationMethod):
            @property
            def name(self) -> str:
                return "demo"

            def analyze(self, inputs: Any) -> Any:
                return inputs

        class S(ScenarioProvider):
            def scenarios(self, context: Mapping[str, Any]) -> Sequence[Any]:
                return ()

        class Sens(SensitivityProvider):
            def sensitivity(self, context: Mapping[str, Any]) -> Any:
                return None

        class E(ExplainabilityProvider):
            def explain(self, steps: Sequence[Mapping[str, Any]]) -> Sequence[Any]:
                return ()

        class V(ValidationProvider):
            def validate(self, inputs: Any) -> Any:
                return ValidationSummary(ok=True)

        class C(ConfidenceProvider):
            def score(self, factors: Mapping[str, float | int | bool | None]) -> Any:
                return ConfidenceEngine().score(factors)

        assert M().name == "demo"
        assert M().analyze(1) == 1
        assert S().scenarios({}) == ()
        assert Sens().sensitivity({}) is None
        assert E().explain([]) == ()
        assert V().validate({}).ok
        assert C().score({"accounting_quality": 1.0}).level in {
            "high",
            "medium",
            "low",
        }


class TestPerformance:
    def test_core_overhead_under_5ms(self) -> None:
        eng_c = ConfidenceEngine()
        eng_v = ValidationEngine()
        eng_s = ScenarioEngine()
        eng_z = SensitivityEngine()
        eng_e = ExplainabilityEngine()
        inputs = {
            "shares_outstanding": 100,
            "wacc": 0.09,
            "terminal_growth": 0.02,
            "tax_rate": 0.25,
            "book_value": 1000,
            "debt": 0,
            "cash": 0,
            "revenue": 500,
            "growth": 0.05,
            "forecast_years": 10,
        }
        t0 = time.perf_counter()
        for _ in range(50):
            eng_c.score({"accounting_quality": 1.0, "data_completeness": 1.0})
            eng_v.validate(inputs)
            eng_s.scenarios(inputs)
            eng_z.sensitivity(inputs)
            eng_e.explain(
                [{"name": "x", "value": 1.0, "formula": "x=1", "confidence": "low"}]
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 50.0
        assert elapsed_ms < 5.0, f"overhead {elapsed_ms:.3f} ms >= 5 ms"


class TestPackageImport:
    def test_core_version_constant(self) -> None:
        assert VALUATION_CORE_VERSION.startswith("0.5.0")
        import valuation

        assert valuation.__version__ == "0.12.0"
