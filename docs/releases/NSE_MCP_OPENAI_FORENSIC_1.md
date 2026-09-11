# NSE-MCP-OPENAI-1 — OpenAI Responses API + official NSE MCP forensic

## STATUS

**PASS WITH LIMITATIONS**

Not production-ready. Not commercially approved. No Cloud Run / production env change.

Limitations that prevent CLOSE as PASS:

1. **Live NSE MCP HTTP is currently timing out in this environment** after a successful TCP/TLS handshake (`MCP_TIMEOUT`). Tool names below were discovered earlier in this forensic (saved local discovery dump) and are covered by mocked tests; they were **not** re-invoked successfully in the closing live probe.
2. **Live OpenAI Responses → remote MCP was not executed.** `OPENAI_API_KEY` / `DSP_AI_OPENAI_API_KEY` is **MISSING**. No key was logged.
3. Native remote-MCP `require_approval=never` is **forensic-only**. It must not become a production default.
4. NSE MCP server instructions restrict use to educational/research purposes. Production DSP valuation remains blocked (`COMMERCIAL_USE_PENDING`).

## CURRENT COMMIT

- branch: `fix/asi003-dsp-platform-boundaries`
- commit SHA: `bdf4f1ed6ea4bd72b11224a026694e14f6efe6f8`
- working-tree: **dirty**. Uncommitted SIMPLE-14N-E research-planner work is preserved. This forensic adds additive OpenAI Responses + NSE MCP files on top. Nested `DSP-AI-Indicator/`, `.bytecode_backup/`, `demoAuth*`, and `artifacts/` are parking noise and are not part of this adapter.

## FORENSIC FINDINGS

Inspected before architectural changes. Existing platform already had a research/evidence boundary. This stage does not replace Chat Completions and does not add Claude, Gemini, or Kite.

### A. OpenAIAdapter interface

`packages/llm_adapters/src/llm_adapters/openai_adapter.py` implements duck-typed `ProviderAdapter` (`llm_adapters/interfaces.py`), which matches copilot `LanguageModelPort`.

It posts to `https://api.openai.com/v1/chat/completions` with **httpx**. No OpenAI SDK. **Left unchanged.**

### B. Callers

`ProviderRegistry` → `CopilotCompleteService` (copilot explain/complete). That path is **not** official research and is **not** a financial-data authority.

### C. Research-specific invocation

No prior live OpenAI research agent. Official research agents in `official_research/agents.py` remain stubs (`enabled=False`). Role assignment is `provider_router.py` (names only; no APIs).

Prompt-assumed files **do not exist** and were not invented: `routing.py`, `model_catalog.py`, `cost_scoring.py`, `quality_gate.py`, `tools/protocol/`.

Config already supports `OPENAI_API_KEY` / `DSP_AI_OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`), `DEFAULT_AI_PROVIDER`.

### D. Tool calls

Chat Completions adapter has **no** tool/function protocol. Additive Responses client uses native `tools[].type=mcp` dicts (no SDK types in DSP domain).

### E. Provider error classification

Copilot adapter returns `LanguageModelStatus` failures. Research MCP uses typed `ResearchFailure` codes. Transport codes may trip `data_engine.market_quote.service.CircuitBreaker`. Domain/data codes do not.

### F. Research-agent routing

`route_research_roles()` assigns FIND/VERIFY/ATTACK/REVIEW names. OpenAI NSE MCP is an additive FIND-capable researcher (`OpenAINseMcpAgent`, `enabled=False` unless configured). It is **not** wired into production routing and does not replace the four-role map.

### G. Evidence entry

`EvidenceItem` in `official_research/models.py`. NSE MCP payloads map to **RAW** via `nse_mcp_evidence.tool_result_to_evidence` with agent `official_nse_mcp`. OpenAI narrative is a `ResearchClaim` only.

### H. EvidenceJudge

`EvidenceJudge` remains the gate: RAW → RECONCILED → VERIFIED.

- `source_type` `llm` / `agent_claim` cannot verify.
- agent `openai_nse_mcp` cannot verify.
- production + NSE MCP URL / `official_nse_mcp` → `UNAVAILABLE` (`COMMERCIAL_USE_PENDING`).

### I. Existing MCP abstraction

