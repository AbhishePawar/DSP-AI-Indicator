# NSE-MCP-OPENAI-2 — Live NSE MCP + OpenAI Responses qualification

## STATUS

**PASS WITH LIMITATIONS**

NSE live gates are proven in this environment:

- initialize **PASS**
- tool discovery **PASS**
- tool call **PASS**
- RAW → EvidenceJudge (forensic, `production=False`) **PASS**
- production commercial block **PASS** (`UNAVAILABLE`)

OpenAI live gate is **BLOCKED**: `OPENAI_API_KEY` / `DSP_AI_OPENAI_API_KEY` is **MISSING**. No key was invented, printed, logged, or committed.

Not production-ready. Commercial use remains **pending**.

## BASELINE

- branch: `fix/asi003-dsp-platform-boundaries`
- HEAD: `bdf4f1ed6ea4bd72b11224a026694e14f6efe6f8`
- working-tree: dirty (SIMPLE-14N-E + NSE-MCP-OPENAI-1 additive files preserved)
- prior report: `docs/releases/NSE_MCP_OPENAI_FORENSIC_1.md` (**PASS WITH LIMITATIONS**)
- NSE-MCP-OPENAI-1 files (unchanged in role; mapping fix below is additive):
  - `packages/llm_adapters/src/llm_adapters/openai_responses.py`
  - `packages/llm_adapters/tests/test_openai_responses.py`
  - `packages/data_engine/src/data_engine/official_research/nse_mcp.py`
  - `packages/data_engine/src/data_engine/official_research/nse_mcp_evidence.py`
  - `packages/data_engine/src/data_engine/official_research/openai_nse_agent.py`
  - `packages/data_engine/src/data_engine/official_research/research_failures.py`
  - `packages/data_engine/src/data_engine/official_research/models.py`
  - `packages/data_engine/src/data_engine/official_research/judge.py`
  - `packages/data_engine/src/data_engine/official_research/source_policy.py`
  - `packages/data_engine/tests/test_nse_mcp_openai.py`
  - `packages/data_engine/tests/test_nse_mcp_live.py`
  - `docs/releases/NSE_MCP_OPENAI_FORENSIC_1.md`

Regression at start of this forensic (mocked, no live): **44 passed** (`test_simple14ne` 16, Chat Completions adapter 2, Responses 5, NSE MCP unit 21).

Chat Completions adapter was **not** modified. `/api/v1/analyse` was **not** modified. Valuation was **not** modified.

## NSE HTTP FORENSIC

Reproduced the OPENAI-1 observation, then isolated the layer. Bounded timeouts (8–12s). No proxy (`HTTP_PROXY`/`HTTPS_PROXY` unset).

| Layer | Result | Notes |
|---|---|---|
| DNS | **PASS** ~120–150ms | `mcp.nseindia.in` → Akamai IPv6 + IPv4 |
| TCP/443 IPv6 | **PASS** ~30ms | `2600:140f:7800::1730:f420` |
| TCP/443 IPv4 | **PASS** ~80–180ms | `23.55.244.122` / curl also hit `23.212.0.116` |
| TLS 1.3 | **PASS** ~90–120ms | `TLS_AES_256_GCM_SHA384`; ALPN `http/1.1` when offered |
| HTTP via curl IPv4 | **PASS** ~360–420ms | `HTTP/1.1 200`, `Content-Type: application/json`, `Mcp-Session-Id` present |
| HTTP via curl IPv6 | **PASS** ~301ms | same 200 body |
| HTTP via curl pinned `23.55.244.122` | **PASS** ~358ms | same 200; OPENAI-1 “bad edge” hypothesis rejected |
| HTTP via Python `urllib` / `http.client` | **PASS** ~273–305ms this session | initialize JSON 761 bytes |
| HTTP via raw Python sockets (manual HTTP/1.1) | **TIMEOUT** 8–10s, 0 bytes | not used by `NseMcpClient`; curl/urllib succeed on the same IPs |
| Proxy | **none** | |

OPENAI-1 closing probe (`MCP_TIMEOUT` after TLS) was **not** reproduced on the urllib client in this session. The server is reachable. The DSP client uses urllib, not raw sockets.

Malformed curl JSON (PowerShell escaping) produced Akamai **403** in 360ms — that is a request-body error, not a hang.

## MCP INITIALIZATION

Live, not mocked.

### Bhavcopy `https://mcp.nseindia.in/bhavcopy/cm/mcp`

