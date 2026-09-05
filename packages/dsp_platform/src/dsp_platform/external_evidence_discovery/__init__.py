"""External evidence discovery seam (production blocked).

The deterministic test implementation lives in ``testing.py`` and must
not be imported by production HTTP, ShareCount, or provider packages.
"""

from __future__ import annotations

from dsp_platform.external_evidence_discovery.models import (
    DISCOVERY_HANDLING,
    DISCOVERY_NOT_CONFIGURED,
    DISCOVERY_SCHEMA_VERSION,
    MAX_DISCOVERY_EXCERPT_CHARS,
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)
from dsp_platform.external_evidence_discovery.port import (
    ExternalEvidenceDiscoveryBlockedError,
    ExternalEvidenceDiscoveryPort,
    ProductionBlockedExternalEvidenceDiscovery,
    validate_discovery_request,
)

__all__ = [
    "DISCOVERY_HANDLING",
    "DISCOVERY_NOT_CONFIGURED",
    "DISCOVERY_SCHEMA_VERSION",
    "MAX_DISCOVERY_EXCERPT_CHARS",
    "ExternalEvidenceDiscoveryBlockedError",
    "ExternalEvidenceDiscoveryPort",
    "ExternalEvidenceDiscoveryRequest",
    "ExternalEvidenceDiscoveryResult",
    "ProductionBlockedExternalEvidenceDiscovery",
    "validate_discovery_request",
]
