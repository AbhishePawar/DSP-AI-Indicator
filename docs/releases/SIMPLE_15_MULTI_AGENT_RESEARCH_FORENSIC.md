# SIMPLE-15 — Controlled Multi-Agent Research Mesh Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED. Live OpenAI was not executed: no API key is present. Architecture is proven on deterministic mocks.

**NO PRODUCTION DEPLOYMENT**

## BASELINE

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| Working tree at start | Parking leftovers only (`.bytecode_backup/`, nested repo, `demoAuth*`, `artifacts/`, `body.txt`) |
| Focused regression before edits | **89 passed** (14N-E 16, 14N-F 17, NSE-MCP 22, OpenAI Responses 5, EvidenceJudge 29) |

Existing work was not discarded.

## CURRENT RESEARCH ARCHITECTURE

Canonical stack (unchanged as the single framework):

```
ResearchRequest
→ ResearchPlan (build_research_plan)
→ acquire_planned_fields / EvidenceJudge
→ VerifiedDataset
→ dsp_gate
→ DSP
```

SIMPLE-15 **extends** this. It does not add a second ResearchRequest, EvidenceItem, EvidenceJudge, source policy, or verification system.

Inspected, not invented:

| Surface | Location | SIMPLE-15 action |
|---|---|---|
| ResearchRequest / EvidenceItem / ResearchResult | `models.py` | Additive optional fields only |
| ResearchPlan | `research_plan.py` | Reused |
| EvidenceJudge | `judge.py` | Reused; still the only VERIFIED writer |
| OpenAI Chat Completions (Copilot) | `llm_adapters/openai_adapter.py` | Untouched |
| OpenAI Responses | `llm_adapters/openai_responses.py` | Reused |
| NSE MCP | `nse_mcp.py` / `openai_nse_agent.py` | Reused; allow-list added |
| Provider router | `provider_router.py` | Extended; legacy `route_research_roles` preserved |
| Model catalog / cost-scoring / quality_gate | **Do not exist** | Not invented. Cost is a router input, not a catalog rewrite |

Duplication found: FIND/VERIFY/ATTACK/REVIEW stubs vs the new `ResearchAgentPort`. Stubs remain interface-compatible (`available() is False`). The mesh uses the port. Not merged into one class to avoid breaking 14N-E agent tests.

## AGENT CONTRACT

`ResearchAgentPort` (`agent_port.py`):

- input: existing `ResearchRequest` + `ResearchPlan` + `ResearchContext`
- output: existing `ResearchResult`

`ResearchContext.user_assumptions` are never evidence.

`ResearchResult` additive fields: `status`, `provider`, `model_label`, `evidence_ids`, `research_trace`, `limitations`, `provenance`, `research_agents`.

No OpenAI SDK types leak into DSP domain code. Payloads remain plain dicts.

Gemini and Claude: `UnavailableResearchPort` — interface only.

Kite: excluded. BSE: not added as an agent. Yahoo: secondary source class only.

## AGENT ROUTER

`route_research_roles` is unchanged (14N-E: FIND substitutes to chatgpt when gemini is off).

New `select_research_agent(RouterInputs)` chooses by:

- availability
- required capabilities (e.g. MCP)
- cost weight
- latency
- quota
- configurable `preferred_model`

Defaults (Gemini=FIND, OpenAI=VERIFY, Claude=REVIEW) are **not** permanent ownership. This stage qualifies **OpenAI only**. If Gemini/Claude are marked available, they still do **not** count as independent researchers (`independent_agents` stays 1 when only OpenAI is qualified).

No fake parallel agents. `research_agents = 1` when only OpenAI is active.

## OPENAI

Primary implementation target: existing additive **Responses** client.

- Copilot Chat Completions: not replaced
- Research: `OpenAINseMcpAgent.research()` → Responses + NSE remote MCP tools → RAW evidence + narrative **claim**
- Narrative `verification_status=REJECT`
- Judge still refuses `agent=openai_nse_mcp` / `source_type=llm`

Live OpenAI: **not run**. `OPENAI_API_KEY` / `DSP_AI_OPENAI_API_KEY` absent. Not fabricated.

