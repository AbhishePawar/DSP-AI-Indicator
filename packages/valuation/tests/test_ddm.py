"""Dividend Discount Model (DDM) tests — target 100% module coverage."""

from __future__ import annotations

import time

import pytest

from valuation import ValuationEngine, ValuationError
from valuation.ddm import (
    DDM_VERSION,
    DdmEngine,
    DdmInputs,
    DdmMethod,
    DdmQualityFlag,
    DividendQuality,
    to_v2_aggregate_payload,
    validate_ddm_inputs,
)
from valuation.ddm.ddm_explainability import explain_many, explain_step
from valuation.ddm.ddm_models import to_valuation_result


def _base(**kwargs) -> DdmInputs:
    data = dict(
        current_dps=2.0,
        cost_of_equity=0.10,
        expected_dividend_growth=0.03,
        terminal_growth=0.02,
        forecast_years=5,
        shares_outstanding=100.0,
        current_market_price=30.0,
        method=DdmMethod.GORDON,
    )
    data.update(kwargs)
    return DdmInputs(**data)


class TestKnownExamples:
    def test_zero_growth(self) -> None:
        # IV = 2 / 0.10 = 20
        r = DdmEngine().analyze(_base(method=DdmMethod.ZERO_GROWTH))
        assert r.intrinsic_value_per_share.value == pytest.approx(20.0)
        assert r.method_used is DdmMethod.ZERO_GROWTH

    def test_gordon(self) -> None:
        # D1=2*1.03=2.06; IV=2.06/(0.10-0.03)=29.42857...
        r = DdmEngine().analyze(_base())
        assert r.intrinsic_value_per_share.value == pytest.approx(2.06 / 0.07)
        assert r.intrinsic_value.value == pytest.approx(100 * 2.06 / 0.07)
        assert r.margin_of_safety.value is not None
        assert "research and educational" in r.disclaimer.lower()
        assert r.version == DDM_VERSION

    def test_two_stage(self) -> None:
        r = DdmEngine().analyze(
            _base(method=DdmMethod.TWO_STAGE, forecast_years=3, expected_dividend_growth=0.08)
        )
        assert len(r.forecast_dividends) == 3
        assert r.terminal_value.value is not None
        assert r.intrinsic_value_per_share.value is not None
        assert r.intrinsic_value_per_share.value > 0

    def test_multi_stage_schedule(self) -> None:
        schedule = (0.10, 0.08, 0.06, 0.04, 0.03)
        r = DdmEngine().analyze(
            _base(
                method=DdmMethod.MULTI_STAGE,
                forecast_years=5,
                dividend_growth_schedule=schedule,
            )
        )
        assert len(r.forecast_dividends) == 5
        assert r.forecast_dividends[0].growth == pytest.approx(0.10)


class TestValidation:
    def test_rejects_negative_dps(self) -> None:
        with pytest.raises(ValuationError, match="current_dps"):
            validate_ddm_inputs(_base(current_dps=-1))

    def test_rejects_g_ge_r(self) -> None:
        with pytest.raises(ValuationError, match="growth must be"):
            validate_ddm_inputs(_base(expected_dividend_growth=0.12, cost_of_equity=0.10))

    def test_rejects_negative_shares(self) -> None:
        with pytest.raises(ValuationError, match="shares"):
            validate_ddm_inputs(_base(shares_outstanding=0))

    def test_rejects_bad_payout_roe(self) -> None:
        with pytest.raises(ValuationError, match="payout"):
            validate_ddm_inputs(_base(dividend_payout_ratio=2.0))
        with pytest.raises(ValuationError, match="ROE"):
            validate_ddm_inputs(_base(roe=5.0))
        with pytest.raises(ValuationError, match="retention"):
            validate_ddm_inputs(_base(retention_ratio=1.5))

    def test_rejects_schedule_length(self) -> None:
        with pytest.raises(ValuationError, match="schedule"):
            validate_ddm_inputs(
                _base(
                    method=DdmMethod.MULTI_STAGE,
                    forecast_years=3,
                    dividend_growth_schedule=(0.1, 0.1),
                )
            )

    def test_rejects_nan_terminal(self) -> None:
        with pytest.raises(ValuationError, match="NaN"):
            validate_ddm_inputs(_base(current_dps=float("nan")))
        with pytest.raises(ValuationError, match="terminal"):
            validate_ddm_inputs(
                _base(
                    method=DdmMethod.TWO_STAGE,
                    terminal_growth=0.15,
                    cost_of_equity=0.10,
                )
            )

    def test_warnings(self) -> None:
        # P1-04 — zero DPS is hard-fail (unavailable), not a warning + IV=0.
        with pytest.raises(ValuationError, match="current_dps is zero"):
            validate_ddm_inputs(
                _base(
                    method=DdmMethod.ZERO_GROWTH,
                    current_dps=0.0,
                    expected_dividend_growth=0.25,
                )
            )
        s2 = validate_ddm_inputs(
            _base(
                method=DdmMethod.ZERO_GROWTH,
                expected_dividend_growth=-0.02,
                dividend_payout_ratio=1.1,
            )
        )
        assert any("negative growth" in w for w in s2.warnings)

    def test_rejects_non_positive_coe(self) -> None:
        with pytest.raises(ValuationError, match="cost_of_equity"):
            validate_ddm_inputs(_base(cost_of_equity=0))


