# SIMPLE-21 — Live Qualitative Research & Browser Qualification Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

This forensic qualified the **existing** SIMPLE-20 qualitative and Advanced Investment Check pipeline against **real external evidence** in a **non-production** environment.

The proven chain is:

REAL SECURITY (Security Master, ISIN + MIC)
→ REAL IDENTITY
→ REAL RESEARCH PLAN (automatic groups)
→ REAL PRIMARY EVIDENCE (NSE UDiFF EOD `ClsPric`)
→ REAL NORMALIZATION / RECONCILIATION / EvidenceJudge
→ QUALITY / MOAT / MANAGEMENT / RISK (honest UNKNOWN without statement primitives)
→ ADVANCED INVESTMENT CHECK (`PARTIAL`, does not replace core DSP, does not alter DCF)
→ FINAL DSP QUALITATIVE RESULT (`DCF_BLOCKED`, never false FULL ANALYSIS)

No second `ResearchRequest`, `ResearchPlan`, `EvidenceItem`, `EvidenceJudge`, source policy, orchestrator, or DSP scoring system was created.

**FULL ANALYSIS was not claimed for any live security.** That is a successful forensic result. The system preferred truthful PARTIAL / DCF_BLOCKED over false complete.

**NO PRODUCTION DEPLOYMENT.** Production environment variables were not changed. OpenAI research was not enabled in production. NSE MCP was not enabled in production. Production `/api/v1/analyse` request shape was not changed. NSE MCP remains `COMMERCIAL_USE_PENDING`.

---

## BASELINE

Recorded at the start of SIMPLE-21, on the uncommitted SIMPLE-15…20 stack. HEAD is still SIMPLE-14N-F.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| Working tree | SIMPLE-15…20 uncommitted official-research work, plus this SIMPLE-21 qualification. Parking leftovers (`.bytecode_backup/`, nested `DSP-AI-Indicator/`, `demoAuth*`, `artifacts/`) remain uncommitted. **Not committed. Not pushed. Not deployed.** |
| Production revision | **Not queried.** This forensic is forbidden from production deploy or Cloud Run inspection-as-change. Local HEAD remains `d55c8ef`. |
| Production image | **Unchanged / not inspected.** No image rebuild, no Cloud Run traffic shift. |
| Canonical ResearchOrchestrator | `packages/data_engine/src/data_engine/official_research/orchestrator.py` — `analyse()` |
| `/api/v1/analyse` | Frozen request DTO (`extra=forbid`). Additive `payload.official_research` only |
| E2E façade | `packages/data_engine/src/data_engine/official_research/end_to_end.py` — `analyse_user_query` / `analyse_listing` |
| Security Master | `packages/data_engine/src/data_engine/security_master/` — identity = ISIN + MIC |
| ResearchPlan | `official_research/research_plan.py` |
| Acquisition loop | `field_acquisition.acquire_planned_fields` (DISCOVER → RETRIEVE → EXTRACT → NORMALIZE → RECONCILE → VERIFY) |
| EvidenceJudge | `official_research/judge.py` — unchanged contract |
| VerifiedDataset | `official_research/verified_dataset.py` |
| Currentness / share judge | `currentness.py`, `share_records.py`, `extraction.py` (`TOTAL_OUTSTANDING` only) |
| DcfMethod | Existing `valuation.methods.dcf` via SIMPLE-18 |
| BusinessQualityEngine | Existing `business_quality` package via `qualitative.run_qualitative_engines` |
| EconomicEngine | Existing `economic_moat` package |
| ManagementEngine | Existing `management_quality` package |
| Company risk view | Existing `dsp_platform.composition.risk_view.build_company_risk_view` |
| Advanced Investment Check | Existing `official_research/advanced_check.py` (`ADVANCED_FAILURE_ASYMMETRY`) |
| Pre-edit regression | SIMPLE-14N-E…20 **112 passed**, 0 failed / skipped / xfail (focused SIMPLE-21 start). Broader 14N-E…20 + engine/MCP/OpenAI suite was green in SIMPLE-20 (**170 passed**). |

`ResearchOrchestrator.research` remains a thin compatibility wrapper over `analyse()`. It is not a second pipeline.

---

## PROVIDER STATUS

Inspected via `load_llm_config()` and existing NSE constants. **No credentials printed. No credentials invented. No credentials committed.**

