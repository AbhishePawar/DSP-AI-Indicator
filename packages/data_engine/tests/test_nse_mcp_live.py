"""Live NSE MCP smoke tests. Skipped unless DSP_NSE_MCP_LIVE=1.

Does not require OpenAI. Does not deploy anything.
"""

from __future__ import annotations

import os

import pytest

from data_engine.official_research.nse_mcp import (
    BHAVCOPY_MCP_URL,
    CMMKT_MCP_URL,
    NseMcpClient,
    select_discovered_tool,
)
from data_engine.official_research.nse_mcp_evidence import research_listing_via_nse_mcp
from data_engine.security_master import SecurityMasterService, load_default_catalog

pytestmark = pytest.mark.skipif(
    os.environ.get("DSP_NSE_MCP_LIVE", "").strip() != "1",
    reason="set DSP_NSE_MCP_LIVE=1 to run live NSE MCP smoke tests",
)


def test_live_bhavcopy_initialize_and_tools() -> None:
    client = NseMcpClient(BHAVCOPY_MCP_URL, timeout_seconds=25.0)
    info = client.initialize()
    assert info.get("protocolVersion")
    tools = client.list_tools()
    names = {item.name for item in tools}
    assert names
    assert select_discovered_tool(tools, "lookup") is not None


def test_live_cmmkt_initialize_and_tools() -> None:
    client = NseMcpClient(CMMKT_MCP_URL, timeout_seconds=25.0)
    info = client.initialize()
    assert info.get("protocolVersion")
    tools = client.list_tools()
    assert tools
    assert select_discovered_tool(tools, "live_quote") is not None or select_discovered_tool(tools, "freshness") is not None


def test_live_generic_fixture_research() -> None:
    master = SecurityMasterService(load_default_catalog())
    resolved = master.resolve("INE467B01029", isin="INE467B01029", mic="XNSE")
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    items = research_listing_via_nse_mcp(resolved.identity)
    assert items
    assert all(item.stage == "RAW" for item in items)
    assert all(item.agent == "official_nse_mcp" for item in items)
    assert all(item.status != "VERIFIED" for item in items)
