"""Any-supported-security end-to-end research → DSP pipeline.

Wires existing contracts only:

  user query
  → SecurityMaster search/resolve (ISIN+MIC)
  → automatic ResearchPlan
  → research loop (discover)
  → acquire_planned_fields (retrieve/extract/normalize/reconcile/verify)
  → EvidenceJudge VerifiedDataset
  → SIMPLE-17 derived fields
  → SIMPLE-18 DCF/DSP

Does not branch on ticker, company, or ISIN.
ResearchOrchestrator.research is a thin compatibility wrapper over this pipeline.
"""

from __future__ import annotations

from datetime import date
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Mapping, Sequence

from data_engine.official_research.assumption_contract import CanonicalAssumption
from data_engine.official_research.assumption_validator import validate_assumption_pack
from data_engine.official_research.advanced_check import evaluate_advanced_check
from data_engine.official_research.dsp_calculation import run_dsp_calculations
from data_engine.official_research.currentness import corporate_action_horizon_status
from data_engine.official_research.extraction import VALUATION_SHARE_SEMANTIC
from data_engine.official_research.field_acquisition import (
    PlannedAcquisitionResult,
    acquire_planned_fields,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import (
    EvidenceItem,
    ResearchRequest,
    new_evidence_id,
)
from data_engine.official_research.qualitative import run_qualitative_engines
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS, redact_mcp_text
from data_engine.official_research.prompt_guard import looks_like_injection
from data_engine.official_research.research_loop import run_research_loop
from data_engine.official_research.research_plan import (
    REQUEST_FIELD_GROUPS,
    ResearchPlan,
    build_research_plan,
    classify_research_capability,
    field_source_priority,
    plan_report_block,
)
from data_engine.official_research.verified_dataset import VerifiedDataset
from data_engine.security_master.catalog import SecurityMasterCatalog, load_default_catalog
from data_engine.security_master.models import (
    UNSUPPORTED_SECURITY_TYPES,
    SecurityListing,
)
from data_engine.security_master.service import (
    SecurityMasterService,
    SecurityResolveResult,
    SecuritySearchResult,
)

__all__ = [
    "AUTO_REQUEST_GROUPS",
    "FULL_ANALYSIS_GATES",
    "CoverageReport",
    "EndToEndResult",
    "SupportedUniverse",
    "analyse_listing",
    "analyse_user_query",
    "analysis_state_for",
    "describe_supported_universe",
    "full_analysis_status",
]

AUTO_REQUEST_GROUPS: tuple[str, ...] = (
    "PRICE",
    "FINANCIALS",
    "SHARES",
    "CORPORATE_ACTIONS",
    "BUSINESS_QUALITY",
    "MOAT",
    "RISK",
    "VALUATION_INPUTS",
)

FULL_ANALYSIS_GATES: tuple[str, ...] = (
    "identity_verified",
    "required_financials_verified",
    "price_verified",
    "outstanding_shares_verified",
    "corporate_action_horizon",
    "required_assumptions_accepted",
    "dcf_hard_gates",
)

ANALYSIS_STATES: tuple[str, ...] = (
    "IDENTITY_AMBIGUOUS",
    "UNKNOWN_SECURITY",
    "UNSUPPORTED_SECURITY",
    "REJECTED",
    "RESEARCH_UNAVAILABLE",
    "PARTIAL_DATA",
    "REFRESH_REQUIRED",
    "CONFLICT",
    "VALUATION_BLOCKED",
    "DCF_BLOCKED",
    "ANALYSIS_READY",
    "FULL_ANALYSIS",
)

@dataclass(frozen=True, slots=True)
class SupportedUniverse:
    exchanges: tuple[str, ...]
    mics: tuple[str, ...]
    security_types: tuple[str, ...]
    equity_series: tuple[str, ...]
    listing_count: int
    eligible_count: int
    dual_listed_isins: int
    unsupported_types: tuple[str, ...]
    identity_rule: str
    authority: dict[str, Any]
    aliases_supported: bool
    delisted_handling: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "exchanges": list(self.exchanges),
            "mics": list(self.mics),
            "security_types": list(self.security_types),
            "equity_series": list(self.equity_series),
            "listing_count": self.listing_count,
            "eligible_count": self.eligible_count,
            "dual_listed_isins": self.dual_listed_isins,
            "unsupported_types": list(self.unsupported_types),
            "identity_rule": self.identity_rule,
            "authority": dict(self.authority),
            "aliases_supported": self.aliases_supported,
            "delisted_handling": self.delisted_handling,
            "hardcoded_five_stock_universe": False,
        }


