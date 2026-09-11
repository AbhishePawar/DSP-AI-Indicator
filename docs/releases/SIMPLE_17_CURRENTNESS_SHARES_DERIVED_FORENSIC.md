# SIMPLE-17 — Currentness, Outstanding Shares & Derived-Field Judge Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED. Currentness, share semantics, corporate-action horizon, stored/new share records, and derived DSP fields (market cap, net debt, EV, FCF) are deterministic and fail closed. Live OpenAI/NSE were not required and were not fabricated. The existing acquisition path still treats “no known CA events” as PASS for 14N-F compatibility; the new `judge_currentness` API requires an explicit CA horizon.

**NO PRODUCTION DEPLOYMENT**

## BASELINE

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| Working tree | SIMPLE-15 + SIMPLE-16 uncommitted, plus parking leftovers |
| SIMPLE-16 report | `docs/releases/SIMPLE_16_EVIDENCE_RECONCILIATION_FORENSIC.md` |
| Focused regression before edits | **120 passed** (14N-E 16, 14N-F 17, SIMPLE-15 12, SIMPLE-16 19, EvidenceJudge 29, NSE MCP 22, OpenAI Responses 5) |

Inspected, not replaced:

| Surface | Location | SIMPLE-17 action |
|---|---|---|
| EvidenceJudge | `judge.py` | Additive `derive_fields`; derived names cannot verify |
| FieldPolicy matrix | `source_policy.py` | Reused (`market_cap`/`fcf`/`EV` remain derived) |
| ResearchPlan | `research_plan.py` | Reused |
| Share labels | `extraction.classify_share_semantic_type` | Preserved; canonical mapping added |
| Corporate actions | `classify_capital_effect` / `CapitalEvent` | Preserved; impact classes added |
| PriceSnapshot | `models.py` | Reused; kinds not rewritten |
| Financial contracts | `verified_dataset.py` | Additive snapshot hash/horizon fields |
| Existing FCF | financial `FORMULA_FCF` = CFO − \|capex\| | Reused, not reinvented |
| Existing net debt | financial `FORMULA_NET_DEBT` = total_debt − cash | Reused |
| Existing market cap | `verified_evidence.py` price × shares | Reused |

Existing work was not discarded.

## CURRENTNESS JUDGE

`judge_currentness` in `currentness.py`.

Inputs: field, as_of, retrieved_at, document_date, current_through, last_verified_at, freshness policy, CA status, events, required analysis date, price kind, `ca_checked_through`, `research_horizon`.

Output: **CURRENT** · **REFRESH_REQUIRED** · **UNKNOWN** · **CONFLICT**

A recent `retrieved_at` does not make a fact current. `evaluate_freshness` STALE maps to REFRESH_REQUIRED.

## FIELD FRESHNESS POLICIES

| Field class | Policy |
|---|---|
| PRICE CURRENT/DELAYED | Research window; delay/kind preserved |
| EOD | Latest required trading date |
| PREVIOUS_CLOSE / HISTORICAL | Never rewritten as live/EOD (`UNKNOWN` for current last_price) |
| FINANCIALS | Required reporting period; a valid annual statement is not rejected because it is not today’s document |
| SHARES | Authoritative TOTAL_OUTSTANDING + as_of + identity + CA horizon through the research date |

## SHARE SEMANTIC JUDGE

One canonical mapping over the existing classifier:

| Candidate | Valuation class |
|---|---|
| Outstanding equity shares | **TOTAL_OUTSTANDING** |
| Issued (not outstanding) | ISSUED |
| Paid-up capital | PAID_UP |
| Listed quantity | LISTED |
| Free float | FREE_FLOAT |
| Promoter holding | PROMOTER |
| Weighted-average / EPS denominator | **WEIGHTED_AVERAGE_EPS** |
| Potential / dilutive equity | **POTENTIAL_DILUTED** |
| Authorized | AUTHORIZED |
| Other / unlabeled | UNKNOWN |

Only **TOTAL_OUTSTANDING** may feed basic market cap. `classify_share_semantic_type` still returns `WEIGHTED_AVERAGE` for 14N-F.

Red flags (10476247846 weighted-average; 70490586 potential equity; free float; paid-up in crore) → REJECTED / UNKNOWN, never VERIFIED outstanding.

Shares are not estimated, not extrapolated, and not reverse-engineered from market cap (`cannot_derive_shares("market_cap")`).

## SHARE CURRENTNESS

`validate_outstanding_shares` requires: identity, primary authority, TOTAL_OUTSTANDING, as_of, numeric > 0, non-money units, CA horizon, no unresolved share-changing event, no AI source.

Failure → UNKNOWN / REFRESH_REQUIRED / CONFLICT / REJECTED.

## CORPORATE-ACTION HORIZON

`corporate_action_horizon_status(as_of, checked_through, research_horizon)`.

Example: shares as_of 2026-03-31, research horizon 2026-09-11, CA checked only through 2026-06-30 → **REFRESH_REQUIRED**. The horizon is never silently extended.