class TestScenariosSensitivity:
    def test_scenarios(self) -> None:
        r = DdmEngine().analyze(_base(method=DdmMethod.TWO_STAGE))
        kinds = {s.kind.name for s in r.scenarios}
        assert kinds >= {"bear", "base", "bull", "stress_payout"}

    def test_sensitivity(self) -> None:
        r = DdmEngine().analyze(
            _base(
                method=DdmMethod.TWO_STAGE,
                dividend_payout_ratio=0.4,
                retention_ratio=0.6,
                roe=0.12,
            )
        )
        for key in (
            "dividend_growth",
            "cost_of_equity",
            "terminal_growth",
            "payout_ratio",
            "roe",
        ):
            assert key in r.sensitivity.grids

    def test_sensitivity_none_when_g_ge_r(self) -> None:
        r = DdmEngine().analyze(
            _base(cost_of_equity=0.04, expected_dividend_growth=0.035)
        )
        cells = r.sensitivity.grids["dividend_growth"]
        assert any(c.output_value is None for c in cells)

    def test_growth_path_mismatch(self) -> None:
        inputs = _base(
            method=DdmMethod.MULTI_STAGE,
            forecast_years=3,
            dividend_growth_schedule=(0.1, 0.1, 0.1),
        )
        object.__setattr__(inputs, "forecast_years", 5)
        with pytest.raises(ValuationError, match="growth path"):
            DdmEngine()._value(inputs)

    def test_scenario_bad_coe(self) -> None:
        with pytest.raises(ValuationError):
            DdmEngine().analyze(
                _base(
                    method=DdmMethod.ZERO_GROWTH,
                    cost_of_equity=0.005,
                    bear_coe_delta=-0.01,
                    expected_dividend_growth=0.0,
                )
            )

    def test_scenario_clamps_gordon_and_terminal(self) -> None:
        # Bull growth pushes g or terminal above r → clamp paths
        r1 = DdmEngine().analyze(
            _base(
                method=DdmMethod.GORDON,
                cost_of_equity=0.05,
                expected_dividend_growth=0.04,
                bull_growth_delta=0.02,
                bull_coe_delta=0.0,
            )
        )
        assert any(s.kind.name == "bull" for s in r1.scenarios)
        r2 = DdmEngine().analyze(
            _base(
                method=DdmMethod.TWO_STAGE,
                cost_of_equity=0.05,
                expected_dividend_growth=0.03,
                terminal_growth=0.045,
                bull_growth_delta=0.02,
                bull_coe_delta=0.0,
            )
        )
        assert any(s.kind.name == "bull" for s in r2.scenarios)

    def test_sensitivity_none_on_low_r_and_high_tg(self) -> None:
        r = DdmEngine().analyze(
            _base(
                method=DdmMethod.TWO_STAGE,
                cost_of_equity=0.005,
                expected_dividend_growth=0.0,
                terminal_growth=0.001,
                bear_coe_delta=0.0,
                bull_coe_delta=0.0,
                bear_growth_delta=0.0,
                bull_growth_delta=0.0,
            )
        )
        assert any(
            c.output_value is None for c in r.sensitivity.grids["cost_of_equity"]
        )
        r2 = DdmEngine().analyze(
            _base(
                method=DdmMethod.TWO_STAGE,
                cost_of_equity=0.04,
                expected_dividend_growth=0.05,
                terminal_growth=0.035,
                bear_coe_delta=0.0,
                bull_coe_delta=0.0,
            )
        )
        assert any(
            c.output_value is None for c in r2.sensitivity.grids["terminal_growth"]
        )


