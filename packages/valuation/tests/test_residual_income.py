"""Tests for Residual Income Valuation enhancements (V1.4 best practices)."""

from __future__ import annotations

import time

import pytest

from valuation import (
    RESEARCH_DISCLAIMER,
    ResidualIncomeEngine,
    ResidualIncomeInputs,
    ResidualIncomeScenario,
    RiQualityFlag,
    RoeForecastModel,
    ValuationEngine,
    ValuationError,
    to_v2_aggregate_payload,
    validate_residual_income_inputs,
    verify_clean_surplus,
)


def _inputs(**kwargs: object) -> ResidualIncomeInputs:
    data = dict(
        current_book_value=1000.0,
        roe_forecast=0.15,
        cost_of_equity=0.10,
        net_income_forecast=150.0,
        dividend_payout_ratio=0.40,
        forecast_years=10,
        terminal_growth=0.02,
        shares_outstanding=100.0,
        current_market_price=12.0,
        currency="USD",
    )
    data.update(kwargs)
    return ResidualIncomeInputs(**data)  # type: ignore[arg-type]


class TestValidation:
    def test_rejects_roe_bounds(self) -> None:
        with pytest.raises(ValuationError, match="ROE"):
            validate_residual_income_inputs(_inputs(roe_forecast=1.5))
        with pytest.raises(ValuationError, match="ROE"):
            validate_residual_income_inputs(_inputs(roe_forecast=-0.6))

    def test_rejects_zero_book(self) -> None:
        with pytest.raises(ValuationError, match="book value"):
            validate_residual_income_inputs(_inputs(current_book_value=0.0))

    def test_rejects_manual_without_series(self) -> None:
        with pytest.raises(ValuationError, match="roe_manual_series"):
            validate_residual_income_inputs(
                _inputs(roe_model=RoeForecastModel.MANUAL, roe_manual_series=None)
            )

    def test_rejects_manual_length(self) -> None:
        with pytest.raises(ValuationError, match="length"):
            validate_residual_income_inputs(
                _inputs(
                    roe_model=RoeForecastModel.MANUAL,
                    forecast_years=5,
                    roe_manual_series=(0.1, 0.1),
                )
            )

    def test_rejects_linear_fade_without_terminal(self) -> None:
        with pytest.raises(ValuationError, match="LINEAR_FADE"):
            validate_residual_income_inputs(
                _inputs(roe_model=RoeForecastModel.LINEAR_FADE, terminal_roe=None)
            )

    def test_rejects_bad_kappa(self) -> None:
        with pytest.raises(ValuationError, match="mean_reversion_kappa"):
            validate_residual_income_inputs(_inputs(mean_reversion_kappa=0.0))

    def test_rejects_bad_aq_score(self) -> None:
        with pytest.raises(ValuationError, match="accounting_quality"):
            validate_residual_income_inputs(_inputs(accounting_quality_score=120))

    def test_ni_roe_warning(self) -> None:
        summary = validate_residual_income_inputs(
            _inputs(net_income_forecast=50.0, roe_forecast=0.15)
        )
        assert summary.warnings
        assert "ROE" in summary.warnings[0]


class TestCleanSurplus:
    def test_identity_holds(self) -> None:
        result = ResidualIncomeEngine().analyze(_inputs())
        assert result.clean_surplus_ok is True
        for y in result.years:
            assert y.clean_surplus.ok is True
            assert y.ending_book_value == pytest.approx(
                y.opening_book_value + y.net_income - y.dividends
            )

    def test_verify_helper_detects_violation(self) -> None:
        check = verify_clean_surplus(
            year=1,
            opening_book_value=100.0,
            net_income=10.0,
            dividends=4.0,
            ending_book_value=99.0,  # should be 106
        )
        assert check.ok is False
        assert check.residual == pytest.approx(7.0)


