"""Graham Intrinsic Value engine tests — target 100% module coverage."""

from __future__ import annotations

import time

import pytest

from valuation import ValuationEngine, ValuationError
from valuation.graham import (
    GRAHAM_VERSION,
    GrahamEngine,
    GrahamFormula,
    GrahamInputs,
    GrahamQualityFlag,
    to_v2_aggregate_payload,
    validate_graham_inputs,
)
from valuation.graham.graham_explainability import explain_many, explain_step
from valuation.graham.graham_models import to_valuation_result


def _base(**kwargs) -> GrahamInputs:
    data = dict(
        eps_trailing=2.0,
        growth_rate=7.0,
        aaa_bond_yield=0.044,
        shares_outstanding=100.0,
        formula=GrahamFormula.ORIGINAL,
        current_market_price=30.0,
        reference_aaa_yield=0.044,
    )
    data.update(kwargs)
    return GrahamInputs(**data)


class TestKnownExamples:
    def test_original_formula(self) -> None:
        # IV = 2 × (8.5 + 2×7) = 2 × 22.5 = 45
        r = GrahamEngine().analyze(_base())
        assert r.intrinsic_value_per_share.value == pytest.approx(45.0)
        assert r.intrinsic_value.value == pytest.approx(4500.0)
        assert r.method_used is GrahamFormula.ORIGINAL
        assert r.margin_of_safety.value == pytest.approx((45 - 30) / 45)
        assert "research and educational" in r.disclaimer.lower()
        assert r.version == GRAHAM_VERSION

    def test_modern_formula_yield_adjustment(self) -> None:
        # base 45 × (0.044/0.055)
        r = GrahamEngine().analyze(
            _base(formula=GrahamFormula.MODERN, aaa_bond_yield=0.055)
        )
        assert r.intrinsic_value_per_share.value == pytest.approx(45.0 * 0.044 / 0.055)

    def test_normalized_eps_and_decimal_growth(self) -> None:
        r = GrahamEngine().analyze(
            _base(
                normalized_eps=3.0,
                growth_rate=0.07,
                growth_as_decimal=True,
                formula=GrahamFormula.ORIGINAL,
            )
        )
        # G=7%, IV=3*(8.5+14)=67.5
        assert r.intrinsic_value_per_share.value == pytest.approx(67.5)
        assert r.growth_assumption.value == pytest.approx(7.0)


class TestValidation:
    def test_rejects_negative_shares(self) -> None:
        with pytest.raises(ValuationError, match="shares"):
            validate_graham_inputs(_base(shares_outstanding=-1))

    def test_rejects_negative_eps(self) -> None:
        with pytest.raises(ValuationError, match="negative EPS"):
            validate_graham_inputs(_base(eps_trailing=-1.0))

    def test_allows_negative_eps_when_flagged(self) -> None:
        s = validate_graham_inputs(
            _base(eps_trailing=-1.0, allow_negative_eps=True)
        )
        assert s.ok

    def test_rejects_impossible_growth(self) -> None:
        with pytest.raises(ValuationError, match="growth"):
            validate_graham_inputs(_base(growth_rate=99))
        with pytest.raises(ValuationError, match="growth"):
            validate_graham_inputs(_base(growth_rate=0.9, growth_as_decimal=True))

    def test_rejects_non_positive_yields(self) -> None:
        with pytest.raises(ValuationError, match="aaa_bond_yield"):
            validate_graham_inputs(_base(aaa_bond_yield=0))
        with pytest.raises(ValuationError, match="reference"):
            validate_graham_inputs(_base(reference_aaa_yield=-0.1))

    def test_rejects_invalid_required_return(self) -> None:
        with pytest.raises(ValuationError, match="required_return"):
            validate_graham_inputs(_base(required_return=0))

    def test_rejects_nan_and_debt(self) -> None:
        with pytest.raises(ValuationError, match="NaN"):
            validate_graham_inputs(_base(eps_trailing=float("nan")))
        with pytest.raises(ValuationError):
            validate_graham_inputs(_base(debt=-1))
        with pytest.raises(ValuationError, match="infinite"):
            validate_graham_inputs(_base(growth_rate=float("inf")))

    def test_warnings_high_growth_zero_eps(self) -> None:
        s = validate_graham_inputs(_base(growth_rate=20, eps_trailing=0.0))
        assert s.warnings
        s2 = validate_graham_inputs(
            _base(growth_rate=0.20, growth_as_decimal=True)
        )
        assert any("high growth" in w for w in s2.warnings)

    def test_optional_fields_and_price(self) -> None:
        s = validate_graham_inputs(
            _base(
                normalized_eps=2.1,
                book_value_per_share=-0.5,
                required_return=0.1,
                average_eps_3y=2.0,
                average_eps_5y=1.9,
                average_eps_10y=1.8,
                normalized_roe=0.12,
                accounting_quality_score=70,
            )
        )
        assert s.ok
        assert any("book" in w for w in s.warnings)
        with pytest.raises(ValuationError, match="current_market_price"):
            validate_graham_inputs(_base(current_market_price=-1))


