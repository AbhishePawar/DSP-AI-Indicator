"""Validation for Research Intelligence artifacts (EPIC-011B)."""

from __future__ import annotations

from dsp_platform.research_intelligence.models import (
    OUTCOME_WINDOWS_MONTHS,
    ResearchSnapshot,
)

__all__ = [
    "ResearchIntelligenceValidationError",
    "validate_research_snapshot",
    "validate_window_months",
]


class ResearchIntelligenceValidationError(ValueError):
    """Invalid research intelligence artifact."""


def validate_window_months(window_months: int) -> int:
    if window_months not in OUTCOME_WINDOWS_MONTHS:
        raise ResearchIntelligenceValidationError(
            f"window_months must be one of {OUTCOME_WINDOWS_MONTHS}"
        )
    return window_months


def validate_research_snapshot(snapshot: ResearchSnapshot) -> None:
    if not snapshot.research_id or not str(snapshot.research_id).strip():
        raise ResearchIntelligenceValidationError("research_id is required")
    if not snapshot.timestamp or not str(snapshot.timestamp).strip():
        raise ResearchIntelligenceValidationError("timestamp is required")
    if not snapshot.content_sha256 or len(snapshot.content_sha256) < 16:
        raise ResearchIntelligenceValidationError("content_sha256 is required")