class TestRoeModels:
    def test_constant(self) -> None:
        r = ResidualIncomeEngine().analyze(
            _inputs(roe_model=RoeForecastModel.CONSTANT)
        )
        assert all(abs(y.roe - 0.15) < 1e-12 for y in r.years)

    def test_linear_fade(self) -> None:
        r = ResidualIncomeEngine().analyze(
            _inputs(
                roe_model=RoeForecastModel.LINEAR_FADE,
                terminal_roe=0.10,
                net_income_forecast=None,
                forecast_years=5,
            )
        )
        assert r.years[0].roe == pytest.approx(0.15 + (0.10 - 0.15) * (1 / 5))
        assert r.years[-1].roe == pytest.approx(0.10)

    def test_mean_reversion(self) -> None:
        r = ResidualIncomeEngine().analyze(
            _inputs(
                roe_model=RoeForecastModel.MEAN_REVERSION,
                roe_long_run=0.10,
                mean_reversion_kappa=0.5,
                net_income_forecast=None,
                forecast_years=4,
            )
        )
        assert r.years[0].roe < 0.15
        assert r.years[-1].roe < r.years[0].roe or r.years[-1].roe == pytest.approx(
            r.years[0].roe, abs=1e-9
        )

    def test_manual(self) -> None:
        series = (0.20, 0.18, 0.16, 0.14, 0.12)
        r = ResidualIncomeEngine().analyze(
            _inputs(
                roe_model=RoeForecastModel.MANUAL,
                forecast_years=5,
                roe_manual_series=series,
                net_income_forecast=None,
            )
        )
        assert tuple(y.roe for y in r.years) == series


class TestCore:
    def test_known_positive_spread(self) -> None:
        result = ResidualIncomeEngine().analyze(_inputs())
        assert result.intrinsic_equity_value.value is not None
        assert result.intrinsic_equity_value.value > 1000.0
        assert result.years[0].residual_income == pytest.approx(50.0)
        assert result.continuing_value_pv.value is not None

    def test_deterministic(self) -> None:
        a = ResidualIncomeEngine().analyze(_inputs())
        b = ResidualIncomeEngine().analyze(_inputs())
        assert a.intrinsic_equity_value.value == pytest.approx(
            b.intrinsic_equity_value.value
        )

    def test_disclaimer(self) -> None:
        result = ResidualIncomeEngine().analyze(_inputs())
        assert result.disclaimer == RESEARCH_DISCLAIMER
        assert "not investment advice" in result.disclaimer.lower()

    def test_performance_budget(self) -> None:
        eng = ResidualIncomeEngine()
        # warm-up
        eng.analyze(_inputs())
        t0 = time.perf_counter()
        for _ in range(20):
            eng.analyze(_inputs())
        elapsed_ms = (time.perf_counter() - t0) * 1000 / 20
        assert elapsed_ms < 50.0


class TestScenariosSensitivity:
    def test_scenarios(self) -> None:
        result = ResidualIncomeEngine().analyze(_inputs())
        by = {s.scenario: s for s in result.scenarios}
        assert set(by) == {
            ResidualIncomeScenario.BEAR,
            ResidualIncomeScenario.BASE,
            ResidualIncomeScenario.BULL,
        }

    def test_sensitivity_includes_payout_and_troe(self) -> None:
        result = ResidualIncomeEngine().analyze(_inputs(terminal_roe=0.12))
        assert len(result.sensitivity.payout_ratio) == 3
        assert len(result.sensitivity.terminal_roe) == 3
        assert len(result.sensitivity.roe) == 3


class TestQualityAndConfidence:
    def test_quality_flags(self) -> None:
        result = ResidualIncomeEngine().analyze(
            _inputs(
                roe_forecast=0.20,
                accounting_quality_score=30.0,
                net_income_forecast=None,
            )
        )
        assert RiQualityFlag.ACCOUNTING_WARNING in result.quality_flags
        assert result.confidence_detail.rationale

    def test_declining_roe_flag(self) -> None:
        result = ResidualIncomeEngine().analyze(
            _inputs(
                roe_model=RoeForecastModel.LINEAR_FADE,
                terminal_roe=0.05,
                net_income_forecast=None,
                forecast_years=5,
            )
        )
        assert RiQualityFlag.DECLINING_ROE in result.quality_flags

    def test_ni_inconsistency_reduces_confidence(self) -> None:
        result = ResidualIncomeEngine().analyze(
            _inputs(net_income_forecast=50.0, roe_forecast=0.15)
        )
        assert result.clean_surplus_warnings
        assert result.confidence in {"medium", "low"}


