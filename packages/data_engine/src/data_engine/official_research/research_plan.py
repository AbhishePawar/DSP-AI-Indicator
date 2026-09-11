"""Capability-driven research planner. No issuer URL tables."""

from __future__ import annotations

from dataclasses import dataclass
import re

from data_engine.official_research.company_sources import (
    CompanySourceMap,
    resolve_company_sources,
)
from data_engine.official_research.forensic_artifacts import is_promotable_artifact
from data_engine.official_research.models import ResearchRequest, new_evidence_id
from data_engine.official_research.research_failures import ResearchFailure
from data_engine.official_research.source_policy import field_authority_chain
from data_engine.security_master.models import SecurityListing, UNSUPPORTED_SECURITY_TYPES

__all__ = [
    "DOCUMENT_REQUIREMENTS",
    "EQUITY_DCF_FIELDS",
    "QUALITATIVE_REQUEST_GROUPS",
    "REQUEST_FIELD_GROUPS",
    "FieldRequirement",
    "ResearchPlan",
    "ResearchTask",
    "build_research_plan",
    "classify_research_capability",
    "expand_requested_fields",
    "field_capabilities",
    "field_freshness_class",
    "field_retrieval_strategy",
    "field_source_priority",
    "plan_report_block",
]

EQUITY_DCF_FIELDS: tuple[str, ...] = (
    "revenue",
    "net_income",
    "cfo",
    "capex",
    "shares_outstanding",
    "eod_close",
)

_EQUITY_REQUIRED: tuple[str, ...] = (
    "eod_close",
    "revenue",
    "net_income",
    "equity",
    "cash",
    "cfo",
    "shares_outstanding",
)
_EQUITY_OPTIONAL: tuple[str, ...] = (
    "total_assets",
    "total_liabilities",
    "operating_profit",
    "debt",
)
_EQUITY_NICE: tuple[str, ...] = ("ebit", "capex")
_BANK_REQUIRED: tuple[str, ...] = (
    "eod_close",
    "net_income",
    "equity",
    "total_assets",
    "total_liabilities",
    "shares_outstanding",
)
_BANK_OPTIONAL: tuple[str, ...] = ("cash", "cfo")
_BANK_NOT_APPLICABLE: tuple[str, ...] = ("revenue", "ebit", "capex")

REQUEST_FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "IDENTITY": (),
    "PRICE": ("eod_close",),
    "FINANCIALS": (
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
    ),
    "SHARES": ("shares_outstanding",),
    "CORPORATE_ACTIONS": (),
    "MANAGEMENT": (),
    "BUSINESS_QUALITY": (),
    "MOAT": (),
    "RISK": (),
    "VALUATION_INPUTS": EQUITY_DCF_FIELDS,
    "EVIDENCE": (),
}
QUALITATIVE_REQUEST_GROUPS: frozenset[str] = frozenset(
    {
        "IDENTITY",
        "CORPORATE_ACTIONS",
        "MANAGEMENT",
        "BUSINESS_QUALITY",
        "MOAT",
        "RISK",
        "EVIDENCE",
    }
)
DOCUMENT_REQUIREMENTS: tuple[str, ...] = (
    "document_type",
    "reporting_period",
    "publication_date",
    "consolidated_or_standalone",
    "audited_or_unaudited",
    "currency",
    "units",
    "url",
    "content_hash",
    "retrieved_at",
)

_FRESHNESS = {
    "eod_close": "session_or_latest_eod",
    "revenue": "latest_audited_period",
    "operating_profit": "latest_audited_period",
    "ebit": "latest_audited_period",
    "net_income": "latest_audited_period",
    "equity": "latest_audited_period",
    "cash": "latest_audited_period",
    "cfo": "latest_audited_period",
    "capex": "latest_audited_period",
    "debt": "latest_audited_period",
    "total_assets": "latest_audited_period",
    "total_liabilities": "latest_audited_period",
    "shares_outstanding": "latest_count_plus_ca_review",
}


@dataclass(frozen=True, slots=True)
class FieldRequirement:
    name: str
    priority: str  # required | optional | nice_to_have | not_applicable
    freshness_class: str


@dataclass(frozen=True, slots=True)
class ResearchTask:
    evidence_class: str
    source_classes: tuple[str, ...]
    status: str


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    request_id: str
    isin: str
    mic: str
    ticker: str
    company: str
    security_type: str
    capability: str
    requested_fields: tuple[str, ...]
    requirements: tuple[FieldRequirement, ...]
    existing_verified: tuple[str, ...]
    stale_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    tasks: tuple[ResearchTask, ...]
    source_classes: tuple[str, ...]
    failures: tuple[ResearchFailure, ...]
    status: str
    ir_status: str
    dcf_status: str
    request_groups: tuple[str, ...] = ()

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.requirements if item.priority == "required")

    @property
    def optional_fields(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.requirements if item.priority == "optional")

    @property
    def nice_to_have_fields(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.requirements if item.priority == "nice_to_have")

    @property
    def not_applicable_fields(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.requirements if item.priority == "not_applicable")


