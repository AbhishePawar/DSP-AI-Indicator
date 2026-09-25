# SIMPLE-23 — Universal Filing Detail & IR Document Extraction Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-22 proved the NSE **index** is a usable primary-evidence backbone (identity, period, consolidation metadata; no line items). SIMPLE-23 proves the platform can follow that backbone to the **actual filing layer**:

```text
NSE INDEX
   ↓
FILING DETAIL (XBRL / annual-report / announcement attachment)
   ↓
DOCUMENT ACQUISITION + VALIDATION
   ↓
GENERIC EXTRACTION (XBRL first; PDF/text fallback)
   ↓
SEMANTIC VALIDATION + CORPORATE-ACTION REVIEW
   ↓
EvidenceJudge
   ↓
VerifiedDataset
```

Live automatic path (six fixtures + five catalog-selected names, no hand-supplied URLs or numbers):

Identity **VERIFIED** · Price **VERIFIED** (EOD) · Financials **VERIFIED** on 10/11 (HDFCBANK **PARTIAL**) · Shares **UNAVAILABLE** · CA **UNKNOWN** · DCF **BLOCKED** · filing discovered **YES** · document acquired **YES** · mode **LIVE**

That is a successful forensic outcome. DCF remains blocked because TOTAL_OUTSTANDING was not established. Missing capex/debt/shares were left UNKNOWN. No values were fabricated.

**NO PRODUCTION DEPLOYMENT.** NSE MCP remains `COMMERCIAL_USE_PENDING`. OpenAI was `NOT_CONFIGURED`. No frontend work. No paid BSE/Kite/Yahoo authority.

---

## BASELINE

Recorded before SIMPLE-23 edits, after SIMPLE-22 closed as PASS WITH LIMITATIONS.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `9030287e1808a471a3d8a48c238085093616bad3` |
| HEAD subject | SIMPLE-15-22: fail-closed official research through live universal NSE acquisition |
| Working tree | Parking leftovers only (`.bytecode_backup/`, nested `DSP-AI-Indicator/`, demo auth, `artifacts/`). **Not committed. Not pushed. Not deployed.** |
| SIMPLE-22 | `docs/releases/SIMPLE_22_UNIVERSAL_LIVE_ACQUISITION_FORENSIC.md` — PASS WITH LIMITATIONS |
| Canonical path | `ResearchOrchestrator.analyse` → Security Master → ResearchPlan → NSE EOD + NSE primary JSON → EvidenceJudge → VerifiedDataset |
| Pre-SIMPLE-23 gap | `acquire_primary_documents()` existed (SIMPLE-14N) but **`analyse()` never called it** on LIVE |
| Production revision | **Not queried. Not changed.** |
| Production image | **Unchanged / not inspected.** |
| Production environment | **Not modified.** |
| Production feature flags | RESEARCH_MODE unchanged; RECOMMENDATION_MODE/SEBI locked; production OpenAI off; NSE MCP pending |

---

## ROOT CAUSE

SIMPLE-22 injected NSE primary JSON into `analyse()`. The financial-results **index** contains identity, period, and consolidation metadata but **not** revenue / net income / CFO / units.

The same index rows already expose the detail layer:

| Index field | Role |
|---|---|
| `xbrl` | Official NSE archive URL (`nsearchives.nseindia.com/corporate/xbrl/*.xml`) |
| `resultDetailedDataLink` | Often null in this session |
| annual-reports `fileName` | Integrated annual-report PDF (and older `.zip`) |
| announcements `attchmntFile` | PDF attachments |

Two acquisition bugs then blocked that layer:

1. **`analyse()` did not download the XBRL/PDF.** Index metadata stopped at JSON.
2. Once download was wired, selection treated an **empty/old XBRL** as success (identity OK, no labeled facts) and **returned**, or ranked FY2026-only / alphabetical titles so a 2019 `WEB.xml` 404 / empty instance won over a labeled annual XBRL. Annual-report PDFs (score 100) also crowded XBRL (score 95) until XBRL-first selection.

A third filter bug dropped year-end rows labeled `Fourth Quarter / Annual` because quarter hints were checked **before** annual hints.

---

## NSE DETAIL DISCOVERY

Live, non-production, same `NsePublicHttp` transport. Not a crawler.

