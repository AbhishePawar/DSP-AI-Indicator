"""Private in-process canonical research assembler (AI execution blocked)."""

from __future__ import annotations

from dsp_platform.research_assembly.assembler import assemble_canonical_research
from dsp_platform.research_assembly.evidence import (
    EvidenceJudge,
    EvidenceStatus,
    SourceEvidence,
    is_primary_source,
)
from dsp_platform.research_assembly.models import (
    AI_EXECUTION_BLOCKED,
    AI_OUTPUT_FIXTURE,
    ASSEMBLY_SCHEMA_VERSION,
    PUBLIC_ASSEMBLY_KEYS,
    AiExecutionState,
    AssemblyOutcome,
    CanonicalResearchAssembly,
)
from dsp_platform.research_assembly.share_count import (
    InMemoryShareCountPort,
    ShareCount,
    ShareCountPort,
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
    "EvidenceJudge",
    "EvidenceStatus",
    "SourceEvidence",
    "is_primary_source",
    "InMemoryShareCountPort",
    "ShareCount",
    "ShareCountPort",
]
