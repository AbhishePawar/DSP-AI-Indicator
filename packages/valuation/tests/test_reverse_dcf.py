"""Tests for Reverse DCF Intelligence (V1.3) — domain only."""

from __future__ import annotations

import math

import pytest

from valuation import (
    ReverseDcfEngine,
    ReverseDcfInputs,
    ReverseDcfScenario,
    ValuationEngine,
    ValuationError,
    validate_reverse_dcf_inputs,
)


def _inputs(**kwargs: object) -> ReverseDcfInputs:
    data = dict(
        current_share_price=50.0,
        shares_outstanding=10.0,
        cash=20.0,
        debt=30.0,
        minority_interest=0.0,
        investments=0.0,
        current_revenue=200.0,
        current_ebit=40.0,
        current_fcff=25.0,
        current_operating_margin=0.20,
        tax_rate=0.25,
        reinvestment_rate=0.30,
        forecast_years=10,
        terminal_growth=0.02,
        wacc=0.09,
        expected_margin_expansion=0.0,
        currency="USD",
        precision=1e-4,
        max_iterations=200,
    )
    data.update(kwargs)
    return ReverseDcfInputs(**data)  # type: ignore[arg-type]


class TestValidation:
    def test_rejects_negative_wacc(self) -> None:
        with pytest.raises(ValuationError, match="WACC"):
            validate_reverse_dcf_inputs(_inputs(wacc=-0.01))

    def test_rejects_terminal_ge_wacc(self) -> None:
        with pytest.raises(ValuationError, match="terminal_growth"):
            validate_reverse_dcf_inputs(_inputs(terminal_growth=0.10, wacc=0.09))

    def test_rejects_negative_shares(self) -> None:
        with pytest.raises(ValuationError, match="shares"):
            validate_reverse_dcf_inputs(_inputs(shares_outstanding=-1))

    def test_rejects_impossible_tax(self) -> None:
        with pytest.raises(ValuationError, match="tax_rate"):
            validate_reverse_dcf_inputs(_inputs(tax_rate=1.5))

    def test_rejects_nan(self) -> None:
        with pytest.raises(ValuationError, match="NaN"):
            validate_reverse_dcf_inputs(_inputs(wacc=float("nan")))

    def test_rejects_inf(self) -> None:
        with pytest.raises(ValuationError, match="infinite"):
            validate_reverse_dcf_inputs(_inputs(current_revenue=float("inf")))

    def test_rejects_negative_debt(self) -> None:
        with pytest.raises(ValuationError, match="capital structure"):
            validate_reverse_dcf_inputs(_inputs(debt=-5))


class TestSolver:
    def test_converges(self) -> None:
        result = ReverseDcfEngine().analyze(_inputs())
        assert result.solver.converged is True
        assert result.solver.iterations <= 200
        assert result.solver.residual_error <= 1e-4 or result.solver.stop_reason in {
            "precision_met",
            "bracket_width_met",
        }
        assert result.implied_revenue_cagr.value is not None
        assert math.isfinite(result.implied_revenue_cagr.value)

    def test_higher_price_implies_higher_growth(self) -> None:
        low = ReverseDcfEngine().analyze(_inputs(current_share_price=30.0))
        high = ReverseDcfEngine().analyze(_inputs(current_share_price=80.0))
        assert low.implied_revenue_cagr.value is not None
        assert high.implied_revenue_cagr.value is not None
        assert high.implied_revenue_cagr.value > low.implied_revenue_cagr.value

    def test_deterministic(self) -> None:
        a = ReverseDcfEngine().analyze(_inputs())
        b = ReverseDcfEngine().analyze(_inputs())
        assert a.implied_revenue_cagr.value == pytest.approx(
            b.implied_revenue_cagr.value
        )
        assert a.residual_error == pytest.approx(b.residual_error)


