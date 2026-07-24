"""Assumptions and input aggregates for the DCF Intelligence Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from valuation.exceptions import ValuationError

__all__ = [
    "CapmInputs",
    "CapitalStructure",
    "CostOfDebtInputs",
    "DcfForecastAssumptions",
    "DcfBridgeInputs",
    "DcfMarketInputs",
    "DcfSensitivitySpec",
    "DcfTerminalAssumptions",
    "HistoricalFcfPoint",
    "TerminalMethod",
]

TerminalMethod = Literal["gordon", "exit_multiple", "both"]


@dataclass(frozen=True, slots=True)
class HistoricalFcfPoint:
    """One historical free-cash-flow observation."""

    period: str
    fcf: float


@dataclass(frozen=True, slots=True)
class CapmInputs:
    """CAPM inputs for cost of equity.

    ``re = risk_free_rate + beta * equity_risk_premium``
    """

    risk_free_rate: float
    beta: float
    equity_risk_premium: float

    def __post_init__(self) -> None:
        if self.risk_free_rate < -0.05 or self.risk_free_rate > 0.25:
            raise ValuationError(
                f"risk_free_rate out of range: {self.risk_free_rate}"
            )
        if self.beta <= 0 or self.beta > 5:
            raise ValuationError(f"beta out of range: {self.beta}")
        if self.equity_risk_premium <= 0 or self.equity_risk_premium > 0.20:
            raise ValuationError(
                f"equity_risk_premium out of range: {self.equity_risk_premium}"
            )


@dataclass(frozen=True, slots=True)
class CostOfDebtInputs:
    """Pre-tax cost of debt."""

    pre_tax_cost_of_debt: float

    def __post_init__(self) -> None:
        if self.pre_tax_cost_of_debt < 0 or self.pre_tax_cost_of_debt > 0.40:
            raise ValuationError(
                "pre_tax_cost_of_debt out of range: "
                f"{self.pre_tax_cost_of_debt}"
            )


@dataclass(frozen=True, slots=True)
class CapitalStructure:
    """Market-value capital structure weights.

    Either provide equity/debt market values, or explicit weights that
    sum to 1.0.
    """

    equity_market_value: float | None = None
    debt_market_value: float | None = None
    equity_weight: float | None = None
    debt_weight: float | None = None

    def __post_init__(self) -> None:
        has_values = (
            self.equity_market_value is not None
            and self.debt_market_value is not None
        )
        has_weights = self.equity_weight is not None and self.debt_weight is not None
        if not has_values and not has_weights:
            raise ValuationError(
                "CapitalStructure requires market values or explicit weights"
            )
        if has_values:
            eq = float(self.equity_market_value)  # type: ignore[arg-type]
            deb = float(self.debt_market_value)  # type: ignore[arg-type]
            if eq < 0 or deb < 0:
                raise ValuationError("capital structure market values must be >= 0")
            if eq + deb <= 0:
                raise ValuationError("equity + debt market values must be > 0")
        if has_weights:
            assert self.equity_weight is not None and self.debt_weight is not None
            if self.equity_weight < 0 or self.debt_weight < 0:
                raise ValuationError("weights must be non-negative")
            s = self.equity_weight + self.debt_weight
            if abs(s - 1.0) > 1e-6:
                raise ValuationError(f"equity_weight + debt_weight must equal 1, got {s}")


@dataclass(frozen=True, slots=True)
class DcfForecastAssumptions:
    """Explicit-period FCFF forecast drivers.

    Default horizon is 10 years per V1.2 domain sprint.
    """

    base_revenue: float
    revenue_growth: float
    operating_margin: float
    tax_rate: float
    depreciation_pct_of_revenue: float
    capex_pct_of_revenue: float
    nwc_pct_of_revenue: float
    forecast_years: int = 10
    historical_fcf: tuple[HistoricalFcfPoint, ...] = ()

    def __post_init__(self) -> None:
        if self.base_revenue <= 0:
            raise ValuationError("base_revenue must be positive")
        if self.revenue_growth < -0.5 or self.revenue_growth > 0.5:
            raise ValuationError(
                f"revenue_growth out of range: {self.revenue_growth}"
            )
        if self.operating_margin <= -0.5 or self.operating_margin > 0.8:
            raise ValuationError(
                f"operating_margin out of range: {self.operating_margin}"
            )
        if self.tax_rate < 0 or self.tax_rate >= 1:
            raise ValuationError(f"tax_rate out of range: {self.tax_rate}")
        for name, pct in (
            ("depreciation_pct_of_revenue", self.depreciation_pct_of_revenue),
            ("capex_pct_of_revenue", self.capex_pct_of_revenue),
            ("nwc_pct_of_revenue", self.nwc_pct_of_revenue),
        ):
            if pct < -0.2 or pct > 1.0:
                raise ValuationError(f"{name} out of range: {pct}")
        if self.forecast_years < 1 or self.forecast_years > 30:
            raise ValuationError(
                f"forecast_years out of range: {self.forecast_years}"
            )


@dataclass(frozen=True, slots=True)
class DcfTerminalAssumptions:
    """Terminal value configuration."""

    method: TerminalMethod = "gordon"
    perpetual_growth: float = 0.02
    exit_ebitda_multiple: float | None = None
    exit_weight_gordon: float = 1.0

    def __post_init__(self) -> None:
        if self.perpetual_growth < -0.02 or self.perpetual_growth > 0.08:
            raise ValuationError(
                f"perpetual_growth out of range: {self.perpetual_growth}"
            )
        if self.method in {"exit_multiple", "both"}:
            if self.exit_ebitda_multiple is None or self.exit_ebitda_multiple <= 0:
                raise ValuationError(
                    "exit_ebitda_multiple required and must be positive "
                    f"for method={self.method!r}"
                )
        if not (0.0 <= self.exit_weight_gordon <= 1.0):
            raise ValuationError("exit_weight_gordon must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class DcfBridgeInputs:
    """Enterprise → equity bridge adjustments."""

    cash: float = 0.0
    total_debt: float = 0.0
    minority_interest: float = 0.0
    non_operating_investments: float = 0.0
    shares_outstanding: float | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("cash", self.cash),
            ("total_debt", self.total_debt),
            ("minority_interest", self.minority_interest),
            ("non_operating_investments", self.non_operating_investments),
        ):
            if value < 0:
                raise ValuationError(f"{name} must be non-negative, got {value}")
        if self.shares_outstanding is not None and self.shares_outstanding <= 0:
            raise ValuationError("shares_outstanding must be positive when set")


@dataclass(frozen=True, slots=True)
class DcfMarketInputs:
    """Market context for margin-of-safety."""

    market_price_per_share: float | None = None
    equity_market_cap: float | None = None

    def __post_init__(self) -> None:
        if self.market_price_per_share is not None and self.market_price_per_share < 0:
            raise ValuationError("market_price_per_share must be non-negative")
        if self.equity_market_cap is not None and self.equity_market_cap < 0:
            raise ValuationError("equity_market_cap must be non-negative")


@dataclass(frozen=True, slots=True)
class DcfSensitivitySpec:
    """Deterministic sensitivity grid deltas (absolute decimal points)."""

    growth_deltas: tuple[float, ...] = (-0.02, 0.0, 0.02)
    wacc_deltas: tuple[float, ...] = (-0.01, 0.0, 0.01)
    terminal_growth_deltas: tuple[float, ...] = (-0.005, 0.0, 0.005)