- HTTP 200, ~737ms (`NseMcpClient`)
- protocol: `2025-03-26`
- session: `Mcp-Session-Id` present (value not required in this report)
- server: `nse-bhavcopy-redis-mcp` v1.0.0
- capabilities: tools, prompts, resources, logging, completions
- `notifications/initialized` accepted (202 on prior transport)
- instructions present: educational/research only; not investment advice

### CM Market `https://mcp.nseindia.in/cmmkt/mcp`

- HTTP 200, ~510ms
- protocol: `2025-03-26`
- session present
- server: `cm-market-mcp` v1.0.0
- capabilities: same family as bhavcopy
- instructions present (educational/research)

No credentials, cookies, or tokens were required or logged.

## TOOL DISCOVERY

Live `tools/list` revalidated. Names match the OPENAI-1 dump; they were **not** assumed.

### Bhavcopy (13) — 302ms

| name | required |
|---|---|
| `get_top_by_volume` | date, n, sortBy |
| `get_top_movers` | date, n, direction |
| `get_volume_analysis` | symbol, days |
| `nse_lookup_symbol` | query |
| `get_stock_history` | symbol, months, endDate |
| `search_symbols` | query |
| `get_market_breadth` | date |
| `get_corporate_actions` | symbol, fromDate, toDate |
| `compare_stocks` | symbols, months |
| `get_ltp_by_date` | symbol, date |
| `get_bulk_quote` | symbols |
| `moving_average` | symbol, days |
| `get_52_week_high_low` | symbol |

### CM Market (13)

| name | required |
|---|---|
| `cm_get_sme_stocks` | *(none in schema)* |
| `cm_get_live_market_data` | index |
| `cm_get_equity_stocks` | *(limit/filter optional in earlier dump; live schema revalidated)* |
| `nse_get_losers` | *(none)* |
| `cm_get_call_auction_stocks` | *(none)* |
| `cm_get_bond_stocks` | *(none)* |
| `cm_get_live_gainers` | *(none)* |
| `nse_get_gainers` | *(none)* |
| `cm_get_data_status` | *(none)* |
| `cm_get_live_losers` | *(none)* |
| `cm_get_stock_quote` | symbol |
| `nse_get_market_movers` | indexName, limit |
| `cm_get_allstocks_status` | *(none)* |

Capability selection remains generic (`lookup` → `nse_lookup_symbol`, `eod_ltp` → `get_ltp_by_date`, `live_quote` → `cm_get_stock_quote`).

## LIVE TOOL CALL

Fixtures only. Engine has no `if ticker ==`.

### 1. TCS (`INE467B01029` / `XNSE`) — controlled

| Call | Tool | Params | Latency | Raw result |
|---|---|---|---|---|
| lookup | `nse_lookup_symbol` | query=`TCS` | 246ms | `{count:2, symbols:["TCS","WSTCSTPAPR"]}` |
| EOD | `get_ltp_by_date` | symbol=`TCS`, date=`2026-09-11` | 203ms | **scalar** `2204.1` |
| delayed | `cm_get_stock_quote` | symbol=`TCS` | 265ms | object `stock.lastTradedPrice=2206.4`, `latestTimestamp=2026-09-11 13:39:33` |

`WSTCSTPAPR` is a substring hit from NSE lookup. Exact ticker `TCS` is present, so identity is not treated as ambiguous.

### 2. Second security (not hard-coded in application logic)

Security Master listing `20MICRONS` / `INE144J01027` / `XNSE` (smaller/non-blue-chip fixture).

| Call | Tool | Latency | Raw result |
|---|---|---|---|
| lookup | `nse_lookup_symbol` query=`20MICRONS` | 293ms | `{count:1, symbols:["20MICRONS"]}` |
| EOD | `get_ltp_by_date` | 172ms | scalar `211.87` |
| delayed | `cm_get_stock_quote` | 219ms | `lastTradedPrice=208.65` |

Generic `research_listing_via_nse_mcp` returned fields `eod_close` + `last_price` for both listings (~1s including rediscovery).

## RAW EVIDENCE

Live payloads preserved separately from normalized rows.

**Mapping defect found and fixed (this forensic only):** `get_ltp_by_date` returns a bare JSON number, not `{close,date,symbol}`. The mapper dropped it (`value=null`, `semantic=UNKNOWN`). Fix: accept a numeric **scalar** as `raw_price_field=scalar`. **Do not invent `as_of`** when the server omitted a date.

After fix (remap of the same live payloads):

