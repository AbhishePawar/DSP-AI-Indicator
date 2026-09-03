"""Primary-source document retrieval port — production remains blocked.

This module does not fetch the web, parse vendor APIs, or accept share
counts. Production uses ProductionBlockedPrimarySourceDocumentRetrieval.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from urllib.parse import urlparse

from dsp_platform.external_evidence.models import (
    PRIVATE_EVIDENCE_FIELD_NAMES,
    ExternalEvidenceIdentity,
    ExternalEvidenceValidationError,
)
from dsp_platform.external_evidence.validation import (
    validate_external_evidence_identity,
)
from dsp_platform.primary_source_retrieval.models import (
    DOCUMENT_RETRIEVAL_NOT_CONFIGURED,
    PrimarySourceDocumentRequest,
    PrimarySourceDocumentType,
    RetrievedPrimarySourceDocument,
)

__all__ = [
    "DocumentRetrievalBlockedError",
    "PrimarySourceDocumentRetrievalPort",
    "ProductionBlockedPrimarySourceDocumentRetrieval",
    "validate_document_locator",
    "validate_retrieval_request",
]


class DocumentRetrievalBlockedError(RuntimeError):
    """Raised when production document retrieval is not configured."""

    def __init__(self, message: str = DOCUMENT_RETRIEVAL_NOT_CONFIGURED) -> None:
        super().__init__(message)
        self.discovery_state = DOCUMENT_RETRIEVAL_NOT_CONFIGURED
        self.retrieval_state = DOCUMENT_RETRIEVAL_NOT_CONFIGURED


class PrimarySourceDocumentRetrievalPort(Protocol):
    """Retrieve a primary-source document. Must not validate financial truth."""

    def retrieve(
        self, request: PrimarySourceDocumentRequest
    ) -> RetrievedPrimarySourceDocument:
        """Return a document envelope. Must not emit canonical share counts."""
        ...


class ProductionBlockedPrimarySourceDocumentRetrieval:
    """Production retrieval port. Always blocked. No fixture fallback."""

    def retrieve(
        self, request: PrimarySourceDocumentRequest
    ) -> RetrievedPrimarySourceDocument:
        if not isinstance(request, PrimarySourceDocumentRequest):
            raise DocumentRetrievalBlockedError(DOCUMENT_RETRIEVAL_NOT_CONFIGURED)
        raise DocumentRetrievalBlockedError(DOCUMENT_RETRIEVAL_NOT_CONFIGURED)


def validate_document_locator(locator: str) -> None:
    """Reject non-http locators and credentialed URLs. Does not fetch."""
    if not isinstance(locator, str) or not locator.strip():
        raise ExternalEvidenceValidationError("document locator is required")
    if locator != locator.strip():
        raise ExternalEvidenceValidationError(
            "document locator must not have surrounding whitespace"
        )
    parsed = urlparse(locator)
    if parsed.scheme not in {"http", "https"}:
        raise ExternalEvidenceValidationError(
            "document locator rejected: only http/https URLs are accepted, "
            f"got {locator!r}"
        )
    if not parsed.netloc:
        raise ExternalEvidenceValidationError(
            "document locator rejected: missing host"
        )
    if parsed.username or parsed.password:
        raise ExternalEvidenceValidationError(
            "document locator rejected: credentials in URL are not allowed"
        )


def validate_retrieval_request(request: PrimarySourceDocumentRequest) -> None:
    """Reject unbound identity and secret-bearing payloads. Not truth-checking."""
    if not isinstance(request, PrimarySourceDocumentRequest):
        raise ExternalEvidenceValidationError(
            "retrieval request must be PrimarySourceDocumentRequest"
        )
    if not isinstance(request.identity, ExternalEvidenceIdentity):
        raise ExternalEvidenceValidationError("retrieval identity is required")
    validate_external_evidence_identity(request.identity)
    if not isinstance(request.document_type, PrimarySourceDocumentType):
        raise ExternalEvidenceValidationError("document_type is required")
    fact_id = request.fact_id
    if not isinstance(fact_id, str) or not fact_id.strip():
        raise ExternalEvidenceValidationError("retrieval fact_id is required")
    if fact_id != fact_id.strip():
        raise ExternalEvidenceValidationError(
            "retrieval fact_id must not have surrounding whitespace"
        )
    if fact_id.strip().lower() in PRIVATE_EVIDENCE_FIELD_NAMES:
        raise ExternalEvidenceValidationError(
            "retrieval fact_id must not be a private/secret field name"
        )
    if not isinstance(request.retrieved_at, datetime):
        raise ExternalEvidenceValidationError("retrieved_at is required")
    if request.retrieved_at.tzinfo is None:
        raise ExternalEvidenceValidationError(
            "retrieved_at must be timezone-aware"
        )
    validate_document_locator(request.locator)
    _reject_private_fields(request.to_dict())


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
            "retrieval objects must not contain secrets or LLM metadata: "
            f"{found}"
        )
