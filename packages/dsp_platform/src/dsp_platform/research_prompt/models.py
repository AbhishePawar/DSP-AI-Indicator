"""Private prompt object — not a public HTTP/client DTO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "DATA_BEGIN",
    "DATA_END",
    "PROMPT_SCHEMA_VERSION",
    "PrivateResearchPrompt",
    "PrivateResearchPromptError",
]

PROMPT_SCHEMA_VERSION = "dsp.private_research_prompt.v1"
DATA_BEGIN = "===== BEGIN UNTRUSTED DSP RESEARCH DATA ====="
DATA_END = "===== END UNTRUSTED DSP RESEARCH DATA ====="


class PrivateResearchPromptError(TypeError):
    """Raised when prompt generation is given a non-ResearchPackage source."""


@dataclass(frozen=True, slots=True)
class PrivateResearchPrompt:
    """Immutable private methodology prompt for a future AI provider.

    ``to_dict`` / ``text`` are server-internal. Do not return this object
    from an HTTP handler or embed it in PublicDecisionPack.
    """

    schema_version: str
    methodology_version: str
    source_pipeline: str
    canary: str
    instructions: str
    data_block: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "methodology_version": self.methodology_version,
            "source_pipeline": self.source_pipeline,
            "canary": self.canary,
            "instructions": self.instructions,
            "data_block": self.data_block,
            "text": self.text,
        }
