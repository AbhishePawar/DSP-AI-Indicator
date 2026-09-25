# SIMPLE-24 — Universal Total Outstanding Shares & Corporate-Action Currentness Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-23 proved universal filing-detail extraction (XBRL-first) and left valuation blocked on:

```text
TOTAL_OUTSTANDING = UNAVAILABLE
DCF = BLOCKED
```

SIMPLE-24 proves the platform can **automatically determine whether a trustworthy current TOTAL_OUTSTANDING exists** for a supported NSE equity:

```text
SECURITY MASTER
      ↓
CANONICAL IDENTITY (ISIN + MIC)
      ↓
LATEST SHARE-COUNT EVIDENCE (SHP XBRL first)
      ↓
SEMANTIC CLASSIFICATION
      ↓
CORPORATE-ACTION SEARCH (calendar + announcements)
      ↓
SHARE-COUNT EFFECT
      ↓
CURRENTNESS JUDGE
      ↓
VERIFIED TOTAL_OUTSTANDING  or  REFRESH_REQUIRED / UNKNOWN / UNAVAILABLE
      ↓
VERIFIED DATASET
      ↓
MARKET CAP  (only VERIFIED price × VERIFIED TOTAL_OUTSTANDING)
      ↓
DCF  (existing gates unchanged)
```

Live automatic path (six fixtures + SIMPLE-23 dynamic five + five newly catalog-selected names, no hand-supplied URLs or share counts):

| Outcome | Count |
|---|---|
| Identity VERIFIED | 16/16 |
| Price VERIFIED (EOD) | 16/16 |
| TOTAL_OUTSTANDING VERIFIED | 9/16 |
| TOTAL_OUTSTANDING REFRESH_REQUIRED (count retained, CA unresolved) | 6/16 |
| TOTAL_OUTSTANDING UNAVAILABLE | 1/16 |
| Share document acquired | 15/16 |
| Market cap CALCULATED | 9/16 (only where shares VERIFIED) |
| DCF CALCULATED | 0/16 (existing gates unchanged) |

Both VERIFIED and REFRESH_REQUIRED / UNAVAILABLE are correct forensic outcomes. No share count was fabricated. Weighted-average / paid-up / promoter / diluted figures were not silently treated as outstanding.

**NO PRODUCTION DEPLOYMENT.** NSE MCP remains `COMMERCIAL_USE_PENDING`. OpenAI was not activated. No frontend work.

---

## BASELINE

Recorded before SIMPLE-24 edits, after SIMPLE-23 = PASS WITH LIMITATIONS. SIMPLE-23 was **not** redone.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `9030287e1808a471a3d8a48c238085093616bad3` |
| HEAD subject | SIMPLE-15-22: fail-closed official research through live universal NSE acquisition |
| SIMPLE-23 | `docs/releases/SIMPLE_23_UNIVERSAL_FILING_DETAIL_EXTRACTION_FORENSIC.md` — PASS WITH LIMITATIONS |
| SIMPLE-23 live | 11/11 identity + documents; 10/11 financials VERIFIED; shares **UNAVAILABLE**; DCF **BLOCKED** |
| Canonical path | `ResearchOrchestrator.analyse` → Security Master → ResearchPlan → NSE EOD + NSE primary → `acquire_primary_documents` (XBRL-first) → EvidenceJudge → VerifiedDataset |
| Pre-SIMPLE-24 gap | Financial XBRL rarely contains `NumberOfEquitySharesOutstanding`. NSE `issuedSize` has no as_of. Old shareholding URL 404'd. Paid-up ÷ face value was not wired. CA calendar was not fetched. `CURRENT_THROUGH` was collapsed onto `AS_OF`. |
| Production revision | **Not queried. Not changed.** |
| Production image | **Unchanged / not inspected.** |
| Production environment | **Not modified.** |
| Production feature flags | RESEARCH_MODE unchanged; RECOMMENDATION_MODE/SEBI locked; production OpenAI off; NSE MCP pending |

Working tree already contained uncommitted SIMPLE-23 production files (`xbrl.py`, acquisition/orchestrator/nse_primary wiring). SIMPLE-24 extended that path. Parking leftovers (`.bytecode_backup/`, nested tree, demo auth, `artifacts/`) were not committed and are not part of this forensic.

---

## ROOT CAUSE

Valuation could not establish TOTAL_OUTSTANDING because the live share path was pointed at the wrong artefacts and the wrong semantics.