class TestScenariosSensitivity:
    def test_scenarios(self) -> None:
        r = GrahamEngine().analyze(
            _base(formula=GrahamFormula.MODERN, bear_growth_delta=-2, bull_growth_delta=2)
        )
        kinds = {s.kind.name for s in r.scenarios}
        assert kinds >= {"bear", "base", "bull", "stress_growth"}
        base = next(s for s in r.scenarios if s.kind.name == "base")
        bear = next(s for s in r.scenarios if s.kind.name == "bear")
        assert bear.intrinsic_value_per_share < base.intrinsic_value_per_share

    def test_sensitivity_grids(self) -> None:
        r = GrahamEngine().analyze(
            _base(required_return=0.10, formula=GrahamFormula.MODERN)
        )
        assert "growth_rate" in r.sensitivity.grids
        assert "bond_yield" in r.sensitivity.grids
        assert "eps" in r.sensitivity.grids
        assert "required_return" in r.sensitivity.grids

    def test_scenario_bad_yield(self) -> None:
        with pytest.raises(ValuationError):
            GrahamEngine().analyze(
                _base(
                    formula=GrahamFormula.MODERN,
                    aaa_bond_yield=0.004,
                    bear_yield_delta=-0.01,
                )
            )

    def test_sensitivity_none_on_bad_yield(self) -> None:
        r = GrahamEngine().analyze(
            _base(
                formula=GrahamFormula.MODERN,
                aaa_bond_yield=0.003,
                bear_yield_delta=0.0,
                bull_yield_delta=0.0,
            )
        )
        cells = r.sensitivity.grids["bond_yield"]
        assert any(c.output_value is None for c in cells)


class TestConfidenceQuality:
    def test_flags_and_confidence(self) -> None:
        r = GrahamEngine().analyze(
            _base(
                growth_rate=20,
                book_value_per_share=0.5,
                average_eps_3y=2.0,
                average_eps_5y=2.0,
                average_eps_10y=2.0,
                accounting_quality_score=20,
                normalized_eps=2.5,
            )
        )
        assert GrahamQualityFlag.HIGH_GROWTH_ASSUMPTION in r.quality_flags
        assert GrahamQualityFlag.LOW_BOOK_VALUE in r.quality_flags
        assert GrahamQualityFlag.STABLE_EARNINGS in r.quality_flags
        assert GrahamQualityFlag.ACCOUNTING_WARNING in r.quality_flags
        assert r.confidence in {"high", "medium", "low"}

    def test_cyclical_negative_low_confidence(self) -> None:
        r = GrahamEngine().analyze(
            _base(
                eps_trailing=-1.0,
                allow_negative_eps=True,
                average_eps_3y=5.0,
                average_eps_5y=1.0,
                average_eps_10y=-2.0,
                accounting_quality_score=0.2,
            )
        )
        assert GrahamQualityFlag.NEGATIVE_EPS in r.quality_flags
        assert (
            GrahamQualityFlag.CYCLICAL_EARNINGS in r.quality_flags
            or GrahamQualityFlag.LOW_CONFIDENCE in r.quality_flags
        )

    def test_confidence_aq_unit_and_declining(self) -> None:
        r = GrahamEngine().analyze(
            _base(
                average_eps_3y=3.0,
                average_eps_5y=2.0,
                eps_trailing=1.0,
                accounting_quality_score=0.8,
            )
        )
        assert r.confidence_detail.score >= 0


class TestExplainabilityIntegration:
    def test_helpers_and_payloads(self) -> None:
        step = explain_step(name="x", value=1.0, formula="x=1")
        assert step.name == "x"
        assert len(explain_many([{"name": "y", "value": 2, "formula": "y=2"}])) == 1

        result = ValuationEngine().analyze_graham(_base(formula=GrahamFormula.MODERN))
        assert len(result.explainability) >= 5
        vr = to_valuation_result(result)
        assert vr.model_name == "graham"
        from valuation import to_graham_valuation_result, to_graham_v2_aggregate_payload

        assert to_graham_valuation_result(result).model_name == "graham"
        payload = to_v2_aggregate_payload(result)
        assert payload["method"] == "graham"
        assert to_graham_v2_aggregate_payload(result)["formula"] == "modern"
        assert result.to_dict()["method_used"] == "modern"


class TestEdgeCases:
    def test_no_price_mos_none(self) -> None:
        r = GrahamEngine().analyze(_base(current_market_price=None))
        assert r.margin_of_safety.value is None

    def test_unknown_formula(self) -> None:
        inputs = _base()
        object.__setattr__(inputs, "formula", "bogus")  # type: ignore[arg-type]
        with pytest.raises(ValuationError, match="unknown Graham"):
            GrahamEngine()._value(inputs)

    def test_value_rejects_zero_yield_modern(self) -> None:
        with pytest.raises(ValuationError, match="aaa_bond_yield"):
            GrahamEngine()._value(
                _base(formula=GrahamFormula.MODERN, aaa_bond_yield=0.0)
            )

    def test_performance_budget(self) -> None:
        engine = GrahamEngine()
        inputs = _base(formula=GrahamFormula.MODERN, required_return=0.09)
        t0 = time.perf_counter()
        for _ in range(20):
            engine.analyze(inputs)
        avg_ms = (time.perf_counter() - t0) * 1000.0 / 20.0
        assert avg_ms < 50.0, f"avg {avg_ms:.2f} ms >= 50"
