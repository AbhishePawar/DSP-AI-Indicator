"""External evidence discovery port — production remains blocked.

This module does not retrieve the web, call LLM providers, or accept
share counts. Production uses ProductionBlockedExternalEvidenceDiscovery.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from dsp_platform.external_evidence.models import (
    PRIVATE_EVIDENCE_FIELD_NAMES,
    ExternalEvidenceIdentity,
    ExternalEvidenceValidationError,
)
from dsp_platform.external_evidence.validation import (
    validate_external_evidence_identity,
)
from dsp_platform.external_evidence_discovery.models import (
    DISCOVERY_NOT_CONFIGURED,
    MAX_DISCOVERY_EXCERPT_CHARS,
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)

__all__ = [
    "ExternalEvidenceDiscoveryBlockedError",
    "ExternalEvidenceDiscoveryPort",
    "ProductionBlockedExternalEvidenceDiscovery",
    "bound_evidence_excerpt",
    "validate_discovery_request",
]


class ExternalEvidenceDiscoveryBlockedError(RuntimeError):
    """Raised when production external-evidence discovery is not configured."""

    def __init__(self, message: str = DISCOVERY_NOT_CONFIGURED) -> None:
        super().__init__(message)
        self.discovery_state = DISCOVERY_NOT_CONFIGURED


class ExternalEvidenceDiscoveryPort(Protocol):
    """Discover candidate external evidence. Must not validate truth."""

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        """Return candidate records only. Must not mutate DSP ports."""
        ...


class ProductionBlockedExternalEvidenceDiscovery:
    """Production discovery port. Always blocked. No fixture fallback."""

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        if not isinstance(request, ExternalEvidenceDiscoveryRequest):
            raise ExternalEvidenceDiscoveryBlockedError(DISCOVERY_NOT_CONFIGURED)
        raise ExternalEvidenceDiscoveryBlockedError(DISCOVERY_NOT_CONFIGURED)


def validate_discovery_request(request: ExternalEvidenceDiscoveryRequest) -> None:
    """Reject unbound identity and secret-bearing payloads. Not truth-checking."""
    if not isinstance(request, ExternalEvidenceDiscoveryRequest):
        raise ExternalEvidenceValidationError(
            "discovery request must be ExternalEvidenceDiscoveryRequest"
        )
    if not isinstance(request.identity, ExternalEvidenceIdentity):
        raise ExternalEvidenceValidationError("discovery identity is required")
    validate_external_evidence_identity(request.identity)
    fact_id = request.fact_id
    if not isinstance(fact_id, str) or not fact_id.strip():
        raise ExternalEvidenceValidationError("discovery fact_id is required")
    if fact_id != fact_id.strip():
        raise ExternalEvidenceValidationError(
            "discovery fact_id must not have surrounding whitespace"
        )
    if fact_id.strip().lower() in PRIVATE_EVIDENCE_FIELD_NAMES:
        raise ExternalEvidenceValidationError(
            "discovery fact_id must not be a private/secret field name"
        )
    if not isinstance(request.retrieved_at, datetime):
        raise ExternalEvidenceValidationError("retrieved_at is required")
    if request.retrieved_at.tzinfo is None:
        raise ExternalEvidenceValidationError(
            "retrieved_at must be timezone-aware"
        )
    if request.as_of_target is not None:
        if isinstance(request.as_of_target, datetime):
            raise ExternalEvidenceValidationError(
                "as_of_target must be a date, not retrieved_at"
            )
        if not isinstance(request.as_of_target, date):
            raise ExternalEvidenceValidationError(
                "as_of_target must be a date when present"
            )
        if request.as_of_target is request.retrieved_at:
            raise ExternalEvidenceValidationError(
                "retrieved_at cannot substitute for as_of_target"
            )
    _reject_private_fields(request.to_dict())


def bound_evidence_excerpt(excerpt: str) -> str:
    if not isinstance(excerpt, str) or not excerpt.strip():
        raise ExternalEvidenceValidationError(
            "evidence_reference / excerpt is required"
        )
    if excerpt != excerpt.strip():
        raise ExternalEvidenceValidationError(
            "evidence_reference must not have surrounding whitespace"
        )
    if len(excerpt) > MAX_DISCOVERY_EXCERPT_CHARS:
        raise ExternalEvidenceValidationError(
            "evidence_reference exceeds discovery excerpt bound"
        )
    return excerpt


def _reject_private_fields(payload: object) -> None:
    found: list[str] = []

    def _walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                name = str(key)
                if name in PRIVATE_EVIDENCE_FIELD_NAMES:
                    found.append(name)
                _walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                _walk(item)

    _walk(payload)
    if found:
        raise ExternalEvidenceValidationError(
            "discovery objects must not contain secrets or LLM metadata: "
            f"{found}"
        )
