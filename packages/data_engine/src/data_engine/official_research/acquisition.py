"""Acquire official primary documents and extract labeled financials/shares.

Discovery is NSE/BSE announcement attachments plus the ISIN IR registry.
Not a crawler. Secondary/forbidden hosts are never fetched as truth.
One annual document is selected; texts are not concatenated across PDFs.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from data_engine.official_research.annual_report import (
    html_document_links,
    latest_completed_indian_fy,
    select_annual_documents,
)
from data_engine.official_research.company_sources import (
    CANONICAL_STATEMENT_BASIS,
    CompanySourceRegistry,
    load_company_source_registry,
    resolve_company_sources,
)
from data_engine.official_research.currentness import CapitalEvent, cache_key
from data_engine.official_research.documents import (
    DocumentRecord,
    DocumentStore,
    RetrievalFailure,
    retrieve_official_document,
)
from data_engine.official_research.extraction import (
    ExtractedField,
    attack_corporate_actions,
    document_identity_matches,
    extract_labeled_field,
    extract_shares_outstanding,
    parse_document_context,
)
from data_engine.official_research.nse_eod import NseHttpTransport
from data_engine.official_research.nse_primary import (
    NseAnnouncementDocument,
    parse_announcement_documents,
)
from data_engine.official_research.pdf_text import document_text_from_payload
from data_engine.official_research.prompt_guard import sanitize_document_text
from data_engine.official_research.source_policy import SourcePolicy
from data_engine.security_master.models import SecurityListing

__all__ = ["PrimaryAcquisitionResult", "acquire_primary_documents"]

_MAX_HTML_PAGES = 2
_MAX_CANDIDATES = 4


@dataclass(frozen=True, slots=True)
class PrimaryAcquisitionResult:
    fields: dict[str, ExtractedField]
    capital_events: tuple[CapitalEvent, ...]
    documents: tuple[DocumentRecord, ...]
    failures: tuple[RetrievalFailure, ...]
    issues: tuple[str, ...]
    sanitized_text: str
    selected_url: str | None = None
    timings: dict[str, float] | None = None


def acquire_primary_documents(
    listing: SecurityListing,
    *,
    transport: NseHttpTransport,
    announcement_payload: object | None = None,
    extra_urls: tuple[str, ...] = (),
    extra_announcements: tuple[NseAnnouncementDocument, ...] = (),
    registry: CompanySourceRegistry | None = None,
    policy: SourcePolicy | None = None,
    extra_document_text: str = "",
    fields: tuple[str, ...] = (),
    fetch_registered_ir: bool = False,
    store: DocumentStore | None = None,
) -> PrimaryAcquisitionResult:
    started = perf_counter()
    timings: dict[str, float] = {}
    policy = policy or SourcePolicy()
    registry = registry or load_company_source_registry()
    store = store or DocumentStore()
    sources = resolve_company_sources(
        listing, registry=registry, candidate_urls=extra_urls
    )
    if sources.registry_issue:
        return PrimaryAcquisitionResult(
            fields={},
            capital_events=(),
            documents=(),
            failures=(),
            issues=(f"registry integrity: {sources.registry_issue}",),
            sanitized_text="",
        )

    docs: list[NseAnnouncementDocument] = []
    if extra_announcements:
        docs = list(extra_announcements)
    elif announcement_payload is not None:
        docs = list(parse_announcement_documents(announcement_payload))

    ir_started = perf_counter()
    ir_links: list[tuple[str, str]] = []
    failures: list[RetrievalFailure] = []
    html_records: list[DocumentRecord] = []
    if fetch_registered_ir:
        pages: list[str] = []
        for url in (
            sources.annual_report_url,
            sources.financial_results_url,
            sources.investor_relations_url,
        ):
            if url and url not in pages:
                pages.append(url)
        for page in pages[:_MAX_HTML_PAGES]:
            result = retrieve_official_document(
                page,
                transport=transport,
                isin=listing.isin,
                mic=listing.mic,
                source_type="company_ir",
                policy=policy,
                registry=registry,
                store=store,
            )
            if isinstance(result, RetrievalFailure):
                failures.append(result)
                continue
            html_records.append(result)
            raw_html = result.payload.decode("utf-8", errors="replace")
            ir_links.extend(
                html_document_links(
                    raw_html,
                    base_url=page,
                    allow_url=lambda href, _isin=listing.isin: registry.allows(
                        listing.isin, href
                    ),
                )
            )
    timings["ir_discovery"] = perf_counter() - ir_started

    ranked = select_annual_documents(
        tuple(docs),
        ir_links=tuple(ir_links),
        financial_year=latest_completed_indian_fy(),
        statement_basis=CANONICAL_STATEMENT_BASIS,
        limit=_MAX_CANDIDATES,
    )
    other_issuers = tuple(
        item.company_name
        for item in registry.records()
        if item.isin != listing.isin and item.company_name
    )

    download_s = 0.0
    extract_s = 0.0
    records: list[DocumentRecord] = list(html_records)
    selected_text = ""
    selected_record: DocumentRecord | None = None
    standalone_fallback: tuple[str, DocumentRecord] | None = None
    for candidate in ranked:
        dl = perf_counter()
        result = retrieve_official_document(
            candidate.url,
            transport=transport,
            isin=listing.isin,
            mic=listing.mic,
            source_type=(
                "regulator" if "nseindia.com" in candidate.url else "company_ir"
            ),
            policy=policy,
            document_date=None if candidate.as_of is None else candidate.as_of.isoformat(),
            registry=registry,
            store=store,
        )
        download_s += perf_counter() - dl
        if isinstance(result, RetrievalFailure):
            failures.append(result)
            continue
        if not result.payload:
            failures.append(
                RetrievalFailure(url=candidate.url, reason="empty document")
            )
            continue
        stripped = result.payload.lstrip()
        pdf_url = candidate.url.lower().split("?", 1)[0].endswith(".pdf")
        if pdf_url and stripped.startswith(b"<"):
            failures.append(
                RetrievalFailure(url=candidate.url, reason="HTML instead of PDF")
            )
            continue
        records.append(result)
        ex = perf_counter()
        extracted = document_text_from_payload(
            result.payload, content_type=result.content_type
        )
        extract_s += perf_counter() - ex
        if extracted is None:
            failures.append(
                RetrievalFailure(
                    url=candidate.url,
                    reason="document text UNAVAILABLE (no text layer)",
                )
            )
            continue
        cleaned = sanitize_document_text(extracted)
        if not document_identity_matches(
            cleaned,
            isin=listing.isin,
            company_name=listing.company_name,
            other_issuers=other_issuers,
        ):
            failures.append(
                RetrievalFailure(
                    url=candidate.url,
                    reason="document identity does not match listing",
                )
            )
            continue
        context = parse_document_context(cleaned)
        if context.period_type == "quarter" and candidate.kind != "annual_report":
            failures.append(
                RetrievalFailure(
                    url=candidate.url,
                    reason="quarterly document rejected for annual selection",
                )
            )
            continue
        if context.statement_basis == "consolidated":
            selected_text = cleaned
            selected_record = result
            break
        if context.statement_basis == "standalone":
            if standalone_fallback is None:
                standalone_fallback = (cleaned, result)
            continue
        if context.statement_basis is None:
            selected_text = cleaned
            selected_record = result
            break
    if selected_record is None and standalone_fallback is not None:
        selected_text, selected_record = standalone_fallback

    timings["document_download"] = download_s
    timings["pdf_extraction"] = extract_s

    combined = selected_text
    if not combined and extra_document_text:
        combined = sanitize_document_text(extra_document_text)
        if not document_identity_matches(
            combined,
            isin=listing.isin,
            company_name=listing.company_name,
            other_issuers=other_issuers,
        ):
            return PrimaryAcquisitionResult(
                fields={},
                capital_events=attack_corporate_actions(combined) if combined else (),
                documents=tuple(records),
                failures=tuple(failures),
                issues=(
                    "document identity does not match listing ISIN; financial values UNKNOWN",
                ),
                sanitized_text=combined,
                timings=timings,
            )

    ca_text = combined
    for item in docs:
        if item.kind == "corporate_action":
            ca_text = f"{ca_text}\n{item.title}"

    context = parse_document_context(combined) if combined else None
    issues: list[str] = []
    if context is not None:
        issues.extend(context.issues)
    if selected_record is None and fetch_registered_ir and not extra_document_text:
        issues.append("no qualifying annual official document")

    fin_started = perf_counter()
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
    share_started = 0.0
    for name in wanted:
        if not combined:
            continue
        mark = perf_counter()
        item = (
            extract_shares_outstanding(combined)
            if name == "shares_outstanding"
            else extract_labeled_field(combined, name)
        )
        if name == "shares_outstanding":
            share_started += perf_counter() - mark
        if item is None:
            continue
        extracted_fields[name] = item
        _ = cache_key(
            isin=listing.isin,
            mic=listing.mic,
            field=name,
            period=None if item.as_of is None else item.as_of.isoformat(),
            source="official_document",
            document_hash=(
                selected_record.document_hash if selected_record is not None else "inline"
            ),
        )
    timings["financial_extraction"] = perf_counter() - fin_started - share_started
    timings["share_extraction"] = share_started
    events = attack_corporate_actions(ca_text) if ca_text else ()
    timings["ca_attack"] = 0.0
    if not combined:
        if extra_document_text or ranked:
            issues.append("no extractable official document text")
    timings["total"] = perf_counter() - started
    return PrimaryAcquisitionResult(
        fields=extracted_fields,
        capital_events=events,
        documents=tuple(records),
        failures=tuple(failures),
        issues=tuple(issues),
        sanitized_text=combined,
        selected_url=None if selected_record is None else selected_record.url,
        timings=timings,
    )
