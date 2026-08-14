"""Institutional Research Intelligence & Validation (EPIC-011B).

Measures research quality over time. Does not change research engines.
"""

from __future__ import annotations

from dsp_platform.research_intelligence.capture import (
    build_snapshot_from_analyse_payload,
    confidence_label_from_value,
)
from dsp_platform.research_intelligence.models import (
    CALIBRATION_BUCKETS,
    OUTCOME_WINDOWS_MONTHS,
    RI_SCHEMA_VERSION,
    RI_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    CalibrationReport,
    OutcomeMeasurement,
    PerformanceDashboard,
    ResearchInsightBundle,
    ResearchSnapshot,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_intelligence.outcomes import (
    UNABLE_MESSAGE,
    measure_outcome,
    measure_outcomes_for_snapshot,
    normalize_recommendation_stance,
)
from dsp_platform.research_intelligence.registry import (
    get_research_intelligence_service,
    reset_research_intelligence_for_tests,
)
from dsp_platform.research_intelligence.service import (
    ResearchIntelligenceService,
    capture_research_snapshot,
)
from dsp_platform.research_intelligence.store import (
    DatabaseResearchSnapshotStore,
    InMemoryResearchSnapshotStore,
    ResearchSnapshotStore,
    SnapshotAlreadyExistsError,
    SnapshotNotFoundError,
)
from dsp_platform.research_intelligence.validation import (
    ResearchIntelligenceValidationError,
    validate_research_snapshot,
    validate_window_months,
)

__all__ = [
    "CALIBRATION_BUCKETS",
    "OUTCOME_WINDOWS_MONTHS",
    "RI_SCHEMA_VERSION",
    "RI_SERVICE_VERSION",
    "UNABLE_MESSAGE",
    "UNAVAILABLE_MESSAGE",
    "CalibrationReport",
    "DatabaseResearchSnapshotStore",
    "InMemoryResearchSnapshotStore",
    "OutcomeMeasurement",
    "PerformanceDashboard",
    "ResearchInsightBundle",
    "ResearchIntelligenceService",
    "ResearchIntelligenceValidationError",
    "ResearchSnapshot",
    "ResearchSnapshotStore",
    "SnapshotAlreadyExistsError",
    "SnapshotNotFoundError",
    "build_snapshot_from_analyse_payload",
    "capture_research_snapshot",
    "confidence_label_from_value",
    "freeze_mapping",
    "get_research_intelligence_service",
    "measure_outcome",
    "measure_outcomes_for_snapshot",
    "normalize_recommendation_stance",
    "reset_research_intelligence_for_tests",
    "utc_now",
    "validate_research_snapshot",
    "validate_window_months",
]
