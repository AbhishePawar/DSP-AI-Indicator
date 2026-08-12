"""DSP Enterprise Commercial Platform foundation (EPS-002 / EPIC-016).

Organizations, teams, enterprise RBAC, licensing, billing ports,
sessions, immutable audit, API keys, usage analytics, ops surfaces,
and collaboration architecture ports. Does not modify research engines.
"""

from __future__ import annotations

from enterprise.billing import BillingPort, NullBillingAdapter, build_billing_adapter
from enterprise.billing_providers import (
    BILLING_PROVIDER_UNAVAILABLE,
    PaddleBillingAdapter,
    RazorpayBillingAdapter,
    StripeBillingAdapter,
)
from enterprise.db_store import DatabaseEnterpriseStore, build_enterprise_store
from enterprise.exceptions import (
    EnterpriseError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from enterprise.models import (
    ENTERPRISE_SCHEMA_VERSION,
    ENTERPRISE_SERVICE_VERSION,
    UNAVAILABLE_MESSAGES,
)
from enterprise.ports import EnterpriseStorePort
from enterprise.service import (
    EnterpriseService,
    get_enterprise_service,
    reset_enterprise_service_for_tests,
)
from enterprise.store import InMemoryEnterpriseStore

__all__ = [
    "BILLING_PROVIDER_UNAVAILABLE",
    "ENTERPRISE_SCHEMA_VERSION",
    "ENTERPRISE_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGES",
    "BillingPort",
    "DatabaseEnterpriseStore",
    "EnterpriseError",
    "EnterpriseService",
    "EnterpriseStorePort",
    "ForbiddenError",
    "InMemoryEnterpriseStore",
    "NotFoundError",
    "NullBillingAdapter",
    "PaddleBillingAdapter",
    "RazorpayBillingAdapter",
    "StripeBillingAdapter",
    "ValidationError",
    "build_billing_adapter",
    "build_enterprise_store",
    "get_enterprise_service",
    "reset_enterprise_service_for_tests",
]

__version__ = "0.2.0"
