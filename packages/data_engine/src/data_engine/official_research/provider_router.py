"""Cost-aware research-agent selection. Defaults are not permanent ownership.

Legacy `route_research_roles` keeps FIND/VERIFY/ATTACK/REVIEW substitution.
SIMPLE-15 selection is capability-first: OpenAI is the qualified implementation
target; Gemini/Claude remain interface-compatible stubs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "DEFAULT_ROLE_PROVIDERS",
    "PROVIDER_FALLBACK_ORDER",
    "QUALIFIED_RESEARCH_PROVIDERS",
    "RESEARCH_ROLES",
    "RouterDecision",
    "RouterInputs",
    "count_independent_agents",
    "estimate_token_cost",
    "route_research_roles",
    "select_research_agent",
]

RESEARCH_ROLES: tuple[str, ...] = ("FIND", "VERIFY", "ATTACK", "REVIEW")

DEFAULT_ROLE_PROVIDERS: dict[str, str] = {
    "FIND": "gemini",
    "VERIFY": "chatgpt",
    "ATTACK": "deep_search",
    "REVIEW": "claude",
}

PROVIDER_FALLBACK_ORDER: tuple[str, ...] = (
    "gemini",
    "chatgpt",
    "claude",
    "deep_search",
)

# This forensic stage. Interface-only providers are not counted as independent researchers.
QUALIFIED_RESEARCH_PROVIDERS: frozenset[str] = frozenset({"openai", "chatgpt"})


def route_research_roles(
    availability: dict[str, bool],
) -> dict[str, str | None]:
    """Map research roles to available provider names. Does not invoke APIs."""
    assigned: dict[str, str | None] = {}
    used: set[str] = set()
    for role in RESEARCH_ROLES:
        preferred = DEFAULT_ROLE_PROVIDERS[role]
        if availability.get(preferred, False) and preferred not in used:
            assigned[role] = preferred
            used.add(preferred)
            continue
        substitute = next(
            (
                name
                for name in PROVIDER_FALLBACK_ORDER
                if availability.get(name, False) and name not in used
            ),
            None,
        )
        assigned[role] = substitute
        if substitute is not None:
            used.add(substitute)
    return assigned


@dataclass(frozen=True, slots=True)
class RouterInputs:
    availability: dict[str, bool]
    capabilities: dict[str, tuple[str, ...]] = field(default_factory=dict)
    cost_weight: dict[str, float] = field(default_factory=dict)
    latency_ms: dict[str, float] = field(default_factory=dict)
    quota_remaining: dict[str, float] = field(default_factory=dict)
    required_capabilities: tuple[str, ...] = ()
    preferred_model: str | None = None
    input_token_usd: float = 0.0
    output_token_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class RouterDecision:
    provider: str | None
    model_label: str | None
    independent_agents: int
    reason: str
    qualified: tuple[str, ...]


def count_independent_agents(availability: dict[str, bool]) -> int:
    """Do not manufacture consensus. Only qualified live-capable providers count."""
    return sum(
        1
        for name in QUALIFIED_RESEARCH_PROVIDERS
        if availability.get(name, False)
    )


def estimate_token_cost(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    input_token_usd: float,
    output_token_usd: float,
) -> float | None:
    if not input_token_usd and not output_token_usd:
        return None
    total = 0.0
    if input_tokens:
        total += input_tokens * input_token_usd
    if output_tokens:
        total += output_tokens * output_token_usd
    return total


def select_research_agent(inputs: RouterInputs) -> RouterDecision:
    """Pick one provider by capability, cost, quota, and latency. No role lock-in."""
    qualified: list[str] = []
    for name, ready in inputs.availability.items():
        if not ready:
            continue
        if name not in QUALIFIED_RESEARCH_PROVIDERS:
            continue
        caps = tuple(inputs.capabilities.get(name, ()))
        if inputs.required_capabilities and not set(inputs.required_capabilities).issubset(caps):
            continue
        if inputs.quota_remaining.get(name, 1.0) <= 0:
            continue
        qualified.append(name)
    qualified.sort(
        key=lambda item: (
            inputs.cost_weight.get(item, 1.0),
            inputs.latency_ms.get(item, 1.0),
        )
    )
    independent = count_independent_agents(inputs.availability)
    if not qualified:
        return RouterDecision(
            provider=None,
            model_label=inputs.preferred_model,
            independent_agents=independent,
            reason="no qualified provider with required capabilities",
            qualified=(),
        )
    chosen = qualified[0]
    return RouterDecision(
        provider=chosen,
        model_label=inputs.preferred_model,
        independent_agents=independent,
        reason="capability_cost_latency",
        qualified=tuple(qualified),
    )
