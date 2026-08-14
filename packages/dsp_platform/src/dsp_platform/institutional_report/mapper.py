"""Read-only field mapper from Research Object payloads (EPIC-R002).

Extracts existing keys only. Never calculates, infers, or fabricates values.
Missing → ``Data unavailable.``
"""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE

__all__ = [
    "UNAVAILABLE_MESSAGE",
    "field_or_unavailable",
    "map_display_fields",
    "section_payload_dict",
]


def section_payload_dict(section: Any) -> dict[str, Any] | None:
    """Plain dict copy of a ResearchSection payload, or None."""
    if section is None or not getattr(section, "available", False):
        return None
    payload = getattr(section, "payload", None)
    if not isinstance(payload, Mapping):
        return None
    return {str(k): v for k, v in payload.items()}


def field_or_unavailable(
    payload: Mapping[str, Any] | None,
    *keys: str,
) -> Any:
    """Return the first present non-None value for ``keys``, else unavailable.

    Also checks a nested ``fields`` mapping (D005 market quote shape) without
    inventing values.
    """
    if not isinstance(payload, Mapping):
        return UNAVAILABLE_MESSAGE
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    nested = payload.get("fields")
    if isinstance(nested, Mapping):
        for key in keys:
            if key in nested and nested[key] is not None:
                return nested[key]
    return UNAVAILABLE_MESSAGE


def map_display_fields(
    payload: Mapping[str, Any] | None,
    field_keys: Mapping[str, tuple[str, ...]],
) -> dict[str, Any]:
    """Map display labels → extracted values (or Data unavailable.)."""
    return {
        label: field_or_unavailable(payload, *keys)
        for label, keys in field_keys.items()
    }