@dataclass(frozen=True, slots=True)
class CoverageReport:
    identity: str
    price: str
    financials: str
    shares: str
    corporate_actions: str
    business_research: str
    risk: str
    moat: str
    valuation: str
    dcf: str
    dsp_conclusion: str
    identity_coverage: float
    price_coverage: float
    financial_coverage: float
    share_coverage: float
    ca_coverage: float
    business_research_coverage: float
    valuation_coverage: float
    dcf_coverage: float
    full_analysis_coverage: float
    automatic_acquisition_success_rate: float
    retrieval_failure_rate: float
    extraction_failure_rate: float
    reconciliation_conflict_rate: float
    unknown_rate: float
    attempted_fields: int
    verified_fields: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    conflict_fields: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "price": self.price,
            "financials": self.financials,
            "shares": self.shares,
            "corporate_actions": self.corporate_actions,
            "business_research": self.business_research,
            "risk": self.risk,
            "moat": self.moat,
            "valuation": self.valuation,
            "dcf": self.dcf,
            "dsp_conclusion": self.dsp_conclusion,
            "metrics": {
                "identity_coverage": self.identity_coverage,
                "price_coverage": self.price_coverage,
                "financial_coverage": self.financial_coverage,
                "share_coverage": self.share_coverage,
                "ca_coverage": self.ca_coverage,
                "business_research_coverage": self.business_research_coverage,
                "valuation_coverage": self.valuation_coverage,
                "dcf_coverage": self.dcf_coverage,
                "full_analysis_coverage": self.full_analysis_coverage,
                "automatic_acquisition_success_rate": self.automatic_acquisition_success_rate,
                "retrieval_failure_rate": self.retrieval_failure_rate,
                "extraction_failure_rate": self.extraction_failure_rate,
                "reconciliation_conflict_rate": self.reconciliation_conflict_rate,
                "unknown_rate": self.unknown_rate,
                "attempted_fields": self.attempted_fields,
            },
            "verified_fields": list(self.verified_fields),
            "unknown_fields": list(self.unknown_fields),
            "conflict_fields": list(self.conflict_fields),
        }


