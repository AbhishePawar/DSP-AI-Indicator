"""Research specification — provider-neutral request contract.

Complexity signals are supplied by DSP (or tests), never chosen by the
AI. Required tools are a subset of ``ToolRegistry.public_manifest()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from llm_adapters.routing import ComplexitySignal, decide_routing
from llm_adapters.model_tiers import ModelTier


SPEC_VERSION = "dsp.research_orchestrator.v1"

# Deterministic prefetch sets. AI may request additional public tools
# through ToolCallBoundary; it cannot invent tools.
SIMPLE_TOOLS: tuple[str, ...] = (
    "dsp.valuation",
    "dsp.margin_of_safety",
    "dsp.business_quality",
    "dsp.economic_moat",
    "dsp.investment_recommendation",
    "dsp.risk",
)

COMPLEX_TOOLS: tuple[str, ...] = SIMPLE_TOOLS + (
    "dsp.management_quality",
    "dsp.financial_strength",
    "dsp.earnings_quality",
    "dsp.growth_quality",
    "dsp.financial_quality",
    "dsp.quantitative_risk",
    "dsp.research_object",
    "dsp.deterministic_committee",
)


@dataclass(frozen=True, slots=True)
class UserResearchRequest:
    """Inbound user request. No provider, model, or prompt fields."""

    symbol: str
    question: str
    complexity_signals: tuple[ComplexitySignal, ...] = ()
    exchange: str | None = None
    request_id: str = "research-unspecified"


@dataclass(frozen=True, slots=True)
class ResearchSpecification:
    """Server-side research spec derived from the user request."""

    spec_id: str
    spec_version: str
    symbol: str
    question: str
    complexity_signals: tuple[ComplexitySignal, ...]
    required_tools: tuple[str, ...]
    exchange: str | None = None

    @classmethod
    def from_user_request(
        cls,
        request: UserResearchRequest,
        *,
        allowed_tools: Iterable[str],
    ) -> "ResearchSpecification":
        symbol = (request.symbol or "").strip().upper()
        question = (request.question or "").strip()
        if not symbol:
            raise ValueError("research request missing symbol")
        if not question:
            raise ValueError("research request missing question")
        allowed = frozenset(allowed_tools)
        signals = tuple(request.complexity_signals)
        routing = decide_routing(signals)
        planned = COMPLEX_TOOLS if routing.routing_tier is ModelTier.PREMIUM else SIMPLE_TOOLS
        required = tuple(name for name in planned if name in allowed)
        if not required:
            raise ValueError("no approved tools available for research specification")
        return cls(
            spec_id=request.request_id.strip() or "research-unspecified",
            spec_version=SPEC_VERSION,
            symbol=symbol,
            question=question,
            complexity_signals=signals,
            required_tools=required,
            exchange=request.exchange.strip() if request.exchange else None,
        )


__all__ = [
    "COMPLEX_TOOLS",
    "SIMPLE_TOOLS",
    "SPEC_VERSION",
    "ResearchSpecification",
    "UserResearchRequest",
]
