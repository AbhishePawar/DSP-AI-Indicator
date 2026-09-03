"""Canonical research AI port — production remains fail-closed.

This module defines the interpret seam. It does not call providers, HTTP,
or DSP engines. Production uses ProductionBlockedCanonicalResearchAiPort.
"""

from __future__ import annotations

from typing import Protocol

from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.research_assembly.models import AI_EXECUTION_BLOCKED
from dsp_platform.research_prompt.models import PrivateResearchPrompt

__all__ = [
    "CanonicalResearchAiBlockedError",
    "CanonicalResearchAiPort",
    "ProductionBlockedCanonicalResearchAiPort",
]


class CanonicalResearchAiBlockedError(RuntimeError):
    """Raised when production AI interpretation is not allowed."""

    def __init__(self, message: str = AI_EXECUTION_BLOCKED) -> None:
        super().__init__(message)
        self.ai_execution_state = AI_EXECUTION_BLOCKED


class CanonicalResearchAiPort(Protocol):
    """Interpret a private prompt into a CanonicalAIDraft.

    Implementations must not calculate DSP values or call providers.
    """

    def interpret(self, prompt: PrivateResearchPrompt) -> CanonicalAIDraft:
        """Return a draft for DSP validation. Must not mutate ResearchPackage."""
        ...


class ProductionBlockedCanonicalResearchAiPort:
    """Production AI port. Always blocked. No provider fallback."""

    def interpret(self, prompt: PrivateResearchPrompt) -> CanonicalAIDraft:
        if not isinstance(prompt, PrivateResearchPrompt):
            raise CanonicalResearchAiBlockedError(AI_EXECUTION_BLOCKED)
        raise CanonicalResearchAiBlockedError(AI_EXECUTION_BLOCKED)
