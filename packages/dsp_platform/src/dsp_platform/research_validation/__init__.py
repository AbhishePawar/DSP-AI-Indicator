"""Canonical ResearchPackage-bound validation (unwired from production AI)."""

from __future__ import annotations

from dsp_platform.research_validation.models import (
    ALLOWED_AI_FIELD_NAMES,
    CanonicalAIResearchOutput,
    CanonicalValidationIssue,
    CanonicalValidationKind,
    CanonicalValidationResult,
    CanonicalValidationStatus,
)
from dsp_platform.research_validation.validator import validate_canonical_research

__all__ = [
    "ALLOWED_AI_FIELD_NAMES",
    "CanonicalAIResearchOutput",
    "CanonicalValidationIssue",
    "CanonicalValidationKind",
    "CanonicalValidationResult",
    "CanonicalValidationStatus",
    "validate_canonical_research",
]
