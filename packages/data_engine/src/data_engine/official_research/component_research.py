"""AI / approved-source connector for DCF *components*, not DCF results.

AI is a data researcher. It may return risk-free rate, beta, ERP, cost of
debt, tax rate, or guidance citations. It may not return WACC, forecast
growth, terminal growth, cost of equity, or intrinsic value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from data_engine.official_research.models import EvidenceItem, ResearchClaim, new_evidence_id
from data_engine.official_research.source_policy import classify_source_url
from data_engine.security_master.models import SecurityListing

__all__ = [
    "AI_FORBIDDEN_RESULT_FIELDS",
    "COMPONENT_RESEARCH_FIELDS",
    "REQUIRED_COMPONENT_EVIDENCE_KEYS",
    "ComponentIngestResult",
    "ingest_researched_components",
    "live_macro_acquisition_status",
    "research_components_from_agent",
]

COMPONENT_RESEARCH_FIELDS: frozenset[str] = frozenset(
    {
        "risk_free_rate",
        "beta",
        "equity_risk_premium",
        "pre_tax_cost_of_debt",
        "tax_rate",
        "statutory_tax_rate",
        "effective_tax_rate",
        "finance_costs",
        "management_guidance_growth",
    }
)
AI_FORBIDDEN_RESULT_FIELDS: frozenset[str] = frozenset(
    {
        "wacc",
        "discount_rate",
        "fcf_growth_rate",
        "terminal_growth_rate",
        "revenue_growth",
        "cost_of_equity",
        "after_tax_cost_of_debt",
        "capital_weights",
        "intrinsic_value",
        "intrinsic_value_per_share",
        "margin_of_safety",
        "dcf",
        "terminal_value",
        "equity_value",
        "fcf",
    }
)
REQUIRED_COMPONENT_EVIDENCE_KEYS: tuple[str, ...] = (
    "field",
    "value",
    "source",
    "source_type",
    "source_url",
    "retrieved_at",
    "as_of",
    "isin",
    "mic",
    "unit",
    "currency",
        "period",
        "evidence_locator",
    )
_OPTIONAL_COMPONENT_EVIDENCE_KEYS: tuple[str, ...] = (
    "document_date",
    "confidence",
    "identity",
    "methodology",
    "market",
    "benchmark",
    "beta_kind",
    "geography",
)
_AI_AGENTS = frozenset(
    {
        "ai",
        "ai_research",
        "ai_synthesis",
        "gemini_find",
        "chatgpt_verify",
        "deep_search_attack",
        "claude_review",
        "openai_nse_mcp",
        "openai",
    }
)


@dataclass(frozen=True, slots=True)
class ComponentIngestResult:
    status: str
    accepted: tuple[Mapping[str, Any], ...]
    rejected: tuple[Mapping[str, Any], ...]
    detail: str
    ai_status: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "accepted": [dict(item) for item in self.accepted],
            "rejected": [dict(item) for item in self.rejected],
            "detail": self.detail,
            "ai_status": self.ai_status,
        }


def ingest_researched_components(
    records: Sequence[Mapping[str, Any]],
    listing: SecurityListing,
    *,
    proposed_by: str = "AI_RESEARCH",
) -> ComponentIngestResult:
    """Accept component evidence. Reject AI-calculated DCF outputs."""
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    agent = proposed_by.strip().lower()
    for raw in records:
        field = str(raw.get("field") or "").strip()
        row = {key: raw.get(key) for key in (*REQUIRED_COMPONENT_EVIDENCE_KEYS, *_OPTIONAL_COMPONENT_EVIDENCE_KEYS, "company", "ticker")}
        row["field"] = field
        if field in AI_FORBIDDEN_RESULT_FIELDS:
            row["status"] = "REJECTED"
            row["detail"] = "AI_CALCULATED_OUTPUT_REJECTED; DSP calculates WACC/growth"
            rejected.append(row)
            continue
        if field not in COMPONENT_RESEARCH_FIELDS:
            row["status"] = "REJECTED"
            row["detail"] = "unknown component field"
            rejected.append(row)
            continue
        missing = [key for key in REQUIRED_COMPONENT_EVIDENCE_KEYS if raw.get(key) in {None, ""}]
        if missing:
            row["status"] = "REJECTED"
            row["detail"] = f"missing evidence fields: {','.join(missing)}"
            rejected.append(row)
            continue
        if str(raw.get("isin") or "").upper() != listing.isin.upper() or raw.get("mic") != listing.mic:
            row["status"] = "REJECTED"
            row["detail"] = "IDENTITY_FAIL"
            rejected.append(row)
            continue
        try:
            Decimal(str(raw["value"]))
        except (InvalidOperation, ValueError, TypeError):
            row["status"] = "REJECTED"
            row["detail"] = "value is not numeric"
            rejected.append(row)
            continue
        source_class = classify_source_url(
            str(raw.get("source_url") or ""),
            source_type=str(raw.get("source_type") or "") or None,
        )
        if source_class == "forbidden":
            row["status"] = "REJECTED"
            row["detail"] = "forbidden source"
            rejected.append(row)
            continue
        if agent in _AI_AGENTS and source_class in {"secondary", "approved_research"}:
            row["authority"] = source_class
            row["detail"] = "AI discovery cannot override missing primary evidence"
        row["status"] = "PROPOSED"
        row["source_class"] = source_class
        row["proposed_by"] = proposed_by
        accepted.append(row)
    status = "PROPOSED" if accepted and not rejected else (
        "REJECTED" if rejected and not accepted else ("PARTIAL" if accepted else "UNKNOWN")
    )
    if rejected and any(
        item.get("detail", "").startswith("AI_CALCULATED_OUTPUT_REJECTED") for item in rejected
    ) and not accepted:
        status = "REJECTED"
    return ComponentIngestResult(
        status=status,
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        detail="component evidence ingested; DSP remains the calculator",
        ai_status="CONFIGURED" if agent in _AI_AGENTS else "NOT_CONFIGURED",
    )


def research_components_from_agent(
    agent: Any,
    listing: SecurityListing,
    *,
    fields: tuple[str, ...] = ("risk_free_rate", "beta", "equity_risk_premium"),
) -> ComponentIngestResult:
    """If the agent is not configured, return NOT_CONFIGURED. Never fabricate."""
    if agent is None or not callable(getattr(agent, "available", None)) or not agent.available():
        return ComponentIngestResult(
            status="UNKNOWN",
            accepted=(),
            rejected=(),
            detail="NOT_CONFIGURED",
            ai_status="NOT_CONFIGURED",
        )
    records: list[dict[str, Any]] = []
    now = datetime.now(tz=UTC)
    for field in fields:
        claim = agent.run(identity=listing.listing_id, field=field, document_text=None)
        if not isinstance(claim, ResearchClaim):
            continue
        records.append(
            {
                "field": claim.field,
                "value": claim.value,
                "source": claim.agent,
                "source_type": "llm",
                "source_url": claim.source_url,
                "retrieved_at": claim.retrieved_at or now,
                "as_of": claim.as_of,
                "isin": listing.isin,
                "mic": listing.mic,
                "unit": "decimal",
                "currency": listing.currency,
                "period": None,
                "evidence_locator": claim.document_locator,
            }
        )
    return ingest_researched_components(records, listing, proposed_by=getattr(agent, "role", "AI_RESEARCH"))


def evidence_item_from_component(
    record: Mapping[str, Any],
    listing: SecurityListing,
    *,
    agent: str = "gemini_find",
) -> EvidenceItem:
    """Build a RAW evidence row. EvidenceJudge still decides VERIFIED."""
    retrieved = record.get("retrieved_at") or datetime.now(tz=UTC)
    as_of = record.get("as_of")
    return EvidenceItem(
        evidence_id=str(record.get("evidence_id") or new_evidence_id()),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=str(record.get("isin") or listing.isin),
        mic=str(record.get("mic") or listing.mic),
        field=str(record["field"]),
        value=None if record.get("value") is None else str(record["value"]),
        as_of=as_of,
        retrieved_at=retrieved,
        source=str(record.get("source") or "unknown"),
        source_type=str(record.get("source_type") or "unknown"),
        source_url=record.get("source_url"),
        document_date=record.get("document_date") or as_of,
        evidence_locator=record.get("evidence_locator") or record.get("methodology"),
        currency=record.get("currency"),
        unit=record.get("unit"),
        statement_basis=record.get("statement_basis"),
        agent=agent,
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence=None if record.get("confidence") in {None, ""} else str(record.get("confidence")),
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
        period=record.get("period"),
        semantic_kind=(
            None
            if record.get("beta_kind") in {None, ""}
            and record.get("market") in {None, ""}
            and record.get("semantic_kind") in {None, ""}
            else str(record.get("beta_kind") or record.get("market") or record.get("semantic_kind"))
        ),
    )


def live_macro_acquisition_status() -> dict[str, Any]:
    """Approved hosts exist. Production does not scrape a new G-sec/ERP/beta feed."""
    return {
        "risk_free_rate": {
            "status": "UNKNOWN",
            "instrument": None,
            "maturity": None,
            "rate": None,
            "currency": "INR",
            "as_of": None,
            "source": "RBI",
            "source_url": "https://www.rbi.org.in",
            "retrieved_at": None,
            "detail": "rbi.org.in is Tier 1A; no production G-sec scraper; not hardcoded",
        },
        "beta": {
            "status": "UNKNOWN",
            "detail": (
                "no approved live beta series; Yahoo cannot VERIFY; "
                "official path has no price-series beta engine"
            ),
        },
        "equity_risk_premium": {
            "status": "UNKNOWN",
            "detail": "no approved ERP series; GDP/inflation/company growth/fixed % are not used",
        },
    }