1. **Wrong SHP index.** `/api/corporate-shareholding-pattern` returns **404**. The working index is `/api/corporate-share-holdings-master?index=equities&symbol={TICKER}`. Rows expose an SHP **XBRL URL**, not `totalNoOfShares`.
2. **Index ISIN is not identity.** The SHP master row can carry a **wrong ISIN** (INFY index row `IN9009A01011` vs equity `INE009A01021`). Identity is taken from SHP XBRL **ISIN facts**, not the index.
3. **Financial XBRL is usually paid-up, not outstanding.** INFY IND-AS has `PaidUpValueOfEquityShareCapital` and `FaceValueOfEquityShareCapital`, not `NumberOfEquitySharesOutstanding`. Deriving `paid-up / face value` is **PAID_UP / DERIVED**, never a silent TOTAL_OUTSTANDING.
4. **Quote-equity `issuedSize` has no as_of** and remains discovery-only (quote-equity itself is often HTTP 403).
5. **SHP XBRL repeats the same concept in category contexts.** `NumberOfFullyPaidUpEquityShares` in the promoter context is **PROMOTER_HOLDING**. Only the `ShareholdingPattern` context is TOTAL_OUTSTANDING.
6. **Currentness was not a CA horizon.** `CURRENT_THROUGH` was set equal to `AS_OF`. NSE CA calendar was not searched. A June SHP after a November buyback was therefore indistinguishable from a June SHP followed by an August ESOP allotment.
7. **Announcements alone over-match ESOP.** A grant of options is not an issuance. An allotment is. Unknown ESOP language stays fail-closed (`capital_changing=True` → REFRESH_REQUIRED, count not invented).

---

## SHARE-COUNT SOURCES

Approved hierarchy, unchanged:

| Tier | Sources | Role |
|---|---|---|
| 1A | NSE (SHP XBRL, CA calendar, announcements), BSE/SEBI/MCA/RBI/NSDL/CDSL | May verify |
| 1B | Company IR, annual reports, audited statements, official filings | May verify |
| 1C | Screener | Cross-check only (`may_verify = false`) |
| 2 | Yahoo, IBEF | Secondary research only |
| 3 | AI | Discovery / extraction / interpretation only. **Cannot write TOTAL_OUTSTANDING.** |

Live path used in this forensic:

| Source | Used | Notes |
|---|---|---|
| NSE SHP master + SHP XBRL | Yes | Primary TOTAL_OUTSTANDING candidate |
| NSE CA calendar `corporates-corporateActions` | Yes | Dividend/AGM dropped; capital events dated from ex/record date |
| NSE announcements | Yes | ESOP/buyback/bonus language; grant vs allotment |
| NSE financial-results XBRL | Supporting | Paid-up derivation only; not TOTAL_OUTSTANDING |
| NSE quote-equity | Discovery only | HTTP 403 in this session; `issuedSize` unlabeled as_of |
| Screener / Yahoo / AI | Not used to verify | |

No company-specific URL. No ticker branch. No hardcoded share count.

---

## XBRL CONCEPTS

Recorded, not assumed from the concept name alone.

### Shareholding-pattern instance (SEBI/BSE SHP taxonomy)

| Concept | Context | Semantic | Valuation |
|---|---|---|---|
| `NumberOfFullyPaidUpEquityShares` | `ShareholdingPattern_ContextI` | TOTAL_OUTSTANDING | May satisfy |
| `NumberOfFullyPaidUpEquityShares` | promoter / public / institution / non-promoter | PROMOTER_HOLDING / other | Reject |
| `NumberOfSharesOnFullyDilutedBasisIncludingWarrantsESOPAndConvertibleSecurities` | any | WEIGHTED_AVERAGE_DILUTED / POTENTIAL_EQUITY | Reject |
| `ISIN` fact | instance | Identity | Required match |
| Entity identifier | often BSE scrip code, **not ISIN** | Not identity | Ignored for ISIN match |

Locator retained: `ShareholdingPattern.NumberOfFullyPaidUpEquityShares`.

INFY live SHP (DateOfReport **2026-06-30**): **4,041,311,051** in the pattern-total context; promoter context **516,677,914** rejected.

### Financial instance (IND-AS)

