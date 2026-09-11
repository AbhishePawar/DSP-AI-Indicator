"""Provider-neutral research-agent port. Reuses canonical ResearchRequest/Result.

Does not introduce a second evidence model. DSP domain code never sees SDK types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from data_engine.official_research.models import ResearchRequest, ResearchResult
from data_engine.official_research.research_plan import ResearchPlan
from data_engine.security_master.models import SecurityListing

__all__ = ["ResearchAgentPort", "ResearchContext"]


@dataclass(frozen=True, slots=True)
class ResearchContext:
    """Runtime extras. User assumptions are never evidence."""

    listing: SecurityListing | None = None
    user_assumptions: tuple[str, ...] = ()
    injected_sources: tuple[str, ...] = ()
    production: bool = False
    preferred_model: str | None = None
    extra: dict[str, Any] | None = None


class ResearchAgentPort(Protocol):
    """Researcher only. Cannot write VERIFIED financial fields."""

    provider: str
    model_label: str

    def available(self) -> bool: ...

    def research(
        self,
        request: ResearchRequest,
        plan: ResearchPlan,
        context: ResearchContext,
    ) -> ResearchResult: ...