## NSE MCP

Still:

- `NSE_MCP_TECHNICAL_STATUS = TECHNICALLY_QUALIFIED`
- `NSE_MCP_COMMERCIAL_STATUS = COMMERCIAL_USE_PENDING`

Tool availability ≠ authority. Official NSE MCP URLs classify as **PRIMARY** for market facts. AI remains **DISCOVERY_ONLY**.

Production judge path still blocks MCP commercial use.

## TOOL POLICY

`nse_mcp_allowed_tool_names(plan)` exposes only tools required by the plan (lookup + price tools and/or corporate actions). `nse_remote_mcp_tools(allowed_tools=...)` passes that allow-list into Responses.

Each recorded tool call stores: name, arguments, timestamp, redacted response, provider, source, evidence locator, authority.

Credentials are not stored.

## RESEARCH TRACE

`ResearchTrace` records:

request_id, security_identity, plan_id, agent_provider, model, steps[], tool_calls[], evidence_ids[], decisions[], errors[], started_at, completed_at, cost, timings, independent_agents

All seven steps are always recorded: PLAN, DISCOVER, RETRIEVE, EXTRACT, NORMALIZE, RECONCILE, VERIFY.

Secrets are redacted (`redact_mcp_text`).

## CLAIM MODEL

`ResearchClaim` now carries optional `evidence_ids`, `as_of`, `retrieved_at`, `verification_status`.

Model prose is a claim, not evidence. Verification is EvidenceJudge output.

## EVIDENCE DEDUPLICATION

`evidence_fingerprint` = ISIN + MIC + field + as_of + value + source URL + document hash.

OpenAI interpretation of an NSE tool result is **not** a second primary source. Dedup keeps the primary tool row.

## UNIVERSAL SECURITY TEST

Same mesh for fixtures TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS, plus one catalog-discovered listing.

No `if ticker ==` / `if company ==` / `if ISIN ==` in mesh/router/tool policy.

Correct UNKNOWN is a PASS when evidence is missing.

## IDENTITY ATTACK

Mismatched ticker vs listing ISIN → `REJECT` / `SECURITY_AMBIGUOUS`.

Unknown ticker/ISIN → `SECURITY_NOT_FOUND` or `SECURITY_UNKNOWN`.

No silent substitution.

## STALE ATTACK

`freshness_status=FAIL` does not verify as current. Outcome is `REFRESH_REQUIRED` or UNKNOWN — not silent current use.

## CONFLICT ATTACK

Two primary values → `CONFLICT`. No averaging. No AI vote. Judge/reconcile decides.

## HALLUCINATION ATTACK

User assumption “5 billion outstanding shares” is recorded as a rejected claim. It does not become `verified_fields`.

USER CLAIM ≠ VERIFIED DATA.

## SOURCE-INJECTION ATTACK

Fake/injected URL is a rejected claim. Screener cannot override primary revenue. Primary value remains VERIFIED.

## FAILURE HANDLING

Transport (may trip breakers): `OPENAI_UNAVAILABLE`, `OPENAI_TIMEOUT`, `OPENAI_RATE_LIMITED`, `NSE_UNAVAILABLE`, `NSE_TIMEOUT`, existing MCP transport codes.

Domain (must not trip breakers): `EVIDENCE_MISSING`, `EVIDENCE_CONFLICT`, `EVIDENCE_STALE`, `NORMALIZATION_FAILURE`, `MCP_TOOL_ERROR`, identity failures.

`is_transport_failure("EVIDENCE_CONFLICT")` is False.

## COST

Router records input/output tokens, tool calls, latency, optional estimated cost from **configurable** USD-per-token inputs. Model label is `preferred_model` / client `model_label`, not a hardcoded obsolete name.

No production spending. No live OpenAI calls.

## PERFORMANCE

Mock-path mesh (11 repetitions, bank-equity FINANCIALS fixture):

- p50 and p95 of wall latency are defined (`p95 >= p50 >= 0`)
- Largest mock-path contributor is typically **extract** (same as 14N-F labeled scan)
- Live OpenAI + NSE MCP latency was **not** measured