class TestAggregationExtensibility:
    def test_v2_payload(self) -> None:
        result = ResidualIncomeEngine().analyze(_inputs())
        payload = to_v2_aggregate_payload(result)
        assert payload["method"] == "residual_income"
        assert payload["intrinsic_equity_value"] == result.intrinsic_equity_value.value
        assert payload["disclaimer"] == RESEARCH_DISCLAIMER


class TestIntegration:
    def test_valuation_engine(self) -> None:
        ve = ValuationEngine()
        result = ve.analyze_residual_income(_inputs())
        assert result.version.startswith("0.4.1")


class TestEdgeCases:
    def test_ending_bv_non_positive(self) -> None:
        from valuation.residual_income.residual_income_engine import _run_core

        with pytest.raises(ValuationError, match="ending book value"):
            _run_core(
                _inputs(
                    dividend_payout_ratio=0.0,
                    net_income_forecast=None,
                    forecast_years=1,
                    roe_model=RoeForecastModel.CONSTANT,
                ),
                roe_shift=-1.65,
            )

    def test_retention_override(self) -> None:
        r = ResidualIncomeEngine().analyze(_inputs(retention_ratio=0.7))
        assert r.book_value.intermediates["retention"] == pytest.approx(0.7)

    def test_aq_score_bands(self) -> None:
        from valuation.residual_income.residual_income_engine import _confidence_detail

        high = _confidence_detail(
            _inputs(accounting_quality_score=80.0),
            clean_surplus_ok=True,
            years=ResidualIncomeEngine().analyze(_inputs()).years,
        )
        assert high.factors["accounting_quality"] == 2
        mid = _confidence_detail(
            _inputs(accounting_quality_score=50.0),
            clean_surplus_ok=True,
            years=ResidualIncomeEngine().analyze(_inputs()).years,
        )
        assert mid.factors["accounting_quality"] == 1

    def test_negative_ri_and_weak_bv(self) -> None:
        result = ResidualIncomeEngine().analyze(
            _inputs(
                roe_forecast=0.05,
                cost_of_equity=0.12,
                dividend_payout_ratio=1.0,
                net_income_forecast=None,
                forecast_years=5,
            )
        )
        assert RiQualityFlag.NEGATIVE_RESIDUAL_INCOME in result.quality_flags

    def test_weak_book_value_growth_flag(self) -> None:
        # Negative ROE with zero payout shrinks book
        result = ResidualIncomeEngine().analyze(
            _inputs(
                roe_forecast=-0.10,
                cost_of_equity=0.10,
                dividend_payout_ratio=0.0,
                net_income_forecast=None,
                forecast_years=5,
            )
        )
        assert RiQualityFlag.WEAK_BOOK_VALUE_GROWTH in result.quality_flags

    def test_clean_surplus_branch_via_monkeypatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from valuation.residual_income import residual_income_engine as mod
        from valuation.residual_income.residual_income_models import CleanSurplusCheck

        def bad_cs(**kwargs: object) -> CleanSurplusCheck:
            return CleanSurplusCheck(
                year=int(kwargs["year"]),  # type: ignore[arg-type]
                opening_book_value=float(kwargs["opening_book_value"]),  # type: ignore[arg-type]
                net_income=float(kwargs["net_income"]),  # type: ignore[arg-type]
                dividends=float(kwargs["dividends"]),  # type: ignore[arg-type]
                ending_book_value=float(kwargs["ending_book_value"]),  # type: ignore[arg-type]
                implied_ending=0.0,
                residual=99.0,
                ok=False,
            )

        monkeypatch.setattr(mod, "verify_clean_surplus", bad_cs)
        result = ResidualIncomeEngine().analyze(_inputs(net_income_forecast=None))
        assert result.clean_surplus_ok is False
        assert any("clean surplus" in w.lower() for w in result.clean_surplus_warnings)

    def test_sensitivity_bounds_and_skips(self) -> None:
        result = ResidualIncomeEngine().analyze(
            _inputs(
                roe_forecast=0.99,
                cost_of_equity=0.025,
                terminal_growth=0.02,
                terminal_roe=0.99,
            )
        )
        assert any(c.intrinsic_equity_value is None for c in result.sensitivity.roe)
        assert any(
            c.intrinsic_equity_value is None for c in result.sensitivity.cost_of_equity
        )

    def test_sensitivity_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from valuation.residual_income import residual_income_engine as mod

        def boom(*_a, **_k):
            raise ValuationError("forced")

        monkeypatch.setattr(mod, "_run_core", boom)
        matrix = mod._sensitivity(_inputs())
        assert all(c.intrinsic_equity_value is None for c in matrix.roe)

    def test_cv_guard(self) -> None:
        from valuation.residual_income.residual_income_engine import _run_core

        with pytest.raises(ValuationError, match="exceed terminal"):
            _run_core(_inputs(cost_of_equity=0.02, terminal_growth=0.02))

    def test_mos_paths(self) -> None:
        from valuation.residual_income.residual_income_engine import _mos

        assert _mos(1000.0, None, _inputs(current_market_price=None), "low").value is None
        assert _mos(0.0, None, _inputs(current_market_price=10.0), "low").value is None
        mos = _mos(1000.0, None, _inputs(current_market_price=5.0), "medium")
        assert mos.value == pytest.approx(0.5)

    def test_explainability_rejects(self) -> None:
        from core.exceptions import ValidationError
        from valuation.residual_income.residual_income_explainability import (
            RiExplainedValue,
        )

        with pytest.raises(ValidationError):
            RiExplainedValue(" ", 1.0, "f", {}, {}, "high")
        with pytest.raises(ValidationError):
            RiExplainedValue("n", 1.0, " ", {}, {}, "high")
        with pytest.raises(ValidationError):
            RiExplainedValue("n", 1.0, "f", {}, {}, "bad")

    def test_validation_misc(self) -> None:
        with pytest.raises(ValuationError, match="NaN"):
            validate_residual_income_inputs(_inputs(roe_forecast=float("nan")))
        with pytest.raises(ValuationError, match="infinite"):
            validate_residual_income_inputs(_inputs(current_book_value=float("inf")))
        with pytest.raises(ValuationError, match="shares"):
            validate_residual_income_inputs(_inputs(shares_outstanding=-1))
        with pytest.raises(ValuationError, match="payout"):
            validate_residual_income_inputs(_inputs(dividend_payout_ratio=2))
        with pytest.raises(ValuationError, match="retention"):
            validate_residual_income_inputs(_inputs(retention_ratio=2))
        with pytest.raises(ValuationError, match="forecast_years"):
            validate_residual_income_inputs(_inputs(forecast_years=0))
        with pytest.raises(ValuationError, match="terminal_roe"):
            validate_residual_income_inputs(_inputs(terminal_roe=2))
        with pytest.raises(ValuationError, match="market_price"):
            validate_residual_income_inputs(_inputs(current_market_price=-1))
        with pytest.raises(ValuationError, match="cost_of_equity"):
            validate_residual_income_inputs(_inputs(cost_of_equity=0))
        with pytest.raises(ValuationError, match="terminal_growth"):
            validate_residual_income_inputs(
                _inputs(terminal_growth=0.2, cost_of_equity=0.1)
            )

    def test_low_confidence_path(self) -> None:
        from valuation.residual_income.residual_income_engine import _confidence_detail

        detail = _confidence_detail(
            _inputs(
                forecast_years=2,
                current_market_price=None,
                net_income_forecast=None,
                accounting_quality_score=10.0,
                roe_forecast=0.9,
                cost_of_equity=0.30,
                historical_roe_series=(0.01, 0.9),
            ),
            clean_surplus_ok=False,
            years=(),
        )
        assert detail.level == "low"

    def test_warning_reduces_high_to_medium(self) -> None:
        # NI mismatch warning with otherwise rich inputs
        result = ResidualIncomeEngine().analyze(
            _inputs(
                net_income_forecast=50.0,
                accounting_quality_score=90.0,
                historical_roe_series=(0.14, 0.15, 0.15),
                forecast_years=10,
            )
        )
        assert result.clean_surplus_warnings
        assert result.confidence in {"medium", "low"}
