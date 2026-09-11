"""Research-role routing design. No live AI APIs.

Roles stay stable. Providers are interchangeable later. This module only
assigns names from an availability map — it never calls Gemini/ChatGPT/Claude.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_ROLE_PROVIDERS",
    "PROVIDER_FALLBACK_ORDER",
    "RESEARCH_ROLES",
    "route_research_roles",
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
