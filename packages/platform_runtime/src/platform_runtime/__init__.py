"""DSP Platform Runtime — enterprise composition root (PEP-004.1).

Composes production_platform + security_platform + compliance.
Does not contain investment logic.
"""

from __future__ import annotations

from platform_runtime.composition import EnterprisePlatform
from platform_runtime.consent_bridge import (
    ComplianceBackedConsentStore,
    consent_source_of_truth,
)
from platform_runtime.readiness import (
    ReadinessCheck,
    ReadinessReport,
    StartupValidation,
    build_readiness_report,
    validate_enterprise_startup,
)

__all__ = [
    "ComplianceBackedConsentStore",
    "EnterprisePlatform",
    "ReadinessCheck",
    "ReadinessReport",
    "StartupValidation",
    "build_readiness_report",
    "consent_source_of_truth",
    "validate_enterprise_startup",
    "__version__",
]

__version__ = "0.1.0"
