"""Private in-process canonical research assembler (no AI execution).

PATH SPLIT (do not silently merge):
    NEW PATH (this module):
        ResearchPackage
            → build_private_research_prompt
            → AI_EXECUTION_BLOCKED | AI_OUTPUT_FIXTURE
            → validate_canonical_research
            → PublicResearchReport
    OLD PATH (unchanged):
        DecisionPack → ResearchOrchestrator → PublicDecisionPack

This assembler does not call providers, HTTP, or DSP engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from dsp_platform.research_prompt.models import PrivateResearchPrompt
from dsp_platform.research_report.models import PublicResearchReport
from dsp_platform.research_validation.models import CanonicalValidationResult

__all__ = [
    "AI_EXECUTION_BLOCKED",
    "AI_OUTPUT_FIXTURE",
    "ASSEMBLY_SCHEMA_VERSION",
    "PUBLIC_ASSEMBLY_KEYS",
    "AiExecutionState",
    "AssemblyOutcome",
    "CanonicalResearchAssembly",
]

ASSEMBLY_SCHEMA_VERSION = "dsp.canonical_research_assembly.v1"
AI_EXECUTION_BLOCKED = "ai_execution_blocked"
AI_OUTPUT_FIXTURE = "ai_output_fixture"

PUBLIC_ASSEMBLY_KEYS = frozenset(
    {
        "schema_version",
        "source_pipeline",
        "ai_execution_state",
        "outcome",
        "validation_status",
        "issues",
        "report",
    }
)


class AiExecutionState(StrEnum):
    AI_EXECUTION_BLOCKED = AI_EXECUTION_BLOCKED
    AI_OUTPUT_FIXTURE = AI_OUTPUT_FIXTURE


class AssemblyOutcome(StrEnum):
    AI_EXECUTION_BLOCKED = AI_EXECUTION_BLOCKED
    VALID = "valid"
    INVALID = "invalid"
    FAILED_CLOSED = "failed_closed"


@dataclass(frozen=True, slots=True)
class CanonicalResearchAssembly:
    """Private assembly result. Serialize publicly only via ``to_public_dict``."""

    schema_version: str
    source_pipeline: str
    ai_execution_state: str
    outcome: str
    private_prompt: PrivateResearchPrompt | None
    validation: CanonicalValidationResult | None
    report: PublicResearchReport | None

    def to_public_dict(self) -> dict[str, Any]:
        """Client-safe view. Never includes the private prompt."""
        issues: list[dict[str, str]] = []
        validation_status = None
        if self.validation is not None:
            validation_status = self.validation.status.value
            issues = [item.to_dict() for item in self.validation.issues]
        payload = {
            "schema_version": self.schema_version,
            "source_pipeline": self.source_pipeline,
            "ai_execution_state": self.ai_execution_state,
            "outcome": self.outcome,
            "validation_status": validation_status,
            "issues": issues,
            "report": None if self.report is None else self.report.to_public_dict(),
        }
        return payload
