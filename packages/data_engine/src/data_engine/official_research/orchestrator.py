"""Provider-neutral research orchestrator: identity → official sources → DSP judge."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from data_engine.official_research.acquisition import acquire_primary_documents
from data_engine.official_research.agents import ResearchAgent, agent_outcome
from data_engine.official_research.currentness import (
    CacheEntry,
    CapitalEvent,
    EvidenceCache,
    cache_key,
    is_current,
    market_cap_status,
)
from data_engine.official_research.documents import DocumentStore
from data_engine.official_research.extraction import (
    attack_corporate_actions,
    document_identity_matches,
    extract_labeled_field,
    extract_shares_outstanding,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.matching import match_udiff_row
from data_engine.official_research.models import (
    EvidenceItem,
    FailureStatus,
    PriceSnapshot,
    ResearchClaim,
    ResearchMode,
    ResearchRequest,
    ResearchResult,
    UdiffCashRow,
    new_evidence_id,
    utc_now,
)
from data_engine.official_research.nse_eod import NseEodBundle, NseEodService
from data_engine.official_research.nse_primary import (
    NsePrimaryBundle,
    NsePrimaryEvidenceService,
)
from data_engine.official_research.price import eod_close_snapshot
from data_engine.official_research.prompt_guard import sanitize_document_text
from data_engine.official_research.semantics import (
    cannot_derive_shares,
    semantic_field_status,
)
from data_engine.official_research.source_policy import SourcePolicy
from data_engine.security_master.models import SecurityListing
from data_engine.security_master.service import SecurityMasterService

__all__ = ["FINANCIAL_FIELDS", "PRICE_FIELDS", "ResearchOrchestrator"]

PRICE_FIELDS = frozenset(
    {"price", "eod_close", "official_closing_price", "cls_pric", "ClsPric"}
)
FINANCIAL_FIELDS = (
    "shares_outstanding",
    "equity",
    "net_income",
    "cfo",
    "capex",
    "ebit",
    "revenue",
    "operating_profit",
    "debt",
    "cash",
    "total_assets",
    "total_liabilities",
)


def _select_nse_row(
    rows: tuple[UdiffCashRow, ...], listing: SecurityListing
) -> UdiffCashRow | None:
    matched = [row for row in rows if match_udiff_row(row, listing)]
    if not matched:
        return None
    eq = [row for row in matched if row.scty_srs == "EQ"]
    pool = eq or matched
    return pool[0]


class ResearchOrchestrator:
    def __init__(
        self,
        *,
        security_master: SecurityMasterService,
        nse_eod: NseEodService | None = None,
        nse_primary: NsePrimaryEvidenceService | None = None,
        judge: EvidenceJudge | None = None,
        cache: EvidenceCache | None = None,
        gemini: ResearchAgent | None = None,
        chatgpt: ResearchAgent | None = None,
        deep_search: ResearchAgent | None = None,
        claude: ResearchAgent | None = None,
        production: bool = False,
        policy: SourcePolicy | None = None,
    ) -> None:
        self._master = security_master
        self._nse_eod = nse_eod
        self._nse_primary = nse_primary
        self._policy = policy or SourcePolicy()
        self._judge = judge or EvidenceJudge(self._policy)
        self._cache = cache or EvidenceCache()
        self._document_store = DocumentStore()
        self._gemini = gemini
        self._chatgpt = chatgpt
        self._deep_search = deep_search
        self._claude = claude
        self._production = production

    def research(
        self,
        request: ResearchRequest,
        *,
        corporate_actions: tuple[CapitalEvent, ...] = (),
        later_filings: tuple[date, ...] = (),
        document_text: str | None = None,
        nse_bundle: NseEodBundle | None = None,
    ) -> ResearchResult:
        if request.mode == "MOCK" and self._production:
            return ResearchResult(
                identity_status="UNAVAILABLE",
                isin=request.isin,
                mic=request.mic,
                company=request.company,
                ticker=request.ticker,
                evidence=(),
                price=None,
                claims=(),
                unresolved=("MOCK evidence cannot enter production",),
                mode=request.mode,
            )
        resolved = self._master.resolve(
            request.ticker or request.company or request.isin or "",
            exchange=request.exchange,
            isin=request.isin,
            mic=request.mic,
        )
        if resolved.status == "AMBIGUOUS":
            return ResearchResult(
                identity_status="UNKNOWN",
                isin=request.isin,
                mic=request.mic,
                company=request.company,
                ticker=request.ticker,
                evidence=(),
                price=None,
                claims=(),
                unresolved=("identity ambiguous — ISIN+MIC required",),
                mode=request.mode,
                agent_outcomes=self._agent_map(),
            )
        if resolved.status != "RESOLVED" or resolved.identity is None:
            status: FailureStatus = (
                "UNKNOWN"
                if resolved.status in {"UNKNOWN", "REJECTED"}
                else "UNAVAILABLE"
            )
            if resolved.status == "UNSUPPORTED":
                status = "UNAVAILABLE"
            return ResearchResult(
                identity_status=status,
                isin=request.isin,
                mic=request.mic,
                company=request.company,
                ticker=request.ticker,
                evidence=(),
                price=None,
                claims=(),
                unresolved=(f"identity {resolved.status}",),
                mode=request.mode,
                agent_outcomes=self._agent_map(),
            )
        listing = resolved.identity
        sanitized = sanitize_document_text(document_text or "")
        primary = self._primary_bundle(listing, request.mode)
        acquired_fields: dict[str, object] = {}
        acquired_url: str | None = None
        if self._nse_eod is not None:
            acquired = acquire_primary_documents(
                listing,
                transport=self._nse_eod.transport,
                announcement_payload=(
                    None if primary is None else primary.announcement_payload
                ),
                extra_urls=request.candidate_urls,
                extra_announcements=(
                    () if primary is None else primary.announcement_documents
                ),
                extra_document_text=sanitized,
                fields=request.fields,
                fetch_registered_ir=request.mode == "LIVE",
                store=self._document_store,
            )
            acquired_fields = acquired.fields
            attacked_extra = acquired.capital_events
            unresolved_acq = list(acquired.issues)
            for failure in acquired.failures:
                unresolved_acq.append(f"{failure.url}: {failure.reason}")
            if acquired.selected_url and not request.document_url:
                acquired_url = acquired.selected_url
            elif acquired.documents and not request.document_url:
                acquired_url = acquired.documents[0].url
            if acquired.sanitized_text:
                sanitized = acquired.sanitized_text
        else:
            attacked_extra = ()
            unresolved_acq = []
        if sanitized and not document_identity_matches(
            sanitized,
            isin=listing.isin,
            company_name=listing.company_name,
        ):
            unresolved_acq.append(
                "document identity mismatch; ignoring document text"
            )
            sanitized = ""
            acquired_fields = {}
        attacked = corporate_actions + attack_corporate_actions(sanitized)
        if primary is not None:
            attacked = attacked + primary.capital_events
        attacked = attacked + attacked_extra
        claims: list[ResearchClaim] = []
        for agent in (self._gemini, self._chatgpt, self._deep_search, self._claude):
            if agent is None:
                continue
            if not agent.available():
                continue
            for field in request.fields:
                claims.append(
                    agent.run(
                        identity=listing.listing_id,
                        field=field,
                        document_text=sanitized,
                    )
                )
        evidence: list[EvidenceItem] = []
        price: PriceSnapshot | None = None
        unresolved: list[str] = list(unresolved_acq)
        if primary is not None:
            unresolved.extend(primary.issues)
            if not primary.last_price_ignored:
                unresolved.append(
                    "quote-equity lastPrice must not enter price evidence"
                )
        wants_price = any(field in PRICE_FIELDS for field in request.fields)
        if wants_price:
            item, snapshot, issue = self._price_evidence(
                listing,
                request.mode,
                nse_bundle=nse_bundle,
            )
            if item is not None:
                evidence.append(item)
            if snapshot is not None:
                price = snapshot
            if issue:
                unresolved.append(issue)
        for field in request.fields:
            if field in PRICE_FIELDS:
                continue
            if cannot_derive_shares("eps") and field == "shares_outstanding":
                pass
            item = self._non_price_field(
                listing,
                field,
                request.mode,
                document_text=sanitized,
                document_url=request.document_url,
                corporate_actions=attacked,
                later_filings=later_filings,
                primary=primary,
                overlay_fields=acquired_fields,
                overlay_url=acquired_url,
            )
            evidence.append(item)
        return ResearchResult(
            identity_status="VERIFIED",
            isin=listing.isin,
            mic=listing.mic,
            company=listing.company_name,
            ticker=listing.ticker,
            evidence=tuple(evidence),
            price=price,
            claims=tuple(claims),
            unresolved=tuple(unresolved),
            mode=request.mode,
            agent_outcomes=self._agent_map(),
        )

    def _agent_map(self) -> dict[str, FailureStatus]:
        return {
            "gemini_find": agent_outcome(self._gemini),
            "chatgpt_verify": agent_outcome(self._chatgpt),
            "deep_search_attack": agent_outcome(self._deep_search),
            "claude_review": agent_outcome(self._claude),
            "dsp_judge": "VERIFIED",
        }

    def _primary_bundle(
        self, listing: SecurityListing, mode: ResearchMode
    ) -> NsePrimaryBundle | None:
        if mode != "LIVE" or self._nse_primary is None:
            return None
        try:
            return self._nse_primary.fetch(listing)
        except LookupError as exc:
            return NsePrimaryBundle(
                fields={},
                capital_events=(),
                announcements_searched=False,
                last_price_ignored=True,
                source_urls={},
                issues=(str(exc),),
            )

    def _price_evidence(
        self,
        listing: SecurityListing,
        mode: ResearchMode,
        *,
        nse_bundle: NseEodBundle | None,
    ) -> tuple[EvidenceItem | None, PriceSnapshot | None, str | None]:
        if listing.mic != "XNSE":
            return (
                None,
                None,
                "BSE venue is separate; NSE EOD MVP requires MIC=XNSE",
            )
        key = cache_key(
            isin=listing.isin,
            mic=listing.mic,
            field="eod_close",
            period=None,
            source="NSE",
        )
        now = utc_now()
        cached = self._cache.get(key, retrieved_at=now)
        if cached is not None and isinstance(cached.value, EvidenceItem):
            snap = None
            if cached.value.value:
                snap = PriceSnapshot(
                    price=Decimal(cached.value.value),
                    price_kind="EOD",
                    as_of=cached.value.as_of or now.date(),
                    retrieved_at=cached.value.retrieved_at,
                    currency=cached.value.currency or "INR",
                    source="NSE",
                    isin=listing.isin,
                    mic=listing.mic,
                    raw_price_field="ClsPric",
                    ticker=listing.ticker,
                    venue="NSE",
                    source_url=cached.value.source_url,
                    evidence_locator=cached.value.evidence_locator,
                    mode=mode,
                )
            return cached.value, snap, None
        bundle = nse_bundle
        if bundle is None:
            if self._nse_eod is None:
                return None, None, "NSE EOD service unavailable"
            try:
                bundle = self._nse_eod.fetch_latest(retrieved_at=now)
            except LookupError as exc:
                return None, None, str(exc)
        row = _select_nse_row(bundle.rows, listing)
        if row is None:
            raw = EvidenceItem(
                evidence_id=new_evidence_id(),
                company=listing.company_name,
                ticker=listing.ticker,
                isin=listing.isin,
                mic=listing.mic,
                field="eod_close",
                value=None,
                as_of=None,
                retrieved_at=bundle.retrieved_at,
                source="NSE",
                source_type="exchange_eod",
                source_url=bundle.discovered.url,
                document_date=None,
                evidence_locator=None,
                currency="INR",
                unit=None,
                statement_basis=None,
                agent="official_nse_eod",
                identity_status="FAIL",
                semantic_status="UNKNOWN",
                freshness_status="UNKNOWN",
                corporate_action_status="UNKNOWN",
                confidence=None,
                stage="RAW",
                status="UNKNOWN",
                mode=mode,
                raw_price_field="ClsPric",
            )
            return (
                self._judge.promote(raw, production=self._production),
                None,
                "ISIN+MIC not in UDiFF",
            )
        try:
            snapshot = eod_close_snapshot(
                row,
                isin=listing.isin,
                mic=listing.mic,
                retrieved_at=bundle.retrieved_at,
                source_url=bundle.discovered.url,
                mode=mode,
            )
        except ValueError as exc:
            return None, None, str(exc)
        freshness = "PASS"
        if not is_current(
            as_of=snapshot.as_of,
            current_through=snapshot.as_of,
            retrieved_at=bundle.retrieved_at,
        ):
            # EOD as_of is the trade date; later retrieval is expected.
            freshness = "PASS"
        session = bundle.market.session_date
        if (
            bundle.market.market_open
            and session is not None
            and snapshot.as_of >= session
        ):
            return None, None, "today's EOD does not exist yet"
        raw = EvidenceItem(
            evidence_id=new_evidence_id(),
            company=listing.company_name,
            ticker=listing.ticker,
            isin=listing.isin,
            mic=listing.mic,
            field="eod_close",
            value=str(snapshot.price),
            as_of=snapshot.as_of,
            retrieved_at=snapshot.retrieved_at,
            source="NSE",
            source_type="exchange_eod",
            source_url=snapshot.source_url,
            document_date=snapshot.as_of,
            evidence_locator=snapshot.evidence_locator,
            currency="INR",
            unit=None,
            statement_basis=None,
            agent="official_nse_eod",
            identity_status="PASS",
            semantic_status="PASS",
            freshness_status=freshness,
            corporate_action_status="PASS",
            confidence="high",
            stage="RAW",
            status="UNKNOWN",
            mode=mode,
            raw_price_field="ClsPric",
            current_through=snapshot.as_of,
            last_verified_at=snapshot.retrieved_at,
            period=snapshot.as_of.isoformat(),
        )
        verified = self._judge.promote(raw, production=self._production)
        self._cache.put(
            key,
            CacheEntry(
                value=verified,
                as_of=verified.as_of,
                current_through=verified.current_through,
                source="NSE",
                retrieved_at=verified.retrieved_at,
            ),
        )
        return verified, snapshot, None

    def _non_price_field(
        self,
        listing: SecurityListing,
        field: str,
        mode: ResearchMode,
        *,
        document_text: str,
        document_url: str | None,
        corporate_actions: tuple[CapitalEvent, ...],
        later_filings: tuple[date, ...],
        primary: NsePrimaryBundle | None = None,
        overlay_fields: dict | None = None,
        overlay_url: str | None = None,
    ) -> EvidenceItem:
        extracted = (
            extract_shares_outstanding(document_text)
            if field == "shares_outstanding"
            else extract_labeled_field(document_text, field)
        )
        overlay = None if overlay_fields is None else overlay_fields.get(field)
        if overlay is not None and getattr(overlay, "semantic_status", None) == "VERIFIED":
            extracted = overlay
            if overlay_url:
                document_url = overlay_url
        primary_field = None if primary is None else primary.fields.get(field)
        if extracted is None and primary_field is not None:
            extracted = primary_field
            if field == "shares_outstanding":
                document_url = primary.source_urls.get(
                    "shareholding"
                ) or primary.source_urls.get("quote_equity")
            else:
                document_url = primary.source_urls.get("financial_results")
        unknown_semantics = extracted is not None and extracted.semantic_status in {
            "UNKNOWN",
            "CONFLICT",
        }
        usable = (
            extracted is not None
            and extracted.semantic_status == "VERIFIED"
            and extracted.value
        )
        as_of = extracted.as_of if extracted is not None else None
        locator = extracted.locator if extracted is not None else None
        value = extracted.value if usable else None
        from_nse_primary = primary_field is not None and extracted is primary_field
        from_overlay = overlay is not None and extracted is overlay
        overlay_is_nse = bool(overlay_url) and "nseindia" in overlay_url.lower()
        if from_nse_primary:
            source = "NSE"
            source_type = "regulator"
            source_url = document_url
            agent = "official_nse_primary"
            statement_basis = None if primary is None else primary.statement_basis
            has_primary_url = bool(source_url) and self._policy.may_verify(
                source_url, source_type="regulator"
            )
            if not has_primary_url:
                source, source_type, source_url = "NONE", "none", None
        elif from_overlay and overlay_is_nse:
            source = "NSE"
            source_type = "regulator"
            source_url = overlay_url
            agent = "official_document"
            statement_basis = extracted.statement_basis
            has_primary_url = bool(source_url) and self._policy.may_verify(
                source_url, source_type="regulator"
            )
            if not has_primary_url:
                source, source_type, source_url = "NONE", "none", None
        else:
            has_primary_url = bool(document_url) and self._policy.may_verify(
                document_url, source_type="company_ir"
            )
            source = "Company IR" if usable and has_primary_url else "NONE"
            source_type = "company_ir" if usable and has_primary_url else "none"
            source_url = document_url if usable and has_primary_url else None
            agent = "document_extract"
            statement_basis = (
                None if extracted is None else extracted.statement_basis
            )
        ca_status: FailureStatus = "UNKNOWN"
        freshness: str = "UNKNOWN"
        now = utc_now()
        searched_ca = bool(document_text) or bool(
            primary is not None and primary.announcements_searched
        )
        if field != "shares_outstanding":
            ca_status = "PASS" if searched_ca or as_of is not None else "UNKNOWN"
        elif corporate_actions and as_of is not None:
            later_events = [
                event
                for event in corporate_actions
                if event.capital_changing
                and event.event_date != date.max
                and event.event_date > as_of
            ]
            ca_status = "REFRESH_REQUIRED" if later_events else "PASS"
        elif corporate_actions:
            dated = [event for event in corporate_actions if event.event_date != date.max]
            ca_status = "REFRESH_REQUIRED" if dated else "UNKNOWN"
        elif searched_ca:
            ca_status = "PASS"
        if (
            later_filings
            and as_of is not None
            and any(item > as_of for item in later_filings)
        ):
            freshness = "FAIL"
            ca_status = "REFRESH_REQUIRED"
        elif as_of is not None and is_current(
            as_of=as_of, current_through=as_of, retrieved_at=now
        ):
            freshness = "PASS"
        _ = cannot_derive_shares("eps")
        _ = market_cap_status
        _ = semantic_field_status
        raw = EvidenceItem(
            evidence_id=new_evidence_id(),
            company=listing.company_name,
            ticker=listing.ticker,
            isin=listing.isin,
            mic=listing.mic,
            field=field,
            value=None if unknown_semantics else value,
            as_of=as_of,
            retrieved_at=now,
            source=source,
            source_type=source_type,
            source_url=source_url,
            document_date=as_of,
            evidence_locator=locator,
            currency=(
                "INR" if value is not None and field != "shares_outstanding" else None
            ),
            unit=(
                None
                if extracted is None
                else extracted.unit_scale or (None if primary is None else primary.unit_scale)
            ),
            statement_basis=statement_basis,
            agent=agent,
            identity_status="PASS",
            semantic_status="FAIL" if unknown_semantics or value is None else "PASS",
            freshness_status=freshness if freshness in {"PASS", "FAIL"} else "UNKNOWN",
            corporate_action_status=ca_status,
            confidence="high" if value is not None and not unknown_semantics else None,
            stage="RAW",
            status="UNKNOWN",
            mode=mode,
            current_through=as_of,
            last_verified_at=now if value is not None else None,
            period=None if as_of is None else as_of.isoformat(),
            raw_value=None if extracted is None else extracted.raw_value,
            raw_unit=None if extracted is None else extracted.raw_unit,
            restated=False if extracted is None else bool(extracted.restated),
        )
        try:
            return self._judge.promote(raw, production=self._production)
        except ValueError:
            return raw