| Listing | Field | Value | Kind | as_of | source_url | agent |
|---|---|---|---|---|---|---|
| TCS | eod_close | 2204.1 | **EOD** | unknown (server omitted) | `https://mcp.nseindia.in/bhavcopy/cm/mcp` | `official_nse_mcp` |
| TCS | last_price | 2206.4 | **DELAYED_15M** | 2026-09-11 | `https://mcp.nseindia.in/cmmkt/mcp` | `official_nse_mcp` |
| 20MICRONS | eod_close | 211.87 | **EOD** | unknown | bhavcopy MCP | `official_nse_mcp` |
| 20MICRONS | last_price | 208.65 | **DELAYED_15M** | 2026-09-11 | cmmkt MCP | `official_nse_mcp` |

EOD and delayed quotes are **not** collapsed. TCS 2204.1 ≠ 2206.4. No silent reconciliation.

Locator includes server, tool, field, `price_kind`, exchange, MIC. Stage remains **RAW** until the judge.

## EVIDENCEJUDGE RESULT

| Item | Forensic `production=False` | Production `production=True` |
|---|---|---|
| EOD scalar (after mapping fix) | **VERIFIED** | **UNAVAILABLE** (`COMMERCIAL_USE_PENDING`) |
| Delayed `cm_get_stock_quote` | **VERIFIED** | **UNAVAILABLE** |
| OpenAI narrative / `agent_claim` / `openai_nse_mcp` | **not VERIFIED** | **not VERIFIED** |

AI narrative is not an accepted financial fact. Primary MCP evidence wins when it passes the judge. Conflicting EOD vs delayed kinds stay distinct; they are not merged into one “price”.

## OPENAI RESPONSES

**BLOCKED — credentials unavailable.**

Environment: `OPENAI_KEY MISSING`, `OPENAI_MODEL unset`. No `.env` backend key was loaded into this process. `apps/web/.env.local` was **not** read (frontend; must not leak).

Unit path still proves:

- `POST https://api.openai.com/v1/responses` (not Chat Completions)
- remote MCP tool objects (`type=mcp`, NSE `server_url`)
- missing key → unavailable, no fabricated evidence
- secret redaction

Live `OpenAI → remote NSE MCP → tool execution` was **not** executed.

## OPENAI REMOTE MCP

Configuration exists and is unit-tested:

```json
{ "type": "mcp", "server_label": "nse_bhavcopy", "server_url": "https://mcp.nseindia.in/bhavcopy/cm/mcp", "require_approval": "never" }
```

`require_approval=never` is **forensic-only**. It is not a production default.

Live remote-MCP invocation by OpenAI: **not run** (no key). Direct NSE MCP tool execution (without OpenAI) is proven above.

## FAILURE TESTS

| Case | How | Result |
|---|---|---|
| missing OpenAI key | unit | unavailable; no evidence |
| OpenAI HTTP 429 / timeout | unit mock | classified; redacted |
| MCP timeout / unavailable / 429 | unit | transport codes; may trip breaker |
| malformed MCP | unit | `MCP_MALFORMED_RESPONSE`; breaker **not** tripped |
| unknown tool JSON-RPC | unit | `MCP_TOOL_NOT_FOUND`; breaker **not** tripped |
| unknown / ambiguous security | unit | domain codes; breaker **not** tripped |
| identity FAIL | unit | `DATA_VALIDATION_FAILED`; not VERIFIED |
| AI narrative vs MCP | unit | narrative rejected; MCP RAW may verify only via judge |
| invalid live curl body | live | Akamai 403, not fake 200 |
| live OpenAI invalid key | **not sent** | no live OpenAI calls |

Provider failure does not mint `VERIFIED_DATASET`. Production MCP remains `UNAVAILABLE`.

## UNIVERSALITY TEST

Same generic path for TCS and `20MICRONS`:

identity (ISIN+MIC) → discover tools → lookup → EOD + delayed quote → RAW → judge.

No `if ticker ==`, no `if company ==`, no special share-count path, no five-stock universe in MCP modules.

OpenAI-in-the-loop universality: **not live** (key missing). Prompt construction remains identity-parameterized.

## SECURITY

- No OpenAI key in this environment; none printed or committed
- MCP calls unauthenticated; no Authorization header used
- Session ids treated as transport metadata, not secrets in logs of this report
- `redact_secrets` / `redact_mcp_text` unit-tested
- No new public API, no `/api/v1/analyse` change, no client provider override
- Chat Completions copilot path unchanged

## PERFORMANCE

