# SIMPLE-19A — E2E Pipeline Convergence & Frontend Integration Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

The platform now has **one canonical research callable**:

`ResearchOrchestrator.analyse` → `analyse_user_query` / `analyse_listing`

USER QUERY → Security Master (ISIN + MIC) → ResearchPlan → DISCOVER → RETRIEVE → EXTRACT → NORMALIZE → RECONCILE → EvidenceJudge → CURRENTNESS → VerifiedDataset → labeled assumptions → deterministic DSP / DcfMethod

`ResearchOrchestrator.research` is a **thin compatibility façade** that maps that result onto the existing `ResearchResult` contract (NSE EOD snapshot + document extraction helpers). It is not an independent pipeline.

`POST /api/v1/analyse` was **not redesigned**. The existing request DTO is unchanged (`extra=forbid`). The response payload is **additive**: `official_research` carries analysis state, gates, coverage, and the result contract. The company-analysis UI maps that block without a visual redesign.

**FULL ANALYSIS was not claimed** for any security in this forensic. No-manual MOCK research resolves identity and leaves missing primitives **UNKNOWN**. DCF stays **BLOCKED** until verified facts exist. No numbers were fabricated.

**NO PRODUCTION DEPLOYMENT.** OpenAI research and NSE MCP were not activated. NSE MCP remains `COMMERCIAL_USE_PENDING`.

---

## BASELINE

Recorded at the start of SIMPLE-19A, on the same uncommitted stack as SIMPLE-19.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| Working tree | SIMPLE-15…19 uncommitted official-research work, plus parking leftovers (`.bytecode_backup/`, nested `DSP-AI-Indicator/`, `demoAuth*`, `artifacts/`, `body.txt`). **Not committed. Not pushed.** |
| Production revision | **Not queried.** This forensic is forbidden from production deploy or Cloud Run inspection-as-change. Local HEAD remains `d55c8ef`. |
| Production image | **Unchanged / not inspected.** No image rebuild, no Cloud Run traffic shift. |
| SIMPLE-19 report | `docs/releases/SIMPLE_19_ANY_SUPPORTED_STOCK_E2E_FORENSIC.md` — PASS WITH LIMITATIONS |
| Current `/api/v1/analyse` | Frozen `AnalyseRequest` (`ticker`, optional `exchange` / `isin` / `mic` / `company` / statements / signals / price). `AnalyseResponse.payload` is an open dict. |
| `ResearchOrchestrator` | Compatibility wrapper after this forensic; canonical entry is `analyse()`. |
| E2E facade | `packages/data_engine/src/data_engine/official_research/end_to_end.py` |
| Frontend analysis client | `apps/web` `CompanyAnalysisWorkspace` → `api.analyse` → `mapResearchView` |
| Security Master | Catalog-driven; 2620 listings; identity = ISIN + MIC; never guesses |
| VerifiedDataset | Single judge-built dataset; shares require `semantic_type == TOTAL_OUTSTANDING` |
| DSP calculation path | `run_dsp_calculations` applies **DcfMethod** (`valuation.methods.dcf`). DCF Intelligence is not invoked. |

### Relevant feature flags (unchanged)

| Flag | Default | SIMPLE-19A |
|---|---|---|
| `RESEARCH_MODE` / `NEXT_PUBLIC_RESEARCH_MODE` | true | Unchanged |
| `RECOMMENDATION_MODE` / `SEBI_MODE` | false | Unchanged. BUY/SELL/HOLD stay locked |
| Production OpenAI research | disabled | **Not activated** |
| NSE MCP | `COMMERCIAL_USE_PENDING` | **Not activated** |
| `DSP_LIVE_NSE_EOD` | unset in this forensic | Live NSE not enabled |

### Pre-edit regression (SIMPLE-19 close)

SIMPLE-14N-E through SIMPLE-19 + EvidenceJudge + NSE MCP + OpenAI Responses: **150 passed**, 0 failed / skipped / xfail (see SIMPLE-19 report). Live provider tests were not enabled.

---

## TWO ORCHESTRATORS

