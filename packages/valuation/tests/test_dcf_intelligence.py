"""Deterministic unit tests for DCF Intelligence Engine (V1.2)."""

from __future__ import annotations

import pytest

from valuation import (
    CapmInputs,
    CapitalStructure,
    CostOfDebtInputs,
    DcfAnalysisInputs,
    DcfBridgeInputs,
    DcfForecastAssumptions,
    DcfMarketInputs,
    DcfMosClassification,
    DcfTerminalAssumptions,
    DiscountedCashFlowEngine,
    HistoricalFcfPoint,
    ValuationEngine,
    ValuationError,
)
from valuation.dcf_intelligence.terminal import compute_terminal_value
from valuation.dcf_intelligence.wacc import compute_wacc


def _base_inputs(**kwargs: object) -> DcfAnalysisInputs:
    data = dict(
        forecast=DcfForecastAssumptions(
            base_revenue=1000.0,
            revenue_growth=0.05,
            operating_margin=0.20,
            tax_rate=0.25,
            depreciation_pct_of_revenue=0.04,
            capex_pct_of_revenue=0.06,
            nwc_pct_of_revenue=0.10,
            forecast_years=10,
            historical_fcf=(
                HistoricalFcfPoint("2022", 80.0),
                HistoricalFcfPoint("2023", 90.0),
            ),
        ),
        capm=CapmInputs(
            risk_free_rate=0.04,
            beta=1.0,
            equity_risk_premium=0.05,
        ),
        cost_of_debt=CostOfDebtInputs(pre_tax_cost_of_debt=0.06),
        capital_structure=CapitalStructure(equity_weight=0.7, debt_weight=0.3),
        terminal=DcfTerminalAssumptions(method="gordon", perpetual_growth=0.02),
        bridge=DcfBridgeInputs(
            cash=50.0,
            total_debt=100.0,
            minority_interest=10.0,
            non_operating_investments=20.0,
            shares_outstanding=10.0,
        ),
        market=DcfMarketInputs(equity_market_cap=800.0),
        currency="USD",
    )
    data.update(kwargs)
    return DcfAnalysisInputs(**data)  # type: ignore[arg-type]


class TestWacc:
    def test_capm_and_wacc_deterministic(self) -> None:
        result = compute_wacc(
            capm=CapmInputs(0.04, 1.0, 0.05),
            debt=CostOfDebtInputs(0.06),
            structure=CapitalStructure(equity_weight=0.7, debt_weight=0.3),
            tax_rate=0.25,
        )
        # re = 0.04 + 1*0.05 = 0.09
        # rd_at = 0.06 * 0.75 = 0.045
        # wacc = 0.7*0.09 + 0.3*0.045 = 0.063 + 0.0135 = 0.0765
        assert result.cost_of_equity.value == pytest.approx(0.09)
        assert result.cost_of_debt_after_tax.value == pytest.approx(0.045)
        assert result.wacc.value == pytest.approx(0.0765)
        assert result.wacc.formula
        assert "re" in result.cost_of_equity.formula


class TestTerminalValue:
    def test_gordon(self) -> None:
        tv = compute_terminal_value(
            last_fcff=100.0,
            last_ebitda=150.0,
            wacc=0.10,
            assumptions=DcfTerminalAssumptions(method="gordon", perpetual_growth=0.02),
        )
        # 100*1.02 / 0.08 = 1275
        assert tv.blended_value.value == pytest.approx(1275.0)

    def test_exit_multiple(self) -> None:
        tv = compute_terminal_value(
            last_fcff=100.0,
            last_ebitda=150.0,
            wacc=0.10,
            assumptions=DcfTerminalAssumptions(
                method="exit_multiple",
                perpetual_growth=0.02,
                exit_ebitda_multiple=10.0,
            ),
        )
        assert tv.blended_value.value == pytest.approx(1500.0)

    def test_gordon_requires_spread(self) -> None:
        with pytest.raises(ValuationError):
            compute_terminal_value(
                last_fcff=100.0,
                last_ebitda=150.0,
                wacc=0.02,
                assumptions=DcfTerminalAssumptions(
                    method="gordon", perpetual_growth=0.02
                ),
            )


class TestDcfEngine:
    def test_full_run_deterministic(self) -> None:
        engine = DiscountedCashFlowEngine()
        first = engine.analyze(_base_inputs())
        second = engine.analyze(_base_inputs())
        assert first.present_value.enterprise_value.value == pytest.approx(
            second.present_value.enterprise_value.value
        )
        assert first.equity.equity_value.value == pytest.approx(
            second.equity.equity_value.value
        )
        assert first.equity.intrinsic_value_per_share.value is not None
        assert len(first.forecast.lines) == 10
        assert first.forecast.historical_fcf_explained.value == pytest.approx(85.0)
        assert first.wacc.wacc.value == pytest.approx(0.0765)
        assert len(first.explained_fields) > 10
        for field in first.explained_fields:
            assert field.formula
            assert field.confidence in {"high", "medium", "low", "insufficient"}

    def test_margin_of_safety_classification(self) -> None:
        # Large intrinsic vs small market → strong cushion
        result = DiscountedCashFlowEngine().analyze(
            _base_inputs(market=DcfMarketInputs(equity_market_cap=100.0))
        )
        assert result.margin_of_safety.ratio.value is not None
        assert result.margin_of_safety.ratio.value > 0.4
        assert (
            result.margin_of_safety.classification
            is DcfMosClassification.STRONG_BUY
        )
        assert "NOT a Buy/Sell" in result.margin_of_safety.disclaimer

    def test_overvalued_band(self) -> None:
        result = DiscountedCashFlowEngine().analyze(
            _base_inputs(market=DcfMarketInputs(equity_market_cap=1_000_000.0))
        )
        assert (
            result.margin_of_safety.classification
            is DcfMosClassification.OVERVALUED
        )

    def test_sensitivity_matrix(self) -> None:
        result = DiscountedCashFlowEngine().analyze(_base_inputs())
        assert len(result.sensitivity.growth) >= 1
        assert len(result.sensitivity.wacc) >= 1
        assert len(result.sensitivity.terminal_growth) >= 1

    def test_rejects_impossible_growth(self) -> None:
        with pytest.raises(ValuationError):
            DcfForecastAssumptions(
                base_revenue=1000,
                revenue_growth=0.9,
                operating_margin=0.2,
                tax_rate=0.25,
                depreciation_pct_of_revenue=0.04,
                capex_pct_of_revenue=0.06,
                nwc_pct_of_revenue=0.1,
            )

    def test_valuation_engine_integration(self) -> None:
        ve = ValuationEngine()
        result = ve.analyze_dcf(_base_inputs())
        assert result.version.startswith("0.2.0")
        assert result.present_value.enterprise_value.value is not None
