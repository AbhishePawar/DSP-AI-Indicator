"""TEST-ONLY local primary-source document retrieval.

Reads an in-memory/local corpus of synthetic filings. Makes no network
calls, uses no credentials, and is never selected by production.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path

from dsp_platform.external_evidence.models import (
    ExternalEvidenceIdentity,
    ExternalEvidenceValidationError,
    SourceTier,
    SourceType,
)
from dsp_platform.external_evidence.validation import (
    assert_identities_compatible,
    validate_external_evidence_record,
)
from dsp_platform.external_evidence_discovery.models import (
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)
from dsp_platform.external_evidence_discovery.port import validate_discovery_request
from dsp_platform.primary_source_retrieval.extraction import (
    extract_candidate_evidence,
)
from dsp_platform.primary_source_retrieval.models import (
    PrimarySourceDocumentRequest,
    PrimarySourceDocumentType,
    RetrievedPrimarySourceDocument,
)
from dsp_platform.primary_source_retrieval.port import validate_retrieval_request

__all__ = [
    "FIXTURE_IDENTITY",
    "FIXTURE_LOCATOR",
    "FIXTURE_SHARES",
    "TEST_ONLY",
    "LocalDocumentExternalEvidenceDiscovery",
    "LocalPrimarySourceDocumentRetrieval",
    "load_local_filing_fixture",
    "parse_local_filing_fixture",
]

TEST_ONLY = True

FIXTURE_IDENTITY = ExternalEvidenceIdentity(
    symbol="DSPX",
    exchange="TESTEX",
    isin="DSPX00000001",
    company_name="DSP Test Synthetic Co",
)
FIXTURE_LOCATOR = (
    "https://fixtures.dsp.test/filings/DSPX-FY24-note12-outstanding"
)
FIXTURE_SHARES = 100.0

_FIXTURE_FILENAME = "DSPX-FY24-note12-outstanding.txt"
_HEADER_KEYS = {
    "Issuer-Symbol": "symbol",
    "Issuer-Exchange": "exchange",
    "Issuer-ISIN": "isin",
    "Issuer-Name": "company_name",
    "Document-Type": "document_type",
    "Publication-Date": "publication_date",
    "Fact-As-Of": "as_of",
    "Source-URL": "locator",
}


class LocalPrimarySourceDocumentRetrieval:
    """In-memory corpus retrieval. Locator is a key, never an HTTP fetch."""

    TEST_ONLY = True

    def __init__(self, corpus: Mapping[str, str]) -> None:
        self._corpus = {str(key): str(value) for key, value in dict(corpus).items()}

    def retrieve(
        self, request: PrimarySourceDocumentRequest
    ) -> RetrievedPrimarySourceDocument:
        validate_retrieval_request(request)
        text = self._corpus.get(request.locator)
        if text is None:
            raise ExternalEvidenceValidationError(
                "document not present in local retrieval corpus"
            )
        document = parse_local_filing_fixture(text, request=request)
        assert_identities_compatible(request.identity, document.identity)
        if document.locator != request.locator:
            raise ExternalEvidenceValidationError(
                "document locator mismatch; retrieval will not remap sources"
            )
        return document


class LocalDocumentExternalEvidenceDiscovery:
    """TEST-ONLY ExternalEvidenceDiscoveryPort backed by local retrieval."""

    TEST_ONLY = True

    def __init__(
        self,
        retrieval: LocalPrimarySourceDocumentRetrieval,
        *,
        locator: str,
        document_type: PrimarySourceDocumentType = (
            PrimarySourceDocumentType.ANNUAL_REPORT
        ),
    ) -> None:
        self._retrieval = retrieval
        self._locator = locator
        self._document_type = document_type

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        validate_discovery_request(request)
        document = self._retrieval.retrieve(
            PrimarySourceDocumentRequest(
                identity=request.identity,
                locator=self._locator,
                document_type=self._document_type,
                fact_id=request.fact_id,
                retrieved_at=request.retrieved_at,
            )
        )
        record = extract_candidate_evidence(
            document,
            fact_id=request.fact_id,
            requested_identity=request.identity,
        )
        if record is None:
            return ExternalEvidenceDiscoveryResult(request=request, records=())
        validate_external_evidence_record(record)
        return ExternalEvidenceDiscoveryResult(
            request=request,
            records=(record,),
        )


def load_local_filing_fixture() -> str:
    """Load the synthetic DSPX annual-report fixture from the test tree."""
    path = (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "fixtures"
        / "primary_sources"
        / _FIXTURE_FILENAME
    )
    if not path.is_file():
        raise FileNotFoundError(f"missing local filing fixture: {path}")
    return path.read_text(encoding="utf-8")


def parse_local_filing_fixture(
    text: str,
    *,
    request: PrimarySourceDocumentRequest,
) -> RetrievedPrimarySourceDocument:
    headers, _body = _split_headers(text)
    symbol = headers.get("symbol")
    exchange = headers.get("exchange")
    isin = headers.get("isin")
    if not symbol:
        raise ExternalEvidenceValidationError(
            "document identity rejected: symbol is required"
        )
    identity = ExternalEvidenceIdentity(
        symbol=symbol,
        exchange=exchange,
        isin=isin,
        company_name=headers.get("company_name"),
    )
    locator = headers.get("locator") or request.locator
    as_of = _parse_iso_date(headers.get("as_of"))
    publication_date = _parse_iso_date(headers.get("publication_date"))
    doc_type = _document_type(
        headers.get("document_type"), fallback=request.document_type
    )
    return RetrievedPrimarySourceDocument(
        identity=identity,
        locator=locator,
        document_type=doc_type,
        source_type=SourceType.FILING,
        source_tier=SourceTier.TIER_1_PRIMARY,
        retrieved_at=request.retrieved_at,
        text=text,
        publication_date=publication_date,
        as_of=as_of,
    )


def _split_headers(text: str) -> tuple[dict[str, str], str]:
    headers: dict[str, str] = {}
    lines = str(text or "").splitlines()
    body_start = 0
    for index, line in enumerate(lines):
        if not line.strip():
            body_start = index + 1
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        mapped = _HEADER_KEYS.get(key.strip())
        if mapped is None:
            continue
        headers[mapped] = value.strip()
        body_start = index + 1
    body = "\n".join(lines[body_start:]).strip()
    return headers, body


def _parse_iso_date(raw: str | None) -> date | None:
    if raw is None or not raw.strip():
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise ExternalEvidenceValidationError(
            "document date must be ISO YYYY-MM-DD when present"
        ) from exc


def _document_type(
    raw: str | None,
    *,
    fallback: PrimarySourceDocumentType,
) -> PrimarySourceDocumentType:
    if not raw:
        return fallback
    try:
        return PrimarySourceDocumentType(raw.strip())
    except ValueError as exc:
        raise ExternalEvidenceValidationError(
            f"unsupported document_type {raw!r}"
        ) from exc
