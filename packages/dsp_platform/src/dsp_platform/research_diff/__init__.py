"""Research Diff & Comparison Engine (EPIC-R005)."""

from __future__ import annotations

from dsp_platform.research_diff.engine import (
    DIFF_ENGINE_VERSION,
    ResearchDiffEngine,
    diff_research_snapshots,
)
from dsp_platform.research_diff.loader import LoadedSnapshot, load_snapshot
from dsp_platform.research_diff.models import (
    DIFF_SCHEMA_VERSION,
    DIFF_STATUSES,
    UNAVAILABLE_MESSAGE,
    FieldDiff,
    ResearchDiffResult,
    SectionDiff,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_diff.serde import (
    research_diff_from_dict,
    research_diff_to_dict,
)
from dsp_platform.research_diff.validation import (
    ResearchDiffValidationError,
    validate_research_diff,
)
from dsp_platform.research_diff.walker import (
    EXPORT_DIFF_SECTIONS,
    REPORT_DIFF_SECTIONS,
    RESEARCH_OBJECT_DIFF_SECTIONS,
    compare_values,
    diff_mapping,
)

__all__ = [
    "DIFF_ENGINE_VERSION",
    "DIFF_SCHEMA_VERSION",
    "DIFF_STATUSES",
    "EXPORT_DIFF_SECTIONS",
    "REPORT_DIFF_SECTIONS",
    "RESEARCH_OBJECT_DIFF_SECTIONS",
    "UNAVAILABLE_MESSAGE",
    "FieldDiff",
    "LoadedSnapshot",
    "ResearchDiffEngine",
    "ResearchDiffResult",
    "ResearchDiffValidationError",
    "SectionDiff",
    "compare_values",
    "diff_mapping",
    "diff_research_snapshots",
    "freeze_mapping",
    "load_snapshot",
    "research_diff_from_dict",
    "research_diff_to_dict",
    "utc_now",
    "validate_research_diff",
]