None before this forensic. Official NSE remote MCP is new, Streamable HTTP, urllib (no new dependency).

### J. SIMPLE-14N-E

Uncommitted universal planner/evidence work is still present and **GREEN** (16/16). No ticker-specific production adapters were added.

## NSE MCP CONNECTIVITY

Endpoints (no auth observed on prior successful init):

| Server | URL | This-session live probe | Prior discovery in this forensic |
|---|---|---|---|
| Bhavcopy | `https://mcp.nseindia.in/bhavcopy/cm/mcp` | **MCP_TIMEOUT** (~12–15s read timeout after TLS) | HTTP 200 initialize ~1.2s; protocol `2025-03-26`; `mcp-session-id`; `notifications/initialized` → 202; `tools/list` often `text/event-stream` |
| CM Market | `https://mcp.nseindia.in/cmmkt/mcp` | **MCP_TIMEOUT** (same) | Same protocol/session behavior |

This-session network facts (do not over-claim):

- DNS `mcp.nseindia.in` resolves (Akamai IPv6 + IPv4).
- TCP 443 connect succeeds (~30ms).
- TLS 1.3 handshake succeeds (~92ms).
- HTTP GET/POST then returns **0 bytes** until read timeout.

Classification: `MCP_TIMEOUT` (transport; may trip breaker). Not treated as `DATA_VALIDATION_FAILED`.

## TOOL DISCOVERY

Tool names were **not hard-coded as a five-stock universe**. Capability aliases (`lookup`, `eod_ltp`, `live_quote`, …) select from **discovered** names.

### Bhavcopy — `nse-bhavcopy-redis-mcp` v1.0.0 (13 tools)

| Tool | Role in this adapter |
|---|---|
| `nse_lookup_symbol` | generic symbol lookup |
| `search_symbols` | lookup fallback |
| `get_ltp_by_date` | EOD close/LTP by date |
| `get_bulk_quote` | EOD bulk |
| `get_stock_history` | historical OHLCV (unadjusted) |
| `get_corporate_actions` | CA discovery |
| `get_top_by_volume` | market scan (not issuer-specific) |
| `get_top_movers` | market scan |
| `get_volume_analysis` | market scan |
| `get_market_breadth` | market scan |
| `compare_stocks` | compare |
| `moving_average` | derived series |
| `get_52_week_high_low` | range |

`get_ltp_by_date` input (observed): `symbol` + `date` (yyyy-MM-dd), both required.

Server instructions: educational/research only; not investment advice.

### CM Market — `cm-market-mcp` v1.0.0 (13 tools)

| Tool | Notes from schema |
|---|---|
| `cm_get_stock_quote` | exact-symbol delayed/live quote; LTP + `latestTimestamp` |
| `cm_get_data_status` | freshness |
| `cm_get_live_market_data` | refresh ~5 minutes |
| `cm_get_equity_stocks` | refresh ~1 minute |
| `cm_get_sme_stocks` / `cm_get_bond_stocks` / `cm_get_call_auction_stocks` | segment lists |
| `cm_get_live_gainers` / `cm_get_live_losers` | raw segment lists |
| `nse_get_gainers` / `nse_get_losers` / `nse_get_market_movers` | movers |
| `cm_get_allstocks_status` | status |

Closing live `tools/call` in this environment: **not re-proven** (`MCP_TIMEOUT`).

## OPENAI RESPONSES MCP

**Unit-proven. Live SKIPPED (no API key).**

Preferred request (httpx, no SDK):

```http
POST https://api.openai.com/v1/responses
```

```json
{
  "model": "<OPENAI_MODEL>",
  "input": "<identity-bearing research prompt>",
  "max_output_tokens": 600,
  "tools": [
    {
      "type": "mcp",
      "server_label": "nse_bhavcopy",
      "server_url": "https://mcp.nseindia.in/bhavcopy/cm/mcp",
      "require_approval": "never"
    },
    {
      "type": "mcp",
      "server_label": "nse_cmmkt",
      "server_url": "https://mcp.nseindia.in/cmmkt/mcp",
      "require_approval": "never"
    }
  ]
}
```

Authentication: backend `Authorization: Bearer …` only. Never logged. Never placed on `EvidenceItem`.

Expected output items: `mcp_list_tools`, `mcp_call`, `message`. Narrative text is **not** financial authority.