SIMPLE-19 found two callables that looked like research engines:

1. `ResearchOrchestrator` — historically identity + NSE EOD + `_non_price_field` document extract + EvidenceJudge, used by `preload_verified_evidence` and `/api/v1/analyse`.
2. E2E facade — `analyse_user_query` / `analyse_listing` — plan → acquire_planned_fields → judge → DSP.

### Why both existed

The E2E facade was added in SIMPLE-19 as the **universal any-supported-security path**. `/analyse` still called `ResearchOrchestrator.research`, so production UI never reached the facade. That was a compatibility split, not two intended architectures.

### Callers

| Callable | Callers |
|---|---|
| `analyse_user_query` / `analyse_listing` | `ResearchOrchestrator.analyse`, SIMPLE-19/19A tests |
| `ResearchOrchestrator.analyse` | `preload_verified_evidence` (`/api/v1/analyse` composition) |
| `ResearchOrchestrator.research` | Official-research engine tests, live-qualify artifacts, SIMPLE-14N acquisition tests |
| `run_research_mesh` | SIMPLE-15 agent mesh (discover/attack/verify roles). **Not a second user pipeline.** |

### Responsibilities after this forensic

| Piece | Role |
|---|---|
| `analyse_listing` / `analyse_user_query` | **Canonical** research + DSP |
| `ResearchOrchestrator.analyse` | Resolves identity, supplies NSE EOD as **candidates**, calls the E2E path |
| `ResearchOrchestrator.research` | Maps E2E → `ResearchResult` (price snapshot, unresolved identity strings, document-field evidence) |
| `_price_evidence` | Unique NSE UDiFF EOD candidate supplier. Not a second judge. |
| `_non_price_field` | Unique **ResearchResult** document extractor for compatibility tests. Canonical acquire still goes through `field_acquisition`. |
| `run_research_mesh` | Agent mesh from SIMPLE-15. Unchanged. Not the user analyse path. |

### Canonical choice

**One canonical research orchestration path:** `analyse_user_query` / `analyse_listing`.

`ResearchOrchestrator` is retained as the object that owns NSE EOD transport, cache, agents, and the `ResearchResult` DTO. It is no longer an independent pipeline.

Neither orchestrator was blindly deleted. Unique NSE EOD fetch remains. Unique `ResearchResult` mapping remains.

---

## CANONICAL PIPELINE

```
USER QUERY
  → SEARCH / RESOLVE (Security Master, ISIN + MIC, never guess)
  → RESEARCH PLAN
  → DISCOVER → RETRIEVE → EXTRACT → NORMALIZE → RECONCILE
  → EvidenceJudge → CURRENTNESS
  → VerifiedDataset
  → accepted assumptions
  → DSP (DcfMethod) → RESULT
```

Provider-neutral security identity: listing object (`isin`, `mic`, `ticker`, `exchange`, `security_type`). No ticker-specific or company-specific production branches in `end_to_end.py` or `orchestrator.py`.

TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS remain **test fixtures only**.

---

## API CONTRACT

**Decision: reuse existing `POST /api/v1/analyse`.**

| Check | Result |
|---|---|
| Request DTO changed? | **No.** `AnalyseRequest` still `extra=forbid`. No new required fields. |
| Existing clients break? | **No.** Additive payload key only. |
| Versioned research field? | **Yes, additive:** `payload.official_research` copied from `authenticated_valuation_trace`. |
| Separate research endpoint? | **Not added.** Unnecessary. |

`preload_verified_evidence` now calls `orch.analyse()` (canonical E2E) and attaches `e2e.to_public_dict()` onto the valuation trace. `pipeline_result_public_dict` copies `official_research` when present.

Identity failures still surface as existing `Data unavailable` / identity status on the trace. Structured `analysis_state` is additive so old clients ignore it.

---

## FRONTEND INTEGRATION

Traced path:

Search (Security Master listing) → selection (ISIN + exchange/MIC required) → Analyze → `loadAuthenticatedAnalyseRequest` → `POST /api/v1/analyse` → `mapResearchView` → Executive Summary.

