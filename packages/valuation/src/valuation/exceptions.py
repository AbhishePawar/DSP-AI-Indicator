"""Exceptions specific to the Valuation Engine."""

from __future__ import annotations

from core.exceptions import DSPAIError


class ValuationError(DSPAIError):
    """Raised when valuation analysis fails.

    Covers unknown method names, method execution failures, and
    assessment aggregation failures. Missing inputs for a single
    method never raise — they disable that method only.
    """