| Provider | Config | Available | Commercial / production |
|---|---|---|---|
| OpenAI | `NOT_CONFIGURED` | `UNAVAILABLE` | `NOT_PRODUCTION_ACTIVATED` |
| Anthropic / Claude | `NOT_CONFIGURED` | `UNAVAILABLE` | `NOT_PRODUCTION_ACTIVATED` |
| Gemini | `NOT_CONFIGURED` | `UNAVAILABLE` | `NOT_PRODUCTION_ACTIVATED` |
| NSE public HTTP (UDiFF EOD / filings) | Public NSE website | **LIVE reachable** in this non-production session (`DSP_LIVE_NSE_EOD` set locally) | Public EOD / filings; not a vendor feed; **not a production activation** |
| NSE MCP | Public MCP endpoint | Technical probe: initialize + `list_tools` **passed** in the dedicated network window; **skipped** once in the combined 184-test session | **`COMMERCIAL_USE_PENDING`** even when technically up |
| Yahoo Finance | Not a DSP provider | Secondary host only | `may_verify=false` |
| Default LLM provider | `deterministic` | Local deterministic path | Not an external research authority |

`LIVE_OPENAI = NOT_CONFIGURED`. No fake OpenAI result was manufactured.

Local flags observed (presence only): `DSP_LIVE_NSE_EOD=SET`, `DSP_NSE_MCP_LIVE=SET`, `DSP_SKIP_LIVE_NSE_EOD=UNSET`. These are **local qualification** flags. Production env was not modified.

---

## LIVE SOURCE POLICY

Existing `SourcePolicy` / `AUTHORITY_TIERS`. Not replaced.

| Tier | Sources | Authority |
|---|---|---|
| Tier 1A | NSE, BSE, SEBI, MCA, RBI, NSDL, CDSL, relevant regulator | May verify |
| Tier 1B | Company official website / IR / annual reports / audited statements / official filings / corporate-action documents | May verify when `source_type=company_ir` and HTTPS |
| Tier 1C | Screener | Cross-check only. `may_verify = false` |
| Tier 2 | Yahoo Finance, IBEF | Secondary research. Cannot become VERIFIED |
| Tier 3 | AI research | Discovery / interpretation only. Not authoritative |

Tests confirmed:

- `https://www.nseindia.com/…` and `https://www.sebi.gov.in/…` → TIER_1A
- Screener → `approved_research`, `may_verify=false`
- Yahoo → TIER_2
- `source_type=llm` → TIER_3

---

## TEST SECURITIES

Fixtures were **not** optimized around successful companies.

| Role | Ticker | Selection |
|---|---|---|
| Fixture A | TCS | Specified |
| Fixture B | INFY | Specified |
| Fixture C | RELIANCE | Specified |
| Fixture D | HDFCBANK | Specified |
| Fixture E | WIPRO | Specified |
| Fixture F | 20MICRONS | Specified |
| Dynamic | **21STCENMGM** | First eligible XNSE ordinary equity in Security Master whose ticker is **not** in the fixture set and whose company name does not contain `"bank"`. **Not hardcoded as the expected winner.** |

Dynamic listing from catalog: `21STCENMGM`, 21st Century Management Services Limited, `INE253B01015`, EQ series, listed 03-MAY-1995.

---

## SECURITY RESOLUTION

Canonical key: **ISIN + MIC**.

| Ticker | Company | ISIN | MIC | Exchange | Type | Eligible | Resolve |
|---|---|---|---|---|---|---|---|
| TCS | Tata Consultancy Services Limited | INE467B01029 | XNSE | NSE | equity | True | RESOLVED |
| INFY | Infosys Limited | INE009A01021 | XNSE | NSE | equity | True | RESOLVED |
| RELIANCE | Reliance Industries Limited | INE002A01018 | XNSE | NSE | equity | True | RESOLVED |
| HDFCBANK | HDFC Bank Limited | INE040A01034 | XNSE | NSE | equity | True | RESOLVED |
| WIPRO | Wipro Limited | INE075A01022 | XNSE | NSE | equity | True | RESOLVED |
| 20MICRONS | 20 Microns Limited | INE144J01027 | XNSE | NSE | equity | True | RESOLVED |
| 21STCENMGM | 21st Century Management Services Limited | INE253B01015 | XNSE | NSE | equity | True | RESOLVED |

Additional identity tests (MOCK, no invented listings):

