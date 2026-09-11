"""Official NSE remote MCP client (Streamable HTTP). Forensic / research only.

Commercial production use is COMMERCIAL_USE_PENDING. Technical qualification
does not authorize production DSP valuation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from data_engine.market_quote.service import CircuitBreaker
from data_engine.official_research.research_failures import ResearchFailure

__all__ = [
    "BHAVCOPY_MCP_URL",
    "CMMKT_MCP_URL",
    "MCP_PROTOCOL_VERSION",
    "NSE_MCP_COMMERCIAL_STATUS",
    "NSE_MCP_TECHNICAL_STATUS",
    "NseMcpClient",
    "NseMcpTool",
    "TRANSPORT_FAILURE_CODES",
    "classify_mcp_http_failure",
    "parse_mcp_sse",
    "redact_mcp_text",
    "select_discovered_tool",
    "trips_circuit_breaker",
]

BHAVCOPY_MCP_URL = "https://mcp.nseindia.in/bhavcopy/cm/mcp"
CMMKT_MCP_URL = "https://mcp.nseindia.in/cmmkt/mcp"
MCP_PROTOCOL_VERSION = "2025-03-26"
NSE_MCP_TECHNICAL_STATUS = "TECHNICALLY_QUALIFIED"
NSE_MCP_COMMERCIAL_STATUS = "COMMERCIAL_USE_PENDING"

TRANSPORT_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "MCP_UNAVAILABLE",
        "MCP_TIMEOUT",
        "MCP_PROTOCOL_ERROR",
        "MCP_RATE_LIMITED",
        "MCP_AUTH_REQUIRED",
    }
)


def trips_circuit_breaker(code: str) -> bool:
    """Transport failures trip the breaker. Domain/data failures do not."""
    return code in TRANSPORT_FAILURE_CODES


_SECRET_RE = re.compile(
    r"(Bearer\s+)[A-Za-z0-9._\-]+|(sk-[A-Za-z0-9\-._]+)|"
    r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s]+",
    re.I,
)


def redact_mcp_text(text: str) -> str:
    """Strip credentials from MCP/provider errors. Never persist raw secrets."""
    return _SECRET_RE.sub(lambda m: (m.group(1) or "") + "[REDACTED]", str(text or ""))


def classify_mcp_http_failure(status: int | None, exc: BaseException | None = None) -> str:
    if isinstance(exc, TimeoutError):
        return "MCP_TIMEOUT"
    if status == 401 or status == 403:
        return "MCP_AUTH_REQUIRED"
    if status == 429:
        return "MCP_RATE_LIMITED"
    if status == 404:
        return "MCP_UNAVAILABLE"
    if status is not None and status >= 500:
        return "MCP_UNAVAILABLE"
    if exc is not None:
        name = type(exc).__name__.lower()
        message = str(exc).lower()
        if "timed out" in message or "timeout" in name:
            return "MCP_TIMEOUT"
        return "MCP_UNAVAILABLE"
    return "MCP_PROTOCOL_ERROR"


def parse_mcp_sse(body: str) -> dict[str, Any]:
    """Parse Streamable HTTP SSE JSON-RPC bodies."""
    chunks: list[str] = []
    for line in str(body or "").splitlines():
        if line.startswith("data:"):
            chunks.append(line[5:].lstrip())
    if not chunks:
        raise ValueError("MCP_MALFORMED_RESPONSE")
    raw = "\n".join(chunks).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("MCP_MALFORMED_RESPONSE") from exc
    if not isinstance(parsed, dict):
        raise ValueError("MCP_MALFORMED_RESPONSE")
    return parsed


@dataclass(frozen=True, slots=True)
class NseMcpTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    server: str
    server_url: str


def select_discovered_tool(
    tools: tuple[NseMcpTool, ...],
    purpose: str,
) -> NseMcpTool | None:
    """Pick a discovered tool by capability. No issuer-specific names."""
    wanted = {
        "lookup": ("nse_lookup_symbol", "search_symbols"),
        "eod_ltp": ("get_ltp_by_date",),
        "eod_bulk": ("get_bulk_quote",),
        "history": ("get_stock_history",),
        "live_quote": ("cm_get_stock_quote",),
        "freshness": ("cm_get_data_status",),
        "corporate_actions": ("get_corporate_actions",),
    }.get(purpose, ())
    by_name = {item.name: item for item in tools}
    for name in wanted:
        if name in by_name:
            return by_name[name]
    if purpose == "lookup":
        return next((item for item in tools if "lookup" in item.name or "search" in item.name), None)
    if purpose == "live_quote":
        return next((item for item in tools if "stock_quote" in item.name), None)
    return None


class NseMcpClient:
    """Session-aware Streamable HTTP MCP client."""

    def __init__(
        self,
        url: str,
        *,
        timeout_seconds: float = 20.0,
        breaker: CircuitBreaker | None = None,
        transport_post=None,
    ) -> None:
        self.url = url
        self._timeout = timeout_seconds
        self._breaker = breaker or CircuitBreaker()
        self._session_id: str | None = None
        self._post = transport_post or _default_post
        self.server_info: dict[str, Any] = {}

    def initialize(self) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "dsp-official-research", "version": "0.1"},
            },
        }
        body, headers, status = self._request(payload)
        session = headers.get("mcp-session-id") or headers.get("Mcp-Session-Id")
        if session:
            self._session_id = session
        result = _rpc_result(body)
        self.server_info = result.get("serverInfo") or {}
        notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        try:
            self._request(notify, allow_empty=True)
        except ResearchFailure:
            pass
        _ = status
        return result

    def list_tools(self) -> tuple[NseMcpTool, ...]:
        if self._session_id is None:
            self.initialize()
        body, _, _ = self._request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        result = _rpc_result(body)
        tools = result.get("tools") or []
        if not isinstance(tools, list):
            raise ResearchFailure("MCP_MALFORMED_RESPONSE", "tools/list missing tools")
        server = str((self.server_info or {}).get("name") or self.url)
        found: list[NseMcpTool] = []
        for item in tools:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            schema = item.get("inputSchema") or item.get("input_schema") or {}
            if not isinstance(schema, dict):
                schema = {}
            found.append(
                NseMcpTool(
                    name=str(item["name"]),
                    description=str(item.get("description") or ""),
                    input_schema=schema,
                    server=server,
                    server_url=self.url,
                )
            )
        return tuple(found)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self._session_id is None:
            self.initialize()
        body, _, _ = self._request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        result = _rpc_result(body)
        if result.get("isError"):
            detail = redact_mcp_text(str(result.get("content") or result))
            raise ResearchFailure("MCP_INVALID_ARGUMENT", detail, field=name)
        return result

    def _request(
        self, payload: dict[str, Any], *, allow_empty: bool = False
    ) -> tuple[dict[str, Any] | None, dict[str, str], int]:
        self._breaker.before_call()
        try:
            status, headers, raw = self._post(
                self.url,
                payload,
                session_id=self._session_id,
                timeout_seconds=self._timeout,
            )
        except ResearchFailure as exc:
            if trips_circuit_breaker(exc.code):
                self._breaker.record_failure()
            raise
        except Exception as exc:  # noqa: BLE001 — classified below
            code = classify_mcp_http_failure(None, exc)
            if trips_circuit_breaker(code):
                self._breaker.record_failure()
            raise ResearchFailure(code, redact_mcp_text(str(exc))) from None
        if status == 202 and allow_empty:
            self._breaker.record_success()
            return None, headers, status
        if status == 429:
            self._breaker.record_failure()
            raise ResearchFailure("MCP_RATE_LIMITED", "rate limited")
        if status in {401, 403}:
            self._breaker.record_failure()
            raise ResearchFailure("MCP_AUTH_REQUIRED", f"HTTP {status}")
        if status >= 400:
            code = classify_mcp_http_failure(status, None)
            if trips_circuit_breaker(code):
                self._breaker.record_failure()
            raise ResearchFailure(code, f"HTTP {status}")
        if not raw.strip():
            if allow_empty:
                self._breaker.record_success()
                return None, headers, status
            self._breaker.record_success()
            raise ResearchFailure("MCP_MALFORMED_RESPONSE", "empty MCP body")
        ctype = headers.get("content-type") or headers.get("Content-Type") or ""
        try:
            parsed = (
                parse_mcp_sse(raw)
                if "event-stream" in ctype
                else json.loads(raw)
            )
        except (json.JSONDecodeError, ValueError):
            self._breaker.record_success()
            raise ResearchFailure("MCP_MALFORMED_RESPONSE", "unparseable MCP body")
        if not isinstance(parsed, dict):
            self._breaker.record_success()
            raise ResearchFailure("MCP_MALFORMED_RESPONSE", "MCP JSON is not an object")
        if parsed.get("error"):
            self._breaker.record_success()
            err = parsed["error"]
            message = redact_mcp_text(str(err))
            if "not found" in message.lower():
                raise ResearchFailure("MCP_TOOL_NOT_FOUND", message)
            raise ResearchFailure("MCP_PROTOCOL_ERROR", message)
        self._breaker.record_success()
        return parsed, headers, status


def _rpc_result(body: dict[str, Any] | None) -> dict[str, Any]:
    if not body or "result" not in body:
        raise ResearchFailure("MCP_MALFORMED_RESPONSE", "missing JSON-RPC result")
    result = body["result"]
    if not isinstance(result, dict):
        raise ResearchFailure("MCP_MALFORMED_RESPONSE", "JSON-RPC result is not an object")
    return result


def _default_post(
    url: str,
    payload: dict[str, Any],
    *,
    session_id: str | None,
    timeout_seconds: float,
) -> tuple[int, dict[str, str], str]:
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            header_map = {str(k): str(v) for k, v in response.headers.items()}
            return int(response.status), header_map, raw
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        header_map = {str(k): str(v) for k, v in (exc.headers or {}).items()}
        if exc.code >= 400:
            code = classify_mcp_http_failure(exc.code, None)
            raise ResearchFailure(code, redact_mcp_text(raw[:300] or f"HTTP {exc.code}")) from None
        return int(exc.code), header_map, raw
    except TimeoutError as exc:
        raise ResearchFailure("MCP_TIMEOUT", "request timed out") from exc
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower():
            raise ResearchFailure("MCP_TIMEOUT", redact_mcp_text(reason)) from None
        raise ResearchFailure("MCP_UNAVAILABLE", redact_mcp_text(reason)) from None
