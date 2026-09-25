"""Coverage registry — server-authored coverage views over ``/analyse`` results."""

from dsp_platform.coverage_registry.models import (
    RATING_SCALE,
    CoverageRecord,
    letter_rating,
)
from dsp_platform.coverage_registry.service import (
    RATING_ORDER,
    CoverageRegistryService,
    get_coverage_registry_service,
)
from dsp_platform.coverage_registry.store import (
    CoverageRegistryStore,
    DatabaseCoverageRegistryStore,
    get_coverage_registry_store,
    reset_coverage_registry_store_for_tests,
)

__all__ = [
    "RATING_ORDER",
    "RATING_SCALE",
    "CoverageRecord",
    "CoverageRegistryService",
    "CoverageRegistryStore",
    "DatabaseCoverageRegistryStore",
    "get_coverage_registry_service",
    "get_coverage_registry_store",
    "letter_rating",
    "reset_coverage_registry_store_for_tests",
]
