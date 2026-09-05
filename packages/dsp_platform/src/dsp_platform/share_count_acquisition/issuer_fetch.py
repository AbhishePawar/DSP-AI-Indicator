"""Allowlisted issuer IR fetch. Not an arbitrary URL GET."""

from __future__ import annotations

from urllib.parse import urlparse

from dsp_platform.controlled_document_retrieval import ControlledHttpsDocumentRetrieval
from dsp_platform.external_evidence import ExternalEvidenceValidationError
from dsp_platform.external_evidence.models import ExternalEvidenceIdentity
from dsp_platform.primary_source_retrieval.models import (
    PrimarySourceDocumentRequest,
    PrimarySourceDocumentType,
)
from dsp_platform.share_count_acquisition.issuer import (
    IssuerEvidenceSource,
    extract_outstanding_observation,
)
from dsp_platform.share_count_acquisition.issuer_documents import (
    fetch_issuer_documents_outstanding,
)
from dsp_platform.share_count_acquisition.universe import ListedEquityInstrument
from dsp_platform.share_count_refresh import ShareCountObservation

__all__ = ["fetch_issuer_outstanding"]


def fetch_issuer_outstanding(
    instrument: ListedEquityInstrument,
    *,
    retrieved_at,
    retrieval: ControlledHttpsDocumentRetrieval | None = None,
    document_http=None,
) -> ShareCountObservation | None:
    """Fetch configured IR locators, then official documents on the same hosts."""
    identity = instrument.identity.normalized()
    client = retrieval or ControlledHttpsDocumentRetrieval(
        tier_1_hosts=instrument.ir_hosts,
        timeout_seconds=10.0,
        max_bytes=1_000_000,
    )
    for url in instrument.ir_urls:
        host = (urlparse(url).hostname or "").strip().lower()
        if host not in instrument.ir_hosts:
            continue
        request = PrimarySourceDocumentRequest(
            identity=ExternalEvidenceIdentity(
                symbol=identity.symbol,
                exchange=identity.exchange,
                isin=identity.isin,
                company_name=identity.issuer,
                mic=identity.mic,
            ),
            locator=url,
            document_type=PrimarySourceDocumentType.INVESTOR_RELATIONS,
            fact_id="current_outstanding",
            retrieved_at=retrieved_at,
        )
        try:
            document = client.retrieve(request)
        except ExternalEvidenceValidationError:
            continue
        source = IssuerEvidenceSource(
            identity=identity,
            ir_url=url,
            issuer_name=identity.issuer,
        )
        observation = extract_outstanding_observation(
            source,
            document_text=document.text or "",
            retrieved_at=retrieved_at,
            publication_at=document.publication_date,
        )
        if observation is not None:
            return observation
    if document_http is None:
        return None
    return fetch_issuer_documents_outstanding(
        instrument,
        http=document_http,
        retrieved_at=retrieved_at,
    )
