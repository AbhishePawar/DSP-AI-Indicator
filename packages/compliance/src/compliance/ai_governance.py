"""AI Challenge Mode — mandatory explainability architecture (PR1.0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = [
    "ChallengeBrief",
    "ChallengeModePort",
]


@dataclass(frozen=True, slots=True)
class ChallengeBrief:
    """Mandatory dual-sided explanation around a research conclusion.

    DSP AI must surface support, opposition, risks, assumptions, unknowns.
    """

    conclusion_summary: str
    reasons_supporting: tuple[str, ...]
    reasons_against: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]
    unknowns: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()


@runtime_checkable
class ChallengeModePort(Protocol):
    """Produces a ChallengeBrief from cite-backed context — no browser AI."""

    def build_challenge(
        self,
        *,
        context_ref: str,
        conclusion_summary: str,
    ) -> ChallengeBrief: ...
