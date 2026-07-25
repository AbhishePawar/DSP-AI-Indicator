"""BusinessQualityEngine public façade — re-exports F3.6 orchestration."""

from __future__ import annotations

from business_quality.business_quality_engine import (
    BUSINESS_QUALITY_ENGINE_VERSION,
    BusinessQualityEngine,
    _strengths,
    _weaknesses,
    aggregate_flags,
    compose_overall_score,
    overall_rating_from_01,
)
from business_quality.metadata import BUSINESS_QUALITY_VERSION

__all__ = [
    "BUSINESS_QUALITY_ENGINE_VERSION",
    "BUSINESS_QUALITY_VERSION",
    "BusinessQualityEngine",
    "aggregate_flags",
    "compose_overall_score",
    "overall_rating_from_01",
    "_strengths",
    "_weaknesses",
]