Where it previously stopped: `/analyse` ran `ResearchOrchestrator.research` / composition engines. It did **not** expose E2E analysis state. The UI could not show PARTIAL vs FULL vs IDENTITY_AMBIGUOUS as first-class research states.

What changed (connection, not redesign):

| Surface | Behavior |
|---|---|
| `mapResearchView.ts` | Maps `payload.official_research` → `officialResearch.analysisState` / `fullAnalysis` / `identityStatus` / `detail` |
| `WorkspaceSections.tsx` Executive Summary | “Analysis completeness” + “Research status” |
| `CompanyAnalysisWorkspace.tsx` | Structured identity errors (`IDENTITY_AMBIGUOUS`, `UNSUPPORTED_SECURITY`); existing loading / empty / auth / retry preserved |
| Analyze button | Already `disabled={analyzing}` in left nav and chrome |

Loading, disabled, error, empty, authentication, retry, and responsive layout were not redesigned.

`RESEARCH_IN_PROGRESS` is the **UI pending state** (`analyseMutation.isPending` + skeleton), not a completed result. The pipeline is synchronous.

---

## SECURITY RESOLUTION

Never guesses. Observed:

| Input | Status |
|---|---|
| TCS + ISIN + MIC | `RESOLVED` / identity `VERIFIED` |
| TCS without MIC | `AMBIGUOUS` |
| ISIN + MIC (wrong ticker) | Resolves by ISIN+MIC; ticker becomes the listing ticker (INFY fixture) |
| Company name “Infosys Limited” | `AMBIGUOUS` |
| Dual listing / ticker alone | `AMBIGUOUS` until MIC selected |
| Unknown ticker `ZZZNOTAREALCO` | `UNKNOWN` |
| Unsupported ETF listing | `UNSUPPORTED` / `UNSUPPORTED_SECURITY` |
| Vendor id `NSE_EQ\|INFY` | `REJECTED` |
| Prompt-injection query | `REJECTED` |

E2E unresolved text for ambiguous identity includes **“ambiguous”** so compatibility clients keep the old contract.

---

## TOTAL_OUTSTANDING

A field named `shares_outstanding` is not enough.

| Gate | Enforcement |
|---|---|
| `canonical_share_semantic_type` | Maps labels / already-canonical tokens. Valuation semantic is `TOTAL_OUTSTANDING`. |
| `EvidenceJudge.verify` | Known-wrong class (weighted average, free float, …) → `REJECTED`. Unknown class → `UNKNOWN` (after AI/source unavailability). |
| `field_acquisition` | Non-`TOTAL_OUTSTANDING` cannot be promoted for valuation. |
| `VerifiedDataset` / `dataset_to_bundle` | Shares rejected unless `semantic_type == TOTAL_OUTSTANDING`. |
| FULL ANALYSIS gate `outstanding_shares_verified` | Requires verified shares **and** `semantic_type == TOTAL_OUTSTANDING`. |

Weighted-average locators cannot feed market cap, EV, DCF per share, or margin of safety.

---

## SHARE EVIDENCE

A candidate share count must retain:

| Property | Where recorded |
|---|---|
| value | `EvidenceItem.value` |
| as_of | `EvidenceItem.as_of` |
| current_through | `EvidenceItem.current_through` (filled from `as_of` when that is the known validity) |
| source | `EvidenceItem.source` |
| source authority | `authority_tier` during reconcile; source_type / URL for verify |
| document date | `EvidenceItem.document_date` |
| corporate-action status | `corporate_action_status` |
| identity | listing ISIN+MIC + `identity_status` |
| semantic classification | `semantic_kind` / `canonical_share_semantic_type` → `TOTAL_OUTSTANDING` |

If `document_date`, `current_through`, or `source` is missing, verify will not mark VERIFIED. AI `source_type=llm` remains `UNAVAILABLE` and is classified **before** generic UNKNOWN so typed failures stay distinguishable.

---

## CURRENTNESS

`retrieved_at` being recent does not make a fact current.

