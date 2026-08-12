"""Canonical Research Object (EPIC-R001)."""

from __future__ import annotations

from dsp_platform.research_object.builder import (
    BUILDER_VERSION,
    ResearchObjectBuilder,
    build_research_object,
)
from dsp_platform.research_object.models import (
    RESEARCH_OBJECT_SCHEMA_VERSION,
    RS_SECTION_ORDER,
    ResearchMetadata,
    ResearchObject,
    ResearchSection,
    ResearchVersion,
    UNAVAILABLE_MESSAGE,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_object.serde import (
    research_object_from_dict,
    research_object_to_dict,
)
from dsp_platform.research_object.validation import (
    ResearchObjectValidationError,
    validate_research_object,
)

__all__ = [
    "BUILDER_VERSION",
    "RESEARCH_OBJECT_SCHEMA_VERSION",
    "RS_SECTION_ORDER",
    "UNAVAILABLE_MESSAGE",
    "ResearchMetadata",
    "ResearchObject",
    "ResearchObjectBuilder",
    "ResearchObjectValidationError",
    "ResearchSection",
    "ResearchVersion",
    "build_research_object",
    "freeze_mapping",
    "research_object_from_dict",
    "research_object_to_dict",
    "utc_now",
    "validate_research_object",
]
