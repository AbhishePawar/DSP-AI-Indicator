"""DSP Compliance bounded context (PR1.0) — architecture scaffold."""

from __future__ import annotations

from compliance.analysis_sections import ANALYSIS_PAGE_ORDER, AnalysisSection
from compliance.feature_flags import FeatureFlags, load_feature_flags
from compliance.terminology import (
    ResearchLabel,
    present_action,
    present_field_label,
)

__all__ = [
    "ANALYSIS_PAGE_ORDER",
    "AnalysisSection",
    "FeatureFlags",
    "ResearchLabel",
    "load_feature_flags",
    "present_action",
    "present_field_label",
]

__version__ = "0.1.0"