Chat Completions remains for copilot. Responses is additive.

## CONTROLLED TEST

Fixture only: TCS / `INE467B01029` / `XNSE`.

| Layer | Result |
|---|---|
| Security Master resolve | MATCHES / RESOLVED |
| Mocked MCP lookup + `get_ltp_by_date` + `cm_get_stock_quote` | PASS — RAW `EvidenceItem` with EOD vs `DELAYED_15M` |
| EvidenceJudge (forensic, `production=False`) | EOD RAW can become VERIFIED when identity/source/semantics pass |
| EvidenceJudge (`production=True`) | UNAVAILABLE — commercial gate |
| OpenAI narrative as `agent_claim` / `openai_nse_mcp` | rejected; not VERIFIED |
| Live NSE research request this session | **FAIL / MCP_TIMEOUT** |
| Live OpenAI → NSE MCP | **SKIPPED** (no key) |

The OpenAI narrative is never treated as authenticated market data.

## UNIVERSAL TEST

Fixtures only: TCS, INFY, RELIANCE, HDFCBANK, WIPRO, plus smaller listing `20MICRONS` (`INE144J01027`).

Mocked generic path (same client, no ticker branches in engine source):

- accepts listing identity (company, ticker, ISIN, MIC)
- discovers tools
- looks up symbol
- fetches EOD + delayed quote
- records provenance

Engine source (`nse_mcp.py`, `nse_mcp_evidence.py`, `openai_nse_agent.py`) contains **no** `if ticker ==` and **no** fixture ticker literals.

Live multi-security MCP fetch this session: **MCP_TIMEOUT** after Security Master resolve succeeded for all six.

## EVIDENCE QUALITY

NSE-derived facts enter as RAW `official_nse_mcp` rows. Missing MCP fields stay unknown. Nothing is manufactured.

Preserved when present:

- `evidence_id`, `company`, `ticker`, `isin`, `mic` (exchange via listing + locator `exchange=` / `mic=`)
- `field`, `value`, `as_of`, `retrieved_at`
- `source`, `source_type`, `source_url`, `document_date`, `evidence_locator`
- `agent`, `identity_status`, `semantic_status`, `freshness_status`, `corporate_action_status`, `confidence`
- `raw_price_field`, `period`, `raw_value`

`EvidenceItem` has no separate `exchange` column; identity remains **ISIN + MIC**. Locator records `exchange=NSE`.

Price semantics (existing `PriceSnapshot`):

- Bhavcopy `get_ltp_by_date` / history → **EOD** / **HISTORICAL**
- CM `cm_get_stock_quote` / live tools → **DELAYED_15M** (frozen `PriceKind` has no 1–5 minute variant; never labeled REALTIME; never labeled EOD)

RAW provider data is **not** VERIFIED until EvidenceJudge checks identity, source authority, freshness, semantics, and (in production) the commercial gate. AI agreement is not evidence.

## FAILURE TESTS

| Code | Breaker | Unit result |
|---|---|---|
| `MCP_UNAVAILABLE` | trips | PASS |
| `MCP_TIMEOUT` | trips | PASS |
| `MCP_RATE_LIMITED` | trips | PASS |
| `MCP_AUTH_REQUIRED` | trips | classified |
| `MCP_PROTOCOL_ERROR` | transport class | classified; JSON-RPC app errors record success first |
| `MCP_MALFORMED_RESPONSE` | does **not** trip | PASS |
| `MCP_TOOL_NOT_FOUND` | does **not** trip | PASS |
| `MCP_INVALID_ARGUMENT` | does **not** trip | classified |
| `SECURITY_NOT_FOUND` | does **not** trip | PASS |
| `SECURITY_AMBIGUOUS` | does **not** trip | PASS |
| `DATA_VALIDATION_FAILED` (identity FAIL) | does **not** trip | PASS |
| `DATA_STALE` | does **not** trip | classified |

Live closing probe: `MCP_TIMEOUT` on both official servers.

## SECURITY

- API keys backend-only. Frontend unchanged. No new public OpenAI proxy endpoint.
- No client-controlled provider/model override.
- `redact_secrets` / `redact_mcp_text` strip Bearer / `sk-` tokens from errors.
- Authorization headers are not logged.
- Provider secrets are not stored on `EvidenceItem`.
- Chat Completions adapter still used only for copilot narrative.

