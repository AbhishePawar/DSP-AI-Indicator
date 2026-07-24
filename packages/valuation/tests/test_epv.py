"""Earnings Power Value (EPV) engine tests — target 100% module coverage."""

from __future__ import annotations

import time

import pytest

from valuation import ValuationEngine, ValuationError
from valuation.epv import (
    EPV_VERSION,
    EpvEngine,
    EpvInputs,
    EpvQualityFlag,
    NormalizationMethod,
    to_v2_aggregate_payload,
    validate_epv_inputs,
)
from valuation.epv.epv_explainability import explain_many, explain_step
from valuation.epv.epv_models import to_valuation_result


def _base(**kwargs) -> EpvInputs:
    data = dict(
        revenue=1000.0,
        ebit=200.0,
        tax_rate=0.25,
        maintenance_capex=40.0,
        depreciation=40.0,
        cost_of_capital=0.10,
        shares_outstanding=100.0,
        cash=50.0,
        debt=100.0,
        minority_interest=0.0,
        investments=0.0,
        current_market_price=5.0,
        normalization_method=NormalizationMethod.MANUAL_OVERRIDE,
    )
    data.update(kwargs)
    return EpvInputs(**data)


class TestKnownExample:
    """Greenwald-style known numbers."""

    def test_zero_growth_capitalization(self) -> None:
        # EBIT_n=100, t=25% → 75; +Dep40 −Maint40 → OE=75; WACC=10% → EV=750
        # Equity=750+50−100=700; /100 shares = 7.0
        inputs = _base(ebit=100.0, maintenance_capex=40.0, depreciation=40.0)
        result = EpvEngine().analyze(inputs)
        assert result.tax_adjusted_ebit.value == pytest.approx(75.0)
        assert result.owner_earnings.value == pytest.approx(75.0)
        assert result.enterprise_epv.value == pytest.approx(750.0)
        assert result.equity_value.value == pytest.approx(700.0)
        assert result.intrinsic_value_per_share.value == pytest.approx(7.0)
        assert result.margin_of_safety.value == pytest.approx((7.0 - 5.0) / 7.0)
        assert "research and educational" in result.disclaimer.lower()
        assert result.version == EPV_VERSION
        assert result.execution_time_ms is not None


class TestNormalization:
    def test_historical_average(self) -> None:
        r = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.HISTORICAL_AVERAGE,
                historical_ebit=(80.0, 100.0, 120.0),
            )
        )
        assert r.normalization.normalized_ebit == pytest.approx(100.0)

    def test_historical_average_via_average_ebit(self) -> None:
        r = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.HISTORICAL_AVERAGE,
                average_ebit=90.0,
            )
        )
        assert r.normalized_ebit.value == pytest.approx(90.0)

    def test_historical_average_via_margin(self) -> None:
        r = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.HISTORICAL_AVERAGE,
                historical_ebit=(),
                normalized_operating_margin=0.15,
            )
        )
        assert r.normalized_ebit.value == pytest.approx(150.0)

    def test_median(self) -> None:
        r = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.MEDIAN,
                historical_ebit=(50.0, 100.0, 300.0),
            )
        )
        assert r.normalized_ebit.value == pytest.approx(100.0)

    def test_median_fallback_average(self) -> None:
        r = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.MEDIAN,
                historical_ebit=(),
                average_ebit=88.0,
            )
        )
        assert r.normalized_ebit.value == pytest.approx(88.0)

    def test_cycle_adjustment(self) -> None:
        r = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.BUSINESS_CYCLE_ADJUSTMENT,
                historical_ebit=(100.0, 100.0),
                cycle_adjustment_factor=0.9,
            )
        )
        assert r.normalized_ebit.value == pytest.approx(90.0)

    def test_cycle_via_average_and_margin(self) -> None:
        r1 = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.BUSINESS_CYCLE_ADJUSTMENT,
                average_ebit=100.0,
                cycle_adjustment_factor=1.1,
            )
        )
        assert r1.normalized_ebit.value == pytest.approx(110.0)
        r2 = EpvEngine().analyze(
            _base(
                normalization_method=NormalizationMethod.BUSINESS_CYCLE_ADJUSTMENT,
                historical_ebit=(),
                average_ebit=None,
                normalized_operating_margin=0.1,
                cycle_adjustment_factor=1.0,
            )
        )
        assert r2.normalized_ebit.value == pytest.approx(100.0)

    def test_manual_margin_and_average(self) -> None:
        r = EpvEngine().analyze(
            _base(normalized_operating_margin=0.12)
        )
        assert r.normalized_ebit.value == pytest.approx(120.0)
        r2 = EpvEngine().analyze(_base(average_ebit=95.0))
        assert r2.normalized_ebit.value == pytest.approx(95.0)

    def test_strip_one_offs(self) -> None:
        r = EpvEngine().analyze(
            _base(
                ebit=100.0,
                one_time_gains=10.0,
                one_time_losses=5.0,
                asset_sales=2.0,
                exceptional_items=3.0,
                accounting_distortions=1.0,
            )
        )
        # 100 -10 +5 -2 -3 -1 = 89
        assert r.normalized_ebit.value == pytest.approx(89.0)

    def test_normalized_earnings_override(self) -> None:
        r = EpvEngine().analyze(_base(normalized_earnings=50.0))
        assert r.owner_earnings.value == pytest.approx(50.0)
        assert r.enterprise_epv.value == pytest.approx(500.0)


