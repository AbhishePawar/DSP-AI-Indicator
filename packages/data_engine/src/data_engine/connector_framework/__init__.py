"""Data Connector Framework — shared cross-domain building blocks.

This package is the composition substrate for every new authenticated
data-provider domain that follows the "News / Filings / Ownership /
Insider Trading / ESG / Transcript" shape: a ``Port`` ABC per domain,
Null/InMemory/HTTP adapters, and a domain ``Service`` wrapping a single
provider with cache + rate-limit + retry + circuit-breaker + timeout —
exactly the pattern already established by ``market_quote`` /
``financial_statement`` / ``corporate_actions`` / ``historical_series``
(EPIC-D001–D004).

What this module adds *on top* of that existing per-domain pattern,
shared once rather than duplicated six times:

- :class:`ProviderHealth`, :class:`ConnectorProvenance`,
  :class:`ConnectorCompanyIdentity` — the common envelope types every
  new domain's bundle model embeds instead of redefining.
- :class:`PriorityProviderRegistry` — a generic, thread-safe registry
  that adds **provider priority** and **enable/disable** on top of the
  existing "named lookup with one default" registries.
- :class:`FailoverGroup` — generic **automatic failover** across an
  ordered list of already-resilient per-provider services: tries
  providers in priority order, records which one ultimately served the
  request, and only reports unavailable once every provider has been
  exhausted.
- :class:`ProviderAuditPort` / :class:`LoggingProviderAuditPort` /
  :class:`InMemoryProviderAuditLog` / :class:`NullProviderAuditPort` —
  a provider-call audit trail. ``data_engine`` cannot depend on
  ``auth`` or ``production_platform`` (see ``test_architecture.py``),
  so this is a small local Protocol; the composition root in
  ``dsp_platform`` may bridge it to a richer audit sink if desired.
- Resilience primitives (:class:`RateLimiter`, :class:`CircuitBreaker`,
  :class:`CircuitOpenError`, :class:`RetryPolicy`) are **re-exported**
  from :mod:`data_engine.market_quote.service`, the module every
  existing authenticated domain already imports them from — this
  framework does not fork a second copy of that logic.
- :class:`JsonHttpClient` / :class:`UrllibJsonHttpClient` — a generic,
  dependency-free JSON-over-HTTP client for vendor adapters, mirroring
  ``adapters/yahoo_finance/http_client.py``.

No business logic lives here: no scoring, no valuation, no vendor field
names. Vendor-specific mapping stays entirely inside each domain's own
``adapters.py``.
"""

from __future__ import annotations

from data_engine.connector_framework.audit import (
    InMemoryProviderAuditLog,
    LoggingProviderAuditPort,
    NullProviderAuditPort,
    ProviderAuditEvent,
    ProviderAuditPort,
)
from data_engine.connector_framework.failover import (
    FailoverGroup,
    FailoverOutcome,
)
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
    ProviderHealth,
    utc_now,
)
from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
    assert_production_investment_connectors_configured,
    finalize_provider_registry,
    is_production_environment,
    memory_adapter_allowed,
    require_authenticated_http_adapter,
)
from data_engine.connector_framework.registry import (
    PriorityProviderRegistry,
    ProviderRegistration,
)
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RetryPolicy,
)

__all__ = [
    "CircuitBreaker",
    "CircuitOpenError",
    "ConnectorCompanyIdentity",
    "ConnectorConfigurationError",
    "ConnectorField",
    "ConnectorProvenance",
    "FailoverGroup",
    "FailoverOutcome",
    "InMemoryProviderAuditLog",
    "JsonHttpClient",
    "LoggingProviderAuditPort",
    "NullProviderAuditPort",
    "PriorityProviderRegistry",
    "ProviderAuditEvent",
    "ProviderAuditPort",
    "ProviderHealth",
    "ProviderRegistration",
    "RateLimiter",
    "RetryPolicy",
    "UrllibJsonHttpClient",
    "assert_production_investment_connectors_configured",
    "finalize_provider_registry",
    "is_production_environment",
    "memory_adapter_allowed",
    "require_authenticated_http_adapter",
    "utc_now",
]
