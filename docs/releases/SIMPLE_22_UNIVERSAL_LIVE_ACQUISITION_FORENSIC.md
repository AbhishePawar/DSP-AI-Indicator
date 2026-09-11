# SIMPLE-22 — Universal Live Financials, Shares & Corporate-Action Acquisition Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-21 proved live identity + NSE UDiFF EOD through the one canonical path. SIMPLE-22 extends that path so **any supported NSE equity** can automatically discover NSE primary JSON (financial results index, shareholding, quote-equity, announcements, annual-report archive) **without ticker-specific branches**.

Live result for six fixtures plus five catalog-selected names:

Identity **VERIFIED** · Price **VERIFIED** (EOD) · Financials **UNKNOWN** · Shares **UNAVAILABLE** · CA **UNKNOWN** · DCF **BLOCKED** · mode **LIVE**

That is a **successful** forensic outcome. The machinery ran unattended. NSE quote-equity returned HTTP 403, shareholding HTTP 404, and the financial-results index contains period/identity/consolidation metadata **without line items or units**. The system did not invent crores, outstanding shares, or FULL ANALYSIS.

**NO PRODUCTION DEPLOYMENT.** NSE MCP remains `COMMERCIAL_USE_PENDING`. OpenAI was not configured. No paid BSE/Kite/Yahoo authority was added.

---

## BASELINE

Recorded before SIMPLE-22 edits, on the uncommitted SIMPLE-15…21 stack.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| Working tree | SIMPLE-15…21 uncommitted official-research work. Parking leftovers remain uncommitted. **Not committed. Not pushed. Not deployed.** |
| SIMPLE-21 | `docs/releases/SIMPLE_21_LIVE_QUALITATIVE_BROWSER_FORENSIC.md` — PASS WITH LIMITATIONS |
| SIMPLE-19A | One canonical callable: `ResearchOrchestrator.analyse` → `analyse_user_query` / `analyse_listing` |
| SIMPLE-20 | Qualitative engines + Advanced Investment Check on that same path |
| SIMPLE-21 changes | PRICE group requests NSE EOD; document sanitizer; live EOD VERIFIED |
| Production revision | **Not queried. Not changed.** |
| Production image | **Unchanged / not inspected.** |
| Production environment | **Not modified.** |
| Production feature flags | RESEARCH_MODE unchanged; RECOMMENDATION_MODE/SEBI locked; production OpenAI off; NSE MCP pending; local `DSP_LIVE_NSE_EOD` is qualification-only |
| Pre-edit regression | **180 passed, 1 skipped, 3 deselected** (`not network`), 0 failed / xfail |

---

## ARCHITECTURE

Unchanged spine:

```text
ResearchOrchestrator.analyse
        ↓
Security Master (ISIN + MIC)
        ↓
ResearchPlan (AUTO_REQUEST_GROUPS)
        ↓
NSE EOD candidates + NSE primary JSON candidates
        ↓
acquire_planned_fields
        ↓
EvidenceJudge
        ↓
VerifiedDataset
        ↓
DSP / DcfMethod (only if gates pass)
```

`NsePrimaryEvidenceService` already existed. SIMPLE-21 did not inject its fields into `analyse()`. SIMPLE-22 does: LIVE primary fields become RAW `EvidenceItem` candidates (same as EOD). EvidenceJudge still verifies. No second judge, dataset, source policy, or orchestrator.

Optional `retrieve_fn` still forwards into the façade. Production `/api/v1/analyse` does not pass it.

---

## SUPPORTED UNIVERSE

Catalog-driven Security Master (not the six fixtures).

| Attribute | Value |
|---|---|
| Source | Official NSE `EQUITY_L.csv` + BSE dual listings of the same ISIN |
| Identity | ISIN + MIC |
| Eligible in tests | `eligibility=True`, `security_type=equity`, `mic=XNSE` |
| Rejected | ETF `NIFTYBEES` → `UNSUPPORTED`; unknown queries stay `UNKNOWN`; ambiguous listings are not guessed |

---

## TEST SECURITIES

### Fixed forensic fixtures (tests only)

TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS

### Dynamic fixtures (not hand-picked)

First catalog hits filling financial / technology / industrial / consumer / other, excluding the fixture set:

| Ticker | Company | ISIN | MIC | Kind |
|---|---|---|---|---|
| AADHARHFC | Aadhar Housing Finance Limited | INE883F01010 | XNSE | financial |
| 3IINFOLTD | 3i Infotech Limited | INE748C01038 | XNSE | technology |
| A2ZINFRA | A2Z Infra Engineering Limited | INE619I01012 | XNSE | industrial |
| ABFRL | Aditya Birla Fashion and Retail Limited | INE647O01011 | XNSE | consumer |
| 21STCENMGM | 21st Century Management Services Limited | INE253B01015 | XNSE | other |

Production modules contain none of these ticker tokens.

---

## SOURCE POLICY

Locked hierarchy unchanged.

| Tier | Role |
|---|---|
| 1A | NSE/BSE/SEBI/MCA/RBI/NSDL/CDSL — may verify |
| 1B | Company IR / filings — may verify with `company_ir` |
| 1C | Screener — `may_verify=false` |
| 2 | Yahoo / IBEF — secondary |
| 3 | AI — discovery only |

---

## DOCUMENT DISCOVERY

Universal locators from identity (ticker/ISIN), not `if ticker ==`:

- NSE quote-equity
- NSE financial-results (`period=Annual`)
- NSE shareholding pattern
- NSE corporate announcements
- NSE annual-reports archive
- Registry IR / annual report / results URLs when the ISIN is mapped

Each candidate keeps source, source_type, URL, retrieved_at. Document hash applies when a body is stored. Dedup remains URL/hash via `DocumentStore` / `document_version_relation`.

---

## DOCUMENT ACQUISITION

Existing `retrieve_official_document` + `NsePublicHttp`. HTTP 200 is not treated as financial proof.

Live probe (INFY, non-production):

| Endpoint | HTTP / parse |
|---|---|
| quote-equity | **403** |
| shareholding | **404** |
| financial-results index | **200** list of 34 annual rows |
| announcements | **200** — CA titles parsed |

Redirects remain allowlisted. Timeouts map to structured failures. HTML/PDF/JSON/text handled by existing extractors. XLS/XLSX not newly added; missing sheets stay UNKNOWN.

---

## PDF/OCR

`select_extraction_strategy` now returns **`ocr_required`** for a PDF with no text layer (was `unavailable`). Native PDF text / table strategies unchanged. **No OCR engine was added.** OCR-required documents cannot become VERIFIED.

---

## FINANCIAL EXTRACTION

Parsers already map explicit particulars (revenue, PAT, CFO, capex, cash, debt, equity). SIMPLE-22:

- attaches **currency INR**, **unit_scale actual** (after crore/lakh/million scale), **statement_basis**, **FY period_end** when those are known
- walks `total assets` / `total liabilities` labels
- `extract_nse_api_field` reuses those parsers on retrieved NSE JSON

**Live index rows have no `particulars`/`value` and no `unit`.** Example metadata: `period=Annual`, `consolidated` ∈ {Consolidated, Non-Consolidated}, `financialYear`, `isin`, `toDate`. Without labeled amounts and units the extract returns UNKNOWN. Offline labeled crore PAT still verifies (INFY sample 26,733 crore → 267,330,000,000 actual).

---

## CONSOLIDATED VS STANDALONE

`_statement_basis` now reads the **field value** (`Consolidated` / `Non-Consolidated` / `resultType`) instead of scanning JSON **key names** (the key `consolidated` previously forced a false match). Mixed unlabeled rows stay UNKNOWN. Canonical preference remains consolidated for ordinary equity; standalone is not mixed into consolidated totals.

---

## PERIOD VALIDATION

Annual rows require annual period text. Quarterly/half-year are skipped. `toDate` / `fromTo` is the period end — not `retrieved_at` or `broadCastDate`. Upload date is not FY.

---

## SHARE COUNT

Highest-priority gate. Live: **UNAVAILABLE** for all eleven names.

| Candidate | Semantic | Live |
|---|---|---|
| quote-equity `issuedSize` | **ISSUED** (rejected for valuation); also unlabeled `as_of`; endpoint **403** | not VERIFIED |
| shareholding `totalNoOfShares` | mapped to **TOTAL_OUTSTANDING** when the label is the SHP total (not promoter/float) | endpoint **404** |
| weighted average / free float / authorized | rejected | — |

No candidate enters VerifiedDataset until EvidenceJudge. Fake 5e9 shares still rejected.

---