Too few repetitions for p50/p95. Single-shot live (this session):

| Step | Time |
|---|---|
| DNS | ~120–150ms |
| TCP | ~30–180ms |
| TLS | ~90–120ms |
| curl initialize | ~300–420ms total |
| urllib initialize | ~273–305ms |
| `NseMcpClient` bhavcopy initialize | 737ms |
| bhavcopy `tools/list` | 302ms |
| cmmkt initialize | 510ms |
| `nse_lookup_symbol` | 246–293ms |
| `get_ltp_by_date` | 172–203ms |
| `cm_get_stock_quote` | 219–265ms |
| generic two-tool research (reusing session) | ~1.0–1.1s |
| OpenAI request | n/a |

Bounded client timeout: 15–20s. Requests kept to discovery + two listings.

## COMMERCIAL STATUS

| Gate | State |
|---|---|
| Technical live NSE MCP | **TECHNICALLY_QUALIFIED** (this environment) |
| Commercial production data source | **COMMERCIAL_USE_PENDING** |
| OpenAI live remote MCP | **not technically qualified live** (no key) |

Server instructions remain educational/research only. Production judge blocks MCP rows.

## TEST RESULTS

```text
python -m pytest packages/llm_adapters/tests/test_openai_responses.py packages/llm_adapters/tests/test_openai_adapter.py packages/data_engine/tests/test_nse_mcp_openai.py packages/data_engine/tests/test_simple14ne.py packages/data_engine/tests/test_nse_mcp_live.py packages/data_engine/tests/test_official_research_engine.py packages/data_engine/tests/test_architecture.py packages/llm_adapters/tests/test_architecture.py --tb=no
```

**82 passed, 0 failed, 0 skipped, 0 xfail** (this shell had `DSP_NSE_MCP_LIVE=1`, so the three live smokes ran).

Without `DSP_NSE_MCP_LIVE=1`, those three tests skip; the suite does not depend on NSE.

Live smokes separately: **3 passed** (`test_nse_mcp_live.py`).

No pre-existing failures hidden in this focused set.

## FILES CHANGED

This forensic (layer fix + report only):

- `packages/data_engine/src/data_engine/official_research/nse_mcp_evidence.py` — accept scalar `get_ltp_by_date` numbers; do not invent dates
- `packages/data_engine/tests/test_nse_mcp_openai.py` — `test_scalar_ltp_payload_is_not_dropped`
- `docs/releases/NSE_MCP_OPENAI_2_LIVE_QUALIFICATION.md`

Live probe artifacts under `artifacts/` are forensic dumps, not production code. Chat Completions adapter untouched.

## PRODUCTION IMPACT

**NO PRODUCTION DEPLOYMENT**

- production environment unchanged
- no production API key
- no production feature flag
- no production MCP access
- no production OpenAI activation
- `/api/v1/analyse` unchanged
- valuation unchanged

## ROOT CAUSE OF ANY BLOCKER

1. **OpenAI live gate BLOCKED:** backend forensic environment has no `OPENAI_API_KEY`. Not an adapter defect. Not worked around.
2. **OPENAI-1 HTTP timeout:** not reproduced on urllib/curl this session. Raw-socket manual HTTP/1.1 still times out; that path is not the client. Treat prior timeout as environmental/Akamai + non-client framing, not as a remaining DSP contract hole.
3. **EOD mapping (fixed):** live `get_ltp_by_date` returns a scalar; object-only parsing dropped the value. Fail-closed was honest; scalar mapping restores the number without fabricating `as_of`.
4. **EOD `as_of` still unknown** when the server returns only a number. That limitation is preserved on purpose.

## DECISION

NSE MCP live HTTP qualification: **PASS** for initialize, discovery, and tool execution, with EvidenceJudge remaining authoritative and commercial production still blocked.

OpenAI Responses remote MCP live qualification: **BLOCKED** (no key).

Overall stage: **PASS WITH LIMITATIONS**.

Do not enable production. Do not treat NSE MCP as a commercially approved source.

## NEXT FORENSIC

NSE-MCP-OPENAI-3 should run **only** when a backend `OPENAI_API_KEY` is present:

1. Smallest Responses request with remote NSE MCP (`require_approval=never` forensic-only)
2. Prove `mcp_list_tools` + `mcp_call` in the Responses output
3. Map `mcp_call` output → RAW `official_nse_mcp` evidence
4. Reject the model narrative as authority
5. Repeat with a second listing (generic identity, no ticker branches)
6. Keep Chat Completions and production dark
