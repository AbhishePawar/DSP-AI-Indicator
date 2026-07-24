"""Comparison status enumerations."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["ComparisonStatus"]


class ComparisonStatus(StrEnum):
    """Outcome of a qualitative comparison run."""

    COMPLETE = "complete"
    DEGRADED = "degraded"
    REFUSED = "refused"
