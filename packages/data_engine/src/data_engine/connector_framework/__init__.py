"""Multi-provider connector framework (priority registry + failover)."""

from __future__ import annotations

from data_engine.connector_framework.audit import (
    InMemoryProviderAuditLog,
    LoggingProviderAuditPort,
    NullProviderAuditPort,
    ProviderAuditEvent,
    ProviderAuditPort,
)
from data_engine.connector_framework.failover import FailoverGroup, FailoverOutcome
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
    ProviderHealth,
    utc_now,
)
from data_engine.connector_framework.registry import (
    PriorityProviderRegistry,
    ProviderRegistration,
)

__all__ = [
    'ConnectorCompanyIdentity',
    'ConnectorField',
    'ConnectorProvenance',
    'FailoverGroup',
    'FailoverOutcome',
    'InMemoryProviderAuditLog',
    'JsonHttpClient',
    'LoggingProviderAuditPort',
    'NullProviderAuditPort',
    'PriorityProviderRegistry',
    'ProviderAuditEvent',
    'ProviderAuditPort',
    'ProviderHealth',
    'ProviderRegistration',
    'UrllibJsonHttpClient',
    'utc_now',
]
