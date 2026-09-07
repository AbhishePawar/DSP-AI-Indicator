"""Official listed-security universe / Security Master.

Identity foundation only. Not a financial dataset, share-count judge,
valuation engine, or research provider.
"""

from __future__ import annotations

from dsp_platform.security_master.classify import eligibility_for
from dsp_platform.security_master.ingest import ingest_documents, ingest_official_universe
from dsp_platform.security_master.models import (
    EligibilityStatus,
    ListingStatus,
    MatchKind,
    ResolutionStatus,
    SearchOutcome,
    SecurityMasterRecord,
    SecurityType,
    SnapshotStatus,
    UniverseSnapshot,
)
from dsp_platform.security_master.search import resolve_exact, search_snapshot
from dsp_platform.security_master.store import (
    configure_security_master_store,
    get_security_master_store,
    reset_security_master_store_for_tests,
)

__all__ = [
    "EligibilityStatus",
    "ListingStatus",
    "MatchKind",
    "ResolutionStatus",
    "SearchOutcome",
    "SecurityMasterRecord",
    "SecurityType",
    "SnapshotStatus",
    "UniverseSnapshot",
    "configure_security_master_store",
    "eligibility_for",
    "get_security_master_store",
    "ingest_documents",
    "ingest_official_universe",
    "reset_security_master_store_for_tests",
    "resolve_exact",
    "search_snapshot",
]
