"""Exceptions for the Business Quality Aggregator bounded context."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "BusinessQualityAggregatorError",
    "BusinessQualityAggregatorValidationError",
]


class BusinessQualityAggregatorError(DSPAIError):
    """Base error for the business_quality_aggregator package."""


class BusinessQualityAggregatorValidationError(BusinessQualityAggregatorError):
    """Raised when an aggregator invariant is not satisfied."""
