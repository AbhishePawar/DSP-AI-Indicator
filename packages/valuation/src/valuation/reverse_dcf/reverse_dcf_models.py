"""Domain models for Reverse DCF Intelligence (research-only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from valuation.reverse_dcf.reverse_dcf_explainability import ReverseExplainedValue

__all__ = [
    "REVERSE_DCF_VERSION",
    "ReverseDcfScenario",
    "ReverseDcfInputs",
    "SolverMetadata",
    "SensitivityCell",
    "SensitivityMatrix",
    "ScenarioResult",
    "ValidationSummary",
    "ReverseDcfResult",
]

REVERSE_DCF_VERSION = "0.3.0-reverse-dcf"


class ReverseDcfScenario(str, Enum):
    """Scenario labels for independent implied-growth solves."""

    BEAR = "bear"
    BASE = "base"
    BULL = "bull"


@dataclass(frozen=True, slots=True)
class ReverseDcfInputs:
    """Inputs required to reverse-engineer implied growth from price."""

    current_share_price: float
    shares_outstanding: float
    cash: float
    debt: float
    minority_interest: float
    investments: float
    current_revenue: float
    current_ebit: float
    current_fcff: float
    current_operating_margin: float
    tax_rate: float
    reinvestment_rate: float
    forecast_years: int
    terminal_growth: float
    wacc: float
    expected_margin_expansion: float = 0.0
    expected_roic: float | None = None
    currency: str = "USD"
    # Scenario margin/growth overlays applied before solve (absolute)
    bear_margin_delta: float = -0.01
    bull_margin_delta: float = 0.01
    # Solver bounds for implied revenue CAGR (decimal)
    growth_low: float = -0.50
    growth_high: float = 0.50
    precision: float = 1e-4  # ±0.01% on growth rate
    max_iterations: int = 200


@dataclass(frozen=True, slots=True)
class SolverMetadata:
    """Convergence metadata for the binary-search solver."""

    iterations: int
    residual_error: float
    converged: bool
    stop_reason: str
    low_bound: float
    high_bound: float
    precision_target: float


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    """One sensitivity grid cell."""

    dimension: str
    parameter_value: float
    implied_revenue_cagr: float | None
    residual_error: float | None
    converged: bool


@dataclass(frozen=True, slots=True)
class SensitivityMatrix:
    """Sensitivity of implied growth to key market/discount inputs."""

    wacc: tuple[SensitivityCell, ...]
    terminal_growth: tuple[SensitivityCell, ...]
    share_price: tuple[SensitivityCell, ...]
    explained: ReverseExplainedValue


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Independent reverse-DCF solve for one scenario."""

    scenario: ReverseDcfScenario
    implied_revenue_cagr: ReverseExplainedValue
    implied_fcff_cagr: ReverseExplainedValue
    implied_ebit_growth: ReverseExplainedValue
    implied_terminal_value: ReverseExplainedValue
    enterprise_value: ReverseExplainedValue
    equity_value: ReverseExplainedValue
    solver: SolverMetadata
    confidence: str


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    """Structured validation outcome."""

    ok: bool
    checks: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReverseDcfResult:
    """Full reverse-DCF research result (base scenario primary fields)."""

    version: str
    currency: str
    disclaimer: str
    implied_revenue_cagr: ReverseExplainedValue
    implied_fcff_cagr: ReverseExplainedValue
    implied_ebit_growth: ReverseExplainedValue
    implied_terminal_value: ReverseExplainedValue
    enterprise_value: ReverseExplainedValue
    equity_value: ReverseExplainedValue
    current_market_price: ReverseExplainedValue
    current_market_cap: ReverseExplainedValue
    discount_rate: ReverseExplainedValue
    terminal_growth: ReverseExplainedValue
    forecast_period: ReverseExplainedValue
    convergence_iterations: int
    residual_error: float
    confidence: str
    validation_summary: ValidationSummary
    solver: SolverMetadata
    scenarios: tuple[ScenarioResult, ...]
    sensitivity: SensitivityMatrix
    explainability: tuple[ReverseExplainedValue, ...]
    methodology: str
    limitations: tuple[str, ...]