| Endpoint / source | Parameters | Status | Content type | Document IDs / URLs | Identity / period | Limitations |
|---|---|---|---|---|---|---|
| `GET /api/corporates-financial-results` | `index=equities&symbol={TICKER}&period=Annual` | **200** | JSON list | `xbrl` URLs; `seqNumber`; `isin`; `toDate`; `consolidated` | Ticker+ISIN on row; `toDate` / `fromTo` | Index has **no line items or units** |
| NSE XBRL archive | URL from index `xbrl` | **200** (current INDAS); **404** on some historical `WEB.xml` | `application/xml` / XBRL instance | filename `INDAS_*` / `BANKING_*`; entity ISIN in context | Entity identifier scheme ISIN; FourD vs OneD contexts | Older files 404; banking taxonomy uses different concept names |
| `GET /api/annual-reports` | `index=equities&symbol={TICKER}` | **200** | JSON | `fileName` PDF/ZIP | `fromYr`/`toYr` | Large PDFs; not needed when XBRL extracts |
| `GET /api/corporate-announcements` | `index=equities&symbol={TICKER}` | **200** | JSON | `attchmntFile` PDFs | announcement date + title | CA titles, not share counts |
| `GET /api/quote-equity` | `symbol={TICKER}` | **403** | — | — | — | Unchanged from SIMPLE-22 |
| `GET /api/corporate-shareholding-pattern` | `index=equities&symbol={TICKER}` | **404** | — | — | — | Unchanged from SIMPLE-22 |
| NSE `resultDetailedDataLink` | from index row | null in this session | — | — | — | Not a usable detail route today |

INFY example (automatic): `https://nsearchives.nseindia.com/corporate/xbrl/INDAS_104589_1099938_19042024112830.xml` → entity ISIN `INE009A01021`, consolidated FourD annual, labeled INR facts.

The index is **not** the final data source. The XBRL URL on the index row is.

---

## COMPANY IR DISCOVERY

Generic, ISIN-keyed `CompanySourceRegistry` + `html_document_links` on the official IR/results/annual-report pages when NSE filing URLs fail.

- No hardcoded per-company PDF URLs in production code.
- IR fallback runs only if XBRL/NSE filing acquisition produced no selected document (`ir_fallback=True`, `fetch_registered_ir=False` on the LIVE analyse path to avoid crawling first).
- Live 11-name run did **not** need IR: NSE XBRL acquired for every name.

Limitation: registry coverage is not the full NSE universe. Unmapped ISINs still have NSE XBRL/annual-report locators from identity (ticker/ISIN), which is the path that worked live.

---

## DOCUMENT CANDIDATES

`NseAnnouncementDocument` + `DocumentRecord` / `DocumentCandidate` retain:

security (ISIN+MIC) · company · ticker · source · source_type · document_type/kind · document_url · document_date/`as_of` · period · retrieved_at · content_type · content_hash · document_id (`seqNumber`) · identity via entity ISIN / body ISIN · `statement_basis`

EvidenceJudge is not bypassed. Extracted facts become RAW `EvidenceItem` candidates (`agent=official_filing_detail`) and are promoted the same way as EOD/primary JSON.

---

## DOCUMENT ACQUISITION

`acquire_primary_documents()` is now called from `ResearchOrchestrator.analyse()` when:

- identity is RESOLVED
- `mode=LIVE`
- no injected `document_text`
- `NsePrimaryEvidenceService` is present

Selection rules (generic):

1. Prefer XBRL/XML from the financial-results index (up to 8 candidates, newest `as_of` after FY match).
2. Skip HTTP failures and **empty XBRL** (identity OK but no labeled facts) and continue.
3. Stop further XBRL once labeled financials exist.
4. Fall back to annual-report / announcement PDFs only if XBRL yielded nothing.
5. IR HTML discovery only if still nothing.

ZIP inner XML/PDF is unwrapped. Inner files are distinct versions.

---

## DOCUMENT VALIDATION

HTTP 200 is not proof. `validate_document_payload` / `retrieve_official_document` handle:

| Condition | Outcome |
|---|---|
| 403 / 404 / 429 / 5xx / timeout | `RetrievalFailure`; no fabricated body |
| empty body | rejected |
| HTML instead of PDF/XML | rejected |
| login/password page | rejected |
| PDF magic `%PDF` | accepted for PDF URLs |
| ZIP `PK` | unwrap then validate inner |
| XML/XBRL | must be XML, not HTML |