## CORPORATE ACTIONS

Announcements were searched automatically (INFY: 230 title matches — ESOP 92, acquisition 78, buyback 41, bonus 12, extinguishment 6, merger 1). Acquisition is **not** assumed to change shares (`NO_SHARE_COUNT_EFFECT` if cash; `POTENTIALLY_CHANGES_OUTSTANDING` if swap/mixed).

`classify_share_count_effect_status` exposes SIMPLE-22 vocabulary over the existing classifier:

INCREASES_OUTSTANDING · DECREASES_OUTSTANDING · NO_SHARE_COUNT_EFFECT · POTENTIALLY_CHANGES_OUTSTANDING · UNKNOWN

Without a dated TOTAL_OUTSTANDING, CA currentness cannot be CURRENT. Live CA status remains **UNKNOWN**, not CURRENT.

---

## CURRENTNESS

Share CURRENT requires dated outstanding evidence **and** a searched CA horizon. EOD `as_of` is the trade date. Retrieval time is not freshness. Live shares never reached CURRENT.

---

## CONFLICTS

Two primaries are not averaged. AI cannot pick a winner. Offline: AI revenue=1 does not replace a primary dialect. Unresolved primaries stay CONFLICT (existing EvidenceJudge).

---

## RECONCILIATION

Existing judge + derived-field checks. No forced Assets = L+E when presentation differs. Live: nothing to reconcile except EOD.

---

## DERIVED VALUES

Market cap / FCF / EV / IV / MoS remain DSP-only. Live DCF **BLOCKED** (no verified shares or statement primitives). No AI market cap.

---

## AI STATUS

`LIVE_OPENAI = NOT_CONFIGURED`. Deterministic default provider. No live AI research call.

---

## AI BOUNDARY

Unchanged. AI may FIND/EXTRACT/PROPOSE; cannot write VerifiedDataset, override the judge, change formulas/weights, or invent facts. Offline injected AI claims stay unverified.

---

## NSE STATUS

| Capability | Live |
|---|---|
| Security Master | used |
| UDiFF EOD | VERIFIED price for all 11 |
| Financial results index | reachable; **no line items/unit** |
| Shareholding JSON | 404 |
| Quote-equity JSON | 403 |
| Announcements | reachable; CA titles parsed |
| Annual-report archive URL | discovered |

No new market-data vendor.

---

## NSE MCP STATUS

`COMMERCIAL_USE_PENDING`. Not production-activated. SIMPLE-22 did not treat MCP as authority.

---

## LIVE COVERAGE MATRIX

Automatic `ResearchOrchestrator.analyse` + shared UDiFF bundle + `NsePrimaryEvidenceService`. No hand-supplied URLs, documents, or numbers.

| Security | Identity | Price | Financials | Shares | CA | Business | Management | Moat | Risk | DCF |
| -------- | -------- | ----- | ---------- | ------ | -- | -------- | ---------- | ---- | ---- | --- |
| TCS | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| INFY | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| RELIANCE | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| HDFCBANK | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| WIPRO | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| 20MICRONS | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| AADHARHFC | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| 3IINFOLTD | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| A2ZINFRA | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| ABFRL | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |
| 21STCENMGM | VERIFIED | VERIFIED | UNKNOWN | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED |

Failure locus (automatic, same for the universe): **NSE primary JSON did not yield labeled, unit-bearing statement lines or dated TOTAL_OUTSTANDING.** UDiFF EOD still verified.

---

## AUTOMATICITY TEST

Dynamic five received **no** manual URLs, documents, financials, shares, or CA. Discovery used Security Master + NSE URL templates + UDiFF. Failures recorded as HTTP 403/404 and unlabeled financial index — not patched per issuer.

---

## COMPANY-SPECIAL-CASE FORENSIC

Production `qualitative.py`, `advanced_check.py`, `end_to_end.py`, `field_acquisition.py`, `orchestrator.py`, `nse_primary.py`: no fixture ticker tokens, no `if ticker ==`, no second EvidenceJudge. Fixtures exist only in tests.

---

## FIXTURE LEAKAGE

Live dataset `mode=LIVE` on every row. MOCK dialect tests stay MOCK. DSPFIX / P109 fixture path is still production-gated off LIVE NSE.

---

## BROWSER

**BLOCKED / skipped.** Playwright user path not executed (no app server session).

---

