"""Acquire official primary documents and extract labeled financials/shares.

Discovery is NSE/BSE announcement attachments plus optional ISIN IR registry.
Not a crawler. Secondary/forbidden hosts are never fetched as truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_engine.official_research.company_sources import (
    CompanySourceRegistry,
    load_company_source_registry,
    resolve_company_sources,
)
from data_engine.official_research.currentness import CapitalEvent, cache_key
from data_engine.official_research.documents import (
    DocumentRecord,
    RetrievalFailure,
    retrieve_official_document,
)
from data_engine.official_research.extraction import (
    ExtractedField,
    attack_corporate_actions,
    extract_labeled_field,
    extract_shares_outstanding,
    parse_document_context,
    document_identity_matches,
)
from data_engine.official_research.nse_eod import NseHttpTransport
from data_engine.official_research.nse_primary import (
    NseAnnouncementDocument,
    NsePrimaryBundle,
    parse_announcement_documents,
)
from data_engine.official_research.pdf_text import document_text_from_payload
from data_engine.official_research.prompt_guard import sanitize_document_text
from data_engine.official_research.source_policy import SourcePolicy
from data_engine.security_master.models import SecurityListing

__all__ = ["PrimaryAcquisitionResult", "acquire_primary_documents"]

_FINANCIAL_KINDS = frozenset({"financial_results", "annual_report", "shareholding"})
_MAX_DOCUMENTS = 5


@dataclass(frozen=True, slots=True)
class PrimaryAcquisitionResult:
    fields: dict[str, ExtractedField]
    capital_events: tuple[CapitalEvent, ...]
    documents: tuple[DocumentRecord, ...]
    failures: tuple[RetrievalFailure, ...]
    issues: tuple[str, ...]
    sanitized_text: str


def _kind_from_title(title: str) -> str:
    lowered = title.lower()
    if "shareholding" in lowered:
        return "shareholding"
    if "annual report" in lowered or "integrated report" in lowered:
        return "annual_report"
    if "financial result" in lowered or "audited" in lowered or "year ended" in lowered:
        return "financial_results"
    return "other"


def acquire_primary_documents(
    listing: SecurityListing,
    *,
    transport: NseHttpTransport,
    announcement_payload: object | None = None,
    extra_urls: tuple[str, ...] = (),
    registry: CompanySourceRegistry | None = None,
    policy: SourcePolicy | None = None,
    extra_document_text: str = "",
    fields: tuple[str, ...] = (),
) -> PrimaryAcquisitionResult:
    policy = policy or SourcePolicy()
    registry = registry or load_company_source_registry()
    sources = resolve_company_sources(
        listing, registry=registry, candidate_urls=extra_urls
    )
    docs: list[NseAnnouncementDocument] = []
    if announcement_payload is not None:
        docs = list(parse_announcement_documents(announcement_payload))
    locators: list[tuple[str, str, str | None]] = []
    for item in docs:
        if item.kind not in _FINANCIAL_KINDS and item.kind != "corporate_action":
            continue
        locators.append((item.url, "regulator", item.as_of.isoformat() if item.as_of else None))
    for url in sources.candidate_urls:
        locators.append((url, "company_ir" if "nseindia.com" not in url else "regulator", None))

    seen: set[str] = set()
    records: list[DocumentRecord] = []
    failures: list[RetrievalFailure] = []
    texts: list[str] = []
    if extra_document_text:
        texts.append(sanitize_document_text(extra_document_text))
    for url, source_type, dated in locators[:_MAX_DOCUMENTS]:
        if url in seen:
            continue
        seen.add(url)
        result = retrieve_official_document(
            url,
            transport=transport,
            isin=listing.isin,
            mic=listing.mic,
            source_type=source_type,
            policy=policy,
            document_date=dated,
            registry=registry,
        )
        if isinstance(result, RetrievalFailure):
            failures.append(result)
            continue
        records.append(result)
        extracted = document_text_from_payload(
            result.payload, content_type=result.content_type
        )
        if extracted is None:
            failures.append(
                RetrievalFailure(url=url, reason="document text UNAVAILABLE (no text layer)")
            )
            continue
        texts.append(sanitize_document_text(extracted))

    combined = "\n\n".join(texts)
    if combined and not document_identity_matches(combined, isin=listing.isin):
        issues_mismatch = (
            "document identity does not match listing ISIN; financial values UNKNOWN"
        )
        return PrimaryAcquisitionResult(
            fields={},
            capital_events=attack_corporate_actions(combined) if combined else (),
            documents=tuple(records),
            failures=tuple(failures),
            issues=(issues_mismatch,),
            sanitized_text=combined,
        )
    context = parse_document_context(combined) if combined else None
    issues: list[str] = []
    if context is not None:
        issues.extend(context.issues)
    events = attack_corporate_actions(combined) if combined else ()
    extracted_fields: dict[str, ExtractedField] = {}
    wanted = fields or (
        "revenue",
        "operating_profit",
        "ebit",
        "net_income",
        "equity",
        "cash",
        "cfo",
        "capex",
        "debt",
        "total_assets",
        "total_liabilities",
        "shares_outstanding",
    )
    for name in wanted:
        item = (
            extract_shares_outstanding(combined)
            if name == "shares_outstanding"
            else extract_labeled_field(combined, name)
        )
        if item is None:
            continue
        extracted_fields[name] = item
        _ = cache_key(
            isin=listing.isin,
            mic=listing.mic,
            field=name,
            period=None if item.as_of is None else item.as_of.isoformat(),
            source="official_document",
            document_hash=records[0].document_hash if records else "inline",
        )
    if not combined:
        if extra_document_text or locators:
            issues.append("no extractable official document text")
    return PrimaryAcquisitionResult(
        fields=extracted_fields,
        capital_events=events,
        documents=tuple(records),
        failures=tuple(failures),
        issues=tuple(issues),
        sanitized_text=combined,
    )
