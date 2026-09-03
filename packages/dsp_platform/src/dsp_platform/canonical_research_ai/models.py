"""Thin envelope around the existing CanonicalAIResearchOutput.

This is not a second AI-output schema. CanonicalAIResearchOutput remains
the narrative draft validated by DSP.
"""

from __future__ import annotations

from dataclasses import dataclass

from dsp_platform.research_validation.models import CanonicalAIResearchOutput

__all__ = ["CanonicalAIDraft"]

# Same token as research_assembly.models.AI_OUTPUT_FIXTURE. Do not import
# research_assembly here — that package's __init__ loads the assembler.
_AI_OUTPUT_FIXTURE = "ai_output_fixture"


@dataclass(frozen=True, slots=True)
class CanonicalAIDraft:
    """In-process AI draft wrapper. Output remains CanonicalAIResearchOutput."""

    output: CanonicalAIResearchOutput
    origin: str = _AI_OUTPUT_FIXTURE
    test_only: bool = True
