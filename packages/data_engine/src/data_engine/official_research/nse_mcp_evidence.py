"""Map NSE MCP tool payloads to RAW EvidenceItem rows. Never fabricate."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from data_engine.official_research.models import (
    EvidenceItem,
    PriceSnapshot,
    new_evidence_id,
    utc_now,
)
from data_engine.official_research.nse_mcp import (
    BHAVCOPY_MCP_URL,
    CMMKT_MCP_URL,
    NseMcpClient,
    NseMcpTool,
    select_discovered_tool,
)
from data_engine.official_research.price import PriceContractError, validate_price_snapshot
from data_engine.official_research.research_failures import ResearchFailure
from data_engine.security_master.models import SecurityListing

__all__ = [
    "evidence_failure_code",
    "mcp_content_payload",
    "mcp_price_kind",
    "research_listing_via_nse_mcp",
    "tool_result_to_evidence",
    "tool_result_to_price_snapshot",
]


def mcp_price_kind(tool_name: str, server_url: str) -> str:
    """Preserve EOD vs delayed/live. Never label bhavcopy as live."""
    name = tool_name.lower()
    if "cmmkt" in server_url or name.startswith("cm_") or "live" in name:
        return "DELAYED_15M"
    if "history" in name:
        return "HISTORICAL"
    return "EOD"


def mcp_content_payload(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    content = result.get("content")
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                texts.append(str(item["text"]))
        if len(texts) == 1:
            try:
                return json.loads(texts[0])
            except json.JSONDecodeError:
                return texts[0]
        if texts:
            return texts
    return result


def _as_date(raw: Any) -> date | None:
    text = str(raw or "").strip()[:10]
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return None


def _dig(obj: Any, keys: tuple[str, ...]) -> tuple[Any, str | None]:
    if isinstance(obj, dict):
        lowered = {str(k).lower(): (k, v) for k, v in obj.items()}
        for key in keys:
            hit = lowered.get(key.lower())
            if hit is not None and hit[1] not in (None, ""):
                return hit[1], str(hit[0])
        for value in obj.values():
            found, name = _dig(value, keys)
            if found is not None:
                return found, name
    if isinstance(obj, list) and obj:
        return _dig(obj[0], keys)
    return None, None


def _scalar_number(payload: Any) -> tuple[Any, str | None]:
    """Preserve a bare numeric tool result. Do not invent a date or symbol."""
    if isinstance(payload, bool):
        return None, None
    if isinstance(payload, (int, float)):
        return payload, "scalar"
    if isinstance(payload, str):
        try:
            return Decimal(payload.replace(",", "").strip()), "scalar"
        except InvalidOperation:
            return None, None
    return None, None


def tool_result_to_evidence(
    *,
    listing: SecurityListing,
    tool: NseMcpTool,
    result: Any,
    field: str,
    retrieved_at: datetime | None = None,
) -> EvidenceItem:
    payload = mcp_content_payload(result)
    value, value_key = _dig(
        payload,
        ("close", "ltp", "lastPrice", "last_price", "lastTradedPrice", "ClsPric", "price"),
    )
    if value is None:
        value, value_key = _scalar_number(payload)
    as_of, _ = _dig(payload, ("date", "tradDt", "timestamp", "latestTimestamp", "asOf"))
    symbol, _ = _dig(payload, ("symbol", "ticker", "tckrSymb", "SYMBOL"))
    identity = "PASS"
    if symbol is not None and str(symbol).strip().upper() not in {
        listing.ticker.upper(),
        *{alias.upper() for alias in listing.aliases},
    }:
        identity = "FAIL"
    semantic = "PASS" if value is not None else "UNKNOWN"
    kind = mcp_price_kind(tool.name, tool.server_url)
    locator = (
        f"mcp:{tool.server}:{tool.name};field={value_key or 'unknown'};"
        f"price_kind={kind};exchange={listing.exchange};mic={listing.mic}"
    )
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field=field,
        value=None if value is None else str(value),
        as_of=_as_date(as_of),
        retrieved_at=retrieved_at or utc_now(),
        source=tool.server,
        source_type="exchange_eod" if kind in {"EOD", "HISTORICAL"} else "regulator",
        source_url=tool.server_url,
        document_date=_as_date(as_of),
        evidence_locator=locator,
        currency="INR",
        unit="actual",
        statement_basis=None,
        agent="official_nse_mcp",
        identity_status=identity,
        semantic_status=semantic if value is not None else "UNKNOWN",
        freshness_status="UNKNOWN",
        corporate_action_status="UNKNOWN",
        confidence="medium" if value is not None else "low",
        stage="RAW",
        status="UNKNOWN",
        mode="LIVE",
        raw_price_field=value_key,
        period=None if as_of is None else str(as_of)[:10],
        raw_value=None if value is None else str(value),
        raw_unit="actual",
    )


def tool_result_to_price_snapshot(
    item: EvidenceItem, listing: SecurityListing, kind: str
) -> PriceSnapshot | None:
    """Preserve EOD vs delayed semantics. Returns None when a snapshot would be fabricated."""
    if item.value is None or item.as_of is None:
        return None
    try:
        price = Decimal(str(item.value).replace(",", "").strip())
    except InvalidOperation:
        return None
    try:
        return validate_price_snapshot(
            PriceSnapshot(
                price=price,
                price_kind=kind,  # type: ignore[arg-type]
                as_of=item.as_of,
                retrieved_at=item.retrieved_at,
                currency=item.currency or "INR",
                source=item.source,
                isin=listing.isin,
                mic=listing.mic,
                raw_price_field=item.raw_price_field or "unknown",
                ticker=listing.ticker,
                venue=listing.exchange,
                source_url=item.source_url,
                evidence_locator=item.evidence_locator,
                mode=item.mode,
            )
        )
    except PriceContractError:
        return None


def evidence_failure_code(item: EvidenceItem) -> str | None:
    if item.identity_status == "FAIL":
        return "DATA_VALIDATION_FAILED"
    if item.freshness_status == "FAIL":
        return "DATA_STALE"
    return None


def research_listing_via_nse_mcp(
    listing: SecurityListing,
    *,
    bhavcopy: NseMcpClient | None = None,
    cmmkt: NseMcpClient | None = None,
    query: str | None = None,
    as_of: date | None = None,
) -> tuple[EvidenceItem, ...]:
    """Generic listing → discover tools → invoke. No issuer branches."""
    items: list[EvidenceItem] = []
    bhavcopy = bhavcopy or NseMcpClient(BHAVCOPY_MCP_URL)
    tools = bhavcopy.list_tools()
    lookup = select_discovered_tool(tools, "lookup")
    needle = (query or listing.ticker or listing.company_name).strip()
    if lookup is not None:
        looked = bhavcopy.call_tool(lookup.name, _arguments(lookup, {"query": needle, "symbol": needle}))
        payload = mcp_content_payload(looked)
        matches = _symbol_matches(payload, listing.ticker)
        exact = listing.ticker.upper()
        if exact not in {item.upper() for item in matches}:
            if matches:
                raise ResearchFailure("SECURITY_AMBIGUOUS", ",".join(matches[:8]))
            raise ResearchFailure("SECURITY_NOT_FOUND", f"MCP lookup missed {listing.ticker}")
    ltp = select_discovered_tool(tools, "eod_ltp")
    if ltp is not None:
        day = (as_of or date.today()).isoformat()
        raw = bhavcopy.call_tool(
            ltp.name,
            _arguments(ltp, {"symbol": listing.ticker, "date": day}),
        )
        items.append(
            tool_result_to_evidence(
                listing=listing, tool=ltp, result=raw, field="eod_close"
            )
        )
    if cmmkt is None:
        cmmkt = NseMcpClient(CMMKT_MCP_URL)
    live_tools = cmmkt.list_tools()
    live = select_discovered_tool(live_tools, "live_quote")
    if live is not None:
        raw_live = cmmkt.call_tool(
            live.name, _arguments(live, {"symbol": listing.ticker})
        )
        items.append(
            tool_result_to_evidence(
                listing=listing, tool=live, result=raw_live, field="last_price"
            )
        )
    return tuple(items)


def _arguments(tool: NseMcpTool, values: dict[str, Any]) -> dict[str, Any]:
    props = (tool.input_schema or {}).get("properties") or {}
    required = (tool.input_schema or {}).get("required") or []
    out: dict[str, Any] = {}
    if not isinstance(props, dict):
        return values
    for key, value in values.items():
        if key in props:
            out[key] = value
    for key in required:
        if key not in out and key in values:
            out[key] = values[key]
        if key not in out and key.lower() in {k.lower() for k in values}:
            match = next(k for k in values if k.lower() == key.lower())
            out[key] = values[match]
    return out


def _symbol_matches(payload: Any, ticker: str) -> tuple[str, ...]:
    found: list[str] = []
    target = ticker.upper()
    symbol_keys = {"symbol", "ticker", "nse_symbol", "tckrsymb"}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in symbol_keys and value not in (None, ""):
                    found.append(str(value).strip().upper())
                else:
                    walk(value)
            return
        if isinstance(node, list):
            if node and all(isinstance(item, str) for item in node):
                for item in node:
                    token = item.strip().upper()
                    if token:
                        found.append(token)
                return
            for item in node:
                walk(item)

    walk(payload)
    unique = tuple(dict.fromkeys(found))
    if target in unique:
        return (target,)
    return unique