- Price: EOD as_of is the trade date; previous close while the market is open is not LIVE.
- Shares: `judge_currentness` / `corporate_action_horizon_status` apply when a research horizon is supplied.
- Dataset currentness is exposed on `result_contract.currentness` and coverage `corporate_actions`.

---

## CORPORATE ACTIONS

Calendar passage is not a capital change. An explicit **corporate-action review horizon** must cover the research date.

Test (SIMPLE-19A):

| Input | Expected |
|---|---|
| share as_of 31 Mar 2026 | recorded |
| CA review through 30 Jun 2026 | `ca_checked_through` |
| research / current date 11 Sep 2026 | `research_horizon` |
| `corporate_action_horizon_status` | **REFRESH_REQUIRED** |
| `gates["corporate_action_horizon"]` | **False** |
| FULL ANALYSIS | **False** |

`full_analysis_status` uses the explicit `research_horizon` / `ca_checked_through` kwargs when provided. It does not treat “recent retrieval” as CA coverage.

---

## AUTOMATIC RESEARCH

`_acquire_one_field` tries injected candidates, then `retrieve_fn` URLs in source-priority order. A failed source does **not** stop the loop.

Typed failures remain distinct via `map_retrieval_to_failure_code`:

| Symptom | Code |
|---|---|
| 403 / 401 | `AUTH` |
| 404 | `DOCUMENT_NOT_FOUND` |
| timeout / DNS / TLS | `NETWORK` |
| other HTTP ≥400 | `HTTP` |
| empty / malformed PDF text | `EXTRACTION_FAILURE` |
| identity mismatch | `IDENTITY_FAILURE` / `REJECTED` |
| stale | `REFRESH_REQUIRED` / `FRESHNESS_FAILURE` |

They do not collapse into one “provider failure”. If every approved source fails: **UNKNOWN**, not a fabricated number.

Live NSE → company IR → approved secondary → AI (where enabled) is the existing source-priority chain. AI still cannot promote facts.

---

## AI BOUNDARY

Unchanged and re-tested.

AI may: discover, search, extract candidates, explain, attack, propose assumptions.

AI may not: promote facts, override EvidenceJudge, override primary evidence, change source authority, change DSP formulas, emit authoritative DCF.

`source_type=llm` / `openai_nse_mcp` → `UNAVAILABLE`. Hallucinated values cannot enter VerifiedDataset.

Prompt injection in the user query is `REJECTED` (`looks_like_injection`).

---

## QUALITY / MOAT / RISK

Repository search found existing engines. **No new scoring architecture was invented.**

| Component | Location | SIMPLE-19A action |
|---|---|---|
| Business quality | `business_quality.BusinessQualityEngine` | Already runs on composition pipeline after an authenticated bundle |
| Aggregator | `business_quality_aggregator.BusinessQualityAggregatorEngine` | Same |
| Economic moat | `economic_moat.EconomicEngine` | Composition stage `ECONOMIC_MOAT` |
| Risk view | `dsp_platform.composition.risk_view` | Composition `RISK` stage |
| E2E `run_dsp_calculations` quality/moat/risk | Optional `quality_components` / `moat_components` / `risk_observations` | Remain **BLOCKED / UNKNOWN** unless those maps are supplied |

**Missing dependency (not invented here):** a verified mapping from composition `FinancialAnalysis` → E2E `quality_components` so the official-research DSP block can display the same scores. Until that adapter exists, E2E DSP quality/moat/risk stay UNKNOWN. The `/analyse` composition path still runs the engines when a bundle exists. Frontend `businessQuality` continues to come from composition, not from a new E2E scorer.

---

## DCF

| Implementation | Purpose | SIMPLE-19A |
|---|---|---|
| `valuation.methods.dcf.DcfMethod` | Canonical DSP DCF (OCF − CapEx FCF, Decimal) | **The formula applied by `run_dsp_calculations`** |
| `official_research.dsp_calculation._run_dcf` | Applies DcfMethod to VerifiedDataset + accepted assumptions | Canonical E2E DSP path |
| `valuation.dcf_intelligence` | FCFF / CAPM WACC / NWC engine | **Documented, not invoked.** VerifiedDataset does not carry those drivers. |
| `valuation.reverse_dcf` | Independent reverse DCF | Not invoked from E2E |

