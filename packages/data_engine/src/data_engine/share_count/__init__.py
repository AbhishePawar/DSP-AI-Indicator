"""Authenticated current shares-outstanding subsystem."""

from __future__ import annotations

from data_engine.share_count.adapters import (
    InMemoryShareCountAdapter,
    NullShareCountAdapter,
    build_default_share_count_adapter_from_env,
    build_share_count_from_mapping,
)
from data_engine.share_count.models import (
    ShareCountBasis,
    ShareCountField,
    ShareCountProvenance,
    ShareCountSnapshot,
    ShareCountUnit,
    utc_now,
)
from data_engine.share_count.port import ShareCountPort, ShareCountProviderHealth
from data_engine.share_count.service import ShareCountService, ShareCountServiceMetrics
from data_engine.share_count.validation import (
    assert_share_count_identity,
    validate_share_count_snapshot,
)

__all__ = [
    "InMemoryShareCountAdapter",
    "NullShareCountAdapter",
    "ShareCountBasis",
    "ShareCountField",
    "ShareCountPort",
    "ShareCountProvenance",
    "ShareCountProviderHealth",
    "ShareCountService",
    "ShareCountServiceMetrics",
    "ShareCountSnapshot",
    "ShareCountUnit",
    "assert_share_count_identity",
    "build_default_share_count_adapter_from_env",
    "build_share_count_from_mapping",
    "utc_now",
    "validate_share_count_snapshot",
]