No premature optimization.

## SECURITY

- API keys: environment only. None present in this forensic.
- Not in frontend, traces, reports, EvidenceItems, or git
- Authorization headers / `sk-` tokens redacted
- User assumptions cannot override source policy, judge rules, or authority

## TEST RESULTS

| Suite | Result |
|---|---|
| `test_simple15.py` | 12 passed |
| `test_simple14ne.py` | 16 passed |
| `test_simple14nf.py` | 17 passed |
| `test_nse_mcp_openai.py` | 22 passed |
| `test_openai_responses.py` | 5 passed |
| `test_official_research_engine.py` | 29 passed |
| **Total** | **101 passed** |

Live OpenAI: not executed. Live NSE MCP: not re-run (prior forensic stands).

## FILES CHANGED

New:

- `packages/data_engine/src/data_engine/official_research/agent_port.py`
- `packages/data_engine/src/data_engine/official_research/research_trace.py`
- `packages/data_engine/src/data_engine/official_research/tool_policy.py`
- `packages/data_engine/src/data_engine/official_research/evidence_identity.py`
- `packages/data_engine/src/data_engine/official_research/research_mesh.py`
- `packages/data_engine/tests/test_simple15.py`
- `docs/releases/SIMPLE_15_MULTI_AGENT_RESEARCH_FORENSIC.md`

Extended:

- `provider_router.py` — cost/capability selection
- `research_failures.py` — OpenAI/NSE/evidence codes
- `models.py` — optional result/claim fields
- `openai_nse_agent.py` — `research()` + plan allow-list
- `agents.py` — `UnavailableResearchPort`
- `official_research/__init__.py`

## PRODUCTION IMPACT

**NONE. NO PRODUCTION DEPLOYMENT.**

Not changed:

- `/api/v1/analyse`
- production environment / Cloud Run
- production OpenAI activation
- production NSE MCP activation
- valuation behavior
- frontend navigation
- Copilot Chat Completions

## COMMERCIAL STATUS

NSE MCP: **COMMERCIAL_USE_PENDING**

OpenAI research path: forensic/mock only. Not production-enabled.

## LIMITATIONS

1. Live OpenAI Responses + remote MCP was not run (no API key).
2. Only one qualified researcher (OpenAI). Gemini/Claude are stubs. This is intentional, not theater.
3. Mesh retrieve still uses injected documents/tool records unless a live agent is configured.
4. No model catalog / cost-scoring / quality_gate modules existed; they were not invented.
5. Production spending remains disabled.

## DECISION

**PASS WITH LIMITATIONS.**

Do not declare CLOSED until a bounded live OpenAI run exists **or** an explicit decision is made that mock-qualified architecture is enough to proceed.

Do not block the platform on one missing API key.

Do not deploy.

## NEXT FORENSIC

**SIMPLE-16 — bounded live OpenAI Responses research (if a key is provided) or a second independent qualified agent.**

Suggested scope:

1. Opt-in live Responses → NSE MCP for one ordinary equity and one bank, with redaction.
2. Keep EvidenceJudge and COMMERCIAL_USE_PENDING unchanged.
3. Still no `/api/v1/analyse` change.

Operating sequence: FORENSIC → FIND → PROVE → FIX → TEST → VERIFY → CLOSE → NEXT.

ONE RESEARCH ARCHITECTURE. ONE EVIDENCE MODEL. ONE JUDGE. MULTIPLE OPTIONAL AGENTS. PRIMARY SOURCES REMAIN AUTHORITY. AI RESEARCHES. DSP JUDGES.

---

Architecture Impact: additive orchestration only; no API/UI/engine redesign.
Components Added: agent port, mesh, trace, tool policy, evidence fingerprint, SIMPLE-15 tests, this report.
Pages Updated: none.
Feature Flags Used: none.
Accessibility / Performance / Responsive Validation: N/A (no UI).
Known Limitations: listed above.
Future Enhancements: bounded live OpenAI qualification.
Regression Summary: 14N-E/F green; focused family 101 passed.
