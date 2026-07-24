"""Abstract interfaces for pluggable valuation infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

__all__ = [
    "ValuationMethod",
    "ScenarioProvider",
    "SensitivityProvider",
    "ExplainabilityProvider",
    "ValidationProvider",
    "ConfidenceProvider",
]


class ValuationMethod(ABC):
    """Contract for a valuation methodology engine."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical method name."""

    @abstractmethod
    def analyze(self, inputs: Any) -> Any:
        """Run the method and return a method-specific or core result."""


class ScenarioProvider(ABC):
    """Produces bear/base/bull/(custom) scenario evaluations."""

    @abstractmethod
    def scenarios(self, context: Mapping[str, Any]) -> Sequence[Any]:
        """Return scenario results for the given context."""


class SensitivityProvider(ABC):
    """Produces sensitivity grids for key assumptions."""

    @abstractmethod
    def sensitivity(self, context: Mapping[str, Any]) -> Any:
        """Return sensitivity matrix / cells."""


class ExplainabilityProvider(ABC):
    """Formats calculation steps into explainability records."""

    @abstractmethod
    def explain(self, steps: Sequence[Mapping[str, Any]]) -> Sequence[Any]:
        """Convert calculation steps into explainability artifacts."""


class ValidationProvider(ABC):
    """Validates method inputs before calculation."""

    @abstractmethod
    def validate(self, inputs: Any) -> Any:
        """Return a validation summary or raise on hard failure."""


class ConfidenceProvider(ABC):
    """Scores research confidence from structured factors."""

    @abstractmethod
    def score(self, factors: Mapping[str, float | int | bool | None]) -> Any:
        """Return confidence detail."""
