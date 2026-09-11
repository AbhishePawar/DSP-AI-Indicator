"""RAW → RECONCILED → VERIFIED. Agents cannot write VERIFIED."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from time import perf_counter

from data_engine.official_research.currentness import (
    CapitalEvent,
    evaluate_freshness,
)
from data_engine.official_research.dsp_gate import (
    default_unverified_assumptions,
    dsp_gate,
)
from data_engine.official_research.evidence_identity import (
    IDENTITY_MISMATCH,
    IDENTITY_VERIFIED,
    classify_security_identity,
    dedupe_evidence,
    identities_comparable,
)
from data_engine.official_research.extraction import (
    VALUATION_SHARE_SEMANTIC,
    canonicalize_period,
    canonical_share_semantic_type,
    classify_share_semantic_type,
    normalize_numeric_to_actual,
    periods_comparable,
    price_semantic_kind,
)
from data_engine.official_research.models import (
    EvidenceItem,
    EvidenceStage,
    FailureStatus,
    ResearchResult,
)
from data_engine.official_research.source_policy import (
    SourcePolicy,
    authority_tier_for,
    field_policy,
    record_source_clash,
)
from data_engine.official_research.verified_dataset import (
    FinancialField,
    FinancialSnapshotVerified,
    SecurityIdentity,
    ShareCountSnapshot,
    VerifiedDataset,
)
from data_engine.security_master.models import UNSUPPORTED_SECURITY_TYPES

__all__ = [
    "CONFLICT_CLASSES",
    "EvidenceEdge",
    "EvidenceGraph",
    "EvidenceJudge",
    "EvidenceNode",
    "ReconciliationDecision",
    "classify_conflict_reason",
]

CONFLICT_CLASSES: frozenset[str] = frozenset(
    {
        "TRUE_CONFLICT",
        "TIME_DIFFERENCE",
        "SEMANTIC_DIFFERENCE",
        "PERIOD_DIFFERENCE",
        "UNIT_DIFFERENCE",
        "CURRENCY_DIFFERENCE",
        "CONSOLIDATION_DIFFERENCE",
        "CORPORATE_ACTION_DIFFERENCE",
        "IDENTITY_MISMATCH",
        "SOURCE_STALENESS",
        "UNRESOLVED",
        "NORMALIZED_MATCH",
        "PRIMARY_AUTHORITY_RETAINED",
        "AI_CLAIM_REJECTED",
        "SEMANTIC_REJECTION",
        "DEDUPLICATED",
        "CORPORATE_ACTION_CONTEXT",
    }
)
_PRIMARY_TIERS = frozenset({"TIER_1A", "TIER_1B"})
_AI_TYPES = frozenset({"llm", "agent_claim"})


@dataclass(frozen=True, slots=True)
class EvidenceNode:
    node_id: str
    kind: str
    label: str


@dataclass(frozen=True, slots=True)
class EvidenceEdge:
    src: str
    dst: str
    relation: str


@dataclass(frozen=True, slots=True)
class EvidenceGraph:
    nodes: tuple[EvidenceNode, ...]
    edges: tuple[EvidenceEdge, ...]


@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    status: FailureStatus
    conflict_class: str | None
    identity_class: str
    chosen: EvidenceItem | None
    retained: tuple[EvidenceItem, ...]
    cross_check: dict[str, object] | None
    reason: str
    timings: dict[str, float]
    graph: EvidenceGraph
    freshness_label: str | None = None
    normalized_match: bool = False
    deduplicated: bool = False


def classify_conflict_reason(
    left: EvidenceItem,
    right: EvidenceItem,
    *,
    field: str,
    capital_events: tuple[CapitalEvent, ...] = (),
) -> str:
    """Why two candidates differ. Different timestamps are not TRUE_CONFLICT."""
    _ = field
    if not identities_comparable(left, right):
        return "IDENTITY_MISMATCH"
    left_ccy = str(left.currency or "").strip().upper()
    right_ccy = str(right.currency or "").strip().upper()
    if left_ccy and right_ccy and left_ccy != right_ccy:
        return "CURRENCY_DIFFERENCE"
    if (
        left.statement_basis
        and right.statement_basis
        and left.statement_basis != right.statement_basis
    ):
        return "CONSOLIDATION_DIFFERENCE"
    left_kind = left.semantic_kind or _infer_semantic_kind(left)
    right_kind = right.semantic_kind or _infer_semantic_kind(right)
    if left_kind and right_kind and left_kind != right_kind and "UNKNOWN" not in {
        left_kind,
        right_kind,
    }:
        return "SEMANTIC_DIFFERENCE"
    left_period = canonicalize_period(left.period, as_of=left.as_of)
    right_period = canonicalize_period(right.period, as_of=right.as_of)
    if (left.period or right.period) and left_period and right_period:
        if not periods_comparable(left_period, right_period):
            return "PERIOD_DIFFERENCE"
    if left.as_of and right.as_of and left.as_of != right.as_of:
        earlier = left.as_of if left.as_of < right.as_of else right.as_of
        later = right.as_of if left.as_of < right.as_of else left.as_of
        for event in capital_events:
            if event.capital_changing and earlier < event.event_date <= later:
                return "CORPORATE_ACTION_DIFFERENCE"
        return "TIME_DIFFERENCE"
    left_n = _comparable_number(left)
    right_n = _comparable_number(right)
    left_unit = str(left.unit or left.raw_unit or "").strip().lower()
    right_unit = str(right.unit or right.raw_unit or "").strip().lower()
    if left_unit and right_unit and left_unit != right_unit:
        if left_n is None or right_n is None:
            return "UNIT_DIFFERENCE"
        if left_n == right_n:
            return "NORMALIZED_MATCH"
        return "TRUE_CONFLICT"
    if left.freshness_status == "FAIL" or right.freshness_status == "FAIL":
        if left_n is not None and right_n is not None and left_n != right_n:
            return "SOURCE_STALENESS"
    if left_n is not None and right_n is not None:
        if left_n == right_n:
            return "NORMALIZED_MATCH"
        return "TRUE_CONFLICT"
    if str(left.value) == str(right.value):
        return "NORMALIZED_MATCH"
    if left_n is None or right_n is None:
        policy = field_policy(left.field)
        if policy.unit_required and (not left_unit or not right_unit):
            return "UNIT_DIFFERENCE"
        return "UNRESOLVED"
    return "UNRESOLVED"


def _infer_semantic_kind(item: EvidenceItem) -> str:
    if item.semantic_kind:
        if item.field == "shares_outstanding":
            return canonical_share_semantic_type(item.semantic_kind)
        return item.semantic_kind
    if item.field == "shares_outstanding":
        return canonical_share_semantic_type(item.evidence_locator or "")
    if item.field in {"eod_close", "last_price", "price"}:
        return price_semantic_kind(
            field=item.field,
            raw_price_field=item.raw_price_field,
            source_type=item.source_type,
        )
    if item.statement_basis in {"consolidated", "standalone"}:
        return item.statement_basis.upper()
    return "UNKNOWN"


def _comparable_number(item: EvidenceItem) -> Decimal | None:
    unit = item.unit or item.raw_unit
    normalized = normalize_numeric_to_actual(item.value, unit)
    if normalized is not None:
        return normalized
    if unit:
        return None
    if item.value is None or str(item.value).strip() == "":
        return None
    try:
        return Decimal(str(item.value).strip().replace(",", "").replace("₹", ""))
    except (InvalidOperation, ValueError):
        return None


def _is_ai(item: EvidenceItem) -> bool:
    return item.source_type in _AI_TYPES or str(item.agent or "") in {
        "gemini_find",
        "chatgpt_verify",
        "claude_review",
        "deep_search_attack",
        "openai_nse_mcp",
        "openai",
    }


class EvidenceJudge:
    """DSP judge. Never promotes LLM answers or secondary sources."""

    def __init__(self, policy: SourcePolicy | None = None) -> None:
        self._policy = policy or SourcePolicy()

    def ingest_raw(self, item: EvidenceItem) -> EvidenceItem:
        if item.stage != "RAW":
            raise ValueError("ingest_raw requires stage=RAW")
        if item.status == "VERIFIED":
            raise ValueError("RAW evidence cannot already be VERIFIED")
        return item

    def reconcile(self, item: EvidenceItem) -> EvidenceItem:
        if item.stage != "RAW":
            raise ValueError("reconcile requires RAW evidence")
        if item.identity_status != "PASS":
            return self._copy(item, stage="RECONCILED", status="UNKNOWN")
        if item.semantic_status != "PASS":
            return self._copy(item, stage="RECONCILED", status="UNKNOWN")
        if item.value is None or item.value == "":
            return self._copy(item, stage="RECONCILED", status="UNKNOWN")
        if not self._policy.may_verify(item.source_url, source_type=item.source_type):
            if self._policy.is_discovery_only(
                item.source_url, source_type=item.source_type
            ):
                return self._copy(item, stage="RECONCILED", status="UNAVAILABLE")
            return self._copy(item, stage="RECONCILED", status="UNAVAILABLE")
        return self._copy(item, stage="RECONCILED", status="UNKNOWN")

    def verify(self, item: EvidenceItem, *, production: bool = False) -> EvidenceItem:
        if item.stage != "RECONCILED":
            raise ValueError(
                "verify requires RECONCILED evidence; RAW cannot enter DSP"
            )
        if production and item.mode == "MOCK":
            return self._copy(item, status="UNAVAILABLE")
        if item.value is None or item.value == "":
            return self._copy(item, status="UNKNOWN")
        if item.identity_class == IDENTITY_MISMATCH:
            return self._copy(item, status="REJECTED")
        if item.identity_status != "PASS" or item.semantic_status != "PASS":
            return self._copy(item, status="UNKNOWN")
        if item.field == "shares_outstanding":
            share_kind = canonical_share_semantic_type(
                item.semantic_kind or item.evidence_locator or ""
            )
            if share_kind not in {VALUATION_SHARE_SEMANTIC, "UNKNOWN"}:
                return self._copy(item, status="REJECTED")
            share_semantic_unknown = share_kind == "UNKNOWN"
        else:
            share_semantic_unknown = False
        if item.field == "last_price" and item.semantic_kind == "EOD":
            return self._copy(item, status="UNKNOWN")
        if item.field == "eod_close" and item.semantic_kind in {"CURRENT", "DELAYED"}:
            return self._copy(item, status="UNKNOWN")
        if item.freshness_label in {"STALE", "REFRESH_REQUIRED"}:
            return self._copy(item, status="REFRESH_REQUIRED")
        if item.freshness_status == "FAIL":
            return self._copy(item, status="REFRESH_REQUIRED")
        if item.corporate_action_status == "REFRESH_REQUIRED":
            return self._copy(item, status="REFRESH_REQUIRED")
        if item.corporate_action_status == "CONFLICT":
            return self._copy(item, status="CONFLICT")
        if item.corporate_action_status == "FAIL":
            return self._copy(item, status="REFRESH_REQUIRED")
        if (
            item.field == "shares_outstanding"
            and item.corporate_action_status == "UNKNOWN"
        ):
            return self._copy(item, status="UNKNOWN")
        if item.source_type in {"llm", "agent_claim"}:
            return self._copy(item, status="UNAVAILABLE")
        if item.agent == "openai_nse_mcp":
            return self._copy(item, status="UNAVAILABLE")
        if production and self._nse_mcp_commercial_blocked(item):
            return self._copy(item, status="UNAVAILABLE")
        if item.field in {
            "market_cap",
            "enterprise_value",
            "fcf",
            "net_debt",
            "fcf_yield",
            "ev_ebit",
            "ev_ebitda",
            "price_to_earnings",
        }:
            return self._copy(item, status="UNAVAILABLE")
        if item.field == "shares_outstanding" and item.as_of is None:
            return self._copy(item, status="UNKNOWN")
        if item.field == "shares_outstanding" and share_semantic_unknown:
            return self._copy(item, status="UNKNOWN")
        if item.field == "shares_outstanding":
            if item.document_date is None or item.current_through is None:
                return self._copy(item, status="UNKNOWN")
            if not item.source or item.source in {"NONE", "none"}:
                return self._copy(item, status="UNKNOWN")
        if not self._policy.may_verify(item.source_url, source_type=item.source_type):
            return self._copy(item, status="UNAVAILABLE")
        if item.agent in {
            "gemini_find",
            "chatgpt_verify",
            "deep_search_attack",
            "claude_review",
            "openai_nse_mcp",
        } and item.source_type not in {"exchange_eod", "company_ir", "regulator"}:
            return self._copy(item, status="UNAVAILABLE")
        return self._copy(item, stage="VERIFIED", status="VERIFIED")

    def promote(self, item: EvidenceItem, *, production: bool = False) -> EvidenceItem:
        raw = self.ingest_raw(item)
        reconciled = self.reconcile(raw)
        return self.verify(reconciled, production=production)

    def derive_fields(self, dataset: VerifiedDataset):
        """DSP calculation. Derived results are not evidence and cannot be promoted."""
        from data_engine.official_research.derived_fields import derive_dsp_fields

        return derive_dsp_fields(dataset)

    def validate_assumption(self, item, **kwargs):
        """AI may propose; DSP validates. Does not write VERIFIED facts."""
        from data_engine.official_research.assumption_validator import validate_assumption

        return validate_assumption(item, **kwargs)

    def calculate(self, dataset: VerifiedDataset, **kwargs):
        """Deterministic DSP calculations from verified facts + accepted assumptions."""
        from data_engine.official_research.dsp_calculation import run_dsp_calculations

        return run_dsp_calculations(dataset, **kwargs)

    def reconcile_candidates(
        self,
        items: tuple[EvidenceItem, ...],
        *,
        field: str,
        listing: object | None = None,
        capital_events: tuple[CapitalEvent, ...] = (),
        production: bool = False,
        required_as_of: date | None = None,
        security_type: str | None = None,
        capability: str | None = None,
    ) -> ReconciliationDecision:
        """Multi-candidate identity → authority → semantic → freshness → judge.

        Does not write VERIFIED. Callers still promote RAW through ingest/verify.
        """
        _ = production
        timings = {
            "dedup": 0.0,
            "normalize": 0.0,
            "reconcile": 0.0,
            "judge": 0.0,
            "candidates": float(len(items)),
        }
        empty_graph = EvidenceGraph(nodes=(), edges=())
        sec_type = security_type or (
            getattr(listing, "security_type", None) if listing is not None else None
        )
        if sec_type in UNSUPPORTED_SECURITY_TYPES:
            return ReconciliationDecision(
                status="REJECTED",
                conflict_class=None,
                identity_class="IDENTITY_UNKNOWN",
                chosen=None,
                retained=items,
                cross_check=None,
                reason="UNSUPPORTED_SECURITY_TYPE",
                timings=timings,
                graph=empty_graph,
            )
        policy = field_policy(field)
        if capability == "bank_equity" and field == "revenue":
            return ReconciliationDecision(
                status="UNKNOWN",
                conflict_class="SEMANTIC_DIFFERENCE",
                identity_class=IDENTITY_VERIFIED,
                chosen=None,
                retained=items,
                cross_check=None,
                reason="bank_equity revenue is not an ordinary-equity field",
                timings=timings,
                graph=empty_graph,
            )
        if policy.derived:
            return ReconciliationDecision(
                status="UNKNOWN",
                conflict_class=None,
                identity_class=IDENTITY_VERIFIED,
                chosen=None,
                retained=items,
                cross_check=None,
                reason=f"{field} is calculated by DSP from verified inputs",
                timings=timings,
                graph=empty_graph,
            )
        t = perf_counter()
        unique = dedupe_evidence(items)
        timings["dedup"] = perf_counter() - t
        deduplicated = len(unique) < len(items)
        expected_isin = getattr(listing, "isin", None) if listing is not None else None
        expected_mic = getattr(listing, "mic", None) if listing is not None else None
        expected_ticker = getattr(listing, "ticker", None) if listing is not None else None
        t = perf_counter()
        annotated = tuple(
            self._annotate_candidate(
                item,
                field=field,
                expected_isin=expected_isin,
                expected_mic=expected_mic,
                expected_ticker=expected_ticker,
                capital_events=capital_events,
                required_as_of=required_as_of,
            )
            for item in unique
        )
        timings["normalize"] = perf_counter() - t
        t = perf_counter()
        identity_classes = {item.identity_class or "IDENTITY_UNKNOWN" for item in annotated}
        if IDENTITY_MISMATCH in identity_classes:
            timings["reconcile"] = perf_counter() - t
            timings["judge"] = 0.0
            return ReconciliationDecision(
                status="REJECTED",
                conflict_class="IDENTITY_MISMATCH",
                identity_class="IDENTITY_MISMATCH",
                chosen=None,
                retained=annotated,
                cross_check=None,
                reason="never reconcile values belonging to different securities",
                timings=timings,
                graph=self.build_evidence_graph(annotated, field=field, status="REJECTED"),
            )
        if field == "shares_outstanding" and annotated:
            kinds = {item.semantic_kind or _infer_semantic_kind(item) for item in annotated}
            if kinds and kinds.isdisjoint({"TOTAL_OUTSTANDING", "UNKNOWN"}):
                timings["reconcile"] = perf_counter() - t
                return ReconciliationDecision(
                    status="REJECTED",
                    conflict_class="SEMANTIC_REJECTION",
                    identity_class=next(iter(identity_classes), IDENTITY_VERIFIED),
                    chosen=annotated[0],
                    retained=annotated,
                    cross_check=None,
                    reason="weighted-average or other share semantics cannot be outstanding shares",
                    timings=timings,
                    graph=self.build_evidence_graph(annotated, field=field, status="REJECTED"),
                )
        usable = tuple(
            item
            for item in annotated
            if not (
                field == "shares_outstanding"
                and (item.semantic_kind or _infer_semantic_kind(item))
                not in {"TOTAL_OUTSTANDING", "UNKNOWN"}
            )
        )
        primaries = [
            item
            for item in usable
            if item.authority_tier in _PRIMARY_TIERS
            and self._policy.may_verify(item.source_url, source_type=item.source_type)
            and not _is_ai(item)
        ]
        research = [
            item
            for item in usable
            if item.authority_tier == "TIER_1C"
            or self._policy.may_cross_check(item.source_url, source_type=item.source_type)
        ]
        secondaries = [item for item in usable if item.authority_tier == "TIER_2"]
        ai_rows = [item for item in usable if item.authority_tier == "TIER_3" or _is_ai(item)]
        conflict_class: str | None = "DEDUPLICATED" if deduplicated and len(usable) <= 1 else None
        normalized_match = False
        if len(primaries) >= 2:
            reason = classify_conflict_reason(
                primaries[0], primaries[1], field=field, capital_events=capital_events
            )
            conflict_class = reason
            if reason == "NORMALIZED_MATCH":
                normalized_match = True
            elif reason == "TRUE_CONFLICT":
                timings["reconcile"] = perf_counter() - t
                return ReconciliationDecision(
                    status="CONFLICT",
                    conflict_class="TRUE_CONFLICT",
                    identity_class=next(iter(identity_classes), IDENTITY_VERIFIED),
                    chosen=self._copy(primaries[0], stage="RECONCILED", status="CONFLICT"),
                    retained=annotated,
                    cross_check=None,
                    reason="two primary values differ after normalization; refusing silent pick",
                    timings=timings,
                    graph=self.build_evidence_graph(annotated, field=field, status="CONFLICT"),
                )
            elif reason == "UNRESOLVED":
                timings["reconcile"] = perf_counter() - t
                return ReconciliationDecision(
                    status="CONFLICT",
                    conflict_class="UNRESOLVED",
                    identity_class=next(iter(identity_classes), IDENTITY_VERIFIED),
                    chosen=self._copy(primaries[0], stage="RECONCILED", status="CONFLICT"),
                    retained=annotated,
                    cross_check=None,
                    reason="primary evidence remains unresolved",
                    timings=timings,
                    graph=self.build_evidence_graph(annotated, field=field, status="CONFLICT"),
                )
            elif reason == "CORPORATE_ACTION_DIFFERENCE":
                timings["reconcile"] = perf_counter() - t
                return ReconciliationDecision(
                    status="UNKNOWN",
                    conflict_class="CORPORATE_ACTION_CONTEXT",
                    identity_class=next(iter(identity_classes), IDENTITY_VERIFIED),
                    chosen=None,
                    retained=annotated,
                    cross_check=None,
                    reason="prices or shares span a capital event; not averaged",
                    timings=timings,
                    graph=self.build_evidence_graph(annotated, field=field, status="UNKNOWN"),
                    freshness_label="UNKNOWN",
                )
        chosen = primaries[0] if primaries else None
        cross_check = None
        if chosen is not None and research:
            weaker = research[0]
            pair = classify_conflict_reason(
                chosen, weaker, field=field, capital_events=capital_events
            )
            clash = record_source_clash(
                field=field,
                primary_url=chosen.source_url or "",
                primary_value=str(chosen.value),
                research_url=weaker.source_url or "",
                research_value=str(weaker.value),
            )
            clash["conflict_class"] = pair
            clash["winner"] = "primary"
            clash["silent_overwrite"] = False
            cross_check = clash
            if pair == "TRUE_CONFLICT":
                conflict_class = "PRIMARY_AUTHORITY_RETAINED"
        if chosen is not None and secondaries:
            weaker = secondaries[0]
            pair = classify_conflict_reason(
                chosen, weaker, field=field, capital_events=capital_events
            )
            if pair in {"TRUE_CONFLICT", "UNRESOLVED", "NORMALIZED_MATCH", "TIME_DIFFERENCE"}:
                conflict_class = (
                    "PRIMARY_AUTHORITY_RETAINED" if pair == "TRUE_CONFLICT" else pair
                )
                cross_check = {
                    "field": field,
                    "winner": "primary",
                    "silent_overwrite": False,
                    "ai_vote": False,
                    "conflict_class": pair,
                    "stronger_source": chosen.source_url,
                    "stronger_value": chosen.value,
                    "weaker_source": weaker.source_url,
                    "weaker_value": weaker.value,
                }
        if chosen is not None and ai_rows:
            conflict_class = "AI_CLAIM_REJECTED"
        if chosen is None and research:
            chosen = research[0]
        timings["reconcile"] = perf_counter() - t
        t = perf_counter()
        status: FailureStatus = "UNKNOWN"
        freshness = None if chosen is None else chosen.freshness_label
        if chosen is None:
            reason = "no primary or cross-check candidate"
            identity_class = next(iter(identity_classes), "IDENTITY_UNKNOWN")
        elif chosen.freshness_label in {"STALE", "REFRESH_REQUIRED"}:
            status = "REFRESH_REQUIRED"
            reason = "authoritative evidence is stale for the requested window"
            identity_class = chosen.identity_class or IDENTITY_VERIFIED
        else:
            reason = "candidates reconciled; EvidenceJudge still must verify"
            identity_class = chosen.identity_class or IDENTITY_VERIFIED
        if deduplicated and conflict_class is None:
            conflict_class = "DEDUPLICATED"
        timings["judge"] = perf_counter() - t
        return ReconciliationDecision(
            status=status,
            conflict_class=conflict_class,
            identity_class=identity_class,
            chosen=chosen,
            retained=annotated,
            cross_check=cross_check,
            reason=reason,
            timings=timings,
            graph=self.build_evidence_graph(
                annotated, field=field, status=status, chosen=chosen
            ),
            freshness_label=freshness,
            normalized_match=normalized_match,
            deduplicated=deduplicated,
        )

    def _annotate_candidate(
        self,
        item: EvidenceItem,
        *,
        field: str,
        expected_isin: str | None,
        expected_mic: str | None,
        expected_ticker: str | None,
        capital_events: tuple[CapitalEvent, ...],
        required_as_of: date | None,
    ) -> EvidenceItem:
        from dataclasses import replace

        policy = field_policy(field)
        identity_class = classify_security_identity(
            item,
            expected_isin=expected_isin,
            expected_mic=expected_mic,
            expected_ticker=expected_ticker,
        )
        semantic_kind = _infer_semantic_kind(item)
        freshness_label = evaluate_freshness(
            field=field,
            as_of=item.as_of,
            retrieved_at=item.retrieved_at,
            current_through=item.current_through,
            freshness_status=item.freshness_status,
            corporate_action_status=str(item.corporate_action_status),
            corporate_actions=capital_events,
            required_as_of=required_as_of,
            freshness_class=policy.freshness_class,
        )
        tier = authority_tier_for(
            item.source_url, source_type=item.source_type, agent=item.agent
        )
        return replace(
            item,
            identity_class=identity_class,
            semantic_kind=semantic_kind,
            freshness_label=freshness_label,
            authority_tier=tier,
        )

    def build_evidence_graph(
        self,
        items: tuple[EvidenceItem, ...],
        *,
        field: str,
        status: str,
        chosen: EvidenceItem | None = None,
    ) -> EvidenceGraph:
        nodes: list[EvidenceNode] = [
            EvidenceNode("field", "FIELD", field),
            EvidenceNode("verification", "VERIFICATION", status),
        ]
        edges: list[EvidenceEdge] = []
        seen_sec: set[str] = set()
        for item in items:
            sec = f"{item.isin}.{item.mic}"
            if sec not in seen_sec:
                seen_sec.add(sec)
                nodes.append(EvidenceNode(sec, "SECURITY", sec))
                edges.append(EvidenceEdge("field", sec, "for_security"))
            src = f"src:{item.authority_tier or item.source}"
            nodes.append(EvidenceNode(src, "SOURCE", item.source))
            doc = f"doc:{item.document_hash or item.source_url or item.evidence_id}"
            nodes.append(EvidenceNode(doc, "DOCUMENT", item.source_url or item.source))
            claim = f"claim:{item.evidence_id}"
            nodes.append(EvidenceNode(claim, "CLAIM", str(item.value)))
            edges.append(EvidenceEdge(src, doc, "published"))
            edges.append(EvidenceEdge(doc, claim, "asserts"))
            edges.append(EvidenceEdge(claim, "field", "for_field"))
            edges.append(EvidenceEdge(claim, "verification", "judged"))
            if chosen is not None and item.evidence_id == chosen.evidence_id:
                edges.append(EvidenceEdge(claim, "verification", "selected"))
        unique_nodes = tuple({node.node_id: node for node in nodes}.values())
        return EvidenceGraph(nodes=unique_nodes, edges=tuple(edges))

    def build_verified_dataset(
        self,
        result: ResearchResult,
        *,
        extra: tuple[EvidenceItem, ...] = (),
        production: bool = False,
        capital_events: tuple = (),
    ) -> VerifiedDataset:
        """Assemble the only dataset allowed into DSP."""
        if production and result.mode == "MOCK":
            return VerifiedDataset(
                identity=None,
                identity_status="UNAVAILABLE",
                price=None,
                price_status="UNAVAILABLE",
                shares=None,
                shares_status="UNAVAILABLE",
                financials=None,
                corporate_action_status="UNKNOWN",
                evidence=(),
                currentness_status="UNAVAILABLE",
                data_quality_status="UNAVAILABLE",
                valuation_gate=self._unavailable_gate(
                    "MOCK evidence cannot enter production"
                ),
                unresolved=("MOCK evidence cannot enter production",),
                mode=result.mode,
            )
        ledger = tuple(result.evidence) + tuple(extra)
        promoted: list[EvidenceItem] = []
        for item in ledger:
            if item.stage == "VERIFIED" and item.status == "VERIFIED":
                if production and item.mode == "MOCK":
                    continue
                promoted.append(item)
                continue
            if item.stage == "RAW":
                try:
                    promoted.append(self.promote(item, production=production))
                except ValueError:
                    promoted.append(item)
            elif item.stage == "RECONCILED":
                promoted.append(self.verify(item, production=production))
            else:
                promoted.append(item)

        verified_rows = tuple(
            item
            for item in promoted
            if item.stage == "VERIFIED" and item.status == "VERIFIED"
        )
        identity = None
        identity_status: FailureStatus = result.identity_status
        if (
            result.identity_status == "VERIFIED"
            and result.isin
            and result.mic
            and result.ticker
            and result.company
        ):
            identity = SecurityIdentity(
                isin=result.isin,
                mic=result.mic,
                ticker=result.ticker,
                company_name=result.company,
            )
        price = result.price
        price_status: FailureStatus = "UNAVAILABLE"
        if price is not None:
            if price.price_kind == "PREVIOUS_CLOSE":
                price_status = "UNAVAILABLE"
                price = None
            elif any(
                item.field in {"eod_close", "price", "ClsPric"}
                and item.status == "VERIFIED"
                for item in verified_rows
            ):
                price_status = "VERIFIED"
            else:
                price_status = "UNAVAILABLE"
                price = None

        shares = self._shares_from(verified_rows, promoted)
        financials = self._financials_from(promoted)
        unresolved = list(result.unresolved)
        for item in promoted:
            if item.field and item.status in {
                "REFRESH_REQUIRED",
                "CONFLICT",
                "UNKNOWN",
            }:
                unresolved.append(f"{item.field}:{item.status}")

        dataset = VerifiedDataset(
            identity=identity,
            identity_status=identity_status,
            price=price if price_status == "VERIFIED" else None,
            price_status=(
                price_status if identity_status == "VERIFIED" else identity_status
            ),
            shares=shares,
            shares_status=shares.status if shares else "UNAVAILABLE",
            financials=financials,
            corporate_action_status=(
                shares.corporate_action_status if shares else "UNKNOWN"
            ),
            evidence=tuple(promoted),
            currentness_status=(
                "VERIFIED" if price_status == "VERIFIED" else "UNAVAILABLE"
            ),
            data_quality_status=(
                "VERIFIED" if identity_status == "VERIFIED" else identity_status
            ),
            valuation_gate=self._unavailable_gate("pending gate"),
            assumptions=default_unverified_assumptions(),
            unresolved=tuple(dict.fromkeys(unresolved)),
            mode=result.mode,
            capital_events=tuple(capital_events),
        )
        decision = dsp_gate(dataset)
        return VerifiedDataset(
            identity=dataset.identity,
            identity_status=dataset.identity_status,
            price=dataset.price,
            price_status=dataset.price_status,
            shares=dataset.shares,
            shares_status=dataset.shares_status,
            financials=dataset.financials,
            corporate_action_status=dataset.corporate_action_status,
            evidence=dataset.evidence,
            currentness_status=dataset.currentness_status,
            data_quality_status=dataset.data_quality_status,
            valuation_gate=decision.valuation,
            assumptions=decision.assumptions,
            unresolved=dataset.unresolved,
            mode=dataset.mode,
            capital_events=tuple(capital_events),
        )

    @staticmethod
    def _unavailable_gate(detail: str):
        from data_engine.official_research.semantics import ValuationGateResult

        return ValuationGateResult(method=None, status="UNAVAILABLE", detail=detail)

    @staticmethod
    def _decimal(raw: str | None) -> Decimal | None:
        if raw is None or raw == "":
            return None
        try:
            return Decimal(raw)
        except (InvalidOperation, ValueError):
            return None

    def _shares_from(
        self,
        verified_rows: tuple[EvidenceItem, ...],
        all_rows: list[EvidenceItem],
    ) -> ShareCountSnapshot | None:
        for item in all_rows:
            if item.field != "shares_outstanding":
                continue
            if item.status == "REFRESH_REQUIRED":
                value = self._decimal(item.value)
                semantic = canonical_share_semantic_type(
                    item.semantic_kind or item.evidence_locator or ""
                )
                if value is None or item.as_of is None:
                    return ShareCountSnapshot(
                        shares=Decimal("0"),
                        as_of=item.as_of or date.min,
                        current_through=item.current_through or item.as_of or date.min,
                        last_verified_at=item.last_verified_at or item.retrieved_at,
                        source=item.source,
                        corporate_action_status="REFRESH_REQUIRED",
                        status="REFRESH_REQUIRED",
                        evidence_id=item.evidence_id,
                        source_url=item.source_url,
                        corporate_actions_checked=("buyback", "bonus", "split", "esop", "rights"),
                        semantic_type=semantic,
                        ca_checked_through=item.current_through or item.as_of,
                    )
                return ShareCountSnapshot(
                    shares=value,
                    as_of=item.as_of,
                    current_through=item.current_through or item.as_of,
                    last_verified_at=item.last_verified_at or item.retrieved_at,
                    source=item.source,
                    corporate_action_status="REFRESH_REQUIRED",
                    status="REFRESH_REQUIRED",
                    evidence_id=item.evidence_id,
                    source_url=item.source_url,
                    corporate_actions_checked=("buyback", "bonus", "split", "esop", "rights"),
                    semantic_type=semantic,
                    evidence_ids=(item.evidence_id,),
                    ca_checked_through=item.current_through or item.as_of,
                )
        for item in verified_rows:
            if item.field != "shares_outstanding":
                continue
            value = self._decimal(item.value)
            if value is None or value <= 0 or item.as_of is None:
                continue
            semantic = canonical_share_semantic_type(
                item.semantic_kind or item.evidence_locator or ""
            )
            if semantic != VALUATION_SHARE_SEMANTIC:
                continue
            ca_status: FailureStatus = (
                "VERIFIED"
                if item.corporate_action_status in {"PASS", "VERIFIED"}
                else (
                    item.corporate_action_status
                    if item.corporate_action_status
                    in {"REFRESH_REQUIRED", "CONFLICT", "UNKNOWN", "UNAVAILABLE", "REJECTED"}
                    else "UNKNOWN"
                )
            )
            return ShareCountSnapshot(
                shares=value,
                as_of=item.as_of,
                current_through=item.current_through or item.as_of,
                last_verified_at=item.last_verified_at or item.retrieved_at,
                source=item.source,
                corporate_action_status=ca_status,
                status="VERIFIED",
                evidence_id=item.evidence_id,
                source_url=item.source_url,
                document_hash=item.document_hash,
                corporate_actions_checked=("buyback", "bonus", "split", "esop", "rights"),
                semantic_type=semantic,
                evidence_ids=(item.evidence_id,),
                ca_checked_through=item.current_through or item.as_of,
            )
        return None

    def _financials_from(
        self, rows: list[EvidenceItem]
    ) -> FinancialSnapshotVerified | None:
        mapping = {
            "revenue": "revenue",
            "operating_profit": "operating_profit",
            "ebit": "ebit",
            "net_income": "net_income",
            "equity": "equity",
            "cash": "cash",
            "cfo": "cfo",
            "capex": "capex",
            "debt": "debt",
            "total_assets": "total_assets",
            "total_liabilities": "total_liabilities",
        }
        fields: dict[str, FinancialField] = {}
        period_end = None
        basis = None
        field_bases: dict[str, str] = {}
        for name in mapping:
            matches = [item for item in rows if item.field == name]
            verified = [item for item in matches if item.status == "VERIFIED"]
            match: EvidenceItem | None = None
            if len(verified) > 1:
                restated_rows = [
                    item for item in verified if getattr(item, "restated", False)
                ]
                values = {item.value for item in verified}
                bases = {
                    item.statement_basis
                    for item in verified
                    if item.statement_basis
                }
                if restated_rows and len(values) > 1:
                    match = restated_rows[-1]
                elif len(values) > 1 or len(bases) > 1:
                    conflict = verified[0]
                    fields[name] = FinancialField(
                        name=name,
                        value=None,
                        status="CONFLICT",
                        as_of=conflict.as_of,
                        evidence_id=conflict.evidence_id,
                        source=conflict.source,
                    )
                    continue
            if match is None:
                match = next((item for item in matches if item.status == "VERIFIED"), None)
            if match is None:
                match = next(iter(matches), None)
            if match is None:
                fields[name] = FinancialField(
                    name=name, value=None, status="UNAVAILABLE"
                )
                continue
            status = (
                match.status
                if match.status
                in {
                    "VERIFIED",
                    "REFRESH_REQUIRED",
                    "CONFLICT",
                    "UNKNOWN",
                    "UNAVAILABLE",
                    "REJECTED",
                }
                else "UNKNOWN"
            )
            value = self._decimal(match.value) if status == "VERIFIED" else None
            if status != "VERIFIED":
                value = None
            fields[name] = FinancialField(
                name=name,
                value=value,
                status=(
                    status
                    if status != "VERIFIED" or value is not None
                    else "UNAVAILABLE"
                ),
                as_of=match.as_of,
                evidence_id=match.evidence_id,
                source=match.source,
            )
            if period_end is None:
                period_end = match.as_of
            if basis is None:
                basis = match.statement_basis
            if status == "VERIFIED" and match.statement_basis:
                field_bases[name] = match.statement_basis
        labeled = set(field_bases.values())
        if len(labeled) > 1:
            fields = {
                name: (
                    FinancialField(
                        name=name,
                        value=None,
                        status="CONFLICT",
                        as_of=item.as_of,
                        evidence_id=item.evidence_id,
                        source=item.source,
                    )
                    if item.status == "VERIFIED"
                    else item
                )
                for name, item in fields.items()
            }
            basis = None
        if all(item.status == "UNAVAILABLE" for item in fields.values()):
            return FinancialSnapshotVerified(
                revenue=fields["revenue"],
                operating_profit=fields["operating_profit"],
                ebit=fields["ebit"],
                net_income=fields["net_income"],
                equity=fields["equity"],
                cash=fields["cash"],
                cfo=fields["cfo"],
                capex=fields["capex"],
                debt=fields["debt"],
                total_assets=fields["total_assets"],
                total_liabilities=fields["total_liabilities"],
                period_end=period_end,
                statement_basis=basis,
                unit_scale="actual",
            )
        return FinancialSnapshotVerified(
            revenue=fields["revenue"],
            operating_profit=fields["operating_profit"],
            ebit=fields["ebit"],
            net_income=fields["net_income"],
            equity=fields["equity"],
            cash=fields["cash"],
            cfo=fields["cfo"],
            capex=fields["capex"],
            debt=fields["debt"],
            total_assets=fields["total_assets"],
            total_liabilities=fields["total_liabilities"],
            period_end=period_end,
            statement_basis=basis,
            unit_scale="actual",
        )

    @staticmethod
    def _nse_mcp_commercial_blocked(item: EvidenceItem) -> bool:
        url = (item.source_url or "").lower()
        return "mcp.nseindia.in" in url or item.agent == "official_nse_mcp"

    @staticmethod
    def _copy(
        item: EvidenceItem,
        *,
        stage: EvidenceStage | None = None,
        status: FailureStatus | None = None,
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=item.evidence_id,
            company=item.company,
            ticker=item.ticker,
            isin=item.isin,
            mic=item.mic,
            field=item.field,
            value=item.value,
            as_of=item.as_of,
            retrieved_at=item.retrieved_at,
            source=item.source,
            source_type=item.source_type,
            source_url=item.source_url,
            document_date=item.document_date,
            evidence_locator=item.evidence_locator,
            currency=item.currency,
            unit=item.unit,
            statement_basis=item.statement_basis,
            agent=item.agent,
            identity_status=item.identity_status,
            semantic_status=item.semantic_status,
            freshness_status=item.freshness_status,
            corporate_action_status=item.corporate_action_status,
            confidence=item.confidence,
            stage=stage or item.stage,
            status=status or item.status,
            mode=item.mode,
            raw_price_field=item.raw_price_field,
            current_through=item.current_through,
            last_verified_at=item.last_verified_at,
            period=item.period,
            raw_value=item.raw_value,
            raw_unit=item.raw_unit,
            restated=item.restated,
            document_hash=item.document_hash,
            identity_class=item.identity_class,
            conflict_class=item.conflict_class,
            semantic_kind=item.semantic_kind,
            authority_tier=item.authority_tier,
            freshness_label=item.freshness_label,
        )