| Concept | Unit | Semantic | Valuation |
|---|---|---|---|
| `NumberOfEquitySharesOutstanding` (when present) | shares | TOTAL_OUTSTANDING | May satisfy |
| `PaidUpValueOfEquityShareCapital` | INR | PAID_UP (amount) | Supporting |
| `FaceValueOfEquityShareCapital` | INRPerShare | face value | Supporting |
| paid-up ÷ face value (integer remainder ≤ 0.01, no partly-paid / DVR) | derived shares | **PAID_UP / DERIVED VALUE** | Cannot satisfy |
| Weighted-average / diluted EPS denominators | shares | WEIGHTED_AVERAGE_BASIC / WEIGHTED_AVERAGE_DILUTED | Reject |

Face-value unit matching uses `pershare` in the unit ident. `unit.kind==shares` is **not** used for face value (`INRPerShare` otherwise looks like a shares unit).

Taxonomy, concept, value, unit, period, entity, document, source, and semantic classification stay on the evidence row.

---

## ANNUAL REPORT EVIDENCE

SIMPLE-23 XBRL-first filing selection is reused. Annual-report PDFs remain the fallback when SHP XBRL is absent. Notes search for share-capital language already exists in the generic extractor; it cannot promote authorized / paid-up / weighted-average labels to TOTAL_OUTSTANDING.

Live TOTAL_OUTSTANDING in this session came from **SHP XBRL**, which is more recent than FY-end annual notes for the names that resolved. Annual-report notes were not required to invent a count.

---

## QUARTERLY EVIDENCE

SHP filings are quarterly (DateOfReport). They were **not** automatically preferred over annual financial XBRL. Ranking is:

1. Semantic class must be TOTAL_OUTSTANDING.
2. Identity (ISIN) must match.
3. Later unresolved capital-changing events between `AS_OF` and the research horizon force REFRESH_REQUIRED.
4. A newer SHP with matching identity replaces an older snapshot in the **append-only** store; the older row remains.

ABINFRA live used SHP `AS_OF=2026-03-31` (older than the June 2026 pattern used by most names) and still VERIFIED because subsequent CA review through **2026-09-11** found no unresolved share-count effect.

---

## SHAREHOLDING EVIDENCE

NSE SHP master JSON does **not** contain a trustworthy `totalNoOfShares` line item. Field names on the index are not accepted.

The engine follows `xbrl` to the SHP instance, classifies `NumberOfFullyPaidUpEquityShares` by **context**, and binds identity from ISIN **facts**. Index ISIN is dropped when it disagrees with the listing ISIN.

`WhetherTheListedEntityHasIssuedAnyPartlyPaidUpShares = false` was observed on INFY; partly-paid true blocks paid-up derivation.

---

## SEMANTIC CLASSIFICATION

Every candidate is classified explicitly. Categories are not collapsed.

```text
TOTAL_OUTSTANDING
ISSUED
SUBSCRIBED
PAID_UP
AUTHORIZED
LISTED
FREE_FLOAT
PROMOTER_HOLDING
WEIGHTED_AVERAGE_BASIC
WEIGHTED_AVERAGE_DILUTED
POTENTIAL_EQUITY
TREASURY/CANCELLED
UNKNOWN
```

**Acceptance rule:** only `TOTAL_OUTSTANDING` may satisfy the valuation share prerequisite.

Aliases retained for older locators (`WEIGHTED_AVERAGE_EPS` → `WEIGHTED_AVERAGE_BASIC`, `POTENTIAL_DILUTED` → `POTENTIAL_EQUITY`, `PROMOTER` → `PROMOTER_HOLDING`). Quote-equity `info.issuedSize` remains **ISSUED**.

---

## PAID-UP CAPITAL DERIVATION

Where financial XBRL provides paid-up equity share capital **and** face value per equity share, and flags do not show partly-paid shares or DVR:

```text
share_count = paid_up_equity_share_capital / face_value_per_share
```

Accepted only as **DERIVED VALUE / PAID_UP**. Locator:

`derived:PaidUpValueOfEquityShareCapital/FaceValueOfEquityShareCapital`

INFY FY24 example: 20,710,000,000 INR ÷ 5 INRPerShare = 4,142,000,000 **PAID_UP**, which is **not** the SHP TOTAL_OUTSTANDING 4,041,311,051 (buyback already reduced the later SHP). Blindly using paid-up as outstanding would have been a CV-001 violation.

Derivation is skipped when remainder is non-integral, partly-paid is true, or DVR is true.

---

## CORPORATE-ACTION DISCOVERY

Automatic, per listing:

| Endpoint | Role |
|---|---|
| `https://www.nseindia.com/api/corporates-corporateActions?index=equities&symbol={TICKER}` | Dated capital calendar (ex-date / record date / broadcast) |
| NSE announcements JSON | Narrative CA titles; ESOP grant vs allotment |
| Filing-detail text | `attack_corporate_actions` on acquired documents |

Successful CA-calendar fetch now sets `announcements_searched=True` even if the announcements endpoint fails, so `ca_checked_through` becomes the research day rather than remaining unknown.

Dividend and AGM subjects are **not** capital events.

INFY live calendar+announcements produced 232 dated events; only events **after** SHP `AS_OF` with `capital_changing=True` affect currentness. The blocking later event was **ESOP 2026-08-24** (allotment-class language). The Nov-2025 buyback is **before** 2026-06-30 and is already in the SHP count.

---

## CORPORATE-ACTION CLASSIFICATION

Every event becomes one of:

```text
NO_SHARE_COUNT_EFFECT
INCREASES_OUTSTANDING
DECREASES_OUTSTANDING
POTENTIALLY_CHANGES_OUTSTANDING
UNKNOWN
```

via `classify_share_count_effect_status`. The engine does **not** treat every announcement as share-count-changing.

| Type | Default effect | Notes |
|---|---|---|
| Dividend / AGM | not an event | Dropped |
| Bonus / split / rights / QIP / FPO / preferential / new issue | INCREASES_OUTSTANDING | Only after effective/allotment date |
| Buyback / cancellation / extinguishment / capital reduction | DECREASES_OUTSTANDING or UNKNOWN | Announcement ≠ extinguishment |
| ESOP grant | NO_SHARE_COUNT_EFFECT (`capital_changing=False`) | Options are not shares |
| ESOP allotment / unknown ESOP | INCREASES / fail-closed | Count not invented; currentness REFRESH_REQUIRED |
| Cash acquisition | NO_SHARE_COUNT_EFFECT | |
| Stock / mixed / unknown acquisition | POTENTIALLY_CHANGES_OUTSTANDING | |
| Merger / demerger / scheme / share swap | POTENTIALLY_CHANGES_OUTSTANDING | Announced scheme is not applied |

---

## BUYBACK ANALYSIS

Stages distinguished:

| Stage | Share-count action |
|---|---|
| Announcement / approval / tender | Do **not** reduce the count. `capital_changing=True` so a later announcement after `AS_OF` yields REFRESH_REQUIRED. |
| Shares extinguished / cancelled / capital reduction | DECREASES_OUTSTANDING. Still no arithmetic on the SHP snapshot; currentness REFRESH_REQUIRED until a later verified snapshot. |

INFY buyback ex-date **14-Nov-2025** is before SHP **2026-06-30**, so it does not stale that snapshot. Extinguishment titles in 2025 are likewise already inside the June SHP.

Negative test: buyback after `AS_OF` → REFRESH_REQUIRED. Count unchanged.

---

## BONUS/SPLIT ANALYSIS

Calendar rows with bonus/split subjects are dated from **ex-date** (else record date). An announcement without an effective date is not applied as a ratio transform. No old/new share arithmetic is invented.

If a bonus/split is effective after the SHP `AS_OF` and on or before the research horizon → REFRESH_REQUIRED.

---

## RIGHTS/QIP/PREFERENTIAL/ESOP ANALYSIS

Only the completed issuance stage may change current outstanding. The engine does not add an allotment quantity onto the SHP total.

- Grant of options: not capital-changing.
- Allotment / listing of equity under ESOP: capital-changing → REFRESH_REQUIRED after `AS_OF`.
- Bare “ESOP” subject: fail-closed capital-changing.

This is why INFY, HDFCBANK, AADHARHFC, 3IINFOLTD, ABFRL, and 360ONE are REFRESH_REQUIRED in this session despite having a verified SHP fact: a later ESOP-class event exists and the next SHP is not yet available.

---

## MERGER/DEMERGER/SHARE-SWAP ANALYSIS

Scheme status, effective date, exchange ratio, and resulting identity are **not** applied as a new count. An unresolved scheme after `AS_OF` is POTENTIALLY_CHANGES_OUTSTANDING / REFRESH_REQUIRED. Cash acquisitions remain NO_SHARE_COUNT_EFFECT.

---

## CURRENTNESS ENGINE

Currentness is:

```text
Latest authoritative share evidence
+ all subsequent relevant corporate actions checked
+ share-count effects resolved
+ identity verified
+ no unresolved conflict
```

