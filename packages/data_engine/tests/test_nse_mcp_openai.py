"""OpenAI Responses API + official NSE MCP — mocked unit tests."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_engine.market_quote.service import CircuitBreaker
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, new_evidence_id
from data_engine.official_research.nse_mcp import (
    BHAVCOPY_MCP_URL,
    CMMKT_MCP_URL,
    NSE_MCP_COMMERCIAL_STATUS,
    NSE_MCP_TECHNICAL_STATUS,
    NseMcpClient,
    NseMcpTool,
    classify_mcp_http_failure,
    parse_mcp_sse,
    redact_mcp_text,
    select_discovered_tool,
    trips_circuit_breaker,
)
from data_engine.official_research.nse_mcp_evidence import (
    evidence_failure_code,
    mcp_price_kind,
    research_listing_via_nse_mcp,
    tool_result_to_evidence,
    tool_result_to_price_snapshot,
)
from data_engine.official_research.openai_nse_agent import (
    OpenAINseMcpAgent,
    evidence_from_mcp_calls,
    nse_remote_mcp_tools,
    research_prompt,
)
from data_engine.official_research.research_failures import ResearchFailure
from data_engine.security_master.models import SecurityListing
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.openai_responses import (
    OPENAI_RESPONSES_URL,
    OpenAIResponsesClient,
    build_remote_mcp_tool,
    build_responses_payload,
    parse_responses_output,
    redact_secrets,
)


def _scripted_client(url: str, tools: list[dict], calls: dict[str, dict]) -> NseMcpClient:
    def fake_post(request_url, payload, *, session_id, timeout_seconds):
        _ = request_url, session_id, timeout_seconds
        method = payload.get("method")
        if method == "initialize":
            return (
                200,
                {"mcp-session-id": "s", "content-type": "application/json"},
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "result": {
                            "protocolVersion": "2025-03-26",
                            "serverInfo": {"name": "scripted"},
                        },
                    }
                ),
            )
        if method == "notifications/initialized":
            return 202, {}, ""
        if method == "tools/list":
            return (
                200,
                {"content-type": "application/json"},
                json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}),
            )
        if method == "tools/call":
            name = payload["params"]["name"]
            return (
                200,
                {"content-type": "application/json"},
                json.dumps({"jsonrpc": "2.0", "id": 3, "result": calls[name]}),
            )
        raise AssertionError(payload)

    return NseMcpClient(url, transport_post=fake_post)


_LOOKUP_TOOL = {
    "name": "nse_lookup_symbol",
    "description": "lookup",
    "inputSchema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}
_LTP_TOOL = {
    "name": "get_ltp_by_date",
    "description": "eod close",
    "inputSchema": {
        "type": "object",
        "properties": {"symbol": {"type": "string"}, "date": {"type": "string"}},
        "required": ["symbol", "date"],
    },
}
_LIVE_TOOL = {
    "name": "cm_get_stock_quote",
    "description": "delayed quote",
    "inputSchema": {
        "type": "object",
        "properties": {"symbol": {"type": "string"}},
        "required": ["symbol"],
    },
}


def _listing(ticker: str, isin: str, name: str) -> SecurityListing:
    return SecurityListing(
        ticker=ticker,
        company_name=name,
        isin=isin,
        exchange="NSE",
        mic="XNSE",
        security_type="equity",
        eligibility=True,
    )


def _config() -> LLMPlatformConfig:
    return LLMPlatformConfig(
        default_provider="openai",
        openai_api_key="sk-test-secret-key",
        anthropic_api_key=None,
        gemini_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude",
        gemini_model="gemini",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def test_responses_request_construction() -> None:
    tool = build_remote_mcp_tool(
        server_label="nse_bhavcopy",
        server_url=BHAVCOPY_MCP_URL,
        require_approval="never",
    )
    payload = build_responses_payload(
        model="gpt-4o-mini",
        input_text="research",
        mcp_tools=(tool,),
        max_output_tokens=200,
    )
    assert payload["model"] == "gpt-4o-mini"
    assert payload["tools"][0]["type"] == "mcp"
    assert payload["tools"][0]["server_url"] == BHAVCOPY_MCP_URL
    assert "chat/completions" not in json.dumps(payload)


def test_remote_mcp_configuration() -> None:
    tools = nse_remote_mcp_tools()
    urls = {item["server_url"] for item in tools}
    assert BHAVCOPY_MCP_URL in urls
    assert CMMKT_MCP_URL in urls
    assert all(item["type"] == "mcp" for item in tools)


def test_mcp_initialization_handling() -> None:
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-03-26",
            "serverInfo": {"name": "nse-bhavcopy-redis-mcp", "version": "1.0.0"},
        },
    }
    posts = [
        (200, {"mcp-session-id": "abc", "content-type": "application/json"}, json.dumps(init)),
        (202, {"content-type": "application/json"}, ""),
    ]

    def fake_post(url, payload, *, session_id, timeout_seconds):
        _ = url, session_id, timeout_seconds
        return posts.pop(0)

    client = NseMcpClient(BHAVCOPY_MCP_URL, transport_post=fake_post)
    result = client.initialize()
    assert result["protocolVersion"] == "2025-03-26"
    assert client._session_id == "abc"


def test_mcp_tool_discovery() -> None:
    listed = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "tools": [
                {
                    "name": "nse_lookup_symbol",
                    "description": "lookup",
                    "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
                },
                {
                    "name": "get_ltp_by_date",
                    "description": "eod close",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string"},
                            "date": {"type": "string"},
                        },
                        "required": ["symbol", "date"],
                    },
                },
            ]
        },
    }
    posts = [
        (
            200,
            {"mcp-session-id": "s", "content-type": "application/json"},
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "bhav"}}}),
        ),
        (202, {}, ""),
        (200, {"content-type": "application/json"}, json.dumps(listed)),
    ]

    def fake_post(url, payload, *, session_id, timeout_seconds):
        _ = url, payload, session_id, timeout_seconds
        return posts.pop(0)

    tools = NseMcpClient(BHAVCOPY_MCP_URL, transport_post=fake_post).list_tools()
    assert select_discovered_tool(tools, "lookup").name == "nse_lookup_symbol"
    assert select_discovered_tool(tools, "eod_ltp").name == "get_ltp_by_date"


def test_mcp_tool_invocation() -> None:
    call = {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"symbol": "TCS", "close": 3001.5, "date": "2026-09-10"}),
                }
            ]
        },
    }
    client = NseMcpClient(BHAVCOPY_MCP_URL, transport_post=lambda *a, **k: (200, {"content-type": "application/json"}, json.dumps(call)))
    client._session_id = "s"
    result = client.call_tool("get_ltp_by_date", {"symbol": "TCS", "date": "2026-09-10"})
    listing = _listing("TCS", "INE467B01029", "Tata Consultancy Services Limited")
    tool = NseMcpTool("get_ltp_by_date", "eod", {}, "bhav", BHAVCOPY_MCP_URL)
    item = tool_result_to_evidence(listing=listing, tool=tool, result=result, field="eod_close")
    assert item.value == "3001.5"
    assert item.agent == "official_nse_mcp"
    assert item.stage == "RAW"
    assert mcp_price_kind("get_ltp_by_date", BHAVCOPY_MCP_URL) == "EOD"


def test_scalar_ltp_payload_is_not_dropped() -> None:
    listing = _listing("TCS", "INE467B01029", "Tata Consultancy Services Limited")
    tool = NseMcpTool("get_ltp_by_date", "eod", {}, "bhav", BHAVCOPY_MCP_URL)
    item = tool_result_to_evidence(
        listing=listing,
        tool=tool,
        result={"content": [{"type": "text", "text": "2204.1"}]},
        field="eod_close",
    )
    assert item.value == "2204.1"
    assert item.as_of is None
    assert item.raw_price_field == "scalar"
    assert item.semantic_status == "PASS"
    judged = EvidenceJudge().promote(item)
    assert judged.stage == "VERIFIED"
    assert EvidenceJudge().promote(item, production=True).status == "UNAVAILABLE"


def test_malformed_mcp_response() -> None:
    with pytest.raises(ValueError):
        parse_mcp_sse("not-sse")
    client = NseMcpClient(
        BHAVCOPY_MCP_URL,
        transport_post=lambda *a, **k: (200, {"content-type": "application/json"}, "not-json"),
    )
    client._session_id = "s"
    with pytest.raises(ResearchFailure) as exc:
        client.call_tool("x", {})
    assert exc.value.code == "MCP_MALFORMED_RESPONSE"
    assert trips_circuit_breaker("MCP_MALFORMED_RESPONSE") is False


def test_timeout() -> None:
    assert classify_mcp_http_failure(None, TimeoutError("timed out")) == "MCP_TIMEOUT"
    assert trips_circuit_breaker("MCP_TIMEOUT") is True


def test_rate_limit() -> None:
    assert classify_mcp_http_failure(429, None) == "MCP_RATE_LIMITED"
    client = NseMcpClient(
        BHAVCOPY_MCP_URL,
        transport_post=lambda *a, **k: (429, {}, ""),
    )
    client._session_id = "s"
    with pytest.raises(ResearchFailure) as exc:
        client.call_tool("x", {})
    assert exc.value.code == "MCP_RATE_LIMITED"
    assert trips_circuit_breaker(exc.value.code) is True


def test_unavailable_mcp() -> None:
    assert classify_mcp_http_failure(503, None) == "MCP_UNAVAILABLE"
    client = NseMcpClient(
        BHAVCOPY_MCP_URL,
        transport_post=lambda *a, **k: (_ for _ in ()).throw(ResearchFailure("MCP_UNAVAILABLE", "down")),
    )
    with pytest.raises(ResearchFailure) as exc:
        client.initialize()
    assert exc.value.code == "MCP_UNAVAILABLE"


def test_provider_secret_redaction() -> None:
    text = redact_secrets("Authorization: Bearer sk-test-secret-key failed")
    assert "sk-test-secret-key" not in text
    assert "[REDACTED]" in text
    assert "sk-test" not in redact_mcp_text("Bearer sk-live-abc")


def test_evidence_provenance() -> None:
    listing = _listing("INFY", "INE009A01021", "Infosys Limited")
    tool = NseMcpTool("get_ltp_by_date", "", {}, "nse-bhavcopy-redis-mcp", BHAVCOPY_MCP_URL)
    item = tool_result_to_evidence(
        listing=listing,
        tool=tool,
        result={"content": [{"type": "text", "text": json.dumps({"symbol": "INFY", "close": "1", "date": "2026-09-10"})}]},
        field="eod_close",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    assert item.isin == "INE009A01021"
    assert item.source_url == BHAVCOPY_MCP_URL
    assert item.evidence_locator
    assert item.document_date == date(2026, 9, 10)
    assert item.identity_status == "PASS"


def test_current_vs_eod_price_semantics() -> None:
    assert mcp_price_kind("get_ltp_by_date", BHAVCOPY_MCP_URL) == "EOD"
    assert mcp_price_kind("get_stock_history", BHAVCOPY_MCP_URL) == "HISTORICAL"
    assert mcp_price_kind("cm_get_stock_quote", CMMKT_MCP_URL) == "DELAYED_15M"
    assert mcp_price_kind("cm_get_live_market_data", CMMKT_MCP_URL) != "EOD"


def test_unknown_security() -> None:
    bhavcopy = _scripted_client(
        BHAVCOPY_MCP_URL,
        [_LOOKUP_TOOL, _LTP_TOOL],
        {
            "nse_lookup_symbol": {
                "content": [{"type": "text", "text": json.dumps([])}]
            }
        },
    )
    listing = _listing("ZZZZZ", "INE000Z01000", "Unknown Fixture Limited")
    with pytest.raises(ResearchFailure) as exc:
        research_listing_via_nse_mcp(listing, bhavcopy=bhavcopy, cmmkt=bhavcopy)
    assert exc.value.code == "SECURITY_NOT_FOUND"
    assert trips_circuit_breaker(exc.value.code) is False


def test_ambiguous_security() -> None:
    bhavcopy = _scripted_client(
        BHAVCOPY_MCP_URL,
        [_LOOKUP_TOOL, _LTP_TOOL],
        {
            "nse_lookup_symbol": {
                "content": [{"type": "text", "text": json.dumps(["AAA", "BBB"])}]
            }
        },
    )
    listing = _listing("ZZZZZ", "INE000Z01000", "Unknown Fixture Limited")
    with pytest.raises(ResearchFailure) as exc:
        research_listing_via_nse_mcp(listing, bhavcopy=bhavcopy, cmmkt=bhavcopy)
    assert exc.value.code == "SECURITY_AMBIGUOUS"
    assert trips_circuit_breaker(exc.value.code) is False


def test_generic_multi_security_research_and_no_ticker_branches() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
    forbidden = ("TCS", "INFY", "RELIANCE", "HDFCBANK", "WIPRO", "20MICRONS")
    for name in ("nse_mcp.py", "nse_mcp_evidence.py", "openai_nse_agent.py"):
        text = (src / name).read_text(encoding="utf-8")
        assert "if ticker ==" not in text
        for ticker in forbidden:
            assert ticker not in text
    fixtures = [
        _listing("TCS", "INE467B01029", "Tata Consultancy Services Limited"),
        _listing("INFY", "INE009A01021", "Infosys Limited"),
        _listing("RELIANCE", "INE002A01018", "Reliance Industries Limited"),
        _listing("HDFCBANK", "INE040A01034", "HDFC Bank Limited"),
        _listing("WIPRO", "INE075A01022", "Wipro Limited"),
        _listing("20MICRONS", "INE144J01027", "20 Microns Limited"),
    ]
    for listing in fixtures:
        prompt = research_prompt(
            company=listing.company_name,
            ticker=listing.ticker,
            isin=listing.isin,
            mic=listing.mic,
        )
        assert listing.isin in prompt
        assert listing.ticker in prompt
        bhavcopy = _scripted_client(
            BHAVCOPY_MCP_URL,
            [_LOOKUP_TOOL, _LTP_TOOL],
            {
                "nse_lookup_symbol": {
                    "content": [
                        {"type": "text", "text": json.dumps([listing.ticker])}
                    ]
                },
                "get_ltp_by_date": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "symbol": listing.ticker,
                                    "close": 101.25,
                                    "date": "2026-09-10",
                                }
                            ),
                        }
                    ]
                },
            },
        )
        cmmkt = _scripted_client(
            CMMKT_MCP_URL,
            [_LIVE_TOOL],
            {
                "cm_get_stock_quote": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "symbol": listing.ticker,
                                    "ltp": 101.5,
                                    "latestTimestamp": "2026-09-11T05:30:00",
                                }
                            ),
                        }
                    ]
                }
            },
        )
        items = research_listing_via_nse_mcp(
            listing, bhavcopy=bhavcopy, cmmkt=cmmkt, as_of=date(2026, 9, 10)
        )
        assert {item.field for item in items} == {"eod_close", "last_price"}
        eod = next(item for item in items if item.field == "eod_close")
        delayed = next(item for item in items if item.field == "last_price")
        assert "price_kind=EOD" in (eod.evidence_locator or "")
        assert "price_kind=DELAYED_15M" in (delayed.evidence_locator or "")
        snapshot = tool_result_to_price_snapshot(eod, listing, "EOD")
        assert snapshot is not None
        assert snapshot.price_kind == "EOD"
        live_snap = tool_result_to_price_snapshot(delayed, listing, "DELAYED_15M")
        assert live_snap is not None
        assert live_snap.price_kind == "DELAYED_15M"
        judged = EvidenceJudge().promote(eod)
        assert judged.stage == "VERIFIED"
        assert EvidenceJudge().promote(eod, production=True).status == "UNAVAILABLE"


def test_evidence_judge_rejects_openai_narrative() -> None:
    listing = _listing("TCS", "INE467B01029", "Tata Consultancy Services Limited")
    narrative = EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field="eod_close",
        value="999999",
        as_of=date(2026, 9, 10),
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        source="openai",
        source_type="agent_claim",
        source_url=None,
        document_date=None,
        evidence_locator="narrative",
        currency="INR",
        unit="actual",
        statement_basis=None,
        agent="openai_nse_mcp",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="LIVE",
    )
    promoted = EvidenceJudge().promote(narrative)
    assert promoted.status != "VERIFIED"
    assert promoted.stage != "VERIFIED"


def test_no_ai_to_dsp_bypass_and_commercial_gate() -> None:
    listing = _listing("TCS", "INE467B01029", "Tata Consultancy Services Limited")
    raw = EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field="eod_close",
        value="3001.5",
        as_of=date(2026, 9, 10),
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        source="nse-bhavcopy-redis-mcp",
        source_type="exchange_eod",
        source_url=BHAVCOPY_MCP_URL,
        document_date=date(2026, 9, 10),
        evidence_locator="mcp:bhav:get_ltp_by_date",
        currency="INR",
        unit="actual",
        statement_basis=None,
        agent="official_nse_mcp",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="medium",
        stage="RAW",
        status="UNKNOWN",
        mode="LIVE",
    )
    judge = EvidenceJudge()
    forensic = judge.promote(raw)
    assert forensic.stage == "VERIFIED"
    production = judge.promote(raw, production=True)
    assert production.status == "UNAVAILABLE"
    assert NSE_MCP_COMMERCIAL_STATUS == "COMMERCIAL_USE_PENDING"
    assert NSE_MCP_TECHNICAL_STATUS == "TECHNICALLY_QUALIFIED"


def test_openai_responses_client_parses_mcp_items() -> None:
    client = OpenAIResponsesClient(_config())
    data = {
        "output": [
            {"type": "mcp_list_tools", "server_label": "nse_bhavcopy", "tools": [{"name": "nse_lookup_symbol"}]},
            {
                "type": "mcp_call",
                "name": "get_ltp_by_date",
                "server_label": "nse_bhavcopy",
                "output": json.dumps({"symbol": "TCS", "close": 1, "date": "2026-09-10"}),
            },
            {"type": "message", "content": [{"type": "output_text", "text": "not a valuation"}]},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    parsed = parse_responses_output(data)
    assert parsed.mcp_list_tools
    assert parsed.mcp_calls
    listing = _listing("TCS", "INE467B01029", "Tata Consultancy Services Limited")
    items = evidence_from_mcp_calls(listing, parsed.mcp_calls)
    assert items[0].agent == "official_nse_mcp"
    assert items[0].stage == "RAW"
    with patch("llm_adapters.openai_responses.httpx.Client") as client_cls:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = data
        client_cls.return_value.__enter__.return_value.post.return_value = response
        result = client.invoke(build_responses_payload(model="gpt-4o-mini", input_text="x"))
        posted = client_cls.return_value.__enter__.return_value.post.call_args
        assert posted.args[0] == OPENAI_RESPONSES_URL
        assert result.mcp_calls


def test_openai_agent_unavailable_without_key() -> None:
    agent = OpenAINseMcpAgent(client=OpenAIResponsesClient(_config()), enabled=True)
    agent.client._config = LLMPlatformConfig(
        default_provider="openai",
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude",
        gemini_model="gemini",
        request_timeout_seconds=5.0,
        max_retries=0,
    )
    assert agent.available() is False
    claim = agent.run(identity="INE467B01029.XNSE", field="eod_close", document_text=None)
    assert claim.value is None
    assert "not fabricated" in (claim.notes or "")


def test_mcp_tool_not_found_does_not_trip_breaker() -> None:
    breaker = CircuitBreaker(failure_threshold=1)
    client = NseMcpClient(
        BHAVCOPY_MCP_URL,
        breaker=breaker,
        transport_post=lambda *a, **k: (
            200,
            {"content-type": "application/json"},
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "error": {"code": -32601, "message": "tool not found"},
                }
            ),
        ),
    )
    client._session_id = "s"
    with pytest.raises(ResearchFailure) as exc:
        client.call_tool("missing", {})
    assert exc.value.code == "MCP_TOOL_NOT_FOUND"
    assert breaker.is_open is False


def test_identity_failure_is_data_validation_not_breaker() -> None:
    listing = _listing("INFY", "INE009A01021", "Infosys Limited")
    tool = NseMcpTool("get_ltp_by_date", "", {}, "bhav", BHAVCOPY_MCP_URL)
    item = tool_result_to_evidence(
        listing=listing,
        tool=tool,
        result={
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"symbol": "TCS", "close": "1", "date": "2026-09-10"}
                    ),
                }
            ]
        },
        field="eod_close",
    )
    assert item.identity_status == "FAIL"
    assert evidence_failure_code(item) == "DATA_VALIDATION_FAILED"
    assert trips_circuit_breaker("DATA_VALIDATION_FAILED") is False
    assert EvidenceJudge().promote(item).status != "VERIFIED"