## COST

Technical observations only. Official current OpenAI list prices were **not** re-verified against production billing.

- Model comes from `OPENAI_MODEL` / `DSP_AI_OPENAI_MODEL`, default **`gpt-4o-mini`**.
- Forensic Responses cap: `max_output_tokens=600`.
- Chat Completions adapter was not replaced with a more expensive model.
- Live token usage: **n/a** (no live OpenAI call).

## COMMERCIAL/LICENSE

Explicit split:

| State | Value |
|---|---|
| Technical adapter path | `TECHNICALLY_QUALIFIED` |
| Commercial production data source | `COMMERCIAL_USE_PENDING` |

NSE MCP server instructions state educational/research use, not investment advice. This forensic **does not** mark NSE MCP as an approved commercial production source. Production EvidenceJudge blocks MCP-derived rows.

## FILES CHANGED

Additive for this forensic (do not treat parking dirs as adapter files):

- `packages/llm_adapters/src/llm_adapters/openai_responses.py`
- `packages/llm_adapters/tests/test_openai_responses.py`
- `packages/data_engine/src/data_engine/official_research/nse_mcp.py`
- `packages/data_engine/src/data_engine/official_research/nse_mcp_evidence.py`
- `packages/data_engine/src/data_engine/official_research/openai_nse_agent.py`
- `packages/data_engine/src/data_engine/official_research/research_failures.py` (MCP + `SECURITY_NOT_FOUND`; `ResearchFailure` is an `Exception`)
- `packages/data_engine/src/data_engine/official_research/models.py` (roles `official_nse_mcp`, `openai_nse_mcp`)
- `packages/data_engine/src/data_engine/official_research/judge.py` (AI/MCP cannot bypass; production commercial block)
- `packages/data_engine/src/data_engine/official_research/source_policy.py` (`nseindia.in`, `mcp.nseindia.in` primary hosts)
- `packages/data_engine/tests/test_nse_mcp_openai.py`
- `packages/data_engine/tests/test_nse_mcp_live.py` (opt-in `DSP_NSE_MCP_LIVE=1`)
- `docs/releases/NSE_MCP_OPENAI_FORENSIC_1.md`

SIMPLE-14N-E files remain in the working tree and were not redesigned.

Not production infrastructure. Chat Completions adapter not removed.

## TEST RESULTS

```text
python -m pytest packages/llm_adapters/tests/test_openai_responses.py packages/data_engine/tests/test_nse_mcp_openai.py packages/data_engine/tests/test_simple14ne.py packages/data_engine/tests/test_nse_mcp_live.py --tb=no
```

**42 passed, 3 skipped** (live smoke skipped unless `DSP_NSE_MCP_LIVE=1`).

Related regression (not in the focused command above):

```text
python -m pytest packages/llm_adapters/tests/test_architecture.py packages/llm_adapters/tests/test_openai_adapter.py packages/data_engine/tests/test_architecture.py packages/data_engine/tests/test_official_research_engine.py -q
```

**36 passed.**

Live opt-in was **not** forced on the whole suite. A separate closing probe against the two official URLs timed out (`MCP_TIMEOUT`).

## PRODUCTION IMPACT

**NO PRODUCTION DEPLOYMENT**

- Cloud Run unchanged
- production environment variables unchanged
- OpenAI not enabled in production
- NSE MCP not enabled as a production data source
- DSP valuation behavior unchanged
- Gemini and existing adapters not removed
- no public proxy endpoint

## DECISION

The **adapter contract** is technically qualified for the **next forensic**:

`ResearchAgent` → OpenAI Responses (httpx) → native remote MCP → RAW `EvidenceItem` → EvidenceJudge`

with commercial production still **pending**.

This stage is **not CLOSED as PASS** because:

- live NSE MCP HTTP did not succeed in the closing environment
- live OpenAI Responses MCP was not executed (missing key)

Next forensic should re-prove:

1. HTTP initialize + `tools/list` + at least one `tools/call` on both NSE servers
2. OpenAI Responses remote MCP with a backend key (redacted)
3. one controlled listing → RAW evidence → judge, without AI authority bypass

Do not enable production. Do not treat this as commercial qualification.