Redirects remain allowlisted. Content hash is stored on `DocumentRecord`.

---

## PDF EXTRACTION

Existing generic machinery unchanged in role:

- native text (`pypdf` + positional fallback)
- statement table reconstruction
- multi-page `[[PAGE n]]` markers
- scanned / textless PDF → **`OCR_REQUIRED`**, not VERIFIED

SIMPLE-23 live path did not need PDF extraction for the 11 names (XBRL succeeded). PDF remains the fallback and is covered by SIMPLE-14N tests.

---

## OCR

**No OCR engine was added.**

`select_extraction_strategy` already returns `ocr_required`. Acquisition records `OCR_REQUIRED: PDF has no text layer`. Insufficient OCR confidence is not applicable because OCR is not run. Scanned filings stay UNKNOWN / REVIEW_REQUIRED, never VERIFIED.

Smallest future integration (if needed): a bounded optional OCR backend behind that existing strategy flag, with provenance. Not required to prove SIMPLE-23’s XBRL filing layer.

---

## FINANCIAL EXTRACTION

Generic XBRL instance parser (`xbrl.py`): concept local-name → canonical field, only when unit, period, and statement basis are explicit.

Preferred annual context: **FourD / year / annual** over **OneD** (NSE often shares Q4 calendar dates between quarter and YTD).

| Field | Live INFY (VERIFIED) | Notes |
|---|---|---|
| Revenue | 1,536,700,000,000 | `RevenueFromOperations`, FourD, INR actual |
| Net income | 262,480,000,000 | PAT / profit-for-period family |
| CFO | 252,100,000,000 | `CashFlowsFromUsedInOperatingActivities` only — not `...InOperations` |
| Equity | 881,160,000,000 | total equity / owners |
| Cash | 147,860,000,000 | cash and cash equivalents |
| Total assets | 1,378,140,000,000 | |
| Total liabilities | 493,530,000,000 | |
| Capex | UNKNOWN | PPE-purchase is still not capex |
| Debt | UNKNOWN on INFY | split current/non-current not summed |

HDFCBANK **PARTIAL**: banking XBRL (`BANKING_*.xml`) uses a different concept dialect; generic industrial names matched CFO/debt in the probe, not revenue/equity. No bank-specific parser was added.

---

## UNITS

Source unit is retained (`iso4217:INR`, `unit_scale=actual`, or explicit crore/lakh/million from labeled text).

Normalize only after the unit is explicit. Unlabeled XBRL facts are dropped (`{field} XBRL unit unlabeled`). Never infer crore from “typical Indian report” convention.

---

## PERIODS

XBRL context start/end or instant → `as_of` = period end. FourD ranked as `period_type=FY`.

Publication / archive timestamp in the filename is **not** the financial period.

`period_start` / `period_end` / `period_type` stay on the extracted field when the context provides them. Index `toDate` is used only to **rank** candidates, not as a substitute for XBRL context.

---

## CONSOLIDATION

Explicit `CONSOLIDATED` / `STANDALONE` / `UNKNOWN`.

Index `consolidated` / `resultType` is passed as `document_basis` when the XBRL context omits the axis (common on NSE INDAS). Context axis wins when present.

Preferred basis remains project canonical **consolidated**. Standalone is kept as fallback and is **not mixed** into consolidated figures.

---

## SHARE COUNT

Live NSE XBRL instances in this session expose paid-up / face-value / equity-share-capital **rupee** concepts, not `NumberOfEquitySharesOutstanding`.

**Paid-up capital ÷ face value is not computed.** Corporate actions and other capital classes make that identity non-deterministic without additional proof.

Shareholding endpoint remains HTTP 404. quote-equity remains HTTP 403. Result: **TOTAL_OUTSTANDING UNAVAILABLE** on all 11 live names. Honest.

When an outstanding-share concept **is** present (offline fixture XML), it is extracted and classified.

---

## SHARE SEMANTICS

`classify_share_semantic_type` / `canonical_share_semantic_type` plus XBRL `_humanize_concept` (CamelCase → phrase).

Rejected as TOTAL_OUTSTANDING:

weighted-average · basic/diluted EPS denominator · potential · free-float · promoter · authorized · paid-up value · face value · employee options / convertibles (forbidden concept substrings)

Only explicit outstanding-share concepts become share candidates. EvidenceJudge still requires `VALUATION_SHARE_SEMANTIC == TOTAL_OUTSTANDING`.

---

## CORPORATE ACTIONS

Announcement titles continue to be parsed into dated `CapitalEvent`s (bonus, split, rights, QIP, FPO, preferential, ESOP, warrants, convertibles, buyback, cancellation, capital reduction, merger, demerger, scheme, share swap, acquisition).

`classify_capital_effect`:

| Class | Types |
|---|---|
| INCREASE | bonus, split, rights, QIP, FPO, preferential, ESOP, warrants, convertibles, new issue |
| DECREASE | buyback, cancellation, extinguishment, capital reduction |
| UNKNOWN / POTENTIAL | merger, demerger, scheme, share_swap, acquisition |

Acquisition is **not** assumed to issue shares. Cash consideration → `NO_SHARE_COUNT_CHANGE`. Share-swap / mixed → `POTENTIAL_CHANGE`. Unknown consideration stays UNKNOWN.

Without a dated share candidate, the CA horizon cannot make shares CURRENT. Live CA status remains **UNKNOWN**.

---

## CURRENTNESS

A share count is CURRENT only when: latest authoritative count + subsequent relevant CA checked + effects resolved + no contradiction.

Live: no share candidate → **UNAVAILABLE**, not CURRENT, not silently historical-as-current.

Financials use document period end as `as_of`. Retrieval time is not substituted for `as_of`.

---

## RECONCILIATION

EvidenceJudge still reconciles **candidates** (identity, authority, semantics, freshness, period, unit, CA, cross-check, consistency) before VERIFIED.

No new hard equality gate was added for Assets = Liabilities + Equity. INFY live figures differ by a small residual (presentation / NCI / rounding). Spec: do not force exact equality; unexplained residuals are not promoted away. FCF stays blocked because capex is UNKNOWN (`CFO − |Capex|` is not inferred).

---

## EVIDENCE PROVENANCE

Each extracted fact retains evidence_id, source=`NSE`, source_url (XBRL/PDF), document_date/`as_of`, retrieved_at, locator/concept, period, currency, unit, ISIN+MIC, extraction method (`official_filing_detail` / XBRL), content hash when stored.

Traceable to the archive URL. AI cannot populate this path.

---

## EVIDENCE JUDGE

Unchanged authority. Order remains:

IDENTITY → SOURCE AUTHORITY → SEMANTICS → FRESHNESS → PERIOD → UNIT → CORPORATE ACTIONS → CROSS-CHECK → CONSISTENCY → VERIFIED

Filing XBRL cannot skip the judge. NSE JSON cannot skip the judge. Company PDF cannot skip the judge.

---

## VERIFIED DATASET

Only judge-approved facts enter `VerifiedDataset`. Live INFY dataset contains verified EOD + verified XBRL financials. Shares stay out. Capex/debt stay out where unlabeled. DCF does not run.

---

## AI STATUS

| Item | Value |
|---|---|
| OpenAI | `NOT_CONFIGURED` |
| NSE MCP | `COMMERCIAL_USE_PENDING` |
| Gemini FIND | optional compatibility façade only; cannot write VERIFIED |

SIMPLE-23 did not wait for AI. No fake provider responses. Deterministic XBRL/PDF pipeline is sufficient.

AI cannot create authoritative financials/shares, override the judge, change currentness, change DCF/DSP weights, create corporate actions, or promote UNKNOWN to VERIFIED.

---

## AUTOMATICITY

No manual documents, URLs, or numbers. No ticker-specific production parsers.

Path:

Security Master → ResearchPlan (`AUTO_REQUEST_GROUPS`) → NSE EOD + NSE primary index → `acquire_primary_documents` → RAW candidates → EvidenceJudge → VerifiedDataset → DSP/DCF only if gates pass.

---

## TEST SECURITIES

### Fixed forensic fixtures (tests only)

TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS

### Dynamic fixtures (catalog-selected, not hand-picked)

Same selection rule as SIMPLE-22 (first catalog hits filling financial / technology / industrial / consumer / other, excluding the fixture set):

