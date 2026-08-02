"""Process-local Research Intelligence service registry (EPIC-011B)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dsp_platform.research_intelligence.service import ResearchIntelligenceService

__all__ = [
    "get_research_intelligence_service",
    "reset_research_intelligence_for_tests",
]

_SERVICE: ResearchIntelligenceService | None = None


def get_research_intelligence_service() -> ResearchIntelligenceService:
    global _SERVICE
    if _SERVICE is None:
        from dsp_platform.research_intelligence.service import (
            ResearchIntelligenceService,
        )

        _SERVICE = ResearchIntelligenceService()
    return _SERVICE


def reset_research_intelligence_for_tests(
    service: ResearchIntelligenceService | None = None,
) -> None:
    global _SERVICE
    _SERVICE = service
