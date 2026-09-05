"""Primary-source document retrieval seam (production blocked).

The deterministic local implementation lives in ``testing.py`` and must
not be imported by production HTTP, ShareCount, or provider packages.
"""

from __future__ import annotations

from dsp_platform.primary_source_retrieval.extraction import (
    extract_candidate_evidence,
)
from dsp_platform.primary_source_retrieval.models import (
    DOCUMENT_RETRIEVAL_HANDLING,
    DOCUMENT_RETRIEVAL_NOT_CONFIGURED,
    DOCUMENT_RETRIEVAL_SCHEMA_VERSION,
    PrimarySourceDocumentRequest,
    PrimarySourceDocumentType,
    RetrievedPrimarySourceDocument,
)
from dsp_platform.primary_source_retrieval.port import (
    DocumentRetrievalBlockedError,
    PrimarySourceDocumentRetrievalPort,
    ProductionBlockedPrimarySourceDocumentRetrieval,
    validate_document_locator,
    validate_retrieval_request,
)

__all__ = [
    "DOCUMENT_RETRIEVAL_HANDLING",
    "DOCUMENT_RETRIEVAL_NOT_CONFIGURED",
    "DOCUMENT_RETRIEVAL_SCHEMA_VERSION",
    "DocumentRetrievalBlockedError",
    "PrimarySourceDocumentRequest",
    "PrimarySourceDocumentRetrievalPort",
    "PrimarySourceDocumentType",
    "ProductionBlockedPrimarySourceDocumentRetrieval",
    "RetrievedPrimarySourceDocument",
    "extract_candidate_evidence",
    "validate_document_locator",
    "validate_retrieval_request",
]