| Ticker | Kind |
|---|---|
| AADHARHFC | financial |
| 3IINFOLTD | technology |
| A2ZINFRA | industrial |
| ABFRL | consumer |
| 21STCENMGM | other |

Production modules contain none of these ticker tokens (architecture test).

---

## LIVE COVERAGE MATRIX

Shared UDiFF bundle; per-name NSE primary + XBRL acquire; `mode=LIVE`; `production=False`.

| Security | Identity | Price | Financials | Shares | CA | DCF | Filing discovered | Document acquired | Analysis state |
|---|---|---|---|---|---|---|---|---|---|
| TCS | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| INFY | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| RELIANCE | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| HDFCBANK | VERIFIED | VERIFIED | PARTIAL | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| WIPRO | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| 20MICRONS | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| AADHARHFC | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| 3IINFOLTD | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| A2ZINFRA | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| ABFRL | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |
| 21STCENMGM | VERIFIED | VERIFIED | VERIFIED | UNAVAILABLE | UNKNOWN | BLOCKED | YES | YES | DCF_BLOCKED |

PARTIAL = some of revenue / net income / CFO / equity verified; not all. Unknown remaining fields were **not** filled.

---

## NEGATIVE TESTS

| Case | Result |
|---|---|
| Wrong ISIN in XBRL entity | identity_ok False; no fields |
| Malformed XML | no fields; issue recorded |
| Empty XBRL then newer labeled XBRL | 404/empty skipped; labeled instance selected |
| HTML masquerading as PDF/XML | rejected |
| Empty document | rejected |
| HTTP 403 | failure recorded; no fabricated values |
| HTTP 404 | continue to next candidate |
| Weighted-average / paid-up / diluted / face-value as shares | not TOTAL_OUTSTANDING; omitted from fields |
| Standalone vs consolidated | not mixed; preferred basis honored |
| Wrong-company document text (Reliance ISIN, INFY request) | identity FAIL; net income not VERIFIED |
| Yahoo URL | cannot verify |
| Gemini FIND enabled | claims cannot write VERIFIED |
| Textless PDF | OCR_REQUIRED / UNAVAILABLE |

---

## COMPANY-SPECIFIC LOGIC FORENSIC

Production `official_research` modules: no `if ticker ==`, no `TCSParser` / `INFYParser`, no fixture ticker tokens in `xbrl.py`, `acquisition.py`, `orchestrator.py`, `nse_primary.py`, `field_acquisition.py`, `end_to_end.py`.

Fixtures may contain expected values. Production code does not.

Banking XBRL dialect is **not** forked per issuer; unmatched bank concepts stay UNKNOWN (HDFCBANK PARTIAL).

---

## PERFORMANCE

Live `analyse` (11 listings, shared UDiFF, per-name index + one XBRL), seconds:

| | |
|---|---|
| p50 | **3.39** |
| p95 | **5.12** |

INFY sanity after XBRL-first fix: **3.5s** end-to-end (previously ~78s when an integrated annual-report PDF was selected). HDFCBANK XBRL-only acquire probe: download **0.23s**, extract **0.03s**.

No optimization pass. Frontend not measured.

---

## SECURITY

Source allowlist unchanged. Secrets not printed. AI cannot verify. Document injection sanitizer remains. NSE MCP not production-activated. No production secrets. No production provider activation.

---

## REGRESSION

Offline (`not network`):

**269 passed, 3 skipped, 5 deselected, 0 failed, 0 xfail.**

| Suite | Result |
|---|---|
| SIMPLE-14N-E | 16 passed |
| SIMPLE-14N-F | 17 passed |
| SIMPLE-15 … 20 | all passed |
| SIMPLE-21 | 10 passed, 1 skipped (browser) |
| SIMPLE-22 | 9 passed, 1 skipped (browser) |
| SIMPLE-23 | 13 passed, 1 skipped (frontend parked) |
| nse_primary | 10 passed |
| official_research_engine + MCP/OpenAI + 14N-A/B/acquisition + analyse | passed |

Live SIMPLE-23 network test: **1 passed** (coverage matrix above).

New failures in this suite: **0**. Pre-existing failures in this suite: **0**.

Frontend suites: **not executed** (parked).

---

## FILES CHANGED

### Production

