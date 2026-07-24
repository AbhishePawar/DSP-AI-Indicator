"""Enumerations for multi-stock analysis."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["BatchFailurePolicy", "BatchStatus", "InstrumentOutcomeStatus"]


class BatchFailurePolicy(StrEnum):
    """How a multi-stock run treats per-instrument failures."""

    STRICT = "strict"
    PARTIAL = "partial"


class BatchStatus(StrEnum):
    """Overall result of a multi-stock analysis run."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class InstrumentOutcomeStatus(StrEnum):
    """Per-instrument outcome status."""

    SUCCESS = "success"
    FAILURE = "failure"