def classify_research_capability(listing: SecurityListing) -> str:
    """Security-class capability. Name tokens, not issuer tables."""
    if listing.security_type in UNSUPPORTED_SECURITY_TYPES:
        return listing.security_type
    name = f"{listing.company_name} {listing.ticker}".lower()
    if re.search(r"\bbank\b|\bbanking\b", name, re.I):
        return "bank_equity"
    if "reit" in name:
        return "reit"
    return "equity"


def field_freshness_class(field: str) -> str:
    return _FRESHNESS.get(field, "latest_reasonable_research_period")


def expand_requested_fields(fields: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Expand provider-neutral groups to DSP field names. Unknown tokens pass through."""
    if not fields:
        return (), ()
    concrete: list[str] = []
    groups: list[str] = []
    for raw in fields:
        token = str(raw or "").strip()
        if not token:
            continue
        key = token.upper()
        if key in REQUEST_FIELD_GROUPS:
            groups.append(key)
            concrete.extend(REQUEST_FIELD_GROUPS[key])
        else:
            concrete.append(token)
    return tuple(dict.fromkeys(concrete)), tuple(dict.fromkeys(groups))


def field_source_priority(field: str) -> tuple[str, ...]:
    return field_authority_chain(field)


def field_retrieval_strategy(field: str) -> str:
    if field in {"eod_close", "last_price"}:
        return "exchange_market_source"
    if field == "shares_outstanding":
        return "official_share_capital_plus_corporate_actions"
    if field_freshness_class(field) == "latest_audited_period":
        return "official_financial_statement"
    return "primary_document_then_approved_cross_check"


def field_capabilities(plan: ResearchPlan) -> dict[str, str]:
    return {item.name: item.priority for item in plan.requirements}


_FIELD_EVIDENCE_CLASS = {
    "eod_close": "market_price",
    "last_price": "market_price",
    "revenue": "financial_statements",
    "operating_profit": "financial_statements",
    "ebit": "financial_statements",
    "net_income": "financial_statements",
    "equity": "financial_statements",
    "cash": "financial_statements",
    "cfo": "financial_statements",
    "capex": "financial_statements",
    "debt": "financial_statements",
    "total_assets": "financial_statements",
    "total_liabilities": "financial_statements",
    "shares_outstanding": "outstanding_shares",
}


def _requirements_for(capability: str) -> tuple[FieldRequirement, ...]:
    if capability == "bank_equity":
        rows = (
            [(name, "required") for name in _BANK_REQUIRED]
            + [(name, "optional") for name in _BANK_OPTIONAL]
            + [(name, "not_applicable") for name in _BANK_NOT_APPLICABLE]
        )
    elif capability in UNSUPPORTED_SECURITY_TYPES or capability in {"etf", "reit"}:
        rows = [(name, "not_applicable") for name in _EQUITY_REQUIRED]
    else:
        rows = (
            [(name, "required") for name in _EQUITY_REQUIRED]
            + [(name, "optional") for name in _EQUITY_OPTIONAL]
            + [(name, "nice_to_have") for name in _EQUITY_NICE]
        )
    return tuple(
        FieldRequirement(name, priority, field_freshness_class(name))
        for name, priority in rows
    )


def _dcf_status(capability: str, missing: tuple[str, ...], verified: tuple[str, ...]) -> str:
    if capability != "equity":
        return "UNAVAILABLE"
    needed = set(EQUITY_DCF_FIELDS)
    if needed.issubset(verified) and not (needed & set(missing)):
        return "ELIGIBLE"
    return "UNAVAILABLE"


def build_research_plan(
    listing: SecurityListing,
    request: ResearchRequest,
    *,
    existing_verified: tuple[str, ...] = (),
    stale_fields: tuple[str, ...] = (),
    sources: CompanySourceMap | None = None,
    artifact_path: str | None = None,
) -> ResearchPlan:
    """Plan from identity + capability. Never reads stale forensic artifacts."""
    if artifact_path and is_promotable_artifact(artifact_path):
        raise RuntimeError("promotable forensic artifact is a contract violation")
    request_id = request.request_id or new_evidence_id()
    capability = classify_research_capability(listing)
    requirements = _requirements_for(capability)
    applicable = {
        item.name
        for item in requirements
        if item.priority in {"required", "optional", "nice_to_have"}
    }
    expanded, request_groups = expand_requested_fields(request.fields)
    if not request.fields:
        wanted = tuple(
            item.name for item in requirements if item.priority != "not_applicable"
        )
    else:
        wanted = tuple(field for field in expanded if field in applicable)
    verified = tuple(field for field in wanted if field in existing_verified)
    stale = tuple(field for field in wanted if field in stale_fields)
    missing = tuple(
        field
        for field in wanted
        if field in applicable and field not in verified and field not in stale
    )
    failures: list[ResearchFailure] = []
    unsupported = listing.security_type in UNSUPPORTED_SECURITY_TYPES
    if unsupported:
        failures.append(
            ResearchFailure(
                "CAPABILITY_UNAVAILABLE",
                f"security_type={listing.security_type} is outside the supported universe",
            )
        )
        missing = ()
    ir_status = "UNKNOWN"
    source_classes = ("primary", "approved_research")
    tasks: list[ResearchTask] = [
        ResearchTask("identity", ("primary",), "RESOLVED"),
    ]
    if sources is None:
        sources = resolve_company_sources(listing)
    if sources.official_domain is None:
        ir_status = "DISCOVERY_REQUIRED"
        failures.append(
            ResearchFailure(
                "DISCOVERY_REQUIRED",
                "official IR registry entry is not verified; will not guess /investors",
            )
        )
    else:
        ir_status = "REGISTRY"
        if (
            sources.investor_relations_url is None
            and sources.annual_report_url is None
        ):
            ir_status = "DOMAIN_ONLY"
    if not unsupported:
        evidence_classes: list[str] = []
        for field in missing:
            evidence_classes.append(_FIELD_EVIDENCE_CLASS.get(field, "research"))
        if any(field == "shares_outstanding" for field in (*missing, *stale)) or (
            "CORPORATE_ACTIONS" in request_groups
        ):
            evidence_classes.append("corporate_actions")
        for group in request_groups:
            if group in QUALITATIVE_REQUEST_GROUPS and group not in {
                "IDENTITY",
                "CORPORATE_ACTIONS",
            }:
                evidence_classes.append(group.lower())
        for evidence_class in dict.fromkeys(evidence_classes):
            tasks.append(
                ResearchTask(evidence_class, ("primary",), "PENDING")
            )
    status = "COMPLETE" if not missing and not stale and not unsupported else "INCOMPLETE"
    if unsupported:
        status = "CAPABILITY_UNAVAILABLE"
    return ResearchPlan(
        request_id=request_id,
        isin=listing.isin,
        mic=listing.mic,
        ticker=listing.ticker,
        company=listing.company_name,
        security_type=listing.security_type,
        capability=capability,
        requested_fields=wanted,
        requirements=requirements,
        existing_verified=verified,
        stale_fields=stale,
        missing_fields=missing,
        tasks=tuple(tasks),
        source_classes=source_classes,
        failures=tuple(failures),
        status=status,
        ir_status=ir_status,
        dcf_status=_dcf_status(capability, missing, verified),
        request_groups=request_groups,
    )


def plan_report_block(plan: ResearchPlan) -> dict[str, object]:
    """Stable forensic dump. A plan is not evidence."""
    return {
        "SECURITY": plan.ticker,
        "ISIN": plan.isin,
        "MIC": plan.mic,
        "SECURITY_TYPE": plan.security_type,
        "CAPABILITY": plan.capability,
        "REQUESTED_FIELDS": list(plan.requested_fields),
        "REQUIRED_FIELDS": list(plan.required_fields),
        "OPTIONAL_FIELDS": list(plan.optional_fields),
        "EXISTING_VERIFIED_FIELDS": list(plan.existing_verified),
        "STALE_FIELDS": list(plan.stale_fields),
        "MISSING_FIELDS": list(plan.missing_fields),
        "RESEARCH_TASKS": [task.evidence_class for task in plan.tasks],
        "SOURCE_CLASSES": list(plan.source_classes),
        "STATUS": plan.status,
        "IR_STATUS": plan.ir_status,
        "DCF_STATUS": plan.dcf_status,
        "REQUEST_GROUPS": list(plan.request_groups),
        "FIELD_CAPABILITIES": field_capabilities(plan),
        "SOURCE_PRIORITY": {
            field: list(field_source_priority(field)) for field in plan.requested_fields
        },
        "RETRIEVAL_STRATEGY": {
            field: field_retrieval_strategy(field) for field in plan.requested_fields
        },
        "FRESHNESS_REQUIREMENT": {
            field: field_freshness_class(field) for field in plan.requested_fields
        },
        "DOCUMENT_REQUIREMENTS": list(DOCUMENT_REQUIREMENTS),
        "CORPORATE_ACTION_REQUIREMENTS": list(
            (
                "bonus",
                "split",
                "rights",
                "qip",
                "fpo",
                "preferential",
                "esop",
                "warrants",
                "conversion",
                "new_issue",
                "buyback",
                "cancellation",
                "capital_reduction",
                "merger",
                "demerger",
                "scheme",
                "share_swap",
                "acquisition",
            )
        ),
        "CROSS_CHECK_REQUIREMENTS": ["screener_may_cross_check_not_override"],
        "VERIFICATION_REQUIREMENTS": ["EvidenceJudge", "RAW_cannot_enter_DSP"],
    }