- `packages/data_engine/src/data_engine/official_research/xbrl.py` — **new** generic XBRL instance extract
- `packages/data_engine/src/data_engine/official_research/acquisition.py` — XBRL-first selection; skip empty XBRL; PDF fallback; identity/basis wiring
- `packages/data_engine/src/data_engine/official_research/annual_report.py` — as_of ranking; statement_basis; XML/XBRL score
- `packages/data_engine/src/data_engine/official_research/nse_primary.py` — parse XBRL URLs from financial-results index; annual-before-quarter period filter
- `packages/data_engine/src/data_engine/official_research/orchestrator.py` — LIVE `analyse()` calls `acquire_primary_documents`; identity on compat extract
- `packages/data_engine/src/data_engine/official_research/documents.py` — payload validation (HTML-vs-PDF/XML, empty, login, zip)
- `packages/data_engine/src/data_engine/official_research/pdf_text.py` — XML/JSON decode path
- `packages/data_engine/src/data_engine/official_research/extraction.py` — CamelCase share-concept humanize

### Tests / docs

- `packages/data_engine/tests/test_simple23.py` — **new**
- `packages/data_engine/tests/test_nse_primary.py`
- `docs/releases/SIMPLE_23_UNIVERSAL_FILING_DETAIL_EXTRACTION_FORENSIC.md`

Frontend files were **not** modified for SIMPLE-23.

---

## PRODUCTION IMPACT

**None.** No Cloud Run, no production env/flags/secrets, no MCP/OpenAI production enablement. Local LIVE qualification uses the same frozen `/api/v1` construction as SIMPLE-22; it now downloads NSE XBRL when the index provides a URL. That does not authorize production MCP, AI, or NSE commercial use.

---

## LIMITATIONS

1. TOTAL_OUTSTANDING not established live (no outstanding-share XBRL concept in sampled INDAS files; shareholding 404; quote-equity 403; paid-up/face-value not divided).
2. Capex often UNKNOWN (PPE purchase remains forbidden as capex).
3. Debt often UNKNOWN when split current/non-current without a total borrowings fact.
4. HDFCBANK (and likely other banks) banking XBRL dialect is only partially mapped — PARTIAL, not a per-bank parser.
5. Some historical XBRL `WEB.xml` URLs 404; selection continues.
6. Year-end XBRL in the Annual index may still be FY24/FY25 rather than the latest completed FY when NSE has not published a newer annual instance.
7. No OCR engine; scanned PDFs stay OCR_REQUIRED / UNKNOWN.
8. Assets vs Liabilities+Equity is not a hard equality gate.
9. OpenAI not configured; NSE MCP commercial use pending.
10. Frontend / a11y / responsive **parked** (SIMPLE-23 backend only).
11. FULL ANALYSIS / DCF not achieved and not claimed.

---

## DECISION

**PASS WITH LIMITATIONS — not CLOSED.**

The generic filing-detail machinery is proven:

- actual filing/document detail can be discovered automatically (NSE `xbrl` URLs)
- documents can be acquired and identity-checked
- financial extraction works generically across fixtures and five dynamic names
- units, periods, and consolidation are preserved
- invalid share counts are rejected; live shares stay UNAVAILABLE
- corporate actions are investigated from announcements; currentness stays deterministic
- EvidenceJudge remains authoritative
- VerifiedDataset contains only verified facts
- no company-specific production parser
- negative tests pass
- regression remains green

Closure still needs a live TOTAL_OUTSTANDING route (shareholding, outstanding-share XBRL concept, or another Tier-1 labeled disclosure) plus CA horizon to CURRENT, without issuer forks. Banking XBRL dialect coverage is a follow-up, not an HDFC parser.

---

## NEXT FORENSIC

**SIMPLE-24 candidate:** universal **outstanding-share** acquisition and currentness (shareholding when the endpoint yields labeled totals; generic outstanding-share XBRL concepts when present; CA horizon after `as_of`) so DCF is unblocked **only** when EvidenceJudge can verify TOTAL_OUTSTANDING. Optional generic banking/NBFC XBRL concept aliases (not issuer parsers). Frontend remains a later FRONTEND phase.

Do not add Kite, paid BSE, or Yahoo-as-authority. Do not activate production MCP/OpenAI. Do not solve companies one by one.
