"""Exceptions specific to the Economic Engine."""

from __future__ import annotations

from core.exceptions import DSPAIError


class EconomicError(DSPAIError):
    """Raised when macroeconomic analysis fails.

    Covers unknown analyzer names, analyzer execution failures, and
    assessment aggregation failures.
    """