No second DCF silently executes on the E2E path. Bank equity remains capability `bank_equity`; ordinary-equity DCF is not forced (HDFCBANK fixture asserts DCF BLOCKED without bank-specific invention).

---

## RESULT CONTRACT

`EndToEndResult.to_public_dict()["result_contract"]` distinguishes:

| Bucket | Content |
|---|---|
| VERIFIED FACTS | `verified_facts` (acquired field names) |
| DERIVED VALUES | calculated FCF / net debt / market cap / EV / DCF / IV/share / MoS |
| ASSUMPTIONS | assumption ids on calculated DSP rows |
| BLOCKED VALUES | DCF / quality / moat / risk when BLOCKED |
| UNKNOWN VALUES | `unknown_fields` |
| EVIDENCE | evidence row count |
| CONFIDENCE | coverage `dsp_conclusion` |
| CURRENTNESS | coverage `corporate_actions` |
| DSP CONCLUSION | same + `analysis_state` + `full_analysis` |

Narrative (`detail`) is separate from numeric authority. Derived values are labeled `derived_is_source_evidence: false`.

---

## ERROR CONTRACT

Structured `analysis_state` values:

`IDENTITY_AMBIGUOUS` · `UNKNOWN_SECURITY` · `UNSUPPORTED_SECURITY` · `REJECTED` · `RESEARCH_UNAVAILABLE` · `PARTIAL_DATA` · `REFRESH_REQUIRED` · `CONFLICT` · `VALUATION_BLOCKED` · `DCF_BLOCKED` · `ANALYSIS_READY` · `FULL_ANALYSIS`

Frontend:

- Pending analyse → loading skeleton (not a fake result).
- `IDENTITY_AMBIGUOUS` / `UNSUPPORTED_SECURITY` thrown before/at request when listing identity is incomplete.
- Completeness row shows PARTIAL ANALYSIS / DCF BLOCKED / … rather than a generic “Something went wrong.”
- HTTP 401 / 403 / 404 / timeout / 5xx keep existing typed messages. CV-001: no fabricated numbers.

`RESEARCH_IN_PROGRESS` is the in-flight UI state, not a completed payload.

---

## PARTIAL ANALYSIS

Identity verified + some fields unknown + DCF blocked is **PARTIAL ANALYSIS** (`PARTIAL_DATA` / `DCF_BLOCKED` / `VALUATION_BLOCKED`), not FAILED and not FULL ANALYSIS.

No-manual “Analyse TCS” (MOCK, no injected financials):

- identity `VERIFIED`
- `full_analysis` **False**
- `analysis_state` `DCF_BLOCKED`
- revenue not verified
- gates: identity true; financials / price / shares / CA / assumptions / DCF false

That is truthful partial research.

---

## FULL ANALYSIS

SIMPLE-19 definition, now enforced as `full_analysis_status` gates:

1. Identity verified
2. Required financial primitives verified (equity vs bank_equity sets)
3. Price verified/current under its semantics
4. `TOTAL_OUTSTANDING` shares verified/current
5. Corporate-action horizon CURRENT for the research date
6. Required assumptions accepted
7. DSP / DcfMethod hard gates pass

Only then `full_analysis=true` and `analysis_state=FULL_ANALYSIS`.

No fixture in this forensic reached that state. Correct.

---

## NO-MANUAL TEST

Canonical path with **no** manually injected price, revenue, CFO, capex, cash, debt, or shares:

`analyse_user_query("TCS", isin=…, mic=…, mode="MOCK")`

- Resolves TCS via Security Master
- Builds a ResearchPlan
- Attempts automatic acquisition
- Missing primitives remain **UNKNOWN**
- DCF **BLOCKED**
- `full_analysis` **False**

