"""DSP Enterprise Commercial Platform foundation (EPS-002).

Organizations, teams, enterprise RBAC, licensing, billing ports,
sessions, immutable audit, API keys, usage analytics, ops surfaces,
and collaboration architecture ports. Does not modify research engines.
"""

from __future__ import annotations

from enterprise.billing import BillingPort, NullBillingAdapter
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
from enterprise.service import (
    EnterpriseService,
    get_enterprise_service,
    reset_enterprise_service_for_tests,
)

__all__ = [
    "ENTERPRISE_SCHEMA_VERSION",
    "ENTERPRISE_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGES",
    "BillingPort",
    "EnterpriseError",
    "EnterpriseService",
    "ForbiddenError",
    "NotFoundError",
    "NullBillingAdapter",
    "ValidationError",
    "get_enterprise_service",
    "reset_enterprise_service_for_tests",
]

__version__ = "0.1.0"