class TestValidation:
    def test_rejects_negative_depreciation_and_mi(self) -> None:
        with pytest.raises(ValuationError, match="depreciation"):
            validate_epv_inputs(_base(depreciation=-1))
        with pytest.raises(ValuationError, match="minority"):
            validate_epv_inputs(_base(minority_interest=-1))
        with pytest.raises(ValuationError):
            validate_epv_inputs(_base(investments=-1))

    def test_rejects_negative_shares(self) -> None:
        with pytest.raises(ValuationError, match="shares"):
            validate_epv_inputs(_base(shares_outstanding=-1))

    def test_rejects_non_positive_wacc(self) -> None:
        with pytest.raises(ValuationError, match="cost_of_capital"):
            validate_epv_inputs(_base(cost_of_capital=0))

    def test_rejects_bad_tax(self) -> None:
        with pytest.raises(ValuationError, match="tax"):
            validate_epv_inputs(_base(tax_rate=1.5))

    def test_rejects_nan(self) -> None:
        with pytest.raises(ValuationError, match="NaN"):
            validate_epv_inputs(_base(ebit=float("nan")))

    def test_rejects_inf(self) -> None:
        with pytest.raises(ValuationError, match="infinite"):
            validate_epv_inputs(_base(revenue=float("inf")))

    def test_rejects_negative_maint(self) -> None:
        with pytest.raises(ValuationError, match="maintenance"):
            validate_epv_inputs(_base(maintenance_capex=-1))

    def test_rejects_history_required(self) -> None:
        with pytest.raises(ValuationError, match="historical"):
            validate_epv_inputs(
                _base(
                    normalization_method=NormalizationMethod.HISTORICAL_AVERAGE,
                    historical_ebit=(),
                    average_ebit=None,
                    normalized_operating_margin=None,
                )
            )

    def test_rejects_cycle_factor(self) -> None:
        with pytest.raises(ValuationError, match="cycle_adjustment"):
            validate_epv_inputs(_base(cycle_adjustment_factor=0))

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(ValuationError, match="current_market_price"):
            validate_epv_inputs(_base(current_market_price=-1))

    def test_rejects_negative_debt_cash(self) -> None:
        with pytest.raises(ValuationError):
            validate_epv_inputs(_base(debt=-1))

    def test_ok_summary(self) -> None:
        s = validate_epv_inputs(_base())
        assert s.ok is True


