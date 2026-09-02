"""Canonical research production-AI activation boundary (OFF by default).

This module answers only:

    Is production AI explicitly activated for the canonical research path?

It does NOT select a provider, select a model, call an SDK, route, execute
tools, or create AI output.

Existing provider-layer guard (not imported here — that would cycle
dsp_platform → llm_adapters):

    llm_adapters.activation_guard.evaluate_activation

That 10-condition evidence gate remains the future production-readiness
check. This canonical-path boundary stays OFF unless a later authorized
step implements execution *and* that guard is READY.

Fail-closed:
    missing config      → OFF
    malformed config    → OFF
    explicit OFF        → OFF
    provider/key/SDK    → OFF
    test fixture        → OFF
    environment         → ignored (never read)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dsp_platform.research_assembly.assembler import assemble_canonical_research
from dsp_platform.research_assembly.models import CanonicalResearchAssembly

__all__ = [
    "CanonicalProductionAiDecision",
    "CanonicalProductionAiState",
    "assemble_canonical_research_production",
    "resolve_canonical_production_ai",
]


class CanonicalProductionAiState(StrEnum):
    """Canonical research production-AI state.

    OFF is the only implemented state. ON is the future-only introduction
    point for provider execution and is not a legal production value here.
    """

    OFF = "off"


@dataclass(frozen=True, slots=True)
class CanonicalProductionAiDecision:
    """Private activation decision. Never serialize this to HTTP clients."""

    state: CanonicalProductionAiState
    activated: bool

    def public_ai_execution_state(self) -> str:
        """Client-visible AI execution label. No activation evidence."""
        return "ai_execution_blocked"


def resolve_canonical_production_ai(
    config: object | None = None,
) -> CanonicalProductionAiDecision:
    """Return whether canonical-path production AI is explicitly activated.

    Always fail-closed in this step: ``activated`` is False. Presence of
    provider names, API keys, SDK objects, fixtures, or
    ``explicitly_activated=True`` does not turn production AI on.
    Environment variables are not read.
    """
    del config
    return CanonicalProductionAiDecision(
        state=CanonicalProductionAiState.OFF,
        activated=False,
    )


def assemble_canonical_research_production(
    research_package: object,
    *,
    activation_config: object | None = None,
) -> CanonicalResearchAssembly:
    """Production assembly entry: consult the gate, then keep AI blocked.

    Future ON execution may be introduced only after this gate returns
    ``activated=True``. That path is not implemented: ``ai_output`` is
    always ``None``.
    """
    decision = resolve_canonical_production_ai(activation_config)
    if decision.activated:
        # Future-only: the single boundary where provider execution may be
        # introduced. Not implemented — do not call providers.
        return assemble_canonical_research(research_package, ai_output=None)
    return assemble_canonical_research(research_package, ai_output=None)