Impact classes: NO_SHARE_COUNT_CHANGE · SHARE_COUNT_INCREASE · SHARE_COUNT_DECREASE · POTENTIAL_CHANGE · UNKNOWN · NOT_APPLICABLE.

Acquisition: CASH → NO_SHARE_COUNT_CHANGE; SHARE_SWAP / MIXED → POTENTIAL_CHANGE until a post-deal count is verified. Acquisition is not assumed to issue shares.

## STORED VS NEW SHARE RECORD

`ShareRecordStore` is append-only (ISIN+MIC). History is preserved.

Compare: MATCH · NEWER_VALID_RECORD · CONFLICT · STALE_STORED · STALE_NEW · UNKNOWN.

Integrity hash: ISIN + MIC + shares + as_of + source + document hash.

No silent overwrite.

## DERIVED FIELD ENGINE

`derive_dsp_fields(VerifiedDataset)` in `derived_fields.py`.

Pipeline remains:

RAW → RECONCILED → VERIFIED_DATASET → **DERIVED_DATA**

Derived data is never source evidence (`is_source_evidence: false`). Promoting `market_cap` / `enterprise_value` / `fcf` / `net_debt` evidence stays UNAVAILABLE.

Statuses: CALCULATED · BLOCKED · UNKNOWN · STALE_INPUT · CONFLICT_INPUT · CALCULATION_BLOCKED.

A numeric value is never returned with an unresolved input.

## MARKET CAP

Canonical formula (existing composition):

**verified EOD/realtime/delayed price × verified TOTAL_OUTSTANDING**

If shares are UNKNOWN, WA, free float, listed, diluted, or stale → BLOCKED / STALE_INPUT.

PREVIOUS_CLOSE cannot feed current market cap.

Price and shares may differ in calendar date only when the share CA horizon covers the price date and no capital-changing event sits between them (`derived_market_cap_input_status`). The older `market_cap_status` used by valuation_gate is unchanged.

## NET DEBT

Existing DSP: **total_debt − cash** (`FORMULA_NET_DEBT`).

Debt is the verified `debt` field (total borrowings). Leases, trade payables, and other liabilities are not substituted. Missing debt or missing cash → BLOCKED (zero is not invented).

## ENTERPRISE VALUE

**market_cap + net_debt** = market_cap + debt − cash.

Requires calculated market cap and calculated net debt. Missing debt or cash → EV BLOCKED.

## FCF

Existing DSP `FORMULA_FCF`: **operating_cash_flow − abs(capex)**.

Missing CFO or capex → BLOCKED. Capex is not inferred. FY2025 CFO + FY2026 capex → CALCULATION_BLOCKED.

## DERIVED PROVENANCE

Every result records: derived_field, formula_version, formula, input_fields, input_evidence_ids, calculated_at, calculation_status, is_source_evidence=false.

Example: MARKET_CAP inputs price + shares, formula `price * shares_outstanding`, version `official_research.derived.market_cap.v1`.

Circular paths are refused: market_cap cannot establish shares; derived rows cannot be verified as primary.

## CURRENCY / UNIT SAFETY

Price currency must match listing currency. Financial unit_scale must normalize (actual / lakh / crore / million / thousand). Unknown units → CALCULATION_BLOCKED. No guessing.

## PERIOD SAFETY

Debt vs cash and CFO vs capex must share a comparable period (`canonicalize_period` / `periods_comparable`). Mixed FY years → CALCULATION_BLOCKED.

## STALE INPUT PROPAGATION

| Input | Derived |
|---|---|
| price REFRESH_REQUIRED | market_cap STALE_INPUT, value None |
| shares REFRESH_REQUIRED | market_cap STALE_INPUT, value None |
| debt UNKNOWN | EV BLOCKED |
| cash UNKNOWN | EV BLOCKED |
| price CONFLICT | market_cap CONFLICT_INPUT |

Blocked calculations are not downgraded to approximations.

## UNIVERSAL SECURITY TEST

Same engine on TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS, plus one dynamically discovered eligible XNSE equity. No ticker/company/ISIN branches in engine files.

## SECURITY-TYPE TEST

Ordinary equity and bank equity (HDFCBANK) use the same share/currentness validators. ETF / unsupported types still return `UNSUPPORTED_SECURITY_TYPE` from the canonical judge and are not forced through ordinary-equity market cap.

## ADVERSARIAL TESTS

| Case | Result |
|---|---|
| A. Old share count, CA checked only to 2026-06-30 | REFRESH_REQUIRED |
| B. Authoritative count + CA through 2026-09-11 | CURRENT / VERIFIED |
| C. Weighted-average 10,476,247,846 | REJECTED / UNKNOWN |
| D. Potential diluted 70,490,586 | REJECTED / UNKNOWN |
| E. Free float | REJECTED / UNKNOWN |
| F. Buyback after stored count | REFRESH_REQUIRED |
| G. Bonus | REFRESH_REQUIRED until new count |
| H. Split | SHARE_COUNT_INCREASE; not silently applied |
| I. Cash acquisition | NO_SHARE_COUNT_CHANGE |
| J. Share-swap acquisition | POTENTIAL_CHANGE |
| K. Price stale | market_cap STALE_INPUT, value None |
| L. Shares stale | market_cap STALE_INPUT, value None |
| M. Missing debt | EV BLOCKED |
| N. Missing cash | EV BLOCKED |
| O. Unknown unit | CALCULATION_BLOCKED |
| P. Period mismatch | CALCULATION_BLOCKED |

