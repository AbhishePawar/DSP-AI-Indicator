"""Private DSP methodology prompt generator (ResearchPackage → prompt)."""

from __future__ import annotations

from dsp_platform.research_prompt.generator import build_private_research_prompt
from dsp_platform.research_prompt.methodology import (
    CONFLICTING_EVIDENCE,
    DSP_SCORE_SCALE,
    INSUFFICIENT_EVIDENCE,
    INSUFFICIENT_SCORE,
    MOS_UNAVAILABLE,
    PRIVATE_METHODOLOGY_CANARY,
    VALUATION_UNAVAILABLE,
    methodology_instructions,
)
from dsp_platform.research_prompt.models import (
    DATA_BEGIN,
    DATA_END,
    PROMPT_SCHEMA_VERSION,
    PrivateResearchPrompt,
    PrivateResearchPromptError,
)

__all__ = [
    "CONFLICTING_EVIDENCE",
    "DATA_BEGIN",
    "DATA_END",
    "DSP_SCORE_SCALE",
    "INSUFFICIENT_EVIDENCE",
    "INSUFFICIENT_SCORE",
    "MOS_UNAVAILABLE",
    "PRIVATE_METHODOLOGY_CANARY",
    "PROMPT_SCHEMA_VERSION",
    "PrivateResearchPrompt",
    "PrivateResearchPromptError",
    "VALUATION_UNAVAILABLE",
    "build_private_research_prompt",
    "methodology_instructions",
]
