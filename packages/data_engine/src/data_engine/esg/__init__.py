"""Authenticated ESG scores (Data Connector Framework)."""

from __future__ import annotations

from data_engine.esg.adapters import (
    FinancialModelingPrepEsgAdapter,
    InMemoryEsgAdapter,
    NullEsgAdapter,
    YahooFinanceEsgAdapter,
    build_default_esg_registry_from_env,
    build_esg_score_from_mapping,
)
from data_engine.esg.models import CONTROVERSY_LEVELS, AuthenticatedEsgScore
from data_engine.esg.registry import EsgProviderRegistry
from data_engine.esg.service import EsgProviderPort, EsgQuery, EsgService, EsgServiceMetrics
from data_engine.esg.validation import validate_authenticated_esg_score

__all__ = [
    "CONTROVERSY_LEVELS",
    "AuthenticatedEsgScore",
    "EsgProviderPort",
    "EsgProviderRegistry",
    "EsgQuery",
    "EsgService",
    "EsgServiceMetrics",
    "FinancialModelingPrepEsgAdapter",
    "InMemoryEsgAdapter",
    "NullEsgAdapter",
    "YahooFinanceEsgAdapter",
    "build_default_esg_registry_from_env",
    "build_esg_score_from_mapping",
    "validate_authenticated_esg_score",
]
