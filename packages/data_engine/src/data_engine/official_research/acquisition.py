"""Acquire official primary documents and extract labeled financials/shares.

Discovery is NSE/BSE announcement attachments plus the ISIN IR registry.
Not a crawler. Secondary/forbidden hosts are never fetched as truth.
One annual document is selected; texts are not concatenated across PDFs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from time import perf_counter

from data_engine.official_research.annual_report import (
    AnnualDocumentCandidate,
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
    unwrap_archive_payload,
    validate_document_payload,
)
from data_engine.official_research.extraction import (
    ExtractedField,
    attack_corporate_actions,
    document_identity_matches,
    extract_classified_capex,
    extract_labeled_field,
    extract_shares_outstanding,
    parse_document_context,
)
from data_engine.official_research.nse_eod import NseHttpTransport
from data_engine.official_research.nse_primary import (
    NseAnnouncementDocument,
    parse_announcement_documents,
)
from data_engine.official_research.pdf_text import document_text_from_payload, split_marked_pages
from data_engine.official_research.prompt_guard import sanitize_document_text
from data_engine.official_research.source_policy import SourcePolicy
from data_engine.official_research.statement_tables import (
    extract_field_from_statements,
    reconstruct_statement_pages,
)
from data_engine.official_research.xbrl import (
    extract_shareholding_xbrl_fields,
    extract_xbrl_fields,
    is_xbrl_payload,
)
from data_engine.security_master.models import SecurityListing

__all__ = ["PrimaryAcquisitionResult", "acquire_primary_documents"]

_MAX_HTML_PAGES = 2
_MAX_CANDIDATES = 4
_MAX_XBRL_CANDIDATES = 8
_MAX_PDF_AFTER_XBRL = 1


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
    field_urls: dict[str, str] | None = None


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
    ir_fallback: bool = False,
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

    xbrl_source = tuple(
        item
        for item in docs
        if (
            item.kind == "xbrl"
            or item.url.lower().split("?", 1)[0].endswith((".xml", ".xbrl"))
        )
        and item.kind != "shareholding"
    )
    shp_source = tuple(item for item in docs if item.kind == "shareholding")
    pdf_source = tuple(
        item for item in docs if item not in xbrl_source and item not in shp_source
    )
    ranked = select_annual_documents(
        xbrl_source or tuple(docs),
        ir_links=() if xbrl_source else tuple(ir_links),
        financial_year=latest_completed_indian_fy(),
        statement_basis=CANONICAL_STATEMENT_BASIS,
        limit=_MAX_XBRL_CANDIDATES if xbrl_source else _MAX_CANDIDATES,
    )
    ranked = _prefer_filing_detail(ranked)
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
    xbrl_fields: dict[str, ExtractedField] = {}
    field_urls: dict[str, str] = {}
    pdf_after_xbrl = 0

    def _try_candidates(candidates) -> None:
        nonlocal download_s, extract_s, selected_text, selected_record, standalone_fallback
        nonlocal xbrl_fields, pdf_after_xbrl
        for candidate in candidates:
            path = candidate.url.lower().split("?", 1)[0]
            is_xbrl = candidate.kind == "xbrl" or path.endswith((".xml", ".xbrl"))
            is_pdf = path.endswith(".pdf")
            is_zip = path.endswith(".zip")
            if is_zip:
                continue
            if is_xbrl and xbrl_fields and candidate.kind != "shareholding":
                continue
            if (
                is_xbrl
                and candidate.kind == "shareholding"
                and "shares_outstanding" in xbrl_fields
            ):
                from data_engine.official_research.extraction import (
                    canonical_share_semantic_type,
                    VALUATION_SHARE_SEMANTIC,
                )

                if (
                    canonical_share_semantic_type(
                        xbrl_fields["shares_outstanding"].locator
                    )
                    == VALUATION_SHARE_SEMANTIC
                ):
                    continue
            if (
                is_pdf
                and xbrl_fields
                and "shares_outstanding" in xbrl_fields
                and pdf_after_xbrl >= _MAX_PDF_AFTER_XBRL
            ):
                continue
            if is_pdf and xbrl_fields:
                pdf_after_xbrl += 1
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
                document_date=(
                    None if candidate.as_of is None else candidate.as_of.isoformat()
                ),
                registry=registry,
                store=store,
            )
            download_s += perf_counter() - dl
            if isinstance(result, RetrievalFailure):
                failures.append(result)
                continue
            payloads = [(candidate.url, result)]
            if result.payload.lstrip().startswith(b"PK"):
                unwrapped = unwrap_archive_payload(result.payload)
                payloads = []
                for name, blob in unwrapped:
                    invalid = validate_document_payload(name, blob)
                    if invalid:
                        failures.append(
                            RetrievalFailure(url=candidate.url, reason=invalid)
                        )
                        continue
                    payloads.append(
                        (
                            f"{candidate.url}#{name}",
                            DocumentRecord(
                                url=result.url,
                                retrieved_at=result.retrieved_at,
                                http_status=result.http_status,
                                content_type=result.content_type,
                                content_length=len(blob),
                                document_hash=result.document_hash,
                                payload=blob,
                                company_isin=result.company_isin,
                                company_mic=result.company_mic,
                                document_date=result.document_date,
                                final_url=result.final_url,
                            ),
                        )
                    )
            for _label, record in payloads:
                records.append(record)
                accepted = _accept_extracted_record(
                    record,
                    listing=listing,
                    other_issuers=other_issuers,
                    candidate_kind=candidate.kind,
                    document_basis=(
                        candidate.statement_basis
                        if candidate.statement_basis
                        else (
                            "consolidated"
                            if candidate.prefers_consolidated
                            else None
                        )
                    ),
                    failures=failures,
                )
                extract_s += accepted[3]
                if accepted[0] is None:
                    continue
                cleaned, basis, xbrl_hit = accepted[0], accepted[1], accepted[2]
                if xbrl_hit:
                    xbrl_fields.update(xbrl_hit)
                    for name in xbrl_hit:
                        field_urls[name] = record.url
                    if selected_record is None:
                        selected_text = cleaned
                        selected_record = record
                    continue
                if xbrl_fields:
                    continue
                if basis == "consolidated":
                    selected_text = cleaned
                    selected_record = record
                    return
                if basis == "standalone":
                    if standalone_fallback is None:
                        standalone_fallback = (cleaned, record)
                    continue
                selected_text = cleaned
                selected_record = record
                return

    _try_candidates(ranked)
    if shp_source:
        shp_ranked = tuple(
            AnnualDocumentCandidate(
                url=item.url,
                title=item.title,
                kind="shareholding",
                score=90,
                financial_year=None if item.as_of is None else item.as_of.year,
                prefers_consolidated=False,
                as_of=item.as_of,
                source=item.source,
                statement_basis=None,
            )
            for item in sorted(
                shp_source, key=lambda item: item.as_of or date.min, reverse=True
            )[:2]
        )
        _try_candidates(shp_ranked)
    if not xbrl_fields and xbrl_source and selected_record is None:
        ranked_pdf = select_annual_documents(
            pdf_source,
            ir_links=tuple(ir_links),
            financial_year=latest_completed_indian_fy(),
            statement_basis=CANONICAL_STATEMENT_BASIS,
            limit=_MAX_CANDIDATES,
        )
        _try_candidates(_prefer_filing_detail(ranked_pdf))
    if (
        selected_record is None
        and ir_fallback
        and not fetch_registered_ir
        and not ir_links
    ):
        ir_started = perf_counter()
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
            records.append(result)
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
        timings["ir_fallback"] = perf_counter() - ir_started
        ranked_ir = select_annual_documents(
            tuple(docs),
            ir_links=tuple(ir_links),
            financial_year=latest_completed_indian_fy(),
            statement_basis=CANONICAL_STATEMENT_BASIS,
            limit=_MAX_CANDIDATES,
        )
        _try_candidates(_prefer_filing_detail(ranked_ir))
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
    if selected_record is None and not extra_document_text and ranked:
        issues.append("no qualifying filing-detail document")

    statement_pages = ()
    if (
        selected_record is not None
        and selected_record.payload.lstrip().startswith(b"%PDF")
        and combined
    ):
        rec_started = perf_counter()
        statement_pages = reconstruct_statement_pages(
            selected_record.payload,
            page_texts=split_marked_pages(combined),
        )
        timings["table_reconstruction"] = perf_counter() - rec_started
        timings["statement_pages"] = float(len(statement_pages))
    else:
        timings["table_reconstruction"] = 0.0

    fin_started = perf_counter()
    extracted_fields: dict[str, ExtractedField] = dict(xbrl_fields)
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
    kinds_present = {page.statement_type for page in statement_pages}
    field_kind = {
        "revenue": "pl",
        "operating_profit": "pl",
        "ebit": "pl",
        "net_income": "pl",
        "equity": "bs",
        "cash": "bs",
        "debt": "bs",
        "total_assets": "bs",
        "total_liabilities": "bs",
        "cfo": "cf",
        "capex": "cf",
    }
    for name in wanted:
        if name in extracted_fields:
            continue
        if not combined and not statement_pages:
            continue
        mark = perf_counter()
        if name != "shares_outstanding" and statement_pages:
            reconstructed = extract_field_from_statements(statement_pages, name)
            if reconstructed is not None:
                extracted_fields[name] = reconstructed
                continue
            # Capex may be disclosed as PPE purchases. Do not skip classified
            # extraction merely because a cash-flow page exists.
            if name != "capex" and field_kind.get(name) in kinds_present:
                continue
        item = (
            extract_shares_outstanding(combined)
            if name == "shares_outstanding"
            else extract_labeled_field(combined, name)
        )
        if item is None and name == "capex":
            item = extract_classified_capex(combined)
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
        field_urls=field_urls or None,
    )


def _prefer_filing_detail(items):
    return tuple(
        sorted(
            items,
            key=lambda item: (
                0
                if item.kind == "xbrl"
                or item.url.lower().split("?", 1)[0].endswith((".xml", ".xbrl"))
                else 1,
            ),
        )
    )


def _accept_extracted_record(
    record: DocumentRecord,
    *,
    listing,
    other_issuers: tuple[str, ...],
    candidate_kind: str,
    document_basis: str | None,
    failures: list[RetrievalFailure],
) -> tuple[str | None, str | None, dict[str, ExtractedField] | None, float]:
    started = perf_counter()
    if is_xbrl_payload(record.payload):
        if candidate_kind == "shareholding" or _looks_like_shareholding(record.payload):
            parsed = extract_shareholding_xbrl_fields(
                record.payload, isin=listing.isin
            )
        else:
            parsed = extract_xbrl_fields(
                record.payload,
                isin=listing.isin,
                document_basis=document_basis,
            )
        extract_s = perf_counter() - started
        if not parsed.identity_ok:
            failures.append(
                RetrievalFailure(
                    url=record.url,
                    reason="document identity does not match listing",
                )
            )
            return None, None, None, extract_s
        if not parsed.fields:
            failures.append(
                RetrievalFailure(
                    url=record.url,
                    reason=(
                        parsed.issues[0]
                        if parsed.issues
                        else "no explicitly labeled XBRL financial particulars"
                    ),
                )
            )
            return None, None, None, extract_s
        cleaned = sanitize_document_text(parsed.labeled_text)
        basis = next(
            (
                item.statement_basis
                for item in parsed.fields.values()
                if item.statement_basis
            ),
            None,
        )
        return cleaned, basis, parsed.fields, extract_s
    extracted = document_text_from_payload(
        record.payload, content_type=record.content_type
    )
    extract_s = perf_counter() - started
    if extracted is None:
        strategy_reason = "document text UNAVAILABLE (no text layer)"
        if record.payload.lstrip().startswith(b"%PDF"):
            strategy_reason = "OCR_REQUIRED: PDF has no text layer"
        failures.append(RetrievalFailure(url=record.url, reason=strategy_reason))
        return None, None, None, extract_s
    cleaned = sanitize_document_text(extracted)
    if not document_identity_matches(
        cleaned,
        isin=listing.isin,
        company_name=listing.company_name,
        other_issuers=other_issuers,
    ):
        failures.append(
            RetrievalFailure(
                url=record.url,
                reason="document identity does not match listing",
            )
        )
        return None, None, None, extract_s
    context = parse_document_context(cleaned)
    if context.period_type == "quarter" and candidate_kind != "annual_report":
        failures.append(
            RetrievalFailure(
                url=record.url,
                reason="quarterly document rejected for annual selection",
            )
        )
        return None, None, None, extract_s
    return cleaned, context.statement_basis, None, extract_s


def _looks_like_shareholding(payload: bytes) -> bool:
    head = payload[:400].decode("utf-8", errors="replace").lower()
    return "shp v" in head or "in-bse-shp" in head or "shareholdingpattern" in head
