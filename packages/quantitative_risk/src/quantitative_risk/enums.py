"""Enumerations for Quantitative Risk domain models (structure only)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "EngineStatus",
    "MetricStatus",
    "MetricType",
    "ReportingStatus",
    "StressScenarioType",
]


class MetricType(StrEnum):
    """Initial E2 catalog metric kinds — additive kinds require freeze amendment."""

    CONCENTRATION = "concentration"
    EXPOSURE = "exposure"
    VOLATILITY = "volatility"
    DRAWDOWN = "drawdown"


class MetricStatus(StrEnum):
    """Metric validity — not a quality/attractiveness score."""

    VALID = "valid"
    PARTIAL = "partial"
    FAILED = "failed"


class StressScenarioType(StrEnum):
    """Declared stress scenario classification."""

    MARKET = "market"
    SECTOR = "sector"
    PORTFOLIO = "portfolio"
    CUSTOM = "custom"


class EngineStatus(StrEnum):
    """Quantitative engine run completeness — not a quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ReportingStatus(StrEnum):
    """Reporting completeness — presentation only, not a risk score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"
