"""Generic planned-field acquisition.

DISCOVER → RETRIEVE → EXTRACT → NORMALIZE → RECONCILE → VERIFY

Issuers are callers' fixtures. This module never branches on ticker, company,
or ISIN. Live providers are optional adapters. Only EvidenceJudge can mark
VERIFIED. RAW provider data and AI answers cannot enter DSP.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from time import perf_counter
from typing import Any

from data_engine.official_research.company_sources import resolve_company_sources
from data_engine.official_research.currentness import (
    CapitalEvent,
    currentness_label,
)
from data_engine.official_research.documents import (
    DocumentRecord,
    RetrievalFailure,
    identify_document_characteristics,
    select_extraction_strategy,
)
from data_engine.official_research.dsp_gate import dsp_gate
from data_engine.official_research.extraction import (
    ExtractedField,
    attack_corporate_actions,
    classify_share_semantic_type,
    document_identity_matches,
    extract_labeled_field,
    parse_document_context,
)
from data_engine.official_research.forensic_artifacts import is_promotable_artifact
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import (
    EvidenceItem,
    FailureStatus,
    PriceSnapshot,
    ResearchRequest,
    ResearchResult,
    new_evidence_id,
    utc_now,
)
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS
from data_engine.official_research.pdf_text import document_text_from_payload
from data_engine.official_research.research_failures import (
    ResearchFailure,
    map_retrieval_to_failure_code,
)
from data_engine.official_research.research_plan import (
    ResearchPlan,
    build_research_plan,
    field_retrieval_strategy,
    field_source_priority,
)
from data_engine.official_research.source_policy import (
    SourcePolicy,
    classify_source_url,
    record_source_clash,
    source_authority_rank,
)
from data_engine.official_research.verified_dataset import VerifiedDataset
from data_engine.security_master.models import SecurityListing, UNSUPPORTED_SECURITY_TYPES

__all__ = [
    "ACQUISITION_STAGES",
    "VALUATION_SHARE_SEMANTIC",
    "FieldAcquisitionOutcome",
    "PlannedAcquisitionResult",
    "acquire_planned_fields",
    "normalize_extracted_field",
]

ACQUISITION_STAGES: tuple[str, ...] = (
    "discover",
    "retrieve",
    "extract",
    "normalize",
    "reconcile",
    "verify",
)
VALUATION_SHARE_SEMANTIC = "TOTAL_OUTSTANDING"
UNSUPPORTED_SECURITY_TYPE = "UNSUPPORTED_SECURITY_TYPE"

_FINANCIAL_CONTEXT_FIELDS = frozenset(
    {
        "revenue",
        "net_income",
        "equity",
        "cash",
        "cfo",
        "operating_profit",
        "ebit",
        "capex",
        "debt",
        "total_assets",
        "total_liabilities",
    }
)

RetrieveFn = Callable[[str], DocumentRecord | RetrievalFailure]


@dataclass(frozen=True, slots=True)
class FieldAcquisitionOutcome:
    field: str
    status: str
    stage_reached: str
    evidence: EvidenceItem | None
    sources_tried: tuple[str, ...]
    failures: tuple[ResearchFailure, ...]
    currentness: str
    semantic_type: str | None = None
    cross_check: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class PlannedAcquisitionResult:
    plan: ResearchPlan
    outcomes: tuple[FieldAcquisitionOutcome, ...]
    evidence: tuple[EvidenceItem, ...]
    verified_fields: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    conflicts: tuple[str, ...]
    refresh_required: tuple[str, ...]
    blocked_calculations: tuple[str, ...]
    timings: dict[str, float]
    nse_mcp_commercial_status: str
    security_type_status: str
    dataset: VerifiedDataset | None
    capital_events: tuple[CapitalEvent, ...] = ()
    document_characteristics: tuple[Any, ...] = ()
    extraction_strategy: str | None = None


def acquire_planned_fields(
    listing: SecurityListing,
    request: ResearchRequest,
    *,
    candidates: Mapping[str, Sequence[EvidenceItem]] | None = None,
    documents: Sequence[DocumentRecord] | None = None,
    document_text: str | None = None,
    document_url: str | None = None,
    capital_events: tuple[CapitalEvent, ...] = (),
    production: bool = False,
    existing_verified: tuple[str, ...] = (),
    stale_fields: tuple[str, ...] = (),
    artifact_path: str | None = None,
    judge: EvidenceJudge | None = None,
    policy: SourcePolicy | None = None,
    retrieve_fn: RetrieveFn | None = None,
) -> PlannedAcquisitionResult:
    """Run the generic loop for every planned field. Never invent a missing value."""
    started = perf_counter()
    timings = {stage: 0.0 for stage in ("plan", *ACQUISITION_STAGES)}
    if artifact_path and is_promotable_artifact(artifact_path):
        raise RuntimeError("promotable forensic artifact is a contract violation")
    policy = policy or SourcePolicy()
    judge = judge or EvidenceJudge(policy)
    t = perf_counter()
    sources = resolve_company_sources(listing)
    plan = build_research_plan(
        listing,
        request,
        existing_verified=existing_verified,
        stale_fields=stale_fields,
        sources=sources,
        artifact_path=artifact_path,
    )
    timings["plan"] = perf_counter() - t

    if listing.security_type in UNSUPPORTED_SECURITY_TYPES:
        elapsed = perf_counter() - started
        timings["discover"] = elapsed
        failure = ResearchFailure(
            "UNSUPPORTED_SECURITY",
            f"security_type={listing.security_type} cannot use ordinary-equity valuation",
        )
        return PlannedAcquisitionResult(
            plan=plan,
            outcomes=(),
            evidence=(),
            verified_fields=(),
            unknown_fields=(),
            conflicts=(),
            refresh_required=(),
            blocked_calculations=("DCF", "earnings_multiple", "book_value"),
            timings=timings,
            nse_mcp_commercial_status=NSE_MCP_COMMERCIAL_STATUS,
            security_type_status=UNSUPPORTED_SECURITY_TYPE,
            dataset=None,
            capital_events=capital_events,
        )

    t = perf_counter()
    discovered = _discover_sources(listing, sources)
    timings["discover"] = perf_counter() - t

    supplied_docs = tuple(documents or ())
    text = document_text or ""
    chars: list[Any] = []
    strategy = None
    t = perf_counter()
    if supplied_docs:
        for record in supplied_docs:
            body = document_text_from_payload(record.payload, content_type=record.content_type)
            chars.append(
                identify_document_characteristics(
                    url=record.url,
                    payload=record.payload,
                    text=body,
                    retrieved_at=record.retrieved_at,
                    content_hash=record.document_hash,
                    document_date=record.document_date,
                )
            )
            if body and not text:
                text = body
                document_url = document_url or record.url
        strategy = chars[0].extraction_strategy if chars else None
    elif text:
        strategy = select_extraction_strategy(text=text)
        chars.append(
            identify_document_characteristics(
                url=document_url or "",
                text=text,
                retrieved_at=utc_now(),
            )
        )
    timings["retrieve"] += perf_counter() - t

    events = list(capital_events)
    if text and not events:
        events.extend(attack_corporate_actions(text))

    candidate_map = {
        field: tuple(items) for field, items in (candidates or {}).items()
    }
    fields = tuple(
        dict.fromkeys(
            (
                *plan.missing_fields,
                *plan.stale_fields,
                *plan.existing_verified,
            )
        )
    )
    if not fields:
        fields = plan.requested_fields

    outcomes: list[FieldAcquisitionOutcome] = []
    ledger: list[EvidenceItem] = []
    for field in fields:
        if field in existing_verified and field not in stale_fields:
            continue
        outcome = _acquire_one_field(
            listing,
            field,
            plan=plan,
            discovered=discovered,
            injected=candidate_map.get(field, ()),
            document_text=text,
            document_url=document_url,
            documents=supplied_docs,
            retrieve_fn=retrieve_fn,
            capital_events=tuple(events),
            judge=judge,
            policy=policy,
            production=production,
            mode=request.mode,
            timings=timings,
        )
        outcomes.append(outcome)
        if outcome.evidence is not None:
            ledger.append(outcome.evidence)

    verified = tuple(item.field for item in outcomes if item.status == "VERIFIED")
    unknown = tuple(item.field for item in outcomes if item.status == "UNKNOWN")
    conflicts = tuple(item.field for item in outcomes if item.status == "CONFLICT")
    refresh = tuple(
        item.field for item in outcomes if item.status == "REFRESH_REQUIRED"
    )
    dataset = _dataset_from_ledger(
        listing,
        request,
        ledger,
        judge=judge,
        production=production,
        capital_events=tuple(events),
        verified_fields=verified,
    )
    blocked = _blocked_calculations(dataset, plan.capability, verified)
    return PlannedAcquisitionResult(
        plan=plan,
        outcomes=tuple(outcomes),
        evidence=tuple(ledger),
        verified_fields=verified,
        unknown_fields=unknown,
        conflicts=conflicts,
        refresh_required=refresh,
        blocked_calculations=blocked,
        timings=timings,
        nse_mcp_commercial_status=NSE_MCP_COMMERCIAL_STATUS,
        security_type_status=plan.capability,
        dataset=dataset,
        capital_events=tuple(events),
        document_characteristics=tuple(chars),
        extraction_strategy=strategy,
    )


def normalize_extracted_field(
    listing: SecurityListing,
    extracted: ExtractedField,
    *,
    source_url: str | None,
    source_type: str,
    source: str,
    retrieved_at: datetime,
    document_hash: str | None = None,
    document_date: date | None = None,
    document_text: str = "",
    mode: str = "MOCK",
    agent: str = "official_research",
) -> EvidenceItem:
    """Convert an extracted candidate to RAW evidence. Ambiguity stays UNKNOWN."""
    identity: str = "PASS"
    if document_text and not document_identity_matches(
        document_text, isin=listing.isin, company_name=listing.company_name
    ):
        identity = "FAIL"
    semantic = "PASS" if extracted.semantic_status == "VERIFIED" else extracted.semantic_status
    semantic_check = "PASS" if semantic in {"PASS", "VERIFIED"} else "FAIL"
    share_type = None
    if extracted.field == "shares_outstanding":
        share_type = classify_share_semantic_type(extracted.locator or "")
        if share_type != VALUATION_SHARE_SEMANTIC:
            semantic_check = "FAIL"
    unit = extracted.raw_unit or extracted.unit_scale
    basis = extracted.statement_basis
    as_of = extracted.as_of
    value = extracted.value or None
    if value == "":
        value = None
    freshness: str = "PASS"
    if as_of is None:
        freshness = "UNKNOWN"
    if extracted.field in _FINANCIAL_CONTEXT_FIELDS:
        if unit is None or basis is None or as_of is None:
            freshness = "UNKNOWN"
            semantic_check = "FAIL" if semantic_check == "PASS" else semantic_check
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field=extracted.field,
        value=value,
        as_of=as_of,
        retrieved_at=retrieved_at,
        source=source,
        source_type=source_type,
        source_url=source_url,
        document_date=document_date or as_of,
        evidence_locator=extracted.locator,
        currency=extracted.currency,
        unit=unit,
        statement_basis=basis,
        agent=agent,
        identity_status=identity,
        semantic_status=semantic_check if semantic_check in {"PASS", "FAIL", "UNKNOWN", "UNAVAILABLE"} else "UNKNOWN",
        freshness_status=freshness if freshness in {"PASS", "FAIL", "UNKNOWN", "UNAVAILABLE"} else "UNKNOWN",
        corporate_action_status="PASS",
        confidence=None,
        stage="RAW",
        status="UNKNOWN",
        mode=mode if mode in {"LIVE", "MOCK"} else "MOCK",
        raw_value=extracted.raw_value,
        raw_unit=extracted.raw_unit,
        restated=extracted.restated,
        document_hash=document_hash,
        period=None if as_of is None else as_of.isoformat(),
        current_through=as_of,
    )


def _discover_sources(listing: SecurityListing, sources) -> tuple[str, ...]:
    _ = listing
    urls: list[str] = []
    for url in sources.candidate_urls:
        kind = classify_source_url(url)
        if kind in {"forbidden", "secondary"}:
            continue
        if kind == "unknown":
            kind = classify_source_url(url, source_type="company_ir")
        if kind in {"primary", "approved_research"}:
            urls.append(url)
    for url in (
        sources.investor_relations_url,
        sources.annual_report_url,
        sources.financial_results_url,
        sources.nse_announcements_url,
        sources.nse_financial_results_url,
    ):
        if url and url not in urls:
            urls.append(url)
    return tuple(urls)


def _acquire_one_field(
    listing: SecurityListing,
    field: str,
    *,
    plan: ResearchPlan,
    discovered: tuple[str, ...],
    injected: Sequence[EvidenceItem],
    document_text: str,
    document_url: str | None,
    documents: tuple[DocumentRecord, ...],
    retrieve_fn: RetrieveFn | None,
    capital_events: tuple[CapitalEvent, ...],
    judge: EvidenceJudge,
    policy: SourcePolicy,
    production: bool,
    mode: str,
    timings: dict[str, float],
) -> FieldAcquisitionOutcome:
    failures: list[ResearchFailure] = []
    tried: list[str] = []
    raw_items: list[EvidenceItem] = []
    _ = plan
    _ = field_source_priority(field)
    _ = field_retrieval_strategy(field)

    t = perf_counter()
    ordered = _order_candidates(field, injected)
    timings["discover"] += perf_counter() - t

    t = perf_counter()
    for item in ordered:
        key = item.source_url or item.source
        if key in tried:
            continue
        tried.append(key)
        if item.value in {None, ""}:
            failures.append(
                ResearchFailure(
                    "EXTRACTION_FAILURE",
                    "candidate had no value; trying next approved source",
                    field=field,
                )
            )
            continue
        raw_items.append(item if item.stage == "RAW" else replace(item, stage="RAW", status="UNKNOWN"))
    timings["retrieve"] += perf_counter() - t

    t = perf_counter()
    if retrieve_fn is not None:
        for url in discovered:
            if url in tried:
                continue
            tried.append(url)
            payload = retrieve_fn(url)
            if isinstance(payload, RetrievalFailure):
                code = map_retrieval_to_failure_code(payload.reason, payload.http_status)
                failures.append(ResearchFailure(code, payload.reason, field=field))
                continue
            body = document_text_from_payload(payload.payload, content_type=payload.content_type)
            if not body:
                failures.append(
                    ResearchFailure("EXTRACTION_FAILURE", "no usable text layer", field=field)
                )
                continue
            extracted = extract_labeled_field(body, field)
            if extracted is None or not extracted.value:
                failures.append(
                    ResearchFailure("EXTRACTION_FAILURE", "label not found", field=field)
                )
                continue
            source_type = _source_type_for_url(url)
            raw_items.append(
                normalize_extracted_field(
                    listing,
                    extracted,
                    source_url=url,
                    source_type=source_type,
                    source=source_type,
                    retrieved_at=payload.retrieved_at,
                    document_hash=payload.document_hash,
                    document_text=body,
                    mode=mode,
                )
            )
    timings["retrieve"] += perf_counter() - t

    t = perf_counter()
    if not raw_items and document_text:
        extracted = extract_labeled_field(document_text, field)
        timings["extract"] += perf_counter() - t
        t = perf_counter()
        if extracted is None or not extracted.value:
            failures.append(
                ResearchFailure(
                    "MISSING_REQUIRED_DATA" if field in plan.required_fields else "EXTRACTION_FAILURE",
                    "no extractable labeled value",
                    field=field,
                )
            )
        else:
            context = parse_document_context(document_text)
            if field in _FINANCIAL_CONTEXT_FIELDS:
                if context.unit_scale is None and extracted.raw_unit is None:
                    failures.append(ResearchFailure("UNIT_UNKNOWN", "units unknown", field=field))
                    return FieldAcquisitionOutcome(
                        field=field,
                        status="UNKNOWN",
                        stage_reached="extract",
                        evidence=None,
                        sources_tried=tuple(tried) or (document_url or "document",),
                        failures=tuple(failures),
                        currentness="UNKNOWN",
                    )
                if context.statement_basis is None and extracted.statement_basis is None:
                    failures.append(ResearchFailure("BASIS_UNKNOWN", "consolidated/standalone unknown", field=field))
                    return FieldAcquisitionOutcome(
                        field=field,
                        status="UNKNOWN",
                        stage_reached="extract",
                        evidence=None,
                        sources_tried=tuple(tried) or (document_url or "document",),
                        failures=tuple(failures),
                        currentness="UNKNOWN",
                    )
                if extracted.as_of is None:
                    failures.append(ResearchFailure("PERIOD_UNKNOWN", "period unknown", field=field))
                    return FieldAcquisitionOutcome(
                        field=field,
                        status="UNKNOWN",
                        stage_reached="extract",
                        evidence=None,
                        sources_tried=tuple(tried) or (document_url or "document",),
                        failures=tuple(failures),
                        currentness="UNKNOWN",
                    )
            source_url = document_url or (documents[0].url if documents else None)
            source_type = _source_type_for_url(source_url)
            raw_items.append(
                normalize_extracted_field(
                    listing,
                    extracted,
                    source_url=source_url,
                    source_type=source_type,
                    source=source_type,
                    retrieved_at=utc_now(),
                    document_hash=documents[0].document_hash if documents else None,
                    document_text=document_text,
                    mode=mode,
                )
            )
        timings["normalize"] += perf_counter() - t
    else:
        timings["extract"] += perf_counter() - t

    if not raw_items:
        code = "MISSING_REQUIRED_DATA" if field in plan.required_fields else "SOURCE_UNAVAILABLE"
        if not any(item.field == field for item in failures):
            failures.append(ResearchFailure(code, "no approved source produced a value", field=field))
        return FieldAcquisitionOutcome(
            field=field,
            status="UNKNOWN",
            stage_reached="retrieve" if tried else "discover",
            evidence=None,
            sources_tried=tuple(tried),
            failures=tuple(failures),
            currentness="UNKNOWN",
        )

    t = perf_counter()
    primaries = [
        item
        for item in raw_items
        if policy.may_verify(item.source_url, source_type=item.source_type)
    ]
    research = [
        item
        for item in raw_items
        if policy.may_cross_check(item.source_url, source_type=item.source_type)
    ]
    clash = None
    if len({item.value for item in primaries}) > 1:
        failures.append(
            ResearchFailure(
                "RECONCILIATION_CONFLICT",
                "two primary values differ; refusing silent pick",
                field=field,
            )
        )
        timings["reconcile"] += perf_counter() - t
        sample = primaries[0]
        return FieldAcquisitionOutcome(
            field=field,
            status="CONFLICT",
            stage_reached="reconcile",
            evidence=replace(sample, stage="RECONCILED", status="CONFLICT"),
            sources_tried=tuple(tried),
            failures=tuple(failures),
            currentness="CONFLICT",
            semantic_type=_share_type(sample) if field == "shares_outstanding" else None,
        )
    chosen = primaries[0] if primaries else None
    if chosen is None and research:
        chosen = research[0]
    if chosen is not None and research and primaries:
        weaker = research[0]
        clash = record_source_clash(
            field=field,
            primary_url=chosen.source_url or "",
            primary_value=str(chosen.value),
            research_url=weaker.source_url or "",
            research_value=str(weaker.value),
        )
    timings["reconcile"] += perf_counter() - t
    if chosen is None:
        failures.append(
            ResearchFailure("MISSING_REQUIRED_DATA", "no primary or cross-check candidate", field=field)
        )
        return FieldAcquisitionOutcome(
            field=field,
            status="UNKNOWN",
            stage_reached="reconcile",
            evidence=None,
            sources_tried=tuple(tried),
            failures=tuple(failures),
            currentness="UNKNOWN",
        )

    t = perf_counter()
    if field == "shares_outstanding":
        share_type = classify_share_semantic_type(chosen.evidence_locator or "")
        if share_type != VALUATION_SHARE_SEMANTIC and share_type != "UNKNOWN":
            failures.append(
                ResearchFailure(
                    "SEMANTIC_FAILURE",
                    f"{share_type} cannot feed the valuation share denominator",
                    field=field,
                )
            )
            timings["verify"] += perf_counter() - t
            return FieldAcquisitionOutcome(
                field=field,
                status="UNKNOWN",
                stage_reached="verify",
                evidence=replace(chosen, semantic_status="FAIL", status="UNKNOWN", stage="RECONCILED"),
                sources_tried=tuple(tried),
                failures=tuple(failures),
                currentness="UNKNOWN",
                semantic_type=share_type,
            )
        ca_status = _share_ca_status(chosen, capital_events)
        chosen = replace(chosen, corporate_action_status=ca_status)
    if chosen.identity_status != "PASS":
        failures.append(ResearchFailure("IDENTITY_FAILURE", "document identity failed", field=field))
    if chosen.freshness_status == "FAIL":
        failures.append(ResearchFailure("FRESHNESS_FAILURE", "evidence is stale", field=field))
    promoted = judge.promote(chosen, production=production)
    if promoted.status == "VERIFIED":
        promoted = replace(
            promoted,
            last_verified_at=utc_now(),
            current_through=promoted.current_through or promoted.as_of,
        )
    label = currentness_label(
        field=field,
        as_of=promoted.as_of,
        retrieved_at=promoted.retrieved_at,
        current_through=promoted.current_through,
        freshness_status=promoted.freshness_status,
        corporate_action_status=str(promoted.corporate_action_status),
        corporate_actions=capital_events,
    )
    if promoted.as_of is None and promoted.status == "VERIFIED":
        promoted = replace(promoted, status="UNKNOWN", stage="RECONCILED")
        failures.append(ResearchFailure("PERIOD_UNKNOWN", "period unknown", field=field))
    timings["verify"] += perf_counter() - t
    status = promoted.status
    if status == "VERIFIED" and label == "STALE":
        status = "REFRESH_REQUIRED"
        promoted = replace(promoted, status="REFRESH_REQUIRED", stage="RECONCILED")
        failures.append(ResearchFailure("FRESHNESS_FAILURE", "currentness review failed", field=field))
    return FieldAcquisitionOutcome(
        field=field,
        status=status,
        stage_reached="verify",
        evidence=promoted,
        sources_tried=tuple(tried),
        failures=tuple(failures),
        currentness=label if status != "CONFLICT" else "CONFLICT",
        semantic_type=_share_type(promoted) if field == "shares_outstanding" else None,
        cross_check=clash,
    )


def _order_candidates(field: str, items: Sequence[EvidenceItem]) -> tuple[EvidenceItem, ...]:
    def key(item: EvidenceItem) -> tuple[int, int]:
        kind = classify_source_url(item.source_url, source_type=item.source_type)
        return source_authority_rank(field, kind, source_type=item.source_type)

    return tuple(sorted(items, key=key))


def _source_type_for_url(url: str | None) -> str:
    kind = classify_source_url(url)
    if kind == "primary":
        host = (url or "").lower()
        if "nseindia" in host or "bseindia" in host:
            return "exchange_eod" if "eod" in host or "archives" in host else "regulator"
        return "company_ir"
    if kind == "approved_research":
        return "approved_research"
    if kind == "secondary":
        return "secondary"
    if url:
        return "company_ir"
    return "company_ir"


def _share_type(item: EvidenceItem) -> str:
    return classify_share_semantic_type(item.evidence_locator or "")


def _share_ca_status(
    item: EvidenceItem, events: tuple[CapitalEvent, ...]
) -> FailureStatus:
    """Calendar passage is not a capital change. Only later capital-changing events stale the count."""
    if item.as_of is None:
        return "UNKNOWN"
    horizon = item.retrieved_at.date()
    for event in events:
        if (
            event.capital_changing
            and event.event_date > item.as_of
            and event.event_date <= horizon
        ):
            return "REFRESH_REQUIRED"
    return "PASS"


def _dataset_from_ledger(
    listing: SecurityListing,
    request: ResearchRequest,
    ledger: Sequence[EvidenceItem],
    *,
    judge: EvidenceJudge,
    production: bool,
    capital_events: tuple[CapitalEvent, ...],
    verified_fields: tuple[str, ...],
) -> VerifiedDataset:
    price = None
    for item in ledger:
        if item.field == "eod_close" and item.status == "VERIFIED" and item.value and item.as_of:
            try:
                price = PriceSnapshot(
                    price=Decimal(item.value),
                    price_kind="EOD",
                    as_of=item.as_of,
                    retrieved_at=item.retrieved_at,
                    currency=item.currency or "INR",
                    source=item.source,
                    isin=listing.isin,
                    mic=listing.mic,
                    raw_price_field=item.raw_price_field or "ClsPric",
                    ticker=listing.ticker,
                    source_url=item.source_url,
                    evidence_locator=item.evidence_locator,
                    mode=item.mode,
                )
            except (InvalidOperation, ValueError):
                price = None
            break
    result = ResearchResult(
        identity_status="VERIFIED",
        isin=listing.isin,
        mic=listing.mic,
        company=listing.company_name,
        ticker=listing.ticker,
        evidence=tuple(ledger),
        price=price,
        claims=(),
        unresolved=(),
        mode=request.mode,
        verified_fields=verified_fields,
    )
    return judge.build_verified_dataset(
        result, production=production, capital_events=capital_events
    )


def _blocked_calculations(
    dataset: VerifiedDataset | None,
    capability: str,
    verified: tuple[str, ...],
) -> tuple[str, ...]:
    if capability != "equity":
        return ("DCF",)
    if dataset is None:
        return ("DCF", "earnings_multiple", "book_value")
    gate = dsp_gate(dataset)
    blocked: list[str] = []
    for method in ("dcf", "earnings_multiple", "book_value"):
        if method not in gate.allowed_methods:
            blocked.append(method.upper() if method == "dcf" else method)
    if "shares_outstanding" not in verified and "DCF" not in blocked:
        blocked.append("DCF")
    return tuple(dict.fromkeys(blocked))