Live documents were not fetched (MOCK, NSE MCP pending, OpenAI off). The system did not invent statements. Same pattern for INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS.

Dialect documents in tests prove extraction **when** a labeled official document is present. They are not production overrides.

---

## DYNAMIC SECURITY TEST

Catalog walk, **not hardcoded**:

| Field | Value |
|---|---|
| Ticker | **21STCENMGM** |
| Company | 21st Century Management Services Limited |
| ISIN | `INE253B01015` |
| MIC | `XNSE` |

Selected as the first eligible XNSE ordinary equity whose ticker is not in the fixture set and whose name does not contain “bank”. Identity verified. Plan built. No ticker branch.

---

## SECURITY TYPES

| Type | Handling |
|---|---|
| Ordinary equity | Capability `equity`; DCF allowed if gates pass |
| Bank equity (HDFCBANK fixture) | Capability `bank_equity`; ordinary-equity DCF not forced; DCF BLOCKED without bank inputs |
| Unsupported ETF | `UNSUPPORTED` / `UNSUPPORTED_SECURITY`; outside ordinary-equity valuation |

---

## FRONTEND E2E

Playwright exists (`apps/web/playwright.config.ts`, `test:browser` / `test:p109`).

**Not executed in this forensic.** No local web server + authenticated API session was running, and this forensic must not start production services or activate live NSE/OpenAI.

What **was** verified:

- Static wiring tests (`test_frontend_and_architecture`): `/api/v1/analyse`, `disabled={analyzing}`, `officialResearch`, completeness copy, additive `official_research` adapter, no ticker branches in E2E/orchestrator.
- Analyze mutation drops stale generations; button disabled while pending.

Limitation: no browser click-through of search → analyse → evidence. Do not claim UI E2E CLOSED.

---

## DUPLICATE REQUESTS

| Case | Control |
|---|---|
| Single click | One `analyseMutation` |
| Double / rapid click | Analyze `disabled={analyzing}` in `WorkspaceLeftNav` and `WorkspaceChrome` |
| Stale response | `analyseGeneration` ref drops older completions after navigation / newer analyse |

No runaway research jobs from repeated clicks in the existing client. Server-side job queue was not added; analyse remains a synchronous request.

---

## FAILURE RECOVERY

| Failure | Result |
|---|---|
| NSE timeout / 403 / 404 | Typed `ResearchFailure`; field UNKNOWN; no hang |
| Malformed PDF | `EXTRACTION_FAILURE` |
| Identity mismatch | REJECTED / UNKNOWN, not guessed |
| Stale evidence | `REFRESH_REQUIRED` |
| Share conflict | `CONFLICT` |
| AI unavailable / hallucination | `UNAVAILABLE`; cannot VERIFIED |
| UI | `isPending` clears; `isError` shows typed message; empty state if no view. **No permanent loading state.** |

---

## SECURITY

| Control | Status |
|---|---|
| Authentication | Analyse still requires token; 401/403 messages unchanged |
| Authorization | Existing analyse permission errors preserved |
| Source allowlist | `SourcePolicy.may_verify` / URL classify — unchanged |
| URL restrictions | Forbidden/secondary cannot verify |
| Prompt injection | User query rejected; document sanitize unchanged |
| AI output validation | Judge + assumption validator; AI cannot write policy |
| Secret redaction | `redact_mcp_text` on unresolved / public dict |
| Untrusted documents | Identity match + policy; MOCK blocked when `production=True` |
| NSE MCP | `COMMERCIAL_USE_PENDING` |
| Production MOCK | `UNAVAILABLE` — “MOCK evidence cannot enter production” |

AI cannot modify system policy.

---

## PERFORMANCE

Measured **canonical MOCK pipeline** (no live HTTP, local catalog), query `Analyse TCS` with ISIN+MIC, 6 samples:

| | seconds |
|---|---|
| Cold start (first call) | 0.0455 |
| Warm p50 | 0.0427 |
| Warm p95 | 0.0494 |

This is SEARCH/RESOLVE → PLAN → ACQUIRE (no documents) → DSP gate. It is **not** the full browser SEARCH → ANALYSE → RESULT including Next.js and API auth.