Result: `CURRENT` / `VERIFIED`, or `REFRESH_REQUIRED`, or `CONFLICT`, or `UNKNOWN`.

`ca_checked_through` is the research day when the NSE CA calendar (or announcements) was actually searched. `judge_currentness` still requires that horizon to cover the research date. Later `capital_changing` events between `AS_OF` and the horizon force REFRESH_REQUIRED **without deleting the snapshot**.

Live proof that `AS_OF` ≠ `CURRENT_THROUGH` ≠ `RETRIEVED_AT`:

| Field | TCS live | INFY live |
|---|---|---|
| OUTSTANDING_SHARES | 3,618,087,518 VERIFIED | 4,041,311,051 retained |
| AS_OF | 2026-06-30 | 2026-06-30 |
| CURRENT_THROUGH | 2026-09-11 | 2026-09-11 |
| CA status | VERIFIED | REFRESH_REQUIRED (ESOP 2026-08-24) |

---

## HISTORICAL SNAPSHOTS

`ShareRecordStore` is append-only, keyed by ISIN+MIC. `EvidenceJudge` now `put`s every share snapshot (VERIFIED or REFRESH_REQUIRED) and exposes `VerifiedDataset.share_history`.

```text
Snapshot A  (older SHP)
    ↓
Bonus / buyback / ESOP  (classified, not arithmetic)
    ↓
Snapshot B  (newer SHP)
```

A newer candidate never overwrites the previous row. Same `AS_OF` + different count → CONFLICT (no average, no AI pick).

In-memory store only in this forensic (no production database mutation).

---

## CONFLICT HANDLING

Two primary SHP values that differ after normalization → `TRUE_CONFLICT`. The judge refuses a silent pick. Tests assert the values are not averaged.

Unresolved period / class / CA differences stay CONFLICT or REFRESH_REQUIRED.

---

## EVIDENCE PROVENANCE

Accepted candidates retain:

source, URL, document ID/hash, document date, retrieval time, page/note/XBRL locator, ISIN, MIC, period, share semantic, corporate-action status, derived-vs-fact label, confidence, judge result.

Share snapshot fields:

```text
OUTSTANDING_SHARES
AS_OF
CURRENT_THROUGH
RETRIEVED_AT  (last_verified_at)
SOURCE
SOURCE_URL
EVIDENCE_ID
CORPORATE_ACTION_STATUS
ca_checked_through
semantic_type
integrity_hash
```

`field_urls["shares_outstanding"]` points at the SHP XBRL, not the financial XBRL, when both were acquired.

---

## AI STATUS

OpenAI remains optional and was **not** activated.

AI may locate documents, classify language, and cross-check. AI may **not** write TOTAL_OUTSTANDING, override EvidenceJudge, invent shares, infer undocumented CAs, or alter historical snapshots.

Negative test: `source_type=llm` share claim → not VERIFIED (`UNAVAILABLE` / `REJECTED` / `UNKNOWN`). Prompt-injection text inside an SHP instance cannot override the XBRL fact (INFY fixture stays 4,041,311,051).

NSE MCP remains `COMMERCIAL_USE_PENDING`.

---

## AUTOMATICITY

Per security:

```text
discover → retrieve → extract → classify → check CA → determine currentness → judge
```

No human intervention. No company-specific URL. No company-specific parser. No hardcoded share count. No hardcoded CA. Architecture test forbids `if ticker ==` and fixture ticker tokens in the production share path (`xbrl.py`, `acquisition.py`, `orchestrator.py`, `nse_primary.py`, `field_acquisition.py`, `end_to_end.py`).

Dynamic names were selected from the Security Master catalog (eligible XNSE equity), not by hand: **APOORVA, ADROITINFO, ABINFRA, ADFFOODS, 360ONE**.

---

## SECURITY COVERAGE

| Kind | Names in this run |
|---|---|
| Ordinary non-financial equity | TCS, INFY, RELIANCE, WIPRO, 20MICRONS, A2ZINFRA, ABFRL, ADROITINFO, ABINFRA, ADFFOODS, APOORVA, 21STCENMGM, 3IINFOLTD |
| Bank equity | HDFCBANK (PARTIAL financials from SIMPLE-23 banking XBRL dialect; shares REFRESH_REQUIRED) |
| Financial company | AADHARHFC, 360ONE |
| Recent CA | INFY (buyback 2025 + later ESOP); several ESOP-allotment REFRESH_REQUIRED names |
| Complex / smaller capital | 20MICRONS, 21STCENMGM, A2ZINFRA |