| Probe | Result |
|---|---|
| Exact ticker (NSE) | `RESOLVED` or `AMBIGUOUS` (dual listings are not guessed) |
| Company name | `analyse_user_query` returns `AMBIGUOUS` / `UNKNOWN` / `PARTIAL` / `FULL_ANALYSIS`; FULL only with VERIFIED identity |
| Unknown security `ZZZNOTAREALCO` | `UNKNOWN` — no listing invented |
| Wrong exchange (INFY / BSE) | Explicit `RESOLVED` / `AMBIGUOUS` / `UNKNOWN` / `UNSUPPORTED` / `REJECTED` — never silently swapped onto NSE |
| Unsupported ETF `NIFTYBEES` | `UNSUPPORTED`; Advanced Check status `UNSUPPORTED` |

Listing status in this catalog is eligible ordinary equity (`eligibility=True`, `security_type=equity`). Unsupported types are not forced through ordinary-equity DCF.

---

## LIVE RESEARCH PLAN

`build_research_plan` from `AUTO_REQUEST_GROUPS`:

`PRICE`, `FINANCIALS`, `SHARES`, `CORPORATE_ACTIONS`, `BUSINESS_QUALITY`, `MOAT`, `RISK`, `VALUATION_INPUTS`

No documents were manually specified.

Expanded required/optional fields include revenue, net income, CFO, cash, debt, equity, assets/liabilities, `shares_outstanding`, and `eod_close`. Bank-equity capability may mark revenue N/A. Qualitative groups `BUSINESS_QUALITY`, `MOAT`, `MANAGEMENT`, `RISK` remain on the plan even when statement primitives are missing.

---

## AUTOMATIC ACQUISITION

Live path:

`ResearchOrchestrator.analyse` (PRICE group now correctly requests NSE EOD)
→ `analyse_user_query` / `analyse_listing`
→ `acquire_planned_fields`
→ EvidenceJudge
→ qualitative engines
→ Advanced Investment Check
→ DSP / DcfMethod (blocked when gates fail)

Bounded live document retrieve: **max 3 unique URLs per listing** via existing `retrieve_official_document` + `DocumentStore`. Failures map to structured `ResearchFailure` codes. Missing values stay **UNKNOWN**. No company facts were typed in by hand.

**Proven gap, then fix:** `analyse()` previously injected NSE EOD only when `request.fields` contained the literal token `eod_close`. The automatic `PRICE` group therefore never received UDiFF candidates, so live `analyse_listing` / group-based `analyse()` reported `price=UNAVAILABLE` even when `_price_evidence` had a VERIFIED `ClsPric` row. Existing `expand_requested_fields` is now used (`requests_price_evidence`). `/api/v1/analyse` already passed `eod_close` literally, so this is a wiring correction for the automatic plan, not a new price engine.

Optional `retrieve_fn` is forwarded from `analyse()` into the existing façade. Production `/api/v1/analyse` does not pass a retrieve function; behavior of that caller is unchanged.

---

## DOCUMENT ACQUISITION

Attempted where technically possible through the existing IR / NSE URL resolver and bounded retrieve.

| Evidence class | What happened |
|---|---|
| NSE source | **Yes.** Official UDiFF Final EOD discovered from NSE daily-reports JSON. Host on `nseindia.com`. Market closed (`market_open=False`), session date `2026-09-11`, payload size 204525 bytes, 3646 NSE cash rows. TCS ISIN matched 1 EQ row, `trad_dt=2026-09-11`. |
| Company official / IR | Attempted via `resolve_company_sources` + bounded retrieve. **Did not yield VERIFIED financial primitives.** |
| Official filing / annual report | Attempted as planned URLs. **No verified labeled statement extraction** in this live bound. |
| Corporate-action evidence | Planned and attacked when text exists. Live CA completeness **not established** → CA remains `UNKNOWN` / not CURRENT. |

Retrieval time is **not** treated as document freshness. EOD `as_of` is the trade date (`ClsPric`); later retrieval is expected.

SHA256 / locator: UDiFF rows carry source URL + `evidence_locator` from `eod_close_snapshot`. Live IR payloads that failed extraction were not promoted to VERIFIED documents. No fabricated hashes.

---

## FINANCIAL EXTRACTION

Live result for every tested security: **financials = UNKNOWN**.

