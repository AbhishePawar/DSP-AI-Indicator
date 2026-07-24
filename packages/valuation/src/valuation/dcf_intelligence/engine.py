"""DCF Intelligence Engine — domain orchestrator (V1.2)."""

from __future__ import annotations

from dataclasses import dataclass

from valuation.dcf_intelligence.assumptions import (
    CapmInputs,
    CapitalStructure,
    CostOfDebtInputs,
    DcfBridgeInputs,
    DcfForecastAssumptions,
    DcfMarketInputs,
    DcfSensitivitySpec,
    DcfTerminalAssumptions,
)
from valuation.dcf_intelligence.equity import EquityBridgeResult, compute_equity_bridge
from valuation.dcf_intelligence.explain import ExplainedValue
from valuation.dcf_intelligence.forecast import ForecastResult, build_fcff_forecast
from valuation.dcf_intelligence.margin import (
    MarginOfSafetyResult,
    compute_margin_of_safety,
)
from valuation.dcf_intelligence.present_value import (
    PresentValueResult,
    compute_present_values,
)
from valuation.dcf_intelligence.sensitivity import (
    SensitivityMatrix,
    build_sensitivity_matrix,
)
from valuation.dcf_intelligence.terminal import (
    TerminalValueResult,
    compute_terminal_value,
)
from valuation.dcf_intelligence.wacc import WaccResult, compute_wacc
from valuation.exceptions import ValuationError

__all__ = [
    "DcfAnalysisInputs",
    "DiscountedCashFlowResult",
    "DiscountedCashFlowEngine",
]

DCF_INTELLIGENCE_VERSION = "0.2.0-dcf-intelligence"


@dataclass(frozen=True, slots=True)
class DcfAnalysisInputs:
    """Complete input aggregate for one DCF run."""

    forecast: DcfForecastAssumptions
    capm: CapmInputs
    cost_of_debt: CostOfDebtInputs
    capital_structure: CapitalStructure
    terminal: DcfTerminalAssumptions = DcfTerminalAssumptions()
    bridge: DcfBridgeInputs = DcfBridgeInputs()
    market: DcfMarketInputs = DcfMarketInputs()
    sensitivity: DcfSensitivitySpec = DcfSensitivitySpec()
    currency: str = "USD"


@dataclass(frozen=True, slots=True)
class DiscountedCashFlowResult:
    """Full explained DCF valuation result."""

    version: str
    currency: str
    wacc: WaccResult
    forecast: ForecastResult
    terminal: TerminalValueResult
    present_value: PresentValueResult
    equity: EquityBridgeResult
    margin_of_safety: MarginOfSafetyResult
    sensitivity: SensitivityMatrix
    explained_fields: tuple[ExplainedValue, ...]
    methodology: str
    limitations: tuple[str, ...]


_METHODOLOGY = (
    "DCF Intelligence (FCFF): CAPM WACC; explicit FCFF forecast "
    "FCFF=EBIT(1−t)+D&A−CapEx−ΔNWC; Gordon and/or Exit Multiple terminal; "
    "EV=ΣPV(FCFF)+PV(TV); Equity=EV−Debt−Minority+Cash+Investments; "
    "MoS research posture from (intrinsic−market)/intrinsic."
)

_LIMITATIONS = (
    "Research posture MoS bands are not trade recommendations",
    "Exit multiple is optional and medium-confidence",
    "Historical FCF is contextual; forecast uses explicit drivers",
    "Does not enable Overall Valuation aggregation by itself",
    "Deterministic; no Monte Carlo or AI opinions",
)