## ACCESSIBILITY

**NOT EXECUTED.**

---

## RESPONSIVE

**NOT EXECUTED.** No redesign.

---

## FAILURE TESTS

| Case | Result |
|---|---|
| NSE 403 / 404 | LookupError → issues tuple; fields empty; not FULL |
| Timeout | existing retrieval failure mapping |
| Scanned PDF | `ocr_required`; not VERIFIED |
| Wrong ISIN on quote-equity | parser reject |
| issuedSize as outstanding | ISSUED ≠ TOTAL_OUTSTANDING |
| AI fake revenue / shares | rejected |
| ETF | UNSUPPORTED |
| Prompt injection | existing sanitizer (SIMPLE-21) |

---

## PERFORMANCE

Live analyse (11 listings, shared UDiFF, per-name primary fetch), seconds:

| | |
|---|---|
| p50 | **3.46** |
| p95 | **5.21** |

No optimization pass. Browser path not measured.

---

## SECURITY

Source allowlist unchanged. Secrets not printed. AI output cannot verify. Document injection sanitizer remains. NSE MCP not production-activated.

---

## REGRESSION

Offline (`not network`):

**197 passed, 2 skipped, 4 deselected, 0 failed, 0 xfail.**

| Suite | Result |
|---|---|
| SIMPLE-14N-E … 20 | all passed (same counts as SIMPLE-21) |
| SIMPLE-21 | 10 passed, 1 skipped |
| SIMPLE-22 | 9 passed, 1 skipped (browser) |
| nse_primary | 8 passed |
| official_research_engine + MCP/OpenAI + analyse | passed |

Live SIMPLE-22 network test: **1 passed** (coverage matrix above).

New failures: **0**. Pre-existing failures in this suite: **0**.

---

## FILES CHANGED

### Production

- `packages/data_engine/src/data_engine/official_research/orchestrator.py` — inject NSE primary candidates + CA into `analyse()`
- `packages/data_engine/src/data_engine/official_research/nse_primary.py` — field context; API field helper; explicit consolidation
- `packages/data_engine/src/data_engine/official_research/field_acquisition.py` — shareholding URL; JSON API extract fallback
- `packages/data_engine/src/data_engine/official_research/extraction.py` — SHP total-share semantic; CA effect vocabulary
- `packages/data_engine/src/data_engine/official_research/documents.py` — `ocr_required`

### Tests / docs

- `packages/data_engine/tests/test_simple22.py`
- `packages/data_engine/tests/test_nse_primary.py`
- `packages/data_engine/tests/test_simple14nf.py` (ocr_required)
- `docs/releases/SIMPLE_22_UNIVERSAL_LIVE_ACQUISITION_FORENSIC.md`

---

## PRODUCTION IMPACT

**None.** No Cloud Run, no production env/flags/secrets, no MCP/OpenAI production enablement. `/api/v1/analyse` already constructed `NsePrimaryEvidenceService` when local live NSE is allowed; it now **uses** those fields as candidates instead of dropping them. That does not authorize production MCP or AI.

---

## LIMITATIONS

1. Live NSE financial-results **index** has no extractable line items or units.
2. Live quote-equity **403** and shareholding **404** in this session.
3. TOTAL_OUTSTANDING not established live.
4. CA titles are high-recall; without dated shares they cannot make CURRENT.
5. OpenAI not configured.
6. Browser / a11y / responsive not executed.
7. FULL ANALYSIS not achieved and not claimed.

---

## DECISION

**PASS WITH LIMITATIONS — not CLOSED.**

Universal automatic acquisition **runs** for any catalog NSE equity. EvidenceJudge remains the authority. DCF stays blocked without verified statements and TOTAL_OUTSTANDING. The platform is better at **finding** NSE primary endpoints without being less strict about **proving** numbers.

Closure still needs a live route that actually returns labeled, unit-bearing financials and dated outstanding shares (same parsers, no issuer forks) plus browser qualification when the app session exists.

---

## NEXT FORENSIC

**SIMPLE-23 candidate:** non-production follow-through on NSE filing **detail** payloads (or company IR PDFs with a text layer) so the existing particulars parser can see revenue/CFO/equity/shares — still fail-closed on 403/unlabeled unit — plus Company Analysis browser checks. Do not add Kite, paid BSE, or Yahoo-as-authority. Do not activate production MCP/OpenAI.
