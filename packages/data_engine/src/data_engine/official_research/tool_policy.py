"""Tool exposure and authority. Availability is not authority."""

from __future__ import annotations

from data_engine.official_research.nse_mcp import BHAVCOPY_MCP_URL, CMMKT_MCP_URL
from data_engine.official_research.research_plan import ResearchPlan
from data_engine.official_research.source_policy import classify_source_url

__all__ = [
    "classify_tool_authority",
    "mcp_tools_for_plan",
    "nse_mcp_allowed_tool_names",
]

_PRICE_TOOLS = (
    "nse_lookup_symbol",
    "get_ltp_by_date",
    "get_bulk_quote",
    "get_stock_history",
    "cm_get_stock_quote",
    "cm_get_data_status",
)
_CA_TOOLS = ("get_corporate_actions",)


def classify_tool_authority(name: str, source_url: str | None = None) -> str:
    """PRIMARY / SECONDARY / DISCOVERY_ONLY. AI is never PRIMARY."""
    lowered = str(name or "").lower()
    if lowered in {"llm", "agent", "openai", "gemini", "claude", "narrative"}:
        return "DISCOVERY_ONLY"
    kind = classify_source_url(source_url)
    if kind == "primary" or (source_url or "") in {BHAVCOPY_MCP_URL, CMMKT_MCP_URL}:
        return "PRIMARY"
    if kind == "secondary":
        return "SECONDARY"
    if kind == "approved_research":
        return "SECONDARY"
    if "mcp.nseindia.in" in str(source_url or "").lower():
        return "PRIMARY"
    return "DISCOVERY_ONLY"


def nse_mcp_allowed_tool_names(plan: ResearchPlan) -> tuple[str, ...]:
    """Expose only tools required by the plan. Never the full catalog by default."""
    names: list[str] = ["nse_lookup_symbol"]
    fields = set(plan.missing_fields) | set(plan.requested_fields)
    if fields & {"eod_close", "last_price", "price"}:
        names.extend(_PRICE_TOOLS)
    if "shares_outstanding" in fields or any(
        task.evidence_class == "corporate_actions" for task in plan.tasks
    ):
        names.extend(_CA_TOOLS)
    if any(task.evidence_class == "market_price" for task in plan.tasks):
        names.extend(_PRICE_TOOLS)
    return tuple(dict.fromkeys(names))


def mcp_tools_for_plan(plan: ResearchPlan) -> tuple[str, ...]:
    return nse_mcp_allowed_tool_names(plan)
