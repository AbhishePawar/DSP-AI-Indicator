"""OpenAI Responses + NSE remote MCP research agent.

The model is a researcher. MCP tool output may become RAW evidence.
The OpenAI narrative never becomes VERIFIED financial truth.

Payloads are plain dicts. This module does not import OpenAI SDK types.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from data_engine.official_research.models import ResearchClaim
from data_engine.official_research.nse_mcp import BHAVCOPY_MCP_URL, CMMKT_MCP_URL, NseMcpTool
from data_engine.official_research.nse_mcp_evidence import tool_result_to_evidence
from data_engine.security_master.models import SecurityListing

__all__ = [
    "OpenAINseMcpAgent",
    "OpenAINseResearchOutcome",
    "evidence_from_mcp_calls",
    "nse_remote_mcp_tools",
    "research_prompt",
]

_SERVER_URLS = {
    "nse_bhavcopy": BHAVCOPY_MCP_URL,
    "nse_cmmkt": CMMKT_MCP_URL,
}


def nse_remote_mcp_tools() -> tuple[dict[str, Any], ...]:
    """Responses API remote-MCP tool list. Tool names are discovered by OpenAI."""
    return (
        {
            "type": "mcp",
            "server_label": "nse_bhavcopy",
            "server_url": BHAVCOPY_MCP_URL,
            "require_approval": "never",
            "server_description": "Official NSE Bhavcopy MCP (EOD/historical). Educational use only.",
        },
        {
            "type": "mcp",
            "server_label": "nse_cmmkt",
            "server_url": CMMKT_MCP_URL,
            "require_approval": "never",
            "server_description": "Official NSE CM Market MCP (delayed/live). Educational use only.",
        },
    )


def research_prompt(*, company: str, ticker: str, isin: str, mic: str) -> str:
    return (
        "Identify the exact NSE security for the provided identity. "
        "Retrieve the latest available market information and relevant historical "
        "price information from official NSE MCP tools. Return raw evidence, "
        "security identity, dates/timestamps, tool/source information, and uncertainty. "
        "Do not provide an investment conclusion.\n"
        f"company={company}\nticker={ticker}\nisin={isin}\nmic={mic}"
    )


@dataclass(frozen=True, slots=True)
class OpenAINseResearchOutcome:
    claims: tuple[ResearchClaim, ...]
    mcp_calls: tuple[dict[str, Any], ...]
    output_text: str | None
    usage: dict[str, Any] | None
    error: str | None


@dataclass(frozen=True, slots=True)
class OpenAINseMcpAgent:
    """FIND-capable researcher. enabled=False unless an OpenAI key is configured."""

    client: Any
    enabled: bool = False
    role: str = "openai_nse_mcp"

    def available(self) -> bool:
        return bool(self.enabled and self.client is not None and self.client.is_configured())

    def run(
        self, *, identity: str, field: str, document_text: str | None
    ) -> ResearchClaim:
        _ = document_text
        if not self.available():
            return ResearchClaim(
                field=field,
                value=None,
                source_url=None,
                document_locator=None,
                agent=self.role,
                notes="agent unavailable — not fabricated",
            )
        return ResearchClaim(
            field=field,
            value=None,
            source_url=None,
            document_locator="openai-nse-mcp-find",
            agent=self.role,
            notes=f"FIND proposal only; identity={identity}; not financial truth",
        )

    def research_listing(self, listing: SecurityListing) -> OpenAINseResearchOutcome:
        if not self.available():
            return OpenAINseResearchOutcome(
                claims=(),
                mcp_calls=(),
                output_text=None,
                usage=None,
                error="OPENAI_API_KEY not configured",
            )
        model = getattr(self.client, "model_label", None) or "gpt-4o-mini"
        payload = {
            "model": model,
            "input": research_prompt(
                company=listing.company_name,
                ticker=listing.ticker,
                isin=listing.isin,
                mic=listing.mic,
            ),
            "max_output_tokens": 600,
            "tools": list(nse_remote_mcp_tools()),
        }
        result = self.client.invoke(payload)
        claim = ResearchClaim(
            field="research_narrative",
            value=None,
            source_url=None,
            document_locator="openai-responses-narrative",
            agent=self.role,
            notes=(result.output_text or result.error or "no narrative")[:1000],
        )
        return OpenAINseResearchOutcome(
            claims=(claim,),
            mcp_calls=result.mcp_calls,
            output_text=result.output_text,
            usage=result.usage,
            error=result.error,
        )


def _mcp_call_url(server_label: str) -> str:
    if server_label in _SERVER_URLS:
        return _SERVER_URLS[server_label]
    lowered = server_label.lower()
    if "cmmkt" in lowered or lowered.endswith("_cm"):
        return CMMKT_MCP_URL
    return BHAVCOPY_MCP_URL


def evidence_from_mcp_calls(
    listing: SecurityListing, calls: tuple[dict[str, Any], ...]
) -> tuple:
    """Promote MCP tool outputs — not the model narrative — to RAW evidence."""
    items = []
    for call in calls:
        name = str(call.get("name") or "")
        server = str(call.get("server_label") or "")
        url = _mcp_call_url(server)
        output = call.get("output")
        if isinstance(output, dict) and "content" in output:
            result: Any = output
        elif isinstance(output, (dict, list)):
            result = {"content": [{"type": "text", "text": json.dumps(output)}]}
        else:
            result = {"content": [{"type": "text", "text": str(output)}]}
        tool = NseMcpTool(
            name=name or "unknown_tool",
            description="",
            input_schema={},
            server=server or "nse_mcp",
            server_url=url,
        )
        field = "last_price" if "cm" in name or "live" in name else "eod_close"
        items.append(
            tool_result_to_evidence(
                listing=listing,
                tool=tool,
                result=result,
                field=field,
            )
        )
    return tuple(items)
