"""Valuation method abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from fundamental import FinancialSnapshot
from valuation.assumptions import ValuationAssumptions
from valuation.models import IntrinsicValueEstimate

__all__ = ["ValuationMethodRunner"]


class ValuationMethodRunner(ABC):
    """Base class every independent valuation method must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical lowercase registry name."""

    @abstractmethod
    def estimate(
        self,
        snapshot: FinancialSnapshot,
        assumptions: ValuationAssumptions,
    ) -> IntrinsicValueEstimate:
        """Produce one intrinsic-value estimate.

        Missing required inputs must return a non-applicable estimate
        (``applicable=False``, ``intrinsic_value=None``) — never raise.
        """
