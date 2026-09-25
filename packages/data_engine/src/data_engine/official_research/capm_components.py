"""Qualify beta and ERP as WACC *ingredients*. Not a second WACC engine.

Approved live hosts do not currently publish an identity-bound company beta
series or an India-equity ERP series that EvidenceJudge can VERIFY. Yahoo is
Tier 2 and cannot VERIFY. GDP/inflation/AI opinion are not ERP.

This module classifies candidates. DSP still calls compute_wacc.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from time import perf_counter
from typing import Any, Mapping

from data_engine.official_research.component_research import (
    live_macro_acquisition_status,
    research_components_from_agent,
)
from data_engine.official_research.dcf_tenor_policy import tenor_policy_public_dict
from data_engine.official_research.models import EvidenceItem, utc_now
from data_engine.official_research.source_policy import classify_source_url
from data_engine.security_master.models import SecurityListing

__all__ = [
    "BETA_FRESHNESS_DAYS",
    "ERP_FRESHNESS_DAYS",
    "FORBIDDEN_BETA_KINDS",
    "FORBIDDEN_ERP_KINDS",
    "CapmComponentResearch",
    "ComponentQualification",
    "qualify_capm_component",
    "research_live_capm_components",
]

BETA_FRESHNESS_DAYS = 365
ERP_FRESHNESS_DAYS = 548
_US_MARKETS = frozenset(
    {
        "us",
        "usa",
        "united states",
        "u.s.",
        "u.s.a.",
        "sp500",
        "s&p 500",
        "nyse",
        "nasdaq",
    }
)
FORBIDDEN_BETA_KINDS = frozenset(
    {
        "industry_beta",
        "unlevered_beta",
        "peer_beta",
        "etf_beta",
        "index_beta",
        "ai_estimate",
    }
)
FORBIDDEN_ERP_KINDS = frozenset(
    {
        "us_market",
        "us_erp",
        "gdp",
        "inflation",
        "ai_estimate",
        "company_growth",
    }
)
_AI_PROPOSERS = frozenset(
    {
        "ai",
        "ai_research",
        "ai_synthesis",
        "gemini_find",
        "chatgpt_verify",
        "deep_search_attack",
        "claude_review",
        "openai",
        "openai_nse_mcp",
    }
)


@dataclass(frozen=True, slots=True)
class ComponentQualification:
    status: str
    field: str
    wacc_eligible: bool
    detail: str
    identity_status: str
    semantic_status: str
    freshness_status: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "field": self.field,
            "wacc_eligible": self.wacc_eligible,
            "detail": self.detail,
            "identity_status": self.identity_status,
            "semantic_status": self.semantic_status,
            "freshness_status": self.freshness_status,
        }


@dataclass(frozen=True, slots=True)
class CapmComponentResearch:
    beta_status: str
    erp_status: str
    beta_detail: str
    erp_detail: str
    ai_status: str
    tenor_policy: dict[str, Any]
    qualifications: tuple[ComponentQualification, ...]
    timings: dict[str, float]
    detail: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "beta_status": self.beta_status,
            "erp_status": self.erp_status,
            "beta_detail": self.beta_detail,
            "erp_detail": self.erp_detail,
            "ai_status": self.ai_status,
            "tenor_policy": dict(self.tenor_policy),
            "qualifications": [item.to_public_dict() for item in self.qualifications],
            "timings": dict(self.timings),
            "detail": self.detail,
        }


def qualify_capm_component(
    record: Mapping[str, Any] | EvidenceItem,
    listing: SecurityListing,
    *,
    valuation_date: date,
) -> ComponentQualification:
    """WACC-input eligibility. Does not calculate WACC."""
    field = _get(record, "field")
    if field == "beta":
        return _qualify_beta(record, listing, valuation_date=valuation_date)
    if field == "equity_risk_premium":
        return _qualify_erp(record, listing, valuation_date=valuation_date)
    if field == "risk_free_rate":
        return ComponentQualification(
            status="REVIEW_REQUIRED",
            field=field,
            wacc_eligible=False,
            detail="risk-free DCF binding is governed by tenor policy, not this qualifier",
            identity_status="UNKNOWN",
            semantic_status="UNKNOWN",
            freshness_status="UNKNOWN",
        )
    return ComponentQualification(
        status="REJECTED",
        field=field,
        wacc_eligible=False,
        detail="not a CAPM WACC ingredient",
        identity_status="UNKNOWN",
        semantic_status="FAIL",
        freshness_status="UNKNOWN",
    )


def research_live_capm_components(
    listing: SecurityListing,
    *,
    agent: Any | None = None,
    valuation_date: date | None = None,
    now: datetime | None = None,
) -> CapmComponentResearch:
    """Approved-source live research. Does not scrape Yahoo/FMP or invent ERP."""
    timings = {"beta_retrieval": 0.0, "erp_retrieval": 0.0, "evidence_judge": 0.0}
    as_of_day = valuation_date or (now or utc_now()).date()
    live = live_macro_acquisition_status()
    qualifications: list[ComponentQualification] = []
    ai_status = "NOT_CONFIGURED"
    t0 = perf_counter()
    if agent is not None and callable(getattr(agent, "available", None)) and agent.available():
        ingest = research_components_from_agent(
            agent, listing, fields=("beta", "equity_risk_premium")
        )
        ai_status = ingest.ai_status
        for row in ingest.accepted:
            qualifications.append(
                qualify_capm_component(row, listing, valuation_date=as_of_day)
            )
        for row in ingest.rejected:
            qualifications.append(
                ComponentQualification(
                    status="REJECTED",
                    field=str(row.get("field") or ""),
                    wacc_eligible=False,
                    detail=str(row.get("detail") or "rejected"),
                    identity_status="FAIL",
                    semantic_status="FAIL",
                    freshness_status="UNKNOWN",
                )
            )
    timings["beta_retrieval"] = perf_counter() - t0
    timings["erp_retrieval"] = timings["beta_retrieval"]
    eligible_beta = any(
        item.field == "beta" and item.wacc_eligible for item in qualifications
    )
    eligible_erp = any(
        item.field == "equity_risk_premium" and item.wacc_eligible for item in qualifications
    )
    beta_status = "VERIFIED_INPUT" if eligible_beta else "UNKNOWN"
    erp_status = "VERIFIED_INPUT" if eligible_erp else "UNKNOWN"
    return CapmComponentResearch(
        beta_status=beta_status,
        erp_status=erp_status,
        beta_detail=str(live["beta"]["detail"]),
        erp_detail=str(live["equity_risk_premium"]["detail"]),
        ai_status=ai_status,
        tenor_policy=tenor_policy_public_dict(),
        qualifications=tuple(qualifications),
        timings=timings,
        detail=(
            "no approved live beta/ERP series; Yahoo cannot VERIFY; "
            "AI is not the authority; GDP/inflation are not ERP"
        ),
    )


def _get(record: Mapping[str, Any] | EvidenceItem, name: str) -> str:
    if isinstance(record, EvidenceItem):
        if name == "field":
            return record.field
        if name == "value":
            return "" if record.value is None else str(record.value)
        if name == "isin":
            return record.isin
        if name == "mic":
            return record.mic
        if name == "source_url":
            return str(record.source_url or "")
        if name == "source_type":
            return str(record.source_type or "")
        if name == "source":
            return str(record.source or "")
        if name == "as_of":
            return "" if record.as_of is None else record.as_of.isoformat()
        if name == "document_date":
            return "" if record.document_date is None else record.document_date.isoformat()
        if name == "period":
            return str(record.period or "")
        if name == "methodology":
            return str(record.evidence_locator or "")
        if name == "market":
            return str(record.semantic_kind or "")
        if name == "beta_kind":
            return str(record.semantic_kind or "")
        if name == "currency":
            return str(record.currency or "")
        if name == "proposed_by":
            return str(record.agent or "")
        return ""
    value = record.get(name)
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value).strip()


def _as_of(record: Mapping[str, Any] | EvidenceItem) -> date | None:
    raw = _get(record, "as_of") or _get(record, "document_date")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _qualify_beta(
    record: Mapping[str, Any] | EvidenceItem,
    listing: SecurityListing,
    *,
    valuation_date: date,
) -> ComponentQualification:
    source_url = _get(record, "source_url")
    if not source_url:
        return _fail("beta", "REJECTED", "beta without provenance", identity="FAIL")
    if _get(record, "isin").upper() != listing.isin.upper():
        return _fail("beta", "REJECTED", "wrong-company beta", identity="FAIL")
    if _get(record, "mic") != listing.mic:
        return _fail("beta", "REJECTED", "wrong-listing beta", identity="FAIL")
    source_class = classify_source_url(
        source_url, source_type=_get(record, "source_type") or None
    )
    if source_class in {"secondary", "forbidden"}:
        return _fail(
            "beta",
            "REJECTED",
            "secondary/forbidden beta cannot VERIFY",
            identity="PASS",
            semantic="FAIL",
        )
    kind = _get(record, "beta_kind").lower() or _get(record, "semantic_kind").lower()
    if kind in FORBIDDEN_BETA_KINDS:
        return _fail(
            "beta",
            "REJECTED",
            f"beta kind {kind} is not a company levered-equity WACC input",
            identity="PASS",
            semantic="FAIL",
        )
    methodology = _get(record, "methodology")
    period = _get(record, "period")
    as_of = _as_of(record)
    if not methodology and not period and as_of is None:
        return _fail(
            "beta",
            "REJECTED",
            "inadequately specified beta (no methodology, period, or as_of)",
            identity="PASS",
            semantic="FAIL",
        )
    freshness = _freshness(as_of, valuation_date, BETA_FRESHNESS_DAYS)
    if freshness == "REJECTED":
        return _fail(
            "beta",
            "REJECTED",
            "beta observation_date is after valuation_date",
            identity="PASS",
            freshness="FAIL",
        )
    if freshness == "REVIEW_REQUIRED":
        return ComponentQualification(
            status="REVIEW_REQUIRED",
            field="beta",
            wacc_eligible=False,
            detail="stale beta; not used as a WACC input",
            identity_status="PASS",
            semantic_status="PASS",
            freshness_status="STALE",
        )
    if freshness == "UNKNOWN" and not period and not methodology:
        return ComponentQualification(
            status="REVIEW_REQUIRED",
            field="beta",
            wacc_eligible=False,
            detail="beta freshness UNKNOWN; WACC blocked",
            identity_status="PASS",
            semantic_status="PASS",
            freshness_status="UNKNOWN",
        )
    return ComponentQualification(
        status="ACCEPTED",
        field="beta",
        wacc_eligible=True,
        detail="beta candidate is WACC-eligible pending EvidenceJudge",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="CURRENT" if freshness == "CURRENT" else freshness,
    )


def _qualify_erp(
    record: Mapping[str, Any] | EvidenceItem,
    listing: SecurityListing,
    *,
    valuation_date: date,
) -> ComponentQualification:
    methodology = _get(record, "methodology")
    as_of = _as_of(record)
    if not methodology or as_of is None:
        return _fail(
            "equity_risk_premium",
            "REJECTED",
            "ERP without methodology/date",
            semantic="FAIL",
        )
    market = (
        _get(record, "market") or _get(record, "semantic_kind") or _get(record, "geography")
    ).lower()
    if market in FORBIDDEN_ERP_KINDS or market in _US_MARKETS:
        return _fail(
            "equity_risk_premium",
            "REJECTED",
            "ERP market/geography is not compatible with Indian equity",
            semantic="FAIL",
        )
    listing_ccy = str(listing.currency or "INR").upper()
    record_ccy = _get(record, "currency").upper()
    if record_ccy and record_ccy != listing_ccy:
        return _fail(
            "equity_risk_premium",
            "REJECTED",
            "ERP currency does not match valuation currency",
            semantic="FAIL",
        )
    lowered_method = methodology.lower()
    if any(token in lowered_method for token in ("gdp", "inflation", "ai estimate", "ai opinion")):
        return _fail(
            "equity_risk_premium",
            "REJECTED",
            "GDP/inflation/AI opinion are not ERP",
            semantic="FAIL",
        )
    source_url = _get(record, "source_url")
    source_class = classify_source_url(
        source_url, source_type=_get(record, "source_type") or None
    )
    if source_class in {"secondary", "forbidden"}:
        return _fail(
            "equity_risk_premium",
            "REJECTED",
            "secondary/forbidden ERP cannot VERIFY",
            semantic="FAIL",
        )
    proposer = _get(record, "proposed_by").lower()
    if proposer in _AI_PROPOSERS and source_class != "primary":
        return _fail(
            "equity_risk_premium",
            "REJECTED",
            "AI ERP is not authoritative without primary evidence",
            semantic="FAIL",
        )
    freshness = _freshness(as_of, valuation_date, ERP_FRESHNESS_DAYS)
    if freshness == "REJECTED":
        return _fail(
            "equity_risk_premium",
            "REJECTED",
            "ERP observation_date is after valuation_date",
            freshness="FAIL",
        )
    if freshness == "REVIEW_REQUIRED":
        return ComponentQualification(
            status="REVIEW_REQUIRED",
            field="equity_risk_premium",
            wacc_eligible=False,
            detail="stale ERP; not used as a WACC input",
            identity_status="PASS",
            semantic_status="PASS",
            freshness_status="STALE",
        )
    return ComponentQualification(
        status="ACCEPTED",
        field="equity_risk_premium",
        wacc_eligible=True,
        detail="ERP candidate is WACC-eligible pending EvidenceJudge",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="CURRENT",
    )


def _freshness(as_of: date | None, valuation_date: date, max_age_days: int) -> str:
    if as_of is None:
        return "UNKNOWN"
    if as_of > valuation_date:
        return "REJECTED"
    if (valuation_date - as_of).days > max_age_days:
        return "REVIEW_REQUIRED"
    return "CURRENT"


def _fail(
    field: str,
    status: str,
    detail: str,
    *,
    identity: str = "PASS",
    semantic: str = "PASS",
    freshness: str = "UNKNOWN",
) -> ComponentQualification:
    return ComponentQualification(
        status=status,
        field=field,
        wacc_eligible=False,
        detail=detail,
        identity_status=identity,
        semantic_status=semantic,
        freshness_status=freshness,
    )