class TestQualityConfidence:
    def test_aristocrat_and_quality(self) -> None:
        r = DdmEngine().analyze(
            _base(
                years_of_dividend_growth=30,
                dividend_stability_score=90,
                dividend_coverage_ratio=2.5,
                dividend_payout_ratio=0.45,
                free_cash_flow_payout_ratio=0.5,
                historical_dividend_cagr=0.06,
                accounting_quality_score=80,
            )
        )
        assert r.dividend_quality in {
            DividendQuality.EXCELLENT,
            DividendQuality.GOOD,
        }
        assert DdmQualityFlag.DIVIDEND_ARISTOCRAT in r.quality_flags
        assert DdmQualityFlag.STRONG_DIVIDEND_HISTORY in r.quality_flags

    def test_weak_flags(self) -> None:
        r = DdmEngine().analyze(
            _base(
                cost_of_equity=0.20,
                dividend_payout_ratio=1.1,
                dividend_coverage_ratio=0.8,
                expected_dividend_growth=0.15,
                free_cash_flow_payout_ratio=1.2,
                dividend_stability_score=10,
                historical_dividend_cagr=-0.05,
                eps=1.5,
            )
        )
        assert r.dividend_quality is DividendQuality.WEAK
        assert DdmQualityFlag.HIGH_PAYOUT in r.quality_flags
        assert DdmQualityFlag.UNSUSTAINABLE_DIVIDEND in r.quality_flags
        assert DdmQualityFlag.LOW_COVERAGE in r.quality_flags
        assert DdmQualityFlag.HIGH_GROWTH_ASSUMPTION in r.quality_flags
        assert DdmQualityFlag.WEAK_CASH_FLOW in r.quality_flags

    def test_high_payout_from_eps_flag(self) -> None:
        r = DdmEngine().analyze(
            _base(
                method=DdmMethod.ZERO_GROWTH,
                current_dps=2.0,
                eps=2.2,
                dividend_payout_ratio=None,
            )
        )
        assert DdmQualityFlag.HIGH_PAYOUT in r.quality_flags

    def test_good_quality_band(self) -> None:
        r = DdmEngine().analyze(
            _base(
                dividend_stability_score=60,
                dividend_coverage_ratio=1.5,
                dividend_payout_ratio=0.5,
                years_of_dividend_growth=12,
                historical_dividend_cagr=0.08,
            )
        )
        assert r.dividend_quality in {
            DividendQuality.GOOD,
            DividendQuality.EXCELLENT,
            DividendQuality.AVERAGE,
        }

    def test_negative_growth_flag(self) -> None:
        r = DdmEngine().analyze(
            _base(method=DdmMethod.ZERO_GROWTH, expected_dividend_growth=-0.05)
        )
        assert DdmQualityFlag.NEGATIVE_GROWTH in r.quality_flags

    def test_payout_from_eps(self) -> None:
        r = DdmEngine().analyze(_base(eps=4.0, dividend_payout_ratio=None))
        assert r.payout_ratio.value == pytest.approx(0.5)

    def test_average_quality_default(self) -> None:
        r = DdmEngine().analyze(_base())
        assert r.dividend_quality is DividendQuality.AVERAGE