Full user-path p50/p95 was **not** measured (no local web/API session). No optimization was attempted. No bottleneck claimed.

---

## ARCHITECTURE FORENSIC

| Finding | Class |
|---|---|
| `ResearchOrchestrator.research` vs E2E | **PRODUCTION LOGIC** — converged: research is a thin façade |
| `run_research_mesh` | **PRODUCTION LOGIC** — SIMPLE-15 agent mesh; not the user analyse path; retained |
| One `ResearchRequest` / `EvidenceItem` / `EvidenceJudge` | Unchanged |
| P109 `DSPFIX` ticker in `preload_verified_evidence` | **TEST FIXTURE** — `if not production` |
| Named ISINs in tests | **TEST FIXTURE** |
| Dialect document strings in tests | **TEST FIXTURE** — not production overrides |
| `dcf_intelligence` | **PRODUCTION LOGIC** (separate engine) — not invoked from E2E; not deleted |
| Hardcoded TCS/INFY financials in E2E/orchestrator | **None found** |
| Manual production overrides | **None found** |
| Fixture leakage into production formulas | **None found** |

No dead production ticker table was deleted. None was proven dead beyond fixtures already gated.

---

## TEST RESULTS

Focused regression after SIMPLE-19A (same suites as SIMPLE-19 plus 19A and `/analyse` smoke):

| Suite | Result |
|---|---|
| SIMPLE-14N-E (`test_simple14ne.py`) | **16 passed** |
| SIMPLE-14N-F (`test_simple14nf.py`) | **17 passed** |
| SIMPLE-15 | **12 passed** |
| SIMPLE-16 | **19 passed** |
| SIMPLE-17 | **10 passed** |
| SIMPLE-18 | **10 passed** |
| SIMPLE-19 | **10 passed** |
| SIMPLE-19A | **9 passed** |
| EvidenceJudge (`test_official_research_engine.py`) | **29 passed** |
| NSE MCP OpenAI | **22 passed** |
| OpenAI Responses | **5 passed** |
| `/api/v1/analyse` smoke (`test_simple14n_analyse.py`) | **2 passed** |
| **Total** | **161 passed** |
| Failed | **0** |
| Skipped | **0** |
| xfail | **0** |

New failures: **none**. Pre-existing failures: **none hidden**. Live provider tests were not enabled.

During implementation, two SIMPLE-16 failures appeared when share UNKNOWN was classified before AI `UNAVAILABLE` / weighted-average `REJECTED`. That order was restored. Typed failures remain distinguishable.

---

## FILES CHANGED

| File | Role |
|---|---|
| `packages/data_engine/src/data_engine/official_research/end_to_end.py` | Canonical pipeline; analysis states; CA horizon gates; result contract; ambiguous identity wording |
| `packages/data_engine/src/data_engine/official_research/orchestrator.py` | Thin `analyse()` wrapper; `research()` compatibility mapping (NSE EOD snapshot, evidence rows) |
| `packages/data_engine/src/data_engine/official_research/field_acquisition.py` | UNKNOWN stubs per field; share completeness; `last_verified_at` when a value exists; CA horizon kwargs |
| `packages/data_engine/src/data_engine/official_research/judge.py` | TOTAL_OUTSTANDING + mandatory share properties; AI unavailability before generic UNKNOWN |
| `packages/data_engine/src/data_engine/official_research/extraction.py` | Canonical share tokens recognized without re-classifying underscores as UNKNOWN |
| `packages/dsp_platform/src/dsp_platform/composition/verified_evidence.py` | `/analyse` preload calls `orch.analyse()`; attaches `official_research` |
| `packages/dsp_platform/src/dsp_platform/composition/adapters.py` | Additive `payload.official_research` |
| `apps/web/src/lib/research/mapResearchView.ts` | Maps official research completeness |
| `apps/web/src/components/company-analysis/WorkspaceSections.tsx` | Completeness + research status rows |
| `apps/web/src/components/company-analysis/CompanyAnalysisWorkspace.tsx` | Structured identity errors |
| `packages/data_engine/tests/test_simple19a.py` | Convergence, identity, TOTAL_OUTSTANDING, CA horizon, no-manual, dynamic, ETF/AI, frontend wiring |
| `docs/releases/SIMPLE_19A_E2E_CONVERGENCE_FORENSIC.md` | This report |