Attempted labels: revenue, net income, CFO, capex, cash, debt, equity, assets, liabilities.

None of those primitives became VERIFIED from live documents in this bounded run. Units were not guessed. Unknown units remain UNKNOWN. Currency / period / consolidated-vs-standalone were not invented.

MOCK adversarial dialect still extracts labeled values when a primary document is supplied — that path is unchanged and is not live primary evidence.

---

## SHARE QUALIFICATION

Live result for every tested security: **shares = UNAVAILABLE**.

`TOTAL_OUTSTANDING` was **not** established from live evidence. Weighted-average EPS shares, free float, promoter shares, authorized capital, and unpaid/paid-up capital without outstanding semantics were not accepted. Fake `5,000,000,000` shares (Attack B) did not become VERIFIED.

Because outstanding shares are a hard valuation gate, DCF stayed **BLOCKED**. That is correct.

---

## CORPORATE ACTIONS

Live CA status: **UNKNOWN** for all seven securities.

The existing CA attack surface (bonus, split, rights, QIP, FPO, preferential, ESOP, warrants, convertibles, buyback, cancellation, capital reduction, merger, demerger, scheme, share swap) was not shown to be complete for a research horizon. Completeness was therefore **not** labeled CURRENT. Acquisition is not treated as share issuance automatically.

`REFRESH_REQUIRED` remains the correct status when a later capital-changing event exists relative to `as_of`. Absence of a searched CA horizon is UNKNOWN, not CURRENT.

---

## BUSINESS RESEARCH

Live qualitative `business` status: **UNKNOWN** for all seven.

No generic “IT services company” filler was promoted to VERIFIED. `run_qualitative_engines` requires verified statement inputs for BusinessQualityEngine. Missing inputs → UNKNOWN, not a made-up model.

---

## MANAGEMENT RESEARCH

Live `management` status: **UNKNOWN**.

No allegations were invented. Attack C (unsupported fraud claim) remains UNVERIFIED / REJECTED as a finding, not a verified fact. AI is not configured in this session, so no live AI allegation was generated.

---

## MOAT RESEARCH

Live `moat` status: **UNKNOWN**.

Attack D (“Wide moat.” with no evidence) stays UNVERIFIED. FACT / INTERPRETATION / DSP ASSESSMENT remain separate labels on Advanced Check findings. No 0–10 moat score was invented.

---

## RISK RESEARCH

Live `risk` status: **UNKNOWN**.

Existing ordinal / qualitative risk view only. **No numeric risk score.** Missing categories stay unavailable. Permanent-loss is not a fabricated number.

---

## ADVANCED INVESTMENT CHECK

Ran on every live listing. UI name **Advanced Investment Check**. Internal `ADVANCED_FAILURE_ASYMMETRY`.

| Property | Live result |
|---|---|
| Status | `PARTIAL` |
| `replaces_core_dsp` | `false` |
| `alters_dcf` | `false` |
| Hard fail | Existing `NONE` / `REVIEW_REQUIRED` (DCF blocked is not silently converted into FULL) |

Dimensions remain generic (leverage, moat attack, management/ownership, earnings quality, permanent-loss, valuation/MoS, industry/external, investor bias). No ticker-specific rules. Missing evidence is UNKNOWN, not a negative finding.

---

## THESIS BREAKERS

Generated only from the existing Advanced Check contract. Unverified AI attacks are not promoted. Inability to establish IV / DCF is represented as UNKNOWN / blocked, not as a fake breaker with invented severity.

Live thesis is not SUPPORTED: DCF is BLOCKED and statement evidence is missing.

---

## AI QUALIFICATION

**`LIVE_OPENAI = NOT_CONFIGURED`**

OpenAI, Anthropic, and Gemini keys were unset. Default provider `deterministic`.

No bounded live research call was executed. No fake AI synthesis was written into VerifiedDataset. AI still cannot: write VerifiedDataset, override EvidenceJudge, override source authority, write authoritative DCF, change formulas, or change weights.

---

## NSE MCP QUALIFICATION

| Item | Result |
|---|---|
| Commercial status | **`COMMERCIAL_USE_PENDING`** (unchanged even when the probe works) |
| Technical constant | `TECHNICALLY_QUALIFIED` (existing; not a production authorization) |
| Dedicated network test | `initialize` + `list_tools` **passed** |
| Combined 184-test session | NSE MCP test **skipped** (unavailability in that later window is fail-closed, not a fake pass) |
| Production eligibility | **Not eligible** solely because a probe works |
| EOD vs delayed | EOD remains EOD. DELAYED_15M must remain delayed. Live UDiFF `ClsPric` was labeled **EOD**, not live LTP |