Unsupported security types were not forced.

---

## LIVE COVERAGE MATRIX

Mode **LIVE**. Production **false**. No hand-supplied documents or counts.

| Security | Identity | Price | Financials | Shares | CA | Market cap | DCF | Share document | Count | AS_OF | CURRENT_THROUGH |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TCS | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 3618087518 | 2026-06-30 | 2026-09-11 |
| INFY | VERIFIED | VERIFIED | VERIFIED | REFRESH_REQUIRED | REFRESH_REQUIRED | BLOCKED | BLOCKED | YES | 4041311051 | 2026-06-30 | 2026-09-11 |
| RELIANCE | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 13303071854 | 2026-06-30 | 2026-09-11 |
| HDFCBANK | VERIFIED | VERIFIED | PARTIAL | REFRESH_REQUIRED | REFRESH_REQUIRED | BLOCKED | BLOCKED | YES | 13350313106 | 2026-06-30 | 2026-09-11 |
| WIPRO | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 9676974515 | 2026-06-30 | 2026-09-11 |
| 20MICRONS | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 35286502 | 2026-06-30 | 2026-09-11 |
| AADHARHFC | VERIFIED | VERIFIED | VERIFIED | REFRESH_REQUIRED | REFRESH_REQUIRED | BLOCKED | BLOCKED | YES | 437337117 | 2026-06-30 | 2026-09-11 |
| 3IINFOLTD | VERIFIED | VERIFIED | VERIFIED | REFRESH_REQUIRED | REFRESH_REQUIRED | BLOCKED | BLOCKED | YES | 207403767 | 2026-06-30 | 2026-09-11 |
| A2ZINFRA | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 177522358 | 2026-06-30 | 2026-09-11 |
| ABFRL | VERIFIED | VERIFIED | VERIFIED | REFRESH_REQUIRED | REFRESH_REQUIRED | BLOCKED | BLOCKED | YES | 1220538192 | 2026-06-30 | 2026-09-11 |
| 21STCENMGM | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 10500000 | 2026-06-30 | 2026-09-11 |
| APOORVA | VERIFIED | VERIFIED | UNKNOWN | **UNAVAILABLE** | UNKNOWN | BLOCKED | BLOCKED | NO | — | — | — |
| ADROITINFO | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 54628520 | 2026-06-30 | 2026-09-11 |
| ABINFRA | VERIFIED | VERIFIED | UNKNOWN | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 638789360 | 2026-03-31 | 2026-09-11 |
| ADFFOODS | VERIFIED | VERIFIED | VERIFIED | **VERIFIED** | VERIFIED | **VERIFIED** | BLOCKED | YES | 109863595 | 2026-06-30 | 2026-09-11 |
| 360ONE | VERIFIED | VERIFIED | VERIFIED | REFRESH_REQUIRED | REFRESH_REQUIRED | BLOCKED | BLOCKED | YES | 406685017 | 2026-06-30 | 2026-09-11 |

New catalog-selected set: APOORVA, ADROITINFO, ABINFRA, ADFFOODS, 360ONE.

APOORVA correctly returned UNAVAILABLE (no SHP/filing share evidence). That is not a parser hole to paper over with a guessed count.

---

## NEGATIVE TESTS

| Case | Result |
|---|---|
| Weighted-average / diluted / potential / free-float / authorized / promoter | ≠ TOTAL_OUTSTANDING; cannot feed valuation |
| `info.issuedSize` | ISSUED, not outstanding |
| Wrong ISIN on SHP XBRL | identity_ok false; no fields |
| Paid-up ÷ face value | PAID_UP derived; not TOTAL_OUTSTANDING |
| Buyback after AS_OF | REFRESH_REQUIRED; count not reduced |
| Bonus / merger announced, not applied as a new count | no invented shares |
| Cash acquisition | NO_SHARE_COUNT_EFFECT |
| Stock / mixed acquisition | POTENTIALLY_CHANGES_OUTSTANDING |
| ESOP grant | not capital-changing |
| ESOP allotment | capital-changing / REFRESH_REQUIRED |
| Conflicting primary SHP values | CONFLICT; not averaged |
| Empty / malformed XBRL | no share field |
| PDF bytes as XBRL | no share field |
| Prompt injection in SHP XML | fact unchanged (4041311051) |
| AI llm share claim | not VERIFIED |
| Frontend / browser | skipped (parked) |