class TestScenarios:
    def test_bear_base_bull(self) -> None:
        result = ReverseDcfEngine().analyze(_inputs())
        scenarios = {s.scenario: s for s in result.scenarios}
        assert ReverseDcfScenario.BEAR in scenarios
        assert ReverseDcfScenario.BASE in scenarios
        assert ReverseDcfScenario.BULL in scenarios
        # Higher margin (bull) typically needs less growth for same EV
        bear_g = scenarios[ReverseDcfScenario.BEAR].implied_revenue_cagr.value
        bull_g = scenarios[ReverseDcfScenario.BULL].implied_revenue_cagr.value
        assert bear_g is not None and bull_g is not None
        assert bear_g >= bull_g - 1e-9


class TestSensitivity:
    def test_matrices_populated(self) -> None:
        result = ReverseDcfEngine().analyze(_inputs())
        assert len(result.sensitivity.wacc) == 3
        assert len(result.sensitivity.terminal_growth) == 3
        assert len(result.sensitivity.share_price) == 3
        assert result.sensitivity.explained.formula


class TestExplainability:
    def test_every_primary_field_explained(self) -> None:
        result = ReverseDcfEngine().analyze(_inputs())
        assert result.disclaimer
        assert "NOT a Buy/Sell" in result.disclaimer
        for field in result.explainability:
            assert field.formula
            assert field.confidence in {"high", "medium", "low"}
        assert result.implied_revenue_cagr.convergence_notes
        assert result.confidence in {"high", "medium", "low"}
        assert result.validation_summary.ok is True


class TestIntegration:
    def test_valuation_engine_analyze_reverse_dcf(self) -> None:
        ve = ValuationEngine()
        result = ve.analyze_reverse_dcf(_inputs())
        assert result.version.startswith("0.3.0")
        assert result.current_market_cap.value == pytest.approx(500.0)
        assert result.enterprise_value.value is not None

    def test_analyze_unchanged_still_callable(self) -> None:
        # Smoke: ValuationEngine still constructs; analyze_dcf path untouched
        ve = ValuationEngine()
        assert hasattr(ve, "analyze")
        assert hasattr(ve, "analyze_dcf")
        assert hasattr(ve, "analyze_reverse_dcf")