class TestScenariosSensitivity:
    def test_scenarios_bear_base_bull_custom(self) -> None:
        r = EpvEngine().analyze(
            _base(bear_earnings_delta=-10.0, bull_earnings_delta=10.0)
        )
        kinds = {s.kind.name for s in r.scenarios}
        assert kinds >= {"bear", "base", "bull", "stress_margin"}
        base = next(s for s in r.scenarios if s.kind.name == "base")
        bear = next(s for s in r.scenarios if s.kind.name == "bear")
        assert bear.intrinsic_value is not None and base.intrinsic_value is not None
        assert bear.intrinsic_value < base.intrinsic_value

    def test_sensitivity_grids(self) -> None:
        r = EpvEngine().analyze(_base())
        assert "cost_of_capital" in r.sensitivity.grids
        assert "normalized_margin" in r.sensitivity.grids
        assert "maintenance_capex" in r.sensitivity.grids
        assert "tax_rate" in r.sensitivity.grids
        assert "owner_earnings" in r.sensitivity.grids
        assert r.sensitivity.to_dict()["heatmap_ready"] is True


class TestConfidenceQuality:
    def test_confidence_and_flags(self) -> None:
        r = EpvEngine().analyze(
            _base(
                historical_ebit=(100.0, 102.0, 101.0),
                historical_ebit_margin=(0.20, 0.19, 0.17),
                exceptional_items=5.0,
                maintenance_capex=60.0,
                depreciation=40.0,
                accounting_quality_score=80.0,
            )
        )
        assert r.confidence in {"high", "medium", "low"}
        assert r.confidence_detail.explanation
        assert EpvQualityFlag.MARGIN_COMPRESSION in r.quality_flags
        assert EpvQualityFlag.ACCOUNTING_WARNING in r.quality_flags
        assert EpvQualityFlag.HIGH_MAINTENANCE_CAPEX in r.quality_flags

    def test_stable_and_strong_oe(self) -> None:
        r = EpvEngine().analyze(
            _base(
                historical_ebit=(100.0, 100.0, 100.0),
                ebit=100.0,
                maintenance_capex=40.0,
                depreciation=40.0,
            )
        )
        assert EpvQualityFlag.STABLE_EARNINGS in r.quality_flags
        assert EpvQualityFlag.STRONG_OWNER_EARNINGS in r.quality_flags

    def test_declining_cyclical_weak(self) -> None:
        r = EpvEngine().analyze(
            _base(
                historical_ebit=(200.0, 50.0, 150.0),
                ebit=100.0,
                maintenance_capex=50.0,
                depreciation=10.0,
                working_capital_adjustment=20.0,
            )
        )
        assert EpvQualityFlag.HIGH_CYCLICALITY in r.quality_flags
        assert EpvQualityFlag.DECLINING_EARNINGS in r.quality_flags
        assert EpvQualityFlag.WEAK_OWNER_EARNINGS in r.quality_flags

    def test_confidence_branches_and_validation_optionals(self) -> None:
        # declining hist for stability; dep=0 capital_allocation branch;
        # optional validation fields ebit_margin / average_ebit_margin
        r = EpvEngine().analyze(
            _base(
                historical_ebit=(100.0, 80.0),
                historical_ebit_margin=(0.2, 0.1),
                depreciation=0.0,
                maintenance_capex=0.0,
                ebit_margin=0.1,
                average_ebit_margin=0.12,
                ebit=100.0,
            )
        )
        assert r.confidence in {"high", "medium", "low"}

    def test_sensitivity_handles_bad_wacc_cell(self) -> None:
        # Axis includes wacc-0.01 <= 0 → evaluator catches ValuationError → None
        r = EpvEngine().analyze(
            _base(
                cost_of_capital=0.005,
                bear_wacc_delta=0.0,
                bull_wacc_delta=0.0,
            )
        )
        cells = r.sensitivity.grids["cost_of_capital"]
        assert any(c.output_value is None for c in cells)


class TestExplainabilityIntegration:
    def test_explain_helpers(self) -> None:
        step = explain_step(
            name="x",
            value=1.0,
            formula="x=1",
            confidence="high",
        )
        assert step.name == "x"
        many = explain_many(
            [{"name": "y", "value": 2.0, "formula": "y=2", "confidence": "low"}]
        )
        assert len(many) == 1

    def test_engine_integration_and_payloads(self) -> None:
        result = ValuationEngine().analyze_epv(_base())
        assert result.enterprise_epv.value is not None
        assert len(result.explainability) >= 5
        vr = to_valuation_result(result)
        assert vr.model_name == "epv"
        assert vr.to_dict()["methodology"]
        # package alias
        from valuation import to_epv_valuation_result, to_epv_v2_aggregate_payload

        assert to_epv_valuation_result(result).model_name == "epv"
        payload = to_v2_aggregate_payload(result)
        assert payload["method"] == "epv"
        assert to_epv_v2_aggregate_payload(result)["module"] == "valuation.epv"
        d = result.to_dict()
        assert d["version"] == EPV_VERSION


