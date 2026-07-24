"""Analyzer abstraction for the Economic Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod

from economic.models import EconomicSignal, EconomicSnapshot

__all__ = ["Analyzer"]


class Analyzer(ABC):
    """Base class every economic analyzer must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical, lowercase identifier for this analyzer."""

    @abstractmethod
    def analyze(self, snapshot: EconomicSnapshot) -> tuple[EconomicSignal, ...]:
        """Produce this analyzer's signals for one snapshot.

        Args:
            snapshot: Macroeconomic inputs to analyze.

        Returns:
            One or more :class:`~economic.models.EconomicSignal`
            objects. Missing inputs yield a neutral / insufficient-data
            signal rather than an empty tuple, so callers always know
            which dimensions were evaluated.
        """