Approved tool names remain the existing allow-list (`nse_lookup_symbol`, bhavcopy/cm quote tools, `get_corporate_actions`). This forensic did not expand the catalog.

---

## EVIDENCE JUDGE

All live EOD candidates passed the existing EvidenceJudge:

- identity PASS (ISIN + MIC)
- authority TIER_1A / `may_verify=true` on `nseindia.com`
- semantics EOD / `ClsPric` (not CURRENT/DELAYED, not PREVIOUS_CLOSE)
- freshness CURRENT for latest EOD session
- AI narrative cannot become VERIFIED by itself (offline Attacks A–F)

---

## REAL VS AI EVIDENCE

| Class | This forensic |
|---|---|
| PRIMARY EVIDENCE | NSE UDiFF EOD `eod_close` / `ClsPric` — VERIFIED |
| SECONDARY EVIDENCE | Yahoo / IBEF not used as truth |
| AI DISCOVERY | Not run (`NOT_CONFIGURED`) |
| AI INTERPRETATION | Offline injected claims rejected / unverified |

No source-class confusion: MCP commercial pending ≠ primary EOD HTTP; Screener cannot verify; LLM cannot verify.

---

## ADVERSARIAL TESTS

Offline, existing judge, TCS fixture. Production=false.

| Attack | Injection | Expected | Result |
|---|---|---|---|
| A Fake revenue | AI claim revenue = 1 vs primary dialect | AI rejected | Primary revenue not replaced by 1 |
| B Fake shares | 5,000,000,000 without authority | Rejected | Not VERIFIED; semantic gate intact |
| C Fake fraud | Unsupported management fraud | UNVERIFIED / REJECTED | Present as attack text, not verified fact |
| D Fake moat | “Wide moat.” | UNVERIFIED | Moat finding not a verified rating |
| E Fake IV | ₹5,000 | Ignored | DSP IV ≠ 5000; DcfMethod independent |
| F Source injection | Document instructs override of source authority | Rejected | `looks_like_injection`; sanitizer strips override; `may_verify` false for invalid hosts |

Retrieved documents are sanitized with the existing `sanitize_document_text` in `field_acquisition` (after download and before extract). Same sanitizer as `acquire_primary_documents`. Not a second pipeline.

---

## ASSUMPTIONS

`AssumptionValidator` still rejects out-of-bounds AI synthesis (`fcf_growth_rate=9.99` from `ai_synthesis` → not accepted). Rejected assumptions never enter DCF. Live run had **no accepted** growth / WACC / terminal pack, so DCF could not run even if statements had existed.

---

## DCF

Canonical `DcfMethod` only. Live: **BLOCKED** for all seven securities.

Gates that failed (honest):

- required financial primitives not VERIFIED
- `TOTAL_OUTSTANDING` not VERIFIED
- CA horizon not satisfied
- required assumptions not accepted

Price **was** VERIFIED (EOD). That is not sufficient for FULL ANALYSIS. AI IV is ignored.

---

## FULL ANALYSIS

`full_analysis_status` gates unchanged.

Live `analysis_state`: **`DCF_BLOCKED`** for every security.

Never falsely reported FULL.

---

## QUALITATIVE COVERAGE

| Surface | Live status |
|---|---|
| Business Quality | UNKNOWN |
| Management | UNKNOWN |
| Moat | UNKNOWN |
| Risk | UNKNOWN |
| Advanced Investment Check | PARTIAL |
| Thesis | not SUPPORTED (DCF blocked, missing evidence) |
| Thesis breakers | existing contract only; unverified AI not promoted |

Scores were not forced.

---

## BROWSER

**BLOCKED / NOT EXECUTED.**

Playwright specs exist (`apps/web/e2e/browser/company-workspace.smoke.spec.ts`) but this forensic did **not** start the web app, authenticate, search, click Analyse, or walk evidence / quality / moat / management / risk / Advanced Investment Check in a real browser.

`test_browser_and_a11y_qualification_is_honest` asserts the Advanced Investment Check section id exists in `sections.ts`, then **skips**. That is not a fake UI pass.

---

