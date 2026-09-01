"""Private in-process canonical research assembler (AI execution blocked)."""

from __future__ import annotations

from dsp_platform.research_assembly.assembler import assemble_canonical_research
from dsp_platform.research_assembly.models import (
    AI_EXECUTION_BLOCKED,
    AI_OUTPUT_FIXTURE,
    ASSEMBLY_SCHEMA_VERSION,
    PUBLIC_ASSEMBLY_KEYS,
    AiExecutionState,
    AssemblyOutcome,
    CanonicalResearchAssembly,
)

__all__ = [
    "AI_EXECUTION_BLOCKED",
    "AI_OUTPUT_FIXTURE",
    "ASSEMBLY_SCHEMA_VERSION",
    "PUBLIC_ASSEMBLY_KEYS",
    "AiExecutionState",
    "AssemblyOutcome",
    "CanonicalResearchAssembly",
    "assemble_canonical_research",
]