class TestEdgeCases:
    def test_zero_price_rejected_via_target_ev(self) -> None:
        # price 0 → equity 0 → EV may be debt-cash; still may solve or fail
        # Use tiny price with high cash making EV non-positive
        with pytest.raises(ValuationError):
            ReverseDcfEngine().analyze(
                _inputs(
                    current_share_price=0.0,
                    cash=1000.0,
                    debt=0.0,
                    investments=0.0,
                )
            )

    def test_roic_path(self) -> None:
        result = ReverseDcfEngine().analyze(
            _inputs(expected_roic=0.15, expected_margin_expansion=0.02)
        )
        assert result.implied_revenue_cagr.value is not None

    def test_negative_share_price(self) -> None:
        with pytest.raises(ValuationError, match="share_price"):
            validate_reverse_dcf_inputs(_inputs(current_share_price=-1))

    def test_expected_roic_nan(self) -> None:
        with pytest.raises(ValuationError, match="NaN"):
            validate_reverse_dcf_inputs(_inputs(expected_roic=float("nan")))

    def test_revenue_non_positive(self) -> None:
        with pytest.raises(ValuationError, match="current_revenue"):
            validate_reverse_dcf_inputs(_inputs(current_revenue=0))

    def test_forecast_years_range(self) -> None:
        with pytest.raises(ValuationError, match="forecast_years"):
            validate_reverse_dcf_inputs(_inputs(forecast_years=0))

    def test_growth_bounds(self) -> None:
        with pytest.raises(ValuationError, match="growth_low"):
            validate_reverse_dcf_inputs(_inputs(growth_low=0.2, growth_high=0.1))

    def test_precision_range(self) -> None:
        with pytest.raises(ValuationError, match="precision"):
            validate_reverse_dcf_inputs(_inputs(precision=0))

    def test_max_iterations_range(self) -> None:
        with pytest.raises(ValuationError, match="max_iterations"):
            validate_reverse_dcf_inputs(_inputs(max_iterations=0))

    def test_reinvestment_range(self) -> None:
        with pytest.raises(ValuationError, match="reinvestment"):
            validate_reverse_dcf_inputs(_inputs(reinvestment_rate=2.0))

    def test_sensitivity_skips_invalid_wacc(self) -> None:
        # terminal growth close to wacc → some deltas invalid
        result = ReverseDcfEngine().analyze(
            _inputs(wacc=0.025, terminal_growth=0.02)
        )
        assert len(result.sensitivity.wacc) == 3

    def test_explainability_rejects_empty(self) -> None:
        from core.exceptions import ValidationError
        from valuation.reverse_dcf.reverse_dcf_explainability import (
            ReverseExplainedValue,
        )

        with pytest.raises(ValidationError):
            ReverseExplainedValue(
                name=" ",
                value=1.0,
                formula="x",
                inputs={},
                intermediates={},
                confidence="high",
            )
        with pytest.raises(ValidationError):
            ReverseExplainedValue(
                name="x",
                value=1.0,
                formula=" ",
                inputs={},
                intermediates={},
                confidence="high",
            )
        with pytest.raises(ValidationError):
            ReverseExplainedValue(
                name="x",
                value=1.0,
                formula="y",
                inputs={},
                intermediates={},
                confidence="nope",
            )

    def test_low_confidence_path(self) -> None:
        # Sparse / extreme inputs still solve but may lower confidence
        result = ReverseDcfEngine().analyze(
            _inputs(
                current_fcff=0.0,
                current_ebit=0.0,
                current_operating_margin=0.9,
                precision=1e-4,
            )
        )
        assert result.confidence in {"high", "medium", "low"}

    def test_project_paths_wacc_guard(self) -> None:
        from valuation.reverse_dcf.reverse_dcf_engine import _project_paths

        bad = _inputs(wacc=0.02, terminal_growth=0.02)
        # Bypass validation by calling private projector directly
        with pytest.raises(ValuationError, match="WACC must exceed"):
            _project_paths(bad, 0.05)

    def test_bound_expansion_low_side(self) -> None:
        # Very cheap equity → need bound expansion toward high growth
        result = ReverseDcfEngine().analyze(
            _inputs(
                current_share_price=1.0,
                growth_low=-0.2,
                growth_high=0.2,
            )
        )
        assert result.implied_revenue_cagr.value is not None

    def test_bound_expansion_high_ev_low(self) -> None:
        # Very expensive relative to fundamentals may push low bound
        result = ReverseDcfEngine().analyze(
            _inputs(
                current_share_price=500.0,
                current_revenue=50.0,
                current_fcff=5.0,
                growth_low=-0.2,
                growth_high=0.2,
            )
        )
        assert result.implied_revenue_cagr.value is not None

    def test_confidence_low_branch(self) -> None:
        from valuation.reverse_dcf.reverse_dcf_engine import _confidence_score

        sparse = _inputs(
            current_fcff=0.0,
            current_ebit=0.0,
            current_operating_margin=0.9,
            current_share_price=0.0,
        )
        assert _confidence_score(sparse, residual=1.0) == "low"

    def test_sensitivity_exception_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from valuation.reverse_dcf import reverse_dcf_engine as mod

        def boom(*_a, **_k):
            raise ValuationError("forced")

        monkeypatch.setattr(mod, "_solve_growth", boom)
        # Still builds cells via except branches
        matrix = mod._sensitivity(_inputs(), target_ev=100.0)
        assert all(c.converged is False for c in matrix.wacc)
        assert all(c.converged is False for c in matrix.terminal_growth)
        assert all(c.converged is False for c in matrix.share_price)

    def test_solver_no_candidates(self) -> None:
        from valuation.reverse_dcf.reverse_dcf_engine import _solve_growth

        # Bypass public validation: zero iterations → no candidate evaluated
        with pytest.raises(ValuationError, match="failed to evaluate"):
            _solve_growth(_inputs(max_iterations=0))