## RESPONSIVE

**NOT EXECUTED.** Desktop / tablet / mobile viewports were not driven. Existing vitest responsive helpers (`apps/web/src/lib/a11y/a11y-responsive.test.tsx`) were not run (`npm` / Playwright session not invoked). No page redesign.

---

## ACCESSIBILITY

**NOT EXECUTED.** Existing `npm run test:a11y` / `vitest-axe` path was not run in this forensic. Keyboard / focus / labels / headings / contrast were not re-measured. No accessibility regression was **claimed** green. Record: **SKIPPED**, not pass.

---

## DUPLICATE ANALYSIS

Offline: two consecutive `analyse_listing` MOCK calls produce the same identity status; no FULL analysis invented; retrieve 403/404/timeout stays fail-closed. Live path uses a per-listing retrieve bound (3 URLs) and a shared UDiFF bundle — no runaway research loop (`MAX_RESEARCH_LOOPS` unchanged).

Browser double-click / rapid Analyse was **not** exercised (browser blocked).

---

## PERFORMANCE

Live canonical path (search identity already resolved; analyse → result), seven listings + dynamic, seconds:

| | Seconds |
|---|---|
| p50 | **30.70** |
| p95 / max in this sample | **41.91** |

Shared UDiFF bundle fetch is outside the per-listing sample (one discover+download for the session). Qualitative + Advanced Check run on UNKNOWN statement inputs are cheap relative to retrieve. **No premature optimization.**

Research / evidence / qualitative / advanced-check timings remain on `EndToEndResult.timings`. Browser search→analyse→result p50/p95: **not measured** (browser blocked).

---

## FAILURE RECOVERY

| Failure | Result |
|---|---|
| NSE timeout / retrieve timeout | `RetrievalFailure` → structured failure, not FULL, not fabricated |
| HTTP 403 | Mapped; analysis not FULL |
| HTTP 404 | Mapped; analysis not FULL |
| Malformed / empty document | `EXTRACTION_FAILURE` / no text layer |
| AI timeout / quota | N/A (`NOT_CONFIGURED`); would remain UNKNOWN |
| Identity mismatch | Resolve UNKNOWN / REJECTED / AMBIGUOUS — never guessed |
| Stale evidence | REFRESH_REQUIRED / currentness labels; EOD trade date ≠ retrieval time |

No permanent loading state in this backend path. No fabricated result.

---

## SECURITY

Verified in existing contracts + SIMPLE-21 tests:

| Control | Result |
|---|---|
| Authentication / authorization | Unchanged frozen `/api/v1`; this forensic did not open production |
| URL allowlist | `SourcePolicy` primary / approved / secondary / forbidden |
| Source restrictions | Screener cannot verify; Yahoo secondary; LLM TIER_3 |
| Prompt / document injection | Attack F; `sanitize_document_text` on retrieve and injected text |
| AI output validation | EvidenceJudge; AssumptionValidator; DCF ignores AI IV |
| Secret redaction | `redact_mcp_text`; provider report asserts no `sk-` / Bearer / env key values |

API keys, tokens, credentials, and session secrets were not printed.

---

## PRODUCTION SAFETY

Explicit checks:

| Check | Result |
|---|---|
| Production revision changed | **No** (not queried, not deployed) |
| Production environment variable changed | **No** |
| Production secret changed | **No** |
| Production OpenAI research enabled | **No** (`NOT_CONFIGURED` locally; not activated in production) |
| Production NSE MCP enabled | **No** (`COMMERCIAL_USE_PENDING`) |
| Production `/api/v1/analyse` request DTO changed | **No** |
| Cloud Run / image traffic shift | **No** |

Local `DSP_LIVE_NSE_EOD` / `DSP_NSE_MCP_LIVE` are qualification flags on this workstation. They were not written into production config.

---

## COVERAGE MATRIX

Live `ResearchOrchestrator.analyse` with automatic `AUTO_REQUEST_GROUPS`, shared official UDiFF bundle, bounded retrieve. Dynamic security = **21STCENMGM**.