@dataclass(frozen=True, slots=True)
class EndToEndResult:
    query: str
    status: str
    identity_status: str
    listing: SecurityListing | None
    search: SecuritySearchResult | None
    resolve: SecurityResolveResult | None
    plan: ResearchPlan | None
    acquisition: PlannedAcquisitionResult | None
    dataset: VerifiedDataset | None
    dsp: Any
    coverage: CoverageReport
    timings: dict[str, float]
    full_analysis: bool
    gates: dict[str, bool]
    unresolved: tuple[str, ...]
    nse_mcp_commercial_status: str
    production: bool
    detail: str
    source_selection: dict[str, tuple[str, ...]] = field(default_factory=dict)
    analysis_state: str = "PARTIAL_DATA"
    qualitative: Any = None
    advanced_check: Any = None

    def to_public_dict(self) -> dict[str, Any]:
        payload = {
            "query": self.query,
            "status": self.status,
            "analysis_state": self.analysis_state,
            "identity_status": self.identity_status,
            "listing": None if self.listing is None else self.listing.to_public_dict(),
            "plan": None if self.plan is None else plan_report_block(self.plan),
            "coverage": self.coverage.to_public_dict(),
            "timings": dict(self.timings),
            "full_analysis": self.full_analysis,
            "gates": dict(self.gates),
            "unresolved": list(self.unresolved),
            "nse_mcp_commercial_status": self.nse_mcp_commercial_status,
            "production": self.production,
            "detail": self.detail,
            "source_selection": {key: list(val) for key, val in self.source_selection.items()},
            "dsp": None if self.dsp is None else self.dsp.to_public_dict(),
            "derived_is_source_evidence": False,
            "result_contract": self._result_contract(),
        }
        if self.qualitative is not None:
            payload["core_dsp"] = self.qualitative.to_public_dict()
        if self.advanced_check is not None:
            payload["advanced_check"] = self.advanced_check.to_public_dict()
            payload["thesis"] = self.advanced_check.thesis.to_public_dict()
            payload["thesis_breakers"] = [
                item.to_public_dict() for item in self.advanced_check.thesis_breakers
            ]
        return payload

    def _result_contract(self) -> dict[str, Any]:
        derived_names: list[str] = []
        blocked: list[str] = []
        assumptions: list[str] = []
        dsp = self.dsp
        if dsp is not None:
            derived = getattr(dsp, "derived", None)
            if derived is not None:
                for name in (
                    "fcf",
                    "net_debt",
                    "market_cap",
                    "enterprise_value",
                ):
                    item = getattr(derived, name, None)
                    status = getattr(item, "status", None)
                    if status == "CALCULATED":
                        derived_names.append(name)
                    elif status == "BLOCKED":
                        blocked.append(name)
            for name in (
                "dcf",
                "intrinsic_value_per_share",
                "margin_of_safety",
            ):
                item = getattr(dsp, name, None)
                status = getattr(item, "status", None)
                if status == "CALCULATED":
                    derived_names.append(name)
                elif status == "BLOCKED":
                    blocked.append(name)
                assumptions.extend(list(getattr(item, "assumption_ids", ()) or ()))
            for name in ("quality", "moat", "risk"):
                item = getattr(dsp, name, None)
                if getattr(item, "status", None) == "BLOCKED":
                    blocked.append(name)
        return {
            "verified_facts": list(self.coverage.verified_fields),
            "derived_values": derived_names,
            "assumptions": list(dict.fromkeys(assumptions)),
            "blocked_values": blocked,
            "unknown_values": list(self.coverage.unknown_fields),
            "evidence": None if self.acquisition is None else len(self.acquisition.evidence),
            "confidence": self.coverage.dsp_conclusion,
            "currentness": self.coverage.corporate_actions,
            "dsp_conclusion": self.coverage.dsp_conclusion,
            "analysis_state": self.analysis_state,
            "full_analysis": self.full_analysis,
            "core_dsp": None if self.qualitative is None else self.qualitative.status,
            "advanced_check": None if self.advanced_check is None else self.advanced_check.status,
            "thesis": None if self.advanced_check is None else self.advanced_check.thesis.status,
            "overall_score": (
                "NOT_CURRENTLY_DEFINED"
                if self.qualitative is None
                else self.qualitative.overall_score_status
            ),
        }


def describe_supported_universe(
    catalog: SecurityMasterCatalog | None = None,
) -> SupportedUniverse:
    catalog = catalog or load_default_catalog()
    listings = catalog.all()
    types = tuple(sorted({item.security_type for item in listings}))
    exchanges = tuple(sorted({item.exchange for item in listings}))
    mics = tuple(sorted({item.mic for item in listings}))
    series = tuple(sorted({item.series or "" for item in listings if item.series}))
    eligible = tuple(item for item in listings if item.eligibility)
    by_isin: dict[str, set[str]] = {}
    for item in eligible:
        by_isin.setdefault(item.isin, set()).add(item.mic)
    dual = sum(1 for mics_for in by_isin.values() if len(mics_for) > 1)
    aliases = any(item.aliases for item in listings)
    return SupportedUniverse(
        exchanges=exchanges,
        mics=mics,
        security_types=types,
        equity_series=series,
        listing_count=len(listings),
        eligible_count=len(eligible),
        dual_listed_isins=dual,
        unsupported_types=tuple(sorted(UNSUPPORTED_SECURITY_TYPES)),
        identity_rule="ISIN + MIC",
        authority=catalog.authority.to_public_dict(),
        aliases_supported=aliases or True,
        delisted_handling="ineligible series / unsupported type → UNSUPPORTED; not guessed",
    )


def _bucket(statuses: Sequence[str]) -> str:
    if not statuses:
        return "UNKNOWN"
    unique = set(statuses)
    if unique <= {"VERIFIED"}:
        return "VERIFIED"
    if "CONFLICT" in unique:
        return "BLOCKED"
    if "REFRESH_REQUIRED" in unique:
        return "PARTIAL"
    if "VERIFIED" in unique:
        return "PARTIAL"
    if unique <= {"UNAVAILABLE", "BLOCKED", "CALCULATION_BLOCKED"}:
        return "BLOCKED"
    return "UNKNOWN"