class DiscountedCashFlowEngine:
    """Domain DCF Intelligence Engine — pure, deterministic, explainable."""

    version = DCF_INTELLIGENCE_VERSION

    def analyze(self, inputs: DcfAnalysisInputs) -> DiscountedCashFlowResult:
        """Run full DCF with validation and explainability.

        Raises:
            ValuationError: On impossible assumptions or non-computable paths.
        """
        if inputs.terminal.perpetual_growth >= 0.99:
            raise ValuationError("impossible perpetual_growth")

        wacc = compute_wacc(
            capm=inputs.capm,
            debt=inputs.cost_of_debt,
            structure=inputs.capital_structure,
            tax_rate=inputs.forecast.tax_rate,
        )
        assert wacc.wacc.value is not None
        wacc_value = float(wacc.wacc.value)

        if wacc_value <= inputs.terminal.perpetual_growth and inputs.terminal.method in {
            "gordon",
            "both",
        }:
            raise ValuationError(
                "WACC must exceed perpetual growth for Gordon terminal value"
            )

        forecast = build_fcff_forecast(inputs.forecast)
        terminal = compute_terminal_value(
            last_fcff=forecast.last_fcff,
            last_ebitda=forecast.last_ebitda,
            wacc=wacc_value,
            assumptions=inputs.terminal,
        )
        assert terminal.blended_value.value is not None
        tv = float(terminal.blended_value.value)

        present = compute_present_values(
            lines=forecast.lines,
            terminal_value=tv,
            wacc=wacc_value,
        )
        assert present.enterprise_value.value is not None
        ev = float(present.enterprise_value.value)

        equity = compute_equity_bridge(enterprise_value=ev, bridge=inputs.bridge)
        assert equity.equity_value.value is not None
        equity_value = float(equity.equity_value.value)

        mos = compute_margin_of_safety(
            intrinsic_equity_value=equity_value,
            intrinsic_per_share=equity.intrinsic_value_per_share.value,
            market=inputs.market,
        )

        def _core(
            forecast_a: DcfForecastAssumptions,
            terminal_a: DcfTerminalAssumptions,
            w: float,
        ) -> tuple[float, float, float | None]:
            f = build_fcff_forecast(forecast_a)
            t = compute_terminal_value(
                last_fcff=f.last_fcff,
                last_ebitda=f.last_ebitda,
                wacc=w,
                assumptions=terminal_a,
            )
            assert t.blended_value.value is not None
            pv = compute_present_values(
                lines=f.lines,
                terminal_value=float(t.blended_value.value),
                wacc=w,
            )
            assert pv.enterprise_value.value is not None
            ev_i = float(pv.enterprise_value.value)
            eq = compute_equity_bridge(enterprise_value=ev_i, bridge=inputs.bridge)
            assert eq.equity_value.value is not None
            return (
                ev_i,
                float(eq.equity_value.value),
                eq.intrinsic_value_per_share.value,
            )

        sensitivity = build_sensitivity_matrix(
            base_forecast=inputs.forecast,
            base_terminal=inputs.terminal,
            base_wacc=wacc_value,
            base_bridge_equity_fn=_core,
            spec=inputs.sensitivity,
        )

        explained: list[ExplainedValue] = [
            *wacc.explained,
            forecast.historical_fcf_explained,
            *[line.explained for line in forecast.lines],
            terminal.blended_value,
            present.sum_pv_fcff,
            present.pv_terminal,
            present.enterprise_value,
            present.terminal_share_of_ev,
            equity.equity_value,
            equity.intrinsic_value_per_share,
            mos.ratio,
            mos.classification_explained,
            sensitivity.explained,
        ]
        if terminal.gordon_value is not None:
            explained.append(terminal.gordon_value)
        if terminal.exit_multiple_value is not None:
            explained.append(terminal.exit_multiple_value)

        return DiscountedCashFlowResult(
            version=self.version,
            currency=inputs.currency,
            wacc=wacc,
            forecast=forecast,
            terminal=terminal,
            present_value=present,
            equity=equity,
            margin_of_safety=mos,
            sensitivity=sensitivity,
            explained_fields=tuple(explained),
            methodology=_METHODOLOGY,
            limitations=_LIMITATIONS,
        )