## INVARIANTS

1. Only TOTAL_OUTSTANDING feeds basic market cap.
2. Derived values cannot establish primary inputs.
3. Stale inputs cannot produce current derived numbers.
4. UNKNOWN inputs are not treated as zero.
5. Conflicting inputs cannot produce numeric derived values.
6. AI claims cannot establish shares.
7. Corporate actions affect share currentness when capital-changing.
8. Historical share snapshots are preserved (append-only store).
9. CA horizon is explicit.
10. Price kinds remain intact (EOD ≠ previous close).
11. Currency/unit mismatch blocks calculation.
12. Period mismatch blocks calculation.
13. No ticker-specific share logic.
14. No ticker-specific derived-field logic.

## PERFORMANCE

24 mock repetitions:

| Step | p50 | p95 |
|---|---|---|
| currentness | 0.002 ms | 0.008 ms |
| share semantic | 0.006 ms | 0.010 ms |
| corporate-action class | <0.002 ms | <0.002 ms |
| derived calculation | 0.034 ms | 0.043 ms |

Largest contributor: **derived calculation**. Not optimized.

## SECURITY

Evidence and AI output remain untrusted. Injection text cannot rewrite source policy, verification rules, or formulas. No secrets in evidence, traces, logs, reports, or Git. NSE MCP commercial status unchanged.

## TEST RESULTS

| Suite | Result |
|---|---|
| SIMPLE-17 | **10 passed** |
| SIMPLE-16 | **19 passed** |
| SIMPLE-15 | **12 passed** |
| SIMPLE-14N-E | **16 passed** |
| SIMPLE-14N-F | **17 passed** |
| EvidenceJudge | **29 passed** |
| NSE MCP OpenAI | **22 passed** |
| OpenAI Responses | **5 passed** |
| Failed / skipped / xfail | **0 / 0 / 0** |

Combined focused run: **130 passed**.

No pre-existing failures were hidden. Live provider tests were not enabled.

## FILES CHANGED

| File | Role |
|---|---|
| `currentness.py` | `judge_currentness`, CA horizon, derived market-cap date rule |
| `extraction.py` | Canonical share semantics, share-count impact |
| `share_records.py` | Append-only snapshots, validate outstanding, stored vs new |
| `derived_fields.py` | Market cap, net debt, EV, FCF + provenance |
| `verified_dataset.py` | integrity_hash, evidence_ids, ca_checked_through |
| `judge.py` | `derive_fields`; derived names cannot verify |
| `official_research/__init__.py` | Exports |
| `tests/test_simple17.py` | Adversarial, universal, invariants |
| `docs/releases/SIMPLE_17_CURRENTNESS_SHARES_DERIVED_FORENSIC.md` | This report |

## PRODUCTION IMPACT

**NO PRODUCTION DEPLOYMENT**

No `/api/v1/analyse` change. No production provider activation. No frontend changes. No production valuation formula change. MOCK still cannot enter production.

## COMMERCIAL STATUS

NSE MCP:

**COMMERCIAL_USE_PENDING**

Unchanged.

## LIMITATIONS

1. Live OpenAI / live NSE MCP were not executed.
2. Acquisition’s older “no known events → PASS” path is unchanged so 14N-F stays green. Explicit horizon lives on `judge_currentness` / `validate_outstanding_shares`.
3. `FinancialSnapshotVerified` has no EBITDA line; EV/EBITDA stays BLOCKED until that primitive exists.
4. Optional ratios (FCF yield, EV/EBIT, P/E) calculate only when every input is already CALCULATED/VERIFIED.
5. Derived fields are not written into `/api/v1/analyse` payloads.

## DECISION

Currentness is not retrieval time. Outstanding shares are not EPS weighted-average shares. Derived data is not primary evidence. Missing is not zero. Stale is not current. Corporate actions matter. EvidenceJudge still decides truth; DSP calculates.

Do **not** mark CLOSED until product chooses whether acquisition must require an explicit CA horizon (breaking the implicit PASS) and whether derived fields should surface on the frozen analyse contract (out of scope here).

## NEXT FORENSIC

SIMPLE-18 (suggested): attach derived provenance to research reports / VerifiedDataset exports without changing valuation formulas or `/api/v1/analyse`. Alternatively: bounded live share-capital + CA horizon against NSE, still `COMMERCIAL_USE_PENDING`.

FORENSIC → FIND → PROVE → FIX → TEST → VERIFY → CLOSE → NEXT.