Expected fail-closed vocabulary: REJECTED / UNKNOWN / REFRESH_REQUIRED / CONFLICT / UNAVAILABLE.

---

## MARKET-CAP GATE

Market cap is calculated only when:

```text
VERIFIED PRICE  ×  VERIFIED TOTAL_OUTSTANDING
```

and `derived_market_cap_input_status` finds no unresolved capital-changing event between the price date and the share CA horizon.

Never calculated from weighted-average shares. REFRESH_REQUIRED shares → not CALCULATED (STALE_INPUT / BLOCKED). CONFLICT → CONFLICT_INPUT.

Live: **9/16 CALCULATED**, exactly the nine VERIFIED share rows. The six REFRESH_REQUIRED rows and APOORVA did not receive a market cap.

---

## DCF GATE

Existing DCF gates were **not** weakened.

DCF still requires the prior CFO / capex / assumption bundle (`dsp_gate`). Verified shares are necessary for per-share IV, not sufficient for DCF.

Live: **0/16 DCF CALCULATED**. `analysis_state` is `DCF_BLOCKED` or `REFRESH_REQUIRED`. That is correct. SIMPLE-24 does not unlock DCF by relaxing shares.

---

## PERFORMANCE

Full LIVE `analyse()` over 16 names (one shared EOD bundle):

| Metric | Seconds |
|---|---|
| p50 | 4.55 |
| p95 | 96.57 |
| wall (16 names) | 170.73 |

p95 is dominated by one slow acquisition (APOORVA had no SHP and fell through IR/filing miss). No optimisation pass: the bottleneck is missing evidence, not a hot loop.

Stage intent (not separately instrumented in this run): SHP index discover, SHP XBRL retrieve/extract, financial XBRL, CA calendar, EvidenceJudge. Offline unit tests remain ~milliseconds.

---

## SECURITY

Source allowlist unchanged. Secrets not printed. AI cannot verify. Document sanitizer remains. NSE MCP not production-activated. No production database writes. No production secrets. Prompt injection in SHP XML cannot override facts.

---

## REGRESSION

Offline (`not network`), SIMPLE-14N-E … SIMPLE-24 + nse_primary + 14N-acquisition:

**205 passed, 4 skipped, 6 deselected, 0 failed, 0 xfail.**

| Suite | Result |
|---|---|
| SIMPLE-14N-E | 16 passed |
| SIMPLE-14N-F | 17 passed |
| SIMPLE-14N-acquisition | 34 passed |
| SIMPLE-15 | 12 passed |
| SIMPLE-16 | 19 passed |
| SIMPLE-17 | 10 passed (taxonomy aliases updated to SIMPLE-24 names; rejection unchanged) |
| SIMPLE-18 | 10 passed (weighted-average still BLOCKS DCF per-share) |
| SIMPLE-19 | 10 passed |
| SIMPLE-19A | 9 passed |
| SIMPLE-20 | 9 passed |
| SIMPLE-21 | 10 passed, 1 skipped (browser) |
| SIMPLE-22 | 9 passed, 1 skipped (browser) |
| SIMPLE-23 | 13 passed, 1 skipped (frontend parked) |
| SIMPLE-24 | 17 passed, 1 skipped (frontend parked) |
| nse_primary | 10 passed |

Live:

| Test | Result |
|---|---|
| SIMPLE-23 network | 1 passed |
| SIMPLE-24 16-name network | 1 passed |

New failures in this suite: **0**. Pre-existing failures in this suite: **0**.

SIMPLE-17/18 assertion text now expects `WEIGHTED_AVERAGE_BASIC` / `POTENTIAL_EQUITY` (SIMPLE-24 taxonomy). Those values still cannot feed market cap or DCF.

Frontend suites: **not executed** (parked).

---

## FILES CHANGED

### Production (SIMPLE-24 increment on the uncommitted SIMPLE-23 tree)

