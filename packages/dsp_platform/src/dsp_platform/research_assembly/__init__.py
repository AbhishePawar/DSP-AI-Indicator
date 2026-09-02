"""Private in-process canonical research assembler (AI execution blocked)."""

from __future__ import annotations

from dsp_platform.research_assembly.ai_port import (
    BlockedCanonicalResearchAiPort,
    CanonicalAiEvidenceGate,
    CanonicalAiEvidenceState,
    CanonicalAiPortBlockedError,
    CanonicalAiPortResult,
    CanonicalAiPortState,
    CanonicalResearchAiPort,
    invoke_canonical_research_ai_port,
    resolve_canonical_ai_execution_access,
)
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
    "BlockedCanonicalResearchAiPort",
    "CanonicalAiEvidenceGate",
    "CanonicalAiEvidenceState",
    "CanonicalAiPortBlockedError",
    "CanonicalAiPortResult",
    "CanonicalAiPortState",
    "CanonicalResearchAiPort",
    "CanonicalResearchAssembly",
    "assemble_canonical_research",
    "invoke_canonical_research_ai_port",
    "resolve_canonical_ai_execution_access",
]
