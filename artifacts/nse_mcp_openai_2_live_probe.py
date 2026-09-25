"""NSE-MCP-OPENAI-2 live qualification probe. Not a production path.

Writes redacted JSON under artifacts/. Does not print secrets.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.nse_mcp import (
    BHAVCOPY_MCP_URL,
    CMMKT_MCP_URL,
    NseMcpClient,
    select_discovered_tool,
)
from data_engine.official_research.nse_mcp_evidence import (
    mcp_content_payload,
    mcp_price_kind,
    research_listing_via_nse_mcp,
    tool_result_to_evidence,
)
from data_engine.security_master import SecurityMasterService, load_default_catalog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "nse_mcp_openai_2_live.json"


def _tool_row(tool) -> dict:
    schema = tool.input_schema or {}
    props = schema.get("properties") or {}
    required = list(schema.get("required") or [])
    optional = [name for name in props if name not in required]
    return {
        "name": tool.name,
        "description": (tool.description or "")[:240],
        "required": required,
        "optional": optional,
        "properties": sorted(props.keys()) if isinstance(props, dict) else [],
    }


def _probe_server(label: str, url: str) -> dict:
    rec: dict = {"label": label, "url": url}
    client = NseMcpClient(url, timeout_seconds=15.0)
    t0 = time.perf_counter()
    info = client.initialize()
    rec["initialize_ms"] = round((time.perf_counter() - t0) * 1000)
    rec["protocol"] = info.get("protocolVersion")
    rec["serverInfo"] = info.get("serverInfo")
    rec["capabilities"] = info.get("capabilities")
    rec["session"] = bool(client._session_id)
    rec["instructions_present"] = bool(info.get("instructions"))
    t1 = time.perf_counter()
    tools = client.list_tools()
    rec["list_ms"] = round((time.perf_counter() - t1) * 1000)
    rec["tools"] = [_tool_row(item) for item in tools]
    rec["client"] = client
    rec["tool_objects"] = tools
    return rec


def main() -> None:
    report: dict = {"servers": {}, "calls": [], "research": {}, "judge": {}}
    bhav = _probe_server("bhavcopy", BHAVCOPY_MCP_URL)
    cmm = _probe_server("cmmkt", CMMKT_MCP_URL)
    bhav_client = bhav.pop("client")
    cmm_client = cmm.pop("client")
    bhav_tools = bhav.pop("tool_objects")
    cmm_tools = cmm.pop("tool_objects")
    report["servers"]["bhavcopy"] = bhav
    report["servers"]["cmmkt"] = cmm

    master = SecurityMasterService(load_default_catalog())
    first = master.resolve("TCS", isin="INE467B01029", mic="XNSE")
    second = master.resolve("20MICRONS", isin="INE144J01027", mic="XNSE")
    fixtures = [("TCS", first), ("other", second)]

    lookup = select_discovered_tool(tuple(bhav_tools), "lookup")
    ltp = select_discovered_tool(tuple(bhav_tools), "eod_ltp")
    live = select_discovered_tool(tuple(cmm_tools), "live_quote")
    day = date.today().isoformat()

    for label, resolved in fixtures:
        listing = resolved.identity
        rec = {
            "fixture_label": label,
            "resolve": resolved.status,
            "ticker": None if listing is None else listing.ticker,
            "isin": None if listing is None else listing.isin,
            "mic": None if listing is None else listing.mic,
        }
        if listing is None:
            rec["error"] = "unresolved"
            report["calls"].append(rec)
            continue
        if lookup is not None:
            t0 = time.perf_counter()
            raw = bhav_client.call_tool(lookup.name, {"query": listing.ticker})
            rec["lookup"] = {
                "tool": lookup.name,
                "ms": round((time.perf_counter() - t0) * 1000),
                "payload": mcp_content_payload(raw),
            }
        if ltp is not None:
            t0 = time.perf_counter()
            raw = bhav_client.call_tool(
                ltp.name, {"symbol": listing.ticker, "date": day}
            )
            payload = mcp_content_payload(raw)
            item = tool_result_to_evidence(
                listing=listing, tool=ltp, result=raw, field="eod_close"
            )
            rec["ltp"] = {
                "tool": ltp.name,
                "params": {"symbol": listing.ticker, "date": day},
                "ms": round((time.perf_counter() - t0) * 1000),
                "payload": payload,
                "price_kind": mcp_price_kind(ltp.name, ltp.server_url),
                "evidence": item.to_public_dict(),
            }
            judged = EvidenceJudge().promote(item)
            prod = EvidenceJudge().promote(item, production=True)
            rec["ltp"]["judge"] = {"status": judged.status, "stage": judged.stage}
            rec["ltp"]["judge_production"] = {"status": prod.status, "stage": prod.stage}
        if live is not None:
            t0 = time.perf_counter()
            raw = cmm_client.call_tool(live.name, {"symbol": listing.ticker})
            payload = mcp_content_payload(raw)
            item = tool_result_to_evidence(
                listing=listing, tool=live, result=raw, field="last_price"
            )
            rec["quote"] = {
                "tool": live.name,
                "ms": round((time.perf_counter() - t0) * 1000),
                "payload": payload,
                "price_kind": mcp_price_kind(live.name, live.server_url),
                "evidence": item.to_public_dict(),
                "judge": {
                    "status": EvidenceJudge().promote(item).status,
                    "stage": EvidenceJudge().promote(item).stage,
                },
            }
        t0 = time.perf_counter()
        items = research_listing_via_nse_mcp(
            listing, bhavcopy=bhav_client, cmmkt=cmm_client, as_of=date.today()
        )
        rec["generic_research_ms"] = round((time.perf_counter() - t0) * 1000)
        rec["generic_fields"] = [item.field for item in items]
        rec["generic_kinds"] = [item.evidence_locator for item in items]
        rec["generic_stages"] = [item.stage for item in items]
        rec["generic_agents"] = [item.agent for item in items]
        report["calls"].append(rec)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, default=str, indent=2)[:250000], encoding="utf-8")
    print("WROTE", OUT)
    print(
        json.dumps(
            {
                "bhav": {
                    "protocol": bhav.get("protocol"),
                    "server": bhav.get("serverInfo"),
                    "n_tools": len(bhav.get("tools") or []),
                    "init_ms": bhav.get("initialize_ms"),
                    "names": [t["name"] for t in bhav.get("tools") or []],
                },
                "cmmkt": {
                    "protocol": cmm.get("protocol"),
                    "server": cmm.get("serverInfo"),
                    "n_tools": len(cmm.get("tools") or []),
                    "init_ms": cmm.get("initialize_ms"),
                    "names": [t["name"] for t in cmm.get("tools") or []],
                },
                "calls": [
                    {
                        "label": c.get("fixture_label"),
                        "ticker": c.get("ticker"),
                        "lookup_tool": (c.get("lookup") or {}).get("tool"),
                        "ltp_tool": (c.get("ltp") or {}).get("tool"),
                        "ltp_kind": (c.get("ltp") or {}).get("price_kind"),
                        "ltp_judge": (c.get("ltp") or {}).get("judge"),
                        "ltp_prod": (c.get("ltp") or {}).get("judge_production"),
                        "quote_kind": (c.get("quote") or {}).get("price_kind"),
                        "quote_judge": (c.get("quote") or {}).get("judge"),
                        "fields": c.get("generic_fields"),
                    }
                    for c in report["calls"]
                ],
            },
            default=str,
        )
    )


if __name__ == "__main__":
    main()