- `packages/data_engine/src/data_engine/official_research/nse_primary.py` — SHP master URL; CA calendar; SHP document parse (drop disagreeing index ISIN); ESOP grant vs allotment; calendar search sets currentness horizon
- `packages/data_engine/src/data_engine/official_research/xbrl.py` — SHP XBRL total vs category; paid-up derivation labeled PAID_UP; ISIN facts for identity
- `packages/data_engine/src/data_engine/official_research/extraction.py` — SIMPLE-24 share taxonomy; `esop_changes_outstanding`; unresolved scheme currentness without inventing a count
- `packages/data_engine/src/data_engine/official_research/acquisition.py` — SHP kind vs financial XBRL; `field_urls` provenance
- `packages/data_engine/src/data_engine/official_research/orchestrator.py` — `ca_checked_through` from searched CA; per-field source URL/hash
- `packages/data_engine/src/data_engine/official_research/field_acquisition.py` — `CURRENT_THROUGH` = CA horizon, not `AS_OF`
- `packages/data_engine/src/data_engine/official_research/judge.py` — append-only `ShareRecordStore`; `share_history` on dataset
- `packages/data_engine/src/data_engine/official_research/verified_dataset.py` — `share_history` public dict
- SIMPLE-23 files remain in the tree (`annual_report.py`, `documents.py`, `pdf_text.py`) and were not redesigned

### Tests / docs

- `packages/data_engine/tests/test_simple24.py` — **new**
- `packages/data_engine/tests/test_simple23.py` — SIMPLE-23 (uncommitted; not redone)
- `packages/data_engine/tests/test_simple17.py` / `test_simple18.py` — taxonomy aliases
- `packages/data_engine/tests/test_nse_primary.py` — SHP URL constant
- `docs/releases/SIMPLE_23_UNIVERSAL_FILING_DETAIL_EXTRACTION_FORENSIC.md` — prior forensic (uncommitted)
- `docs/releases/SIMPLE_24_UNIVERSAL_TOTAL_OUTSTANDING_SHARES_FORENSIC.md` — this report

### Not changed

Frontend, production flags, NSE MCP, OpenAI, databases, ticker-specific parsers.

---

## PRODUCTION IMPACT

**None.** `production=False` on every live run. No deployment. No flag change. No provider activation. No production AI. No NSE MCP production activation. No production database mutation.

---

## LIMITATIONS

1. VERIFIED TOTAL_OUTSTANDING is not available for every NSE equity. Missing SHP (APOORVA) → UNAVAILABLE. Later unresolved ESOP/allotment → REFRESH_REQUIRED. Both are specified success modes.
2. ESOP allotment quantity is not applied as arithmetic. The next SHP is required to re-verify.
3. Quote-equity remains 403; `issuedSize` cannot verify.
4. HDFCBANK financials remain PARTIAL (SIMPLE-23 banking XBRL dialect). No bank-specific parser was added.
5. Share history is in-process only.
6. DCF remains blocked on capex / verified assumptions even when shares and market cap are VERIFIED.
7. Annual-report note extraction is generic; live outstanding in this session came from SHP XBRL.
8. p95 latency on a name with no SHP is high; not optimised.

---

## DECISION

**PASS WITH LIMITATIONS.**

The universal share engine is proven:

- TOTAL_OUTSTANDING is discovered automatically where SHP XBRL evidence exists (9/16 VERIFIED in this session).
- Invalid semantics are rejected.
- XBRL contexts are classified; promoter/diluted/paid-up cannot silently become outstanding.
- Paid-up derivation is DERIVED / PAID_UP only.
- Corporate actions are discovered and classified.
- Currentness is deterministic (`AS_OF` ≠ `CURRENT_THROUGH`).
- Historical snapshots are append-only.
- Conflicts fail closed.
- Market cap requires verified price × verified TOTAL_OUTSTANDING.
- DCF gates are unchanged.
- Fixed + two dynamic sets tested. No company-specific production branches. No fabricated shares. Regression green.

Not CLOSED: some names legitimately lack a current verified count (`UNKNOWN` / `REFRESH_REQUIRED` / `UNAVAILABLE`). Closing would require pretending those are VERIFIED.

---

## NEXT FORENSIC

**SIMPLE-25 — remaining DCF blockers after shares.**

Now that TOTAL_OUTSTANDING can be established (or honestly refused) for the supported NSE equity path, DCF is still BLOCKED on the **existing** gates: verified capex, verified discount/growth assumptions, and (for some names) complete financials (HDFCBANK PARTIAL) or missing filings (APOORVA).

Do not weaken DCF. Do not invent ESOP increments. Do not treat REFRESH_REQUIRED shares as VERIFIED to force market cap.

Optional follow-ons, not this close:

- SHP miss forensics (why APOORVA had no share document)
- ESOP allotment **filings** as a later verified snapshot (still no arithmetic on the previous SHP)
- Persist `ShareRecordStore` beyond process memory (still no production DB in that forensic unless explicitly scoped)

FORENSIC → FIND → PROVE → FIX → TEST → VERIFY → CLOSE → NEXT.