| Security | Identity | Price | Financials | Shares | CA | Business | Management | Moat | Risk | DCF | Advanced Check | Full Analysis |
| -------- | -------- | ----- | ---------- | ------ | -- | -------- | ---------- | ---- | ---- | --- | -------------- | ------------- |
| TCS | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED | PARTIAL | DCF_BLOCKED |
| INFY | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED | PARTIAL | DCF_BLOCKED |
| RELIANCE | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED | PARTIAL | DCF_BLOCKED |
| HDFCBANK | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED | PARTIAL | DCF_BLOCKED |
| WIPRO | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED | PARTIAL | DCF_BLOCKED |
| 20MICRONS | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED | PARTIAL | DCF_BLOCKED |
| 21STCENMGM | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED | PARTIAL | DCF_BLOCKED |

Coverage is **not** inflated. Price VERIFIED is official NSE EOD. Everything else that was not evidenced stays UNKNOWN / UNAVAILABLE / BLOCKED.

---

## PROVIDER REPORT

| Provider | Technical | Data capability shown here | Authority | Commercial | Latency (this session) | Failure behavior | Production eligibility |
|---|---|---|---|---|---|---|---|
| NSE public HTTP UDiFF | Available | Latest EOD `ClsPric` by ISIN+MIC | TIER_1A primary | Public market data; not a paid feed contract | Bundle fetch ~seconds; per-name analyse p50 30.7s including bounded retrieve | LookupError → skip/UNKNOWN, never fake EOD | **Not authorized by this forensic** |
| NSE MCP | Initialize/list_tools worked once; skipped later | Tool discovery only in this stage | Primary **if** commercially authorized — **not authorized** | **`COMMERCIAL_USE_PENDING`** | Probe ~seconds when up | Skip / structured MCP codes | **No** |
| Company IR / filings HTTP | URLs discovered | No VERIFIED statement extract in 3-URL bound | TIER_1B when verified | Public issuer documents | Inside per-name 30–42s | 403/404/timeout/no text layer → UNKNOWN | N/A |
| OpenAI | Not configured | None | TIER_3 | Not activated | N/A | Honest `NOT_CONFIGURED` | **No** |
| Gemini | Not configured | None | TIER_3 | Not activated | N/A | Honest `NOT_CONFIGURED` | **No** |
| Claude | Not configured | None | TIER_3 | Not activated | N/A | Honest `NOT_CONFIGURED` | **No** |
| Yahoo | Host classified only | None | TIER_2 | `may_verify=false` | N/A | Cannot verify | **No** |

Technical success is **not** a recommendation to activate production OpenAI or NSE MCP.

---

## ARCHITECTURE FORENSIC

Confirmed **no new**:

- ResearchRequest
- EvidenceItem
- EvidenceJudge
- ResearchOrchestrator class
- SourcePolicy
- DSP calculator / DcfMethod

Added only:

- `requests_price_evidence()` next to existing `PRICE_FIELDS` — expands the `PRICE` group with existing `expand_requested_fields`
- optional `retrieve_fn` passthrough on existing `analyse()` / `research()`
- reuse of `sanitize_document_text` inside existing `acquire_planned_fields`

Scan: production `qualitative.py`, `advanced_check.py`, `end_to_end.py`, `field_acquisition.py` contain **no** fixture ticker tokens (`TCS`, `INFY`, `RELIANCE`, `HDFCBANK`, `WIPRO`, `20MICRONS`). No `if ticker ==`. No `EvidenceJudge2` / `ResearchOrchestrator2`. Quality / moat weights unchanged (`0.30` earnings quality, `0.20` brand).

No dead-code deletion beyond what was already unused. No hardcoded financials, shares, or qualitative findings.

---

## TEST RESULTS

Command (SIMPLE-14N-E … SIMPLE-21 + official research engine + NSE MCP/OpenAI adapters + `/analyse` smoke):

**182 passed, 2 skipped, 0 failed, 0 xfail.**

| Suite | Result |
|---|---|
| SIMPLE-14N-E | 16 passed |
| SIMPLE-14N-F | 17 passed |
| SIMPLE-15 | 12 passed |
| SIMPLE-16 | 19 passed |
| SIMPLE-17 | 10 passed |
| SIMPLE-18 | 10 passed |
| SIMPLE-19 | 10 passed |
| SIMPLE-19A | 9 passed |
| SIMPLE-20 | 9 passed |
| SIMPLE-21 | 12 passed, **2 skipped** (browser/a11y honest skip; NSE MCP skip in the combined session) |
| official_research_engine | 29 passed |
| nse_mcp_openai | 22 passed |
| openai_responses | 5 passed |
| simple14n_analyse | 2 passed |

