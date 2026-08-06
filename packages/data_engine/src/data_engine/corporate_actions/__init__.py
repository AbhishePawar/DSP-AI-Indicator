"""Authenticated corporate actions subsystem (EPIC-D003)."""

from __future__ import annotations

from data_engine.corporate_actions.adapters import (
    ConfiguredHttpCorporateActionAdapter,
    InMemoryAuthenticatedCorporateActionAdapter,
    NullAuthenticatedCorporateActionAdapter,
    build_actions_from_mapping,
    build_default_corporate_action_adapter_from_env,
    build_event_from_mapping,
)
from data_engine.corporate_actions.models import (
    ACTION_TYPES,
    AuthenticatedCorporateAction,
    AuthenticatedCorporateActions,
    CorporateActionCompanyIdentity,
    CorporateActionField,
    CorporateActionProvenance,
    utc_now,
)
from data_engine.corporate_actions.registry import CorporateActionProviderRegistry
from data_engine.corporate_actions.service import (
    CorporateActionPort,
    CorporateActionProviderHealth,
    CorporateActionQuery,
    CorporateActionService,
    CorporateActionServiceMetrics,
)
from data_engine.corporate_actions.validation import (
    validate_authenticated_corporate_actions,
)

__all__ = [
    "ACTION_TYPES",
    "AuthenticatedCorporateAction",
    "AuthenticatedCorporateActions",
    "ConfiguredHttpCorporateActionAdapter",
    "CorporateActionCompanyIdentity",
    "CorporateActionField",
    "CorporateActionPort",
    "CorporateActionProvenance",
    "CorporateActionProviderHealth",
    "CorporateActionProviderRegistry",
    "CorporateActionQuery",
    "CorporateActionService",
    "CorporateActionServiceMetrics",
    "InMemoryAuthenticatedCorporateActionAdapter",
    "NullAuthenticatedCorporateActionAdapter",
    "build_actions_from_mapping",
    "build_default_corporate_action_adapter_from_env",
    "build_event_from_mapping",
    "utc_now",
    "validate_authenticated_corporate_actions",
]