SIMPLE-15…19 files remain uncommitted from prior forensics. They were not redesigned into a new architecture.

**Not changed:** `AnalyseRequest` fields, production env, Cloud Run, NSE MCP commercial status, DcfMethod formula, OpenAI enablement.

---

## PRODUCTION IMPACT

**None deployed.**

- No Cloud Run revision
- No image push
- No traffic shift
- No production env change
- MOCK cannot enter production (`production=True` → `UNAVAILABLE`)

---

## COMMERCIAL STATUS

| Item | Status |
|---|---|
| NSE MCP | `COMMERCIAL_USE_PENDING` |
| OpenAI research in production | **Off** |
| Live NSE EOD (`DSP_LIVE_NSE_EOD`) | **Not enabled for this forensic** |

Do not activate either in production without a later authorized forensic.

---

## LIMITATIONS

1. **FULL ANALYSIS** is not reachable in MOCK without labeled official documents, verified TOTAL_OUTSTANDING shares, CA horizon covering the research date, accepted assumptions, and DcfMethod gates.
2. **Live no-manual retrieval** of NSE / company IR PDFs was not run (commercial + production constraints).
3. **Quality / moat / risk** engines exist on the composition pipeline but are not mapped into E2E `quality_components`. E2E DSP scores stay UNKNOWN/BLOCKED.
4. **Playwright** search → analyse → evidence was not executed (no local authenticated web+API).
5. **Browser user-path p50/p95** not measured.
6. Compatibility `research()` still uses `_non_price_field` for `ResearchResult` document rows. Canonical `/analyse` uses `analyse()` → acquire.
7. `run_research_mesh` remains as the SIMPLE-15 agent mesh; it is not the user analyse path.
8. P109 `DSPFIX` CI fixture remains gated off production.

These prevent CLOSED. They do not reopen a second research architecture.

---

## DECISION

**PASS WITH LIMITATIONS**

Closure criteria that **hold**:

- One canonical research pipeline
- Duplicate orchestrator reduced to a thin compatibility wrapper
- Frontend can reach the canonical path through existing `/api/v1/analyse`
- Existing API request contract unchanged
- Universal security resolution intact
- TOTAL_OUTSTANDING enforced
- Currentness and CA horizon enforced
- No manual company production fixes
- Dynamic security test passes (21STCENMGM)
- No-manual research does not fabricate
- Partial analysis represented truthfully
- Full-analysis status is truthful (false)
- AI remains behind EvidenceJudge
- Deterministic DSP / DcfMethod unchanged
- Duplicate clicks controlled in UI
- Security tests in the focused suite pass
- Previous regressions remain green (161 passed)

Closure criteria that **do not hold**:

- Live automatic document research to FULL ANALYSIS
- Playwright frontend E2E
- E2E quality/moat/risk connected to composition engines

Do not claim CLOSED.

---

## NEXT FORENSIC

**SIMPLE-20** should be authorized separately. Suggested scope only — do not start it in this change set:

1. Optional verified adapter: composition BusinessQuality / EconomicEngine / risk_view → E2E `quality_components` / `moat_components` (reuse engines, no new scorer).
2. Local Playwright: authenticate → search → select ISIN+MIC → Analyse → assert PARTIAL ANALYSIS and no fabricated numbers.
3. Live acquisition forensic **only if** commercial NSE MCP / OpenAI policy is explicitly authorized. Until then keep `COMMERCIAL_USE_PENDING`.
4. Measure real SEARCH → ANALYSE → RESULT p50/p95 with the running API+web, then optimize only a measured bottleneck.

FORENSIC → FIND → PROVE → FIX → TEST → VERIFY → CLOSE → NEXT.