def _rate(ok: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return ok / total


def _empty_coverage(*, identity: str = "UNKNOWN") -> CoverageReport:
    return CoverageReport(
        identity=identity,
        price="UNKNOWN",
        financials="UNKNOWN",
        shares="UNKNOWN",
        corporate_actions="UNKNOWN",
        business_research="UNKNOWN",
        risk="UNKNOWN",
        moat="UNKNOWN",
        valuation="UNKNOWN",
        dcf="BLOCKED",
        dsp_conclusion="UNKNOWN",
        identity_coverage=1.0 if identity == "VERIFIED" else 0.0,
        price_coverage=0.0,
        financial_coverage=0.0,
        share_coverage=0.0,
        ca_coverage=0.0,
        business_research_coverage=0.0,
        valuation_coverage=0.0,
        dcf_coverage=0.0,
        full_analysis_coverage=0.0,
        automatic_acquisition_success_rate=0.0,
        retrieval_failure_rate=0.0,
        extraction_failure_rate=0.0,
        reconciliation_conflict_rate=0.0,
        unknown_rate=1.0,
        attempted_fields=0,
        verified_fields=(),
        unknown_fields=(),
        conflict_fields=(),
    )


def full_analysis_status(
    *,
    listing: SecurityListing | None,
    dataset: VerifiedDataset | None,
    dsp: Any,
    assumptions_accepted: bool,
    capability: str,
    research_horizon: date | None = None,
    ca_checked_through: date | None = None,
) -> tuple[bool, dict[str, bool]]:
    identity_ok = (
        listing is not None
        and dataset is not None
        and dataset.identity_status == "VERIFIED"
    )
    required = ("net_income", "equity", "cfo", "cash")
    if capability == "equity":
        required = ("revenue", "net_income", "equity", "cfo", "cash")
    elif capability == "bank_equity":
        required = ("net_income", "equity", "total_assets", "total_liabilities")
    financials_ok = bool(
        dataset is not None
        and all(dataset.field_status(name) == "VERIFIED" for name in required)
    )
    price_ok = bool(dataset is not None and dataset.price_status == "VERIFIED")
    shares_ok = bool(
        dataset is not None
        and dataset.shares_status == "VERIFIED"
        and dataset.shares is not None
        and dataset.shares.semantic_type == VALUATION_SHARE_SEMANTIC
    )
    ca_ok = False
    if shares_ok and dataset is not None and dataset.shares is not None:
        horizon = research_horizon
        if horizon is None and dataset.shares.last_verified_at is not None:
            horizon = dataset.shares.last_verified_at.date()
        checked = ca_checked_through or dataset.shares.ca_checked_through
        ca_ok = (
            dataset.shares.corporate_action_status == "VERIFIED"
            and corporate_action_horizon_status(
                as_of=dataset.shares.as_of,
                checked_through=checked,
                research_horizon=horizon,
            )
            == "CURRENT"
        )
    dcf_ok = bool(dsp is not None and dsp.dcf.status == "CALCULATED")
    gates = {
        "identity_verified": identity_ok,
        "required_financials_verified": financials_ok,
        "price_verified": price_ok,
        "outstanding_shares_verified": shares_ok,
        "corporate_action_horizon": ca_ok,
        "required_assumptions_accepted": assumptions_accepted,
        "dcf_hard_gates": dcf_ok,
    }
    return all(gates.values()), gates


def analysis_state_for(
    *,
    status: str,
    identity_status: str,
    coverage: CoverageReport | None,
    dsp: Any,
    full: bool,
) -> str:
    if status == "REJECTED" or identity_status == "REJECTED":
        return "REJECTED"
    if status == "AMBIGUOUS" or identity_status == "AMBIGUOUS":
        return "IDENTITY_AMBIGUOUS"
    if status == "UNSUPPORTED" or identity_status == "UNSUPPORTED":
        return "UNSUPPORTED_SECURITY"
    if status == "UNAVAILABLE":
        return "RESEARCH_UNAVAILABLE"
    if identity_status in {"UNKNOWN", "UNAVAILABLE"} and status == "UNKNOWN":
        return "UNKNOWN_SECURITY"
    if full:
        return "FULL_ANALYSIS"
    if coverage is not None and coverage.conflict_fields:
        return "CONFLICT"
    if coverage is not None and coverage.corporate_actions == "PARTIAL":
        return "REFRESH_REQUIRED"
    if dsp is not None and getattr(getattr(dsp, "dcf", None), "status", None) == "BLOCKED":
        return "DCF_BLOCKED"
    if coverage is not None and coverage.valuation == "BLOCKED":
        return "VALUATION_BLOCKED"
    if coverage is not None and coverage.verified_fields:
        return "PARTIAL_DATA"
    return "PARTIAL_DATA"


def _coverage(
    *,
    identity: str,
    acquisition: PlannedAcquisitionResult | None,
    dataset: VerifiedDataset | None,
    dsp: Any,
    full: bool,
    capability: str,
) -> CoverageReport:
    outcomes = () if acquisition is None else acquisition.outcomes
    by_field = {item.field: item.status for item in outcomes}
    financial_names = REQUEST_FIELD_GROUPS["FINANCIALS"]
    fin_status = [by_field[name] for name in financial_names if name in by_field]
    price_status = [by_field[name] for name in ("eod_close",) if name in by_field]
    share_status = [by_field[name] for name in ("shares_outstanding",) if name in by_field]
    attempted = len(outcomes)
    verified = tuple(item.field for item in outcomes if item.status == "VERIFIED")
    unknown = tuple(item.field for item in outcomes if item.status == "UNKNOWN")
    conflicts = tuple(item.field for item in outcomes if item.status == "CONFLICT")
    retrieval_fail = 0
    extract_fail = 0
    if acquisition is not None:
        for item in outcomes:
            for fail in item.failures:
                if fail.code in {"HTTP", "NETWORK", "NSE_UNAVAILABLE", "NSE_TIMEOUT", "SOURCE_UNAVAILABLE"}:
                    retrieval_fail += 1
                if fail.code == "EXTRACTION_FAILURE":
                    extract_fail += 1
    dcf_status = "BLOCKED"
    if dsp is not None:
        dcf_status = "VERIFIED" if dsp.dcf.status == "CALCULATED" else "BLOCKED"
    valuation = "UNKNOWN"
    if dataset is not None:
        if dataset.valuation_gate.status == "VERIFIED":
            valuation = "VERIFIED"
        elif dataset.valuation_gate.status in {"UNAVAILABLE", "UNKNOWN"}:
            valuation = "UNKNOWN"
        else:
            valuation = "BLOCKED"
    business = "UNKNOWN"
    if dsp is not None:
        if dsp.quality.status == "CALCULATED":
            business = "PARTIAL"
        if dsp.moat.status == "CALCULATED" and dsp.quality.status == "CALCULATED":
            business = "VERIFIED"
    risk = "UNKNOWN"
    moat = "UNKNOWN"
    if dsp is not None:
        risk = "PARTIAL" if dsp.risk.status == "CALCULATED" else "UNKNOWN"
        moat = "VERIFIED" if dsp.moat.status == "CALCULATED" else "UNKNOWN"
    ca = "UNKNOWN"
    if dataset is not None and dataset.shares is not None:
        if dataset.shares.corporate_action_status == "VERIFIED":
            ca = "VERIFIED"
        elif dataset.shares.corporate_action_status == "REFRESH_REQUIRED":
            ca = "PARTIAL"
        else:
            ca = "UNKNOWN"
    dsp_conclusion = "VERIFIED" if full else ("PARTIAL" if verified else "UNKNOWN")
    _ = capability
    return CoverageReport(
        identity=identity,
        price=_bucket(price_status),
        financials=_bucket(fin_status),
        shares=_bucket(share_status),
        corporate_actions=ca,
        business_research=business,
        risk=risk,
        moat=moat,
        valuation=valuation,
        dcf=dcf_status if dcf_status == "VERIFIED" else "BLOCKED",
        dsp_conclusion=dsp_conclusion,
        identity_coverage=1.0 if identity == "VERIFIED" else 0.0,
        price_coverage=_rate(sum(1 for s in price_status if s == "VERIFIED"), max(1, len(price_status))),
        financial_coverage=_rate(sum(1 for s in fin_status if s == "VERIFIED"), max(1, len(fin_status))),
        share_coverage=_rate(sum(1 for s in share_status if s == "VERIFIED"), max(1, len(share_status))),
        ca_coverage=1.0 if ca == "VERIFIED" else 0.0,
        business_research_coverage=1.0 if business == "VERIFIED" else (0.5 if business == "PARTIAL" else 0.0),
        valuation_coverage=1.0 if valuation == "VERIFIED" else 0.0,
        dcf_coverage=1.0 if dcf_status == "VERIFIED" else 0.0,
        full_analysis_coverage=1.0 if full else 0.0,
        automatic_acquisition_success_rate=_rate(len(verified), attempted),
        retrieval_failure_rate=_rate(retrieval_fail, max(attempted, 1)),
        extraction_failure_rate=_rate(extract_fail, max(attempted, 1)),
        reconciliation_conflict_rate=_rate(len(conflicts), max(attempted, 1)),
        unknown_rate=_rate(len(unknown), max(attempted, 1)),
        attempted_fields=attempted,
        verified_fields=verified,
        unknown_fields=unknown,
        conflict_fields=conflicts,
    )


def _blocked_result(
    query: str,
    *,
    status: str,
    identity_status: str,
    detail: str,
    timings: dict[str, float],
    production: bool,
    search: SecuritySearchResult | None = None,
    resolve: SecurityResolveResult | None = None,
    listing: SecurityListing | None = None,
    plan: ResearchPlan | None = None,
) -> EndToEndResult:
    qualitative = run_qualitative_engines(None, listing) if listing is not None else None
    advanced = None
    if listing is not None:
        advanced = evaluate_advanced_check(
            dataset=None,
            dsp=None,
            qualitative=qualitative,
            listing=listing,
            production=production,
            capability=classify_research_capability(listing),
        )
    return EndToEndResult(
        query=query,
        status=status,
        identity_status=identity_status,
        listing=listing,
        search=search,
        resolve=resolve,
        plan=plan,
        acquisition=None,
        dataset=None,
        dsp=None,
        coverage=_empty_coverage(identity=identity_status if identity_status in {"VERIFIED", "UNKNOWN", "BLOCKED"} else "UNKNOWN"),
        timings=timings,
        full_analysis=False,
        gates={name: False for name in FULL_ANALYSIS_GATES},
        unresolved=(detail,),
        nse_mcp_commercial_status=NSE_MCP_COMMERCIAL_STATUS,
        production=production,
        detail=detail,
        analysis_state=analysis_state_for(
            status=status,
            identity_status=identity_status,
            coverage=None,
            dsp=None,
            full=False,
        ),
        qualitative=qualitative,
        advanced_check=advanced,
    )


def analyse_listing(
    listing: SecurityListing,
    *,
    query: str | None = None,
    mode: str = "MOCK",
    production: bool = False,
    document_text: str | None = None,
    document_url: str | None = None,
    documents: Sequence[Any] | None = None,
    candidates: Mapping[str, Sequence[EvidenceItem]] | None = None,
    retrieve_fn: Any | None = None,
    assumptions: tuple[CanonicalAssumption, ...] = (),
    capital_events: tuple[Any, ...] = (),
    quality_components: Mapping[str, Any] | None = None,
    moat_components: Mapping[str, Any] | None = None,
    risk_observations: tuple[str, ...] = (),
    judge: EvidenceJudge | None = None,
    master: SecurityMasterService | None = None,
    search: SecuritySearchResult | None = None,
    resolve: SecurityResolveResult | None = None,
    fields: tuple[str, ...] | None = None,
    research_horizon: date | None = None,
    ca_checked_through: date | None = None,
    claims: Sequence[Any] = (),
) -> EndToEndResult:
    """Automatic plan → acquire → judge → DSP for one resolved listing."""
    _ = master
    timings: dict[str, float] = {
        "search_identity": 0.0,
        "identity_plan": 0.0,
        "plan_acquisition": 0.0,
        "acquisition_dataset": 0.0,
        "dataset_dsp": 0.0,
        "qualitative": 0.0,
        "advanced_check": 0.0,
        "complete": 0.0,
    }
    started = perf_counter()
    if production and mode == "MOCK":
        return _blocked_result(
            query or listing.ticker,
            status="UNAVAILABLE",
            identity_status="UNAVAILABLE",
            detail="MOCK evidence cannot enter production",
            timings=timings,
            production=production,
            listing=listing,
        )
    if listing.security_type in UNSUPPORTED_SECURITY_TYPES or not listing.eligibility:
        t = perf_counter()
        request = ResearchRequest(
            fields=AUTO_REQUEST_GROUPS,
            ticker=listing.ticker,
            company=listing.company_name,
            isin=listing.isin,
            mic=listing.mic,
            exchange=listing.exchange,
            mode=mode,  # type: ignore[arg-type]
            request_id=new_evidence_id(),
            security_type=listing.security_type,
        )
        plan = build_research_plan(listing, request)
        timings["identity_plan"] = perf_counter() - t
        timings["complete"] = perf_counter() - started
        return _blocked_result(
            query or listing.ticker,
            status="UNSUPPORTED",
            identity_status="UNAVAILABLE",
            detail=f"security_type={listing.security_type} is outside ordinary-equity valuation",
            timings=timings,
            production=production,
            listing=listing,
            plan=plan,
            search=search,
            resolve=resolve,
        )

    request_fields = fields or AUTO_REQUEST_GROUPS
    request = ResearchRequest(
        fields=request_fields,
        ticker=listing.ticker,
        company=listing.company_name,
        isin=listing.isin,
        mic=listing.mic,
        exchange=listing.exchange,
        mode=mode,  # type: ignore[arg-type]
        request_id=new_evidence_id(),
        security_type=listing.security_type,
    )
    t = perf_counter()
    loop = run_research_loop(listing, request)
    plan = loop.plan
    timings["identity_plan"] = perf_counter() - t
    source_selection = {
        field: field_source_priority(field)
        for field in dict.fromkeys(plan.required_fields + plan.optional_fields)
    }
    t = perf_counter()
    acquisition = acquire_planned_fields(
        listing,
        request,
        candidates=candidates,
        documents=documents,
        document_text=document_text,
        document_url=document_url,
        capital_events=capital_events,
        production=production,
        judge=judge,
        retrieve_fn=retrieve_fn,
        research_horizon=research_horizon,
        ca_checked_through=ca_checked_through,
    )
    timings["plan_acquisition"] = perf_counter() - t
    t = perf_counter()
    dataset = acquisition.dataset
    timings["acquisition_dataset"] = perf_counter() - t
    validated = validate_assumption_pack(assumptions)
    accepted = tuple(item.assumption for item in validated if item.accepted)
    assumptions_accepted = bool(accepted) and all(
        name in {row.field for row in accepted}
        for name in ("fcf_growth_rate", "terminal_growth_rate")
    ) and any(row.field in {"discount_rate", "wacc"} for row in accepted)
    t = perf_counter()
    qualitative = run_qualitative_engines(dataset, listing)
    timings["qualitative"] = perf_counter() - t
    q_components = quality_components or qualitative.quality_components
    m_components = moat_components or qualitative.moat_components
    observations = risk_observations or qualitative.risk_observations
    t = perf_counter()
    dsp = None
    if dataset is not None:
        dsp = run_dsp_calculations(
            dataset,
            assumptions=accepted,
            listing=listing,
            quality_components=q_components,
            moat_components=m_components,
            risk_observations=observations,
        )
    timings["dataset_dsp"] = perf_counter() - t
    capability = classify_research_capability(listing)
    t = perf_counter()
    advanced = evaluate_advanced_check(
        dataset=dataset,
        dsp=dsp,
        qualitative=qualitative,
        listing=listing,
        claims=claims,
        production=production,
        capability=capability,
    )
    timings["advanced_check"] = perf_counter() - t
    full, gates = full_analysis_status(
        listing=listing,
        dataset=dataset,
        dsp=dsp,
        assumptions_accepted=assumptions_accepted,
        capability=capability,
        research_horizon=research_horizon,
        ca_checked_through=ca_checked_through,
    )
    coverage = _coverage(
        identity="VERIFIED",
        acquisition=acquisition,
        dataset=dataset,
        dsp=dsp,
        full=full,
        capability=capability,
    )
    unresolved: list[str] = []
    unresolved.extend(str(item) for item in loop.failures)
    if dataset is not None:
        unresolved.extend(dataset.unresolved)
    if dsp is not None and dsp.dcf.status != "CALCULATED":
        unresolved.append(dsp.dcf.detail)
    unresolved = [redact_mcp_text(item) for item in unresolved if item]
    timings["complete"] = perf_counter() - started
    status = "FULL_ANALYSIS" if full else ("PARTIAL" if coverage.verified_fields else "UNKNOWN")
    return EndToEndResult(
        query=query or listing.ticker,
        status=status,
        identity_status="VERIFIED",
        listing=listing,
        search=search,
        resolve=resolve,
        plan=plan,
        acquisition=acquisition,
        dataset=dataset,
        dsp=dsp,
        coverage=coverage,
        timings=timings,
        full_analysis=full,
        gates=gates,
        unresolved=tuple(str(item) for item in unresolved if item),
        nse_mcp_commercial_status=NSE_MCP_COMMERCIAL_STATUS,
        production=production,
        detail="automatic research completed; missing fields remain UNKNOWN",
        source_selection=source_selection,
        analysis_state=analysis_state_for(
            status=status,
            identity_status="VERIFIED",
            coverage=coverage,
            dsp=dsp,
            full=full,
        ),
        qualitative=qualitative,
        advanced_check=advanced,
    )


def analyse_user_query(
    query: str,
    *,
    exchange: str | None = None,
    isin: str | None = None,
    mic: str | None = None,
    master: SecurityMasterService | None = None,
    **kwargs: Any,
) -> EndToEndResult:
    """SEARCH → SELECT/RESOLVE → automatic research. Never guesses a listing."""
    timings_pre: dict[str, float] = {}
    production = bool(kwargs.get("production", False))
    if looks_like_injection(query):
        return _blocked_result(
            query,
            status="REJECTED",
            identity_status="REJECTED",
            detail="user input cannot inject source policy or formulas",
            timings={"search_identity": 0.0, "complete": 0.0},
            production=production,
        )
    service = master or SecurityMasterService(load_default_catalog())
    t = perf_counter()
    search = service.search(query, exchange=exchange)
    resolve = service.resolve(query, exchange=exchange, isin=isin, mic=mic)
    timings_pre["search_identity"] = perf_counter() - t
    if resolve.status == "RESOLVED" and resolve.identity is not None:
        result = analyse_listing(
            resolve.identity,
            query=query,
            master=service,
            search=search,
            resolve=resolve,
            **kwargs,
        )
        merged = dict(result.timings)
        merged["search_identity"] = timings_pre["search_identity"]
        merged["complete"] = merged.get("complete", 0.0) + timings_pre["search_identity"]
        return EndToEndResult(
            query=result.query,
            status=result.status,
            identity_status=result.identity_status,
            listing=result.listing,
            search=search,
            resolve=resolve,
            plan=result.plan,
            acquisition=result.acquisition,
            dataset=result.dataset,
            dsp=result.dsp,
            coverage=result.coverage,
            timings=merged,
            full_analysis=result.full_analysis,
            gates=result.gates,
            unresolved=result.unresolved,
            nse_mcp_commercial_status=result.nse_mcp_commercial_status,
            production=result.production,
            detail=result.detail,
            source_selection=result.source_selection,
            analysis_state=result.analysis_state,
            qualitative=result.qualitative,
            advanced_check=result.advanced_check,
        )
    mapped = {
        "AMBIGUOUS": "AMBIGUOUS",
        "UNKNOWN": "UNKNOWN",
        "UNSUPPORTED": "UNSUPPORTED",
        "REJECTED": "REJECTED",
    }.get(resolve.status, resolve.status)
    detail = {
        "AMBIGUOUS": "identity ambiguous — ISIN+MIC required; never guessed",
        "UNKNOWN": "security unknown — no listing invented",
        "UNSUPPORTED": "instrument is outside the supported universe",
        "REJECTED": resolve.detail,
    }.get(resolve.status, resolve.detail)
    if search.status == "MATCHES" and resolve.status != "RESOLVED":
        if len(search.results) > 1:
            mapped = "AMBIGUOUS"
            detail = "identity ambiguous — ISIN+MIC required; search returned candidates; never guessed"
        elif mapped != "AMBIGUOUS":
            detail = resolve.detail or detail
    result = _blocked_result(
        query,
        status=mapped,
        identity_status=mapped,
        detail=detail,
        timings={**timings_pre, "complete": timings_pre["search_identity"]},
        production=production,
        search=search,
        resolve=resolve,
    )
    return result