class TestEdgeCases:
    def test_scenario_bad_wacc(self) -> None:
        with pytest.raises(ValuationError):
            EpvEngine().analyze(
                _base(cost_of_capital=0.01, bear_wacc_delta=-0.02)
            )

    def test_unknown_normalization_method(self) -> None:
        inputs = _base()
        object.__setattr__(inputs, "normalization_method", "bogus")  # type: ignore[arg-type]
        with pytest.raises(ValuationError, match="unknown normalization"):
            EpvEngine()._normalize_ebit(inputs)

    def test_value_rejects_zero_wacc(self) -> None:
        with pytest.raises(ValuationError, match="cost_of_capital"):
            EpvEngine()._value(_base(cost_of_capital=0.0))

    def test_no_market_price_mos_none(self) -> None:
        r = EpvEngine().analyze(_base(current_market_price=None))
        assert r.margin_of_safety.value is None

    def test_manual_margin_requires_revenue(self) -> None:
        with pytest.raises(ValuationError, match="revenue"):
            EpvEngine().analyze(
                _base(revenue=0.0, normalized_operating_margin=0.1)
            )

    def test_historical_average_missing_raises(self) -> None:
        with pytest.raises(ValuationError):
            EpvEngine()._normalize_ebit(
                _base(
                    normalization_method=NormalizationMethod.HISTORICAL_AVERAGE,
                    historical_ebit=(),
                    average_ebit=None,
                    normalized_operating_margin=None,
                )
            )

    def test_median_missing_raises(self) -> None:
        with pytest.raises(ValuationError, match="median"):
            EpvEngine()._normalize_ebit(
                _base(
                    normalization_method=NormalizationMethod.MEDIAN,
                    historical_ebit=(),
                    average_ebit=None,
                )
            )

    def test_cycle_missing_raises(self) -> None:
        with pytest.raises(ValuationError, match="business_cycle"):
            EpvEngine()._normalize_ebit(
                _base(
                    normalization_method=NormalizationMethod.BUSINESS_CYCLE_ADJUSTMENT,
                    historical_ebit=(),
                    average_ebit=None,
                    normalized_operating_margin=None,
                )
            )

    def test_negative_enterprise_rejected(self) -> None:
        with pytest.raises(ValuationError, match="impossible enterprise"):
            EpvEngine().analyze(
                _base(
                    ebit=-500.0,
                    maintenance_capex=100.0,
                    depreciation=0.0,
                    normalized_earnings=None,
                )
            )

    def test_sensitivity_zero_revenue_margin(self) -> None:
        # Should still produce matrix; margin axis may yield None cells
        r = EpvEngine().analyze(_base(revenue=0.0, ebit=50.0))
        assert "normalized_margin" in r.sensitivity.grids

    def test_confidence_aq_unit_interval(self) -> None:
        r = EpvEngine().analyze(_base(accounting_quality_score=0.7))
        assert r.confidence_detail.score >= 0

    def test_performance_budget(self) -> None:
        engine = EpvEngine()
        inputs = _base(historical_ebit=(90.0, 100.0, 110.0))
        t0 = time.perf_counter()
        for _ in range(20):
            engine.analyze(inputs)
        avg_ms = (time.perf_counter() - t0) * 1000.0 / 20.0
        assert avg_ms < 50.0, f"avg {avg_ms:.2f} ms >= 50"

    def test_validation_margin_needs_revenue(self) -> None:
        with pytest.raises(ValuationError):
            validate_epv_inputs(
                _base(
                    revenue=0.0,
                    normalization_method=NormalizationMethod.MEDIAN,
                    historical_ebit=(),
                    average_ebit=None,
                    normalized_operating_margin=0.1,
                )
            )
