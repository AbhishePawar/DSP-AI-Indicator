"""Provider-neutral live research composition.

Product path: ``llm_adapters.gemini`` / ``openai`` / ``anthropic`` /
``deep_search`` plus this package. Stage names such as SIMPLE-14I are
forensic labels, not import paths.

Composition is imported lazily so provider ``research_agent`` modules can
import ``llm_adapters.research.claims`` without a circular import.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from llm_adapters.research.catalog import qualification_security_master
from llm_adapters.research.claims import claims_from_model_output
from llm_adapters.research.qualification import (
    AgentQualification,
    LiveQualificationStatus,
)

if TYPE_CHECKING:
    from llm_adapters.research.composition import (
        build_research_agents,
        qualify_agents,
    )

__all__ = [
    "AgentQualification",
    "LiveQualificationStatus",
    "build_research_agents",
    "claims_from_model_output",
    "qualification_security_master",
    "qualify_agents",
]


def __getattr__(name: str) -> Any:
    if name in {"build_research_agents", "qualify_agents"}:
        from llm_adapters.research.composition import (
            build_research_agents,
            qualify_agents,
        )

        exports = {
            "build_research_agents": build_research_agents,
            "qualify_agents": qualify_agents,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
