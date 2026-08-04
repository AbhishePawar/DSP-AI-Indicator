"""Validate ResearchObject structure (EPIC-R001) — no calculations."""

from __future__ import annotations

from dsp_platform.research_object.models import (
    RESEARCH_OBJECT_SCHEMA_VERSION,
    RS_SECTION_ORDER,
    ResearchObject,
    ResearchSection,
)

__all__ = [
    "ResearchObjectValidationError",
    "validate_research_object",
]


class ResearchObjectValidationError(ValueError):
    """Research object failed structural validation."""


_ALLOWED_STATUS = frozenset({"ok", "unavailable", "partial"})
_CONTENT_SECTIONS = tuple(s for s in RS_SECTION_ORDER if s not in {"metadata"})


def _validate_section(section: ResearchSection, expected_name: str) -> None:
    if section.name != expected_name:
        raise ResearchObjectValidationError(
            f"section name mismatch: expected {expected_name!r}, got {section.name!r}"
        )
    if section.status not in _ALLOWED_STATUS:
        raise ResearchObjectValidationError(
            f"section {expected_name!r} has invalid status {section.status!r}"
        )
    if section.available and section.payload is None:
        raise ResearchObjectValidationError(
            f"section {expected_name!r} marked available with null payload"
        )
    if not section.available and section.payload is not None:
        raise ResearchObjectValidationError(
            f"section {expected_name!r} has payload but marked unavailable"
        )
    if section.available and section.message == "Data unavailable.":
        # available sections must not carry the unavailable message
        raise ResearchObjectValidationError(
            f"section {expected_name!r} available with unavailable message"
        )


def validate_research_object(obj: ResearchObject) -> None:
    """Reject structurally invalid research objects. Never invents replacements."""
    if obj.version.schema_version != RESEARCH_OBJECT_SCHEMA_VERSION:
        raise ResearchObjectValidationError(
            f"unsupported schema_version {obj.version.schema_version!r}"
        )
    if not obj.metadata.research_object_id or not str(
        obj.metadata.research_object_id
    ).strip():
        raise ResearchObjectValidationError("missing research_object_id")
    if not obj.metadata.created_at:
        raise ResearchObjectValidationError("missing created_at")
    if not obj.metadata.research_mode:
        raise ResearchObjectValidationError("missing research_mode")

    # Identity must always exist as a section; symbol preferred when available
    _validate_section(obj.identity, "identity")
    if obj.identity.available and obj.identity.payload is not None:
        symbol = obj.identity.payload.get("symbol") or obj.identity.payload.get("ticker")
        if not symbol:
            raise ResearchObjectValidationError("identity payload missing symbol/ticker")

    for name in _CONTENT_SECTIONS:
        _validate_section(obj.section(name), name)

    # Provenance map must be a mapping (may be empty)
    if obj.provenance is None:
        raise ResearchObjectValidationError("missing provenance")