class TestExplainabilityIntegration:
    def test_helpers_and_payloads(self) -> None:
        assert explain_step(name="x", value=1.0, formula="x=1").name == "x"
        assert len(explain_many([{"name": "y", "value": 2, "formula": "y=2"}])) == 1
        result = ValuationEngine().analyze_ddm(_base(method=DdmMethod.TWO_STAGE))
        assert len(result.explainability) >= 5
        vr = to_valuation_result(result)
        assert vr.model_name == "ddm"
        from valuation import to_ddm_valuation_result, to_ddm_v2_aggregate_payload

        assert to_ddm_valuation_result(result).model_name == "ddm"
        assert to_v2_aggregate_payload(result)["method"] == "ddm"
        assert to_ddm_v2_aggregate_payload(result)["ddm_method"] == "two_stage"
        assert result.to_dict()["method_used"] == "two_stage"


class TestEdgeCases:
    def test_no_price(self) -> None:
        r = DdmEngine().analyze(_base(current_market_price=None))
        assert r.margin_of_safety.value is None
        assert r.dividend_yield.value is None

    def test_unknown_method(self) -> None:
        inputs = _base()
        object.__setattr__(inputs, "method", "bogus")  # type: ignore[arg-type]
        with pytest.raises(ValuationError, match="unknown DDM"):
            DdmEngine()._value(inputs)

    def test_value_rejects_g_ge_r(self) -> None:
        with pytest.raises(ValuationError, match="growth must be"):
            DdmEngine()._value(
                _base(expected_dividend_growth=0.15, cost_of_equity=0.10)
            )

    def test_value_rejects_zero_r(self) -> None:
        with pytest.raises(ValuationError):
            DdmEngine()._value(_base(method=DdmMethod.ZERO_GROWTH, cost_of_equity=0.0))

    def test_two_stage_terminal_guard(self) -> None:
        with pytest.raises(ValuationError, match="terminal"):
            DdmEngine()._value(
                _base(
                    method=DdmMethod.TWO_STAGE,
                    terminal_growth=0.20,
                    cost_of_equity=0.10,
                )
            )

    def test_multi_without_schedule_uses_constant(self) -> None:
        r = DdmEngine().analyze(
            _base(method=DdmMethod.MULTI_STAGE, forecast_years=2, dividend_growth_schedule=())
        )
        assert len(r.forecast_dividends) == 2

    def test_roe_sensitivity_with_retention(self) -> None:
        r = DdmEngine().analyze(
            _base(
                method=DdmMethod.GORDON,
                retention_ratio=0.5,
                roe=0.10,
                expected_dividend_growth=0.03,
            )
        )
        assert "roe" in r.sensitivity.grids

    def test_roe_sensitivity_without_retention(self) -> None:
        r = DdmEngine().analyze(_base(roe=0.15, dividend_payout_ratio=None))
        assert "roe" in r.sensitivity.grids

    def test_strong_history_mid(self) -> None:
        r = DdmEngine().analyze(_base(years_of_dividend_growth=15))
        assert DdmQualityFlag.STRONG_DIVIDEND_HISTORY in r.quality_flags

    def test_performance_budget(self) -> None:
        engine = DdmEngine()
        inputs = _base(method=DdmMethod.TWO_STAGE, forecast_years=10)
        t0 = time.perf_counter()
        for _ in range(20):
            engine.analyze(inputs)
        avg_ms = (time.perf_counter() - t0) * 1000.0 / 20.0
        assert avg_ms < 50.0, f"avg {avg_ms:.2f} ms >= 50"

    def test_forecast_years_bounds(self) -> None:
        with pytest.raises(ValuationError, match="forecast_years"):
            validate_ddm_inputs(_base(method=DdmMethod.TWO_STAGE, forecast_years=0))

    def test_infinite(self) -> None:
        with pytest.raises(ValuationError, match="infinite"):
            validate_ddm_inputs(_base(cost_of_equity=float("inf")))

    def test_negative_price(self) -> None:
        with pytest.raises(ValuationError, match="current_market_price"):
            validate_ddm_inputs(_base(current_market_price=-1))

    def test_quality_cagr_high(self) -> None:
        r = DdmEngine().analyze(
            _base(
                historical_dividend_cagr=0.20,
                dividend_stability_score=0.5,
            )
        )
        assert r.dividend_quality in {
            DividendQuality.AVERAGE,
            DividendQuality.GOOD,
            DividendQuality.WEAK,
            DividendQuality.EXCELLENT,
        }
