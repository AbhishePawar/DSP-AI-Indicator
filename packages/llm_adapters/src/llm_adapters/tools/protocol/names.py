"""Bidirectional mapping between internal DSP tool names and provider names.

Provider function/tool identifiers typically allow ``[A-Za-z0-9_]`` only
(Gemini forbids dots). Internal DSP names use dotted form
(``dsp.valuation``). Mapping is derived from the public manifest so an
unknown provider name can never invent a DSP tool.
"""

from __future__ import annotations

from typing import Iterable, Mapping


def to_provider_name(internal_name: str) -> str:
    """Map ``dsp.valuation`` → ``dsp_valuation``."""
    return internal_name.replace(".", "_")


def provider_name_map(internal_names: Iterable[str]) -> dict[str, str]:
    """Return ``{provider_name: internal_name}`` for the allowed set."""
    mapping: dict[str, str] = {}
    for name in internal_names:
        provider = to_provider_name(name)
        existing = mapping.get(provider)
        if existing is not None and existing != name:
            raise ValueError(
                f"provider name collision: {provider!r} maps to both "
                f"{existing!r} and {name!r}"
            )
        mapping[provider] = name
    return mapping


def resolve_internal_name(
    provider_name: str,
    *,
    allowed_internal: Iterable[str],
) -> str | None:
    """Resolve a provider-facing name to an allowed internal name.

    Returns ``None`` when the name is not in the public allow-list.
    Internal dotted names are accepted only when they themselves appear
    in the allow-list (fail-closed otherwise).
    """
    allowed = frozenset(allowed_internal)
    reverse = provider_name_map(allowed)
    if provider_name in reverse:
        return reverse[provider_name]
    if provider_name in allowed:
        return provider_name
    return None


def allowed_names_from_manifest(manifest: Iterable[Mapping[str, object]]) -> frozenset[str]:
    names: set[str] = set()
    for entry in manifest:
        name = entry.get("name") if isinstance(entry, Mapping) else None
        if isinstance(name, str) and name:
            names.add(name)
    return frozenset(names)


__all__ = [
    "allowed_names_from_manifest",
    "provider_name_map",
    "resolve_internal_name",
    "to_provider_name",
]