SIMPLE-21 dedicated `-m network` window: **3 passed** (live E2E matrix, orchestrator TCS EOD wiring, NSE MCP initialize).

| Class | Count |
|---|---|
| New failures | **0** |
| Pre-existing failures in this suite | **0** |
| Skipped | 2 (not disguised as pass) |
| xfail | 0 |

Frontend vitest / Playwright: **not run**.

---

## FILES CHANGED

### Production (data_engine)

- `packages/data_engine/src/data_engine/official_research/orchestrator.py` — PRICE group requests NSE EOD; optional `retrieve_fn` passthrough
- `packages/data_engine/src/data_engine/official_research/field_acquisition.py` — sanitize retrieved / injected document text with the existing prompt guard

### Tests

- `packages/data_engine/tests/test_simple21.py` *(new)*

### Docs

- `docs/releases/SIMPLE_21_LIVE_QUALITATIVE_BROWSER_FORENSIC.md` *(this file)*

No frontend redesign. Advanced Investment Check UI from SIMPLE-20 is unchanged.

---

## PRODUCTION IMPACT

**None.** No image rebuild, no Cloud Run traffic shift, no production OpenAI, no production NSE MCP, no feature-flag flip. Local HEAD remains `d55c8ef`. SIMPLE-15…21 remain uncommitted working-tree work unless a later human commit is requested.

`POST /api/v1/analyse` still uses `ResearchOrchestrator.analyse` with literal `eod_close` in fields (SIMPLE-14M composition). The PRICE-group wiring fix makes the automatic E2E plan match that already-correct production field list. It does not enable OpenAI or NSE MCP in production.

---

## COMMERCIAL STATUS

NSE MCP: **`COMMERCIAL_USE_PENDING`**

OpenAI research: **not configured locally; not activated in production.**

Public NSE EOD HTTP: used for **non-production qualification only**.

---

## LIMITATIONS

1. Live statement extraction did not produce VERIFIED financial primitives (3-URL bound; no fabricated numbers).
2. `TOTAL_OUTSTANDING` was not verified from live documents.
3. Corporate-action horizon was not established as CURRENT.
4. Qualitative engines stayed UNKNOWN — correct, given missing statements.
5. OpenAI live research was not run (`NOT_CONFIGURED`).
6. Browser, responsive, and accessibility user-path tests were not executed.
7. Duplicate-click UX was not browser-tested.
8. NSE MCP commercial use remains pending even after a successful initialize.
9. Overall mixed DSP score remains `NOT_CURRENTLY_DEFINED`.
10. FULL ANALYSIS was not achieved and was not claimed.

---

## DECISION

**PASS WITH LIMITATIONS — not CLOSED.**

This stage is not about making every company FULL ANALYSIS. It proved the system can use **real** NSE EOD evidence correctly and can **refuse** to complete valuation without shares, statements, CA completeness, and accepted assumptions.

Closure gates that hold:

- real identity resolution (ISIN + MIC) for fixtures + dynamic 21STCENMGM
- real approved-source EOD retrieval and EvidenceJudge verification
- AI remains behind EvidenceJudge (offline attacks; live AI not configured)
- AI cannot fabricate facts or change DSP methodology
- `TOTAL_OUTSTANDING` still enforced (UNAVAILABLE → DCF BLOCKED)
- currentness: EOD `as_of` is trade date, not retrieval time
- DCF remains deterministic and blocked without gates
- Advanced Investment Check runs on real identity + EOD without replacing core DSP
- previous regressions remain green
- no production deployment

Gates that keep this from CLOSED:

- live financial / share / CA / qualitative evidence not yet VERIFIED
- live OpenAI not configured
- NSE MCP not commercially authorized
- browser / a11y / responsive / duplicate-click path not executed
- FULL ANALYSIS not achieved (and must not be faked)

---

## NEXT FORENSIC

**SIMPLE-22 candidate:** non-production live **statement and share** acquisition beyond the 3-URL bound — still through the same orchestrator / EvidenceJudge / DcfMethod — plus Company Analysis **browser** qualification of Advanced Investment Check, evidence honesty, responsive, and a11y once `apps/web` dependencies and a running app session are present.

Do not activate OpenAI or NSE MCP in production in that forensic. Do not invent FULL ANALYSIS. Do not invent an overall DSP mega-score unless an existing methodology document defines one.
