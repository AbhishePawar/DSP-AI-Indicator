"""Valuation Core Framework — shared error hierarchy.

All framework errors subclass the package :class:`~valuation.exceptions.ValuationError`
so existing ``except ValuationError`` handlers continue to work.
"""

from __future__ import annotations

from valuation.exceptions import ValuationError

__all__ = [
    "ValuationError",
    "ValidationError",
    "ForecastError",
    "ConvergenceError",
    "SensitivityError",
    "ScenarioError",
    "MetadataError",
    "ExplainabilityError",
]


class ValidationError(ValuationError):
    """Raised when shared validation rules reject inputs."""


class ForecastError(ValuationError):
    """Raised when forecast construction fails."""


class ConvergenceError(ValuationError):
    """Raised when a numerical solver fails to converge."""


class SensitivityError(ValuationError):
    """Raised when sensitivity grid generation fails."""


class ScenarioError(ValuationError):
    """Raised when scenario evaluation fails."""


class MetadataError(ValuationError):
    """Raised when metadata construction fails."""


class ExplainabilityError(ValuationError):
    """Raised when explainability records are invalid."""
