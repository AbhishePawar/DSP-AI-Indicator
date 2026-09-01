"""Private canonical DSP ResearchPackage (compose_intelligence aggregator)."""

from __future__ import annotations

from dsp_platform.research_package.builder import build_research_package
from dsp_platform.research_package.models import (
    ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE,
    PRIVATE_FIELD_NAMES,
    RESEARCH_PACKAGE_SCHEMA_VERSION,
    SOURCE_PIPELINE_COMPOSE_INTELLIGENCE,
    PackageSection,
    ResearchPackage,
    ResearchPackageSourceError,
    SectionStatus,
    contains_private_fields,
    freeze_mapping,
    strip_private_fields,
)

__all__ = [
    "ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE",
    "PRIVATE_FIELD_NAMES",
    "RESEARCH_PACKAGE_SCHEMA_VERSION",
    "SOURCE_PIPELINE_COMPOSE_INTELLIGENCE",
    "PackageSection",
    "ResearchPackage",
    "ResearchPackageSourceError",
    "SectionStatus",
    "build_research_package",
    "contains_private_fields",
    "freeze_mapping",
    "strip_private_fields",
]
