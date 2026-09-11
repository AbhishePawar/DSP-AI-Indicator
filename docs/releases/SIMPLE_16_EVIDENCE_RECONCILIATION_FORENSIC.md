# SIMPLE-16 — Evidence Reconciliation & Authority Judge Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED. The canonical `EvidenceJudge` now performs deterministic multi-candidate reconciliation. Live OpenAI/NSE qualification was not part of this stage and is not fabricated. Weighted-average share rows remain fail-closed (`REJECTED` at the judge; `UNKNOWN` + `SEMANTIC_FAILURE` in acquisition for SIMPLE-14N-F compatibility).

**NO PRODUCTION DEPLOYMENT**

## BASELINE

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| SIMPLE-15 report | `docs/releases/SIMPLE_15_MULTI_AGENT_RESEARCH_FORENSIC.md` (uncommitted at start) |
| Working tree at start | SIMPLE-15 sources + parking leftovers (`.bytecode_backup/`, nested repo, `demoAuth*`, `artifacts/`, `body.txt`) |
| Focused regression before edits | **74 passed** (14N-E 16, 14N-F 17, SIMPLE-15 12, EvidenceJudge 29) |

Existing work was not discarded. SIMPLE-15 remains the research mesh. This stage extends the judge, not the agent layer.

Canonical contracts reused: `EvidenceItem`, `EvidenceJudge`, `SourcePolicy`, `ResearchPlan`, `ResearchResult`, `ResearchTrace`, provenance fields on `EvidenceItem`, extraction/normalization in `extraction.py`.

## CURRENT EVIDENCE ARCHITECTURE

One pipeline remains canonical:

```
candidates
→ identity (ISIN + MIC)
→ source authority (field-specific)
→ semantic kind
→ freshness (as_of ≠ retrieved_at)
→ period / currency / unit
→ corporate-action context
→ EvidenceJudge.reconcile_candidates
→ EvidenceJudge.promote / verify
→ VerifiedDataset
→ dsp_gate
→ DSP
```

Overlapping logic identified (not replaced with a second engine):

| Surface | Before SIMPLE-16 | SIMPLE-16 action |
|---|---|---|
| `EvidenceJudge.reconcile` | Single RAW row | Preserved |
| `EvidenceJudge.promote` | Only VERIFIED writer | Preserved; extra fail-closed checks |
| `field_acquisition` raw primary-value clash | Two different strings → CONFLICT | Now calls `reconcile_candidates` (normalized) |
| `source_policy.FIELD_AUTHORITY_CHAIN` | Group chains | Extended with `FieldPolicy` matrix |
| `evidence_identity.dedupe_evidence` | Fingerprint dedupe | Reused; identity classes added |
| `currentness.is_current` | Cache/currentness | `evaluate_freshness` added |
| `extraction` units / share labels / CA | Extract-time | `normalize_numeric_to_actual`, `canonicalize_period` added |

No `EvidenceJudgeV2`. No second source-policy engine. No new AI providers.

## AUTHORITY MODEL

Locked hierarchy, encoded in `authority_tier_for`:

| Tier | Sources | May become VERIFIED? |
|---|---|---|
| **TIER_1A** | NSE, BSE, SEBI, MCA, RBI, NSDL, CDSL (and hosts already in `PRIMARY_HOST_SUFFIXES`) | Yes, if all other gates pass |
| **TIER_1B** | Issuer IR / annual report / audited filing (`source_type=company_ir`) | Yes; filings rank equal to exchange for financials |
| **TIER_1C** | Screener | Cross-check only. Cannot override primary. Cannot itself verify |
| **TIER_2** | Yahoo Finance, IBEF | Secondary. Disagreement recorded. Never overwrites |
| **TIER_3** | OpenAI / Gemini / Claude / Deep Search | Discovery/interpretation only |

AI is never financial authority.

## FIELD AUTHORITY MATRIX

`FIELD_POLICY_MATRIX` in `source_policy.py` covers at least:

PRICE (`eod_close` / `last_price`) · REVENUE · EBIT · EBITDA · NET_INCOME · CFO · FCF · CASH · DEBT · EQUITY · SHARES · MARKET_CAP · ENTERPRISE_VALUE

Each policy records: authority chain, freshness class, semantic kinds, as-of/period/unit/currency/basis/CA requirements, calculation dependency, allowed security types.

Examples:

- **PRICE:** exchange/regulator → issuer → Screener → Yahoo/IBEF → AI
- **AUDITED FINANCIALS:** company filing ≈ exchange-filed document → Screener cross-check
- **SHARES / CA:** exchange/regulator/company → Screener
- **FCF / MARKET_CAP / EV:** marked `derived=True`. DSP calculates from verified inputs. Direct provider values are not independently VERIFIED.

Unsupported instruments (`etf`, warrants, …) return `UNSUPPORTED_SECURITY_TYPE`. Ordinary-equity revenue is not applied when `capability=bank_equity`.

## IDENTITY RECONCILIATION

Canonical identity: **ISIN + MIC**.

`classify_security_identity`:

| Status | Rule |
|---|---|
| IDENTITY_VERIFIED | ISIN and MIC present and match the expected listing |
| IDENTITY_AMBIGUOUS | Ticker or company name only; missing ISIN or MIC |
| IDENTITY_MISMATCH | ISIN, MIC, or ticker/ISIN pairing disagrees |
| IDENTITY_UNKNOWN | No identity material |

Ticker alone is insufficient. Company name alone is insufficient. Same issuer on NSE vs BSE remains distinguishable by MIC. Mismatched identities are never value-reconciled.

## SEMANTIC RECONCILIATION

Before comparing numbers, candidates are labeled:

- **PRICE:** CURRENT · DELAYED · EOD · PREVIOUS_CLOSE · HISTORICAL_CLOSE
- **SHARES:** TOTAL_OUTSTANDING · ISSUED · PAID_UP · LISTED · FREE_FLOAT · PROMOTER · WEIGHTED_AVERAGE · AUTHORIZED · …
- **FINANCIALS:** CONSOLIDATED vs STANDALONE; period type FY / QUARTER / TTM / YTD

Weighted-average shares cannot become outstanding shares (`SEMANTIC_REJECTION`). EOD cannot become live `last_price`. Consolidated net income is not compared with standalone as a true conflict.

## TIME/FRESHNESS

Every row already distinguishes `as_of`, `retrieved_at`, `document_date`, `current_through`, `last_verified_at`. Retrieval time is never the financial date.

`evaluate_freshness` output: CURRENT · STALE · REFRESH_REQUIRED · UNKNOWN

Field classes (from the planner, now enforced at the judge):

- current/delayed price → research window
- EOD → required trading date / session currentness
- annual financials → required reporting period; calendar passage after year-end is not automatic staleness
- shares → latest count plus subsequent **capital-changing** CA review

Stale authoritative evidence → `REFRESH_REQUIRED`, not silent use.

## PERIOD/CURRENCY/UNIT

`canonicalize_period` maps `2025-26`, `FY2026`, and `year ended March 31 2026` to `FY2026` (Indian year ending 31 March). FY, Q4, TTM, and YTD are not combined.

`normalize_numeric_to_actual` converts rupees / thousands / lakhs / millions / crores. Example: ₹926,240 million = ₹92,624 crore → `NORMALIZED_MATCH`.

Unknown units are never guessed → `UNIT_DIFFERENCE` / UNKNOWN. INR vs USD without an FX source → `CURRENCY_DIFFERENCE`, not a converted average.

## CORPORATE ACTIONS

Existing `CapitalEvent` types (bonus, split, rights, QIP, FPO, preferential, ESOP, warrants, conversion, new issue, buyback, cancellation, capital reduction, merger, demerger, scheme, share swap, acquisition) remain canonical.

Acquisition consideration stays CASH / SHARE_SWAP / MIXED / UNKNOWN. Acquisition is not assumed to change the share count.

Prices or share counts spanning a capital-changing event classify as `CORPORATE_ACTION_DIFFERENCE` / `CORPORATE_ACTION_CONTEXT`, not averaged TRUE_CONFLICT.

## CONFLICT CLASSIFICATION

`classify_conflict_reason` returns one of:

TRUE_CONFLICT · TIME_DIFFERENCE · SEMANTIC_DIFFERENCE · PERIOD_DIFFERENCE · UNIT_DIFFERENCE · CURRENCY_DIFFERENCE · CONSOLIDATION_DIFFERENCE · CORPORATE_ACTION_DIFFERENCE · IDENTITY_MISMATCH · SOURCE_STALENESS · UNRESOLVED · NORMALIZED_MATCH

Only **TRUE_CONFLICT** or **UNRESOLVED** block after normalization. Different timestamps are not called a conflict. Values are never averaged.

## PRIMARY CONFLICT HANDLING

Two Tier-1A/1B values that remain different after identity, semantics, period, units, and time → `CONFLICT`. Both records are retained. No AI vote. No silent pick.

## SECONDARY CONFLICT HANDLING

Primary X vs Yahoo/Screener Y, otherwise comparable → primary retained (`PRIMARY_AUTHORITY_RETAINED`). Secondary remains disagreement/cross-check evidence. No overwrite. No average.

## AI CLAIM HANDLING

OpenAI (or any TIER_3) claim vs valid primary → `AI_CLAIM_REJECTED`. LLM `source_type` still cannot `promote` to VERIFIED (`UNAVAILABLE`). Primary evidence wins if valid; otherwise UNKNOWN / CONFLICT.

## DEDUPLICATION

Existing fingerprint: source URL + security + field + as_of + value + document hash.

AI interpretation of an NSE document is not a second primary. Duplicate count → `DEDUPLICATED`, not consensus.

## EVIDENCE GRAPH

In-memory `EvidenceGraph` (`SOURCE → DOCUMENT → CLAIM → FIELD → SECURITY → VERIFICATION`). No separate graph database. Sufficient for provenance of a field decision.

## VERIFICATION RULES

A field becomes VERIFIED only when:

identity passes **and** source authority passes **and** semantics pass **and** period passes **and** currency/unit pass where required **and** freshness passes **and** corporate-action requirements pass where required **and** reconciliation passes **and** no unresolved primary contradiction remains.

Otherwise: UNKNOWN, CONFLICT, REFRESH_REQUIRED, or REJECTED.

Verification is field-level. PRICE/REVENUE can be VERIFIED while SHARES stay UNKNOWN and DCF stays blocked. `dsp_gate` still refuses non-VERIFIED inputs. `REJECTED` is in `DSP_BLOCKED_STATUSES`. RAW provider values still cannot `verify()` without RECONCILED.

## ADVERSARIAL TESTS

| Case | Result |
|---|---|
| A. NSE TCS + Yahoo other company | IDENTITY_MISMATCH / REJECTED |
| B. Same security, different timestamp | TIME_DIFFERENCE, not TRUE_CONFLICT |
| C. 926240 million vs 92624 crore | NORMALIZED_MATCH |
| D. Consolidated vs standalone | CONSOLIDATION_DIFFERENCE |
| E. Weighted-average vs outstanding | SEMANTIC_REJECTION / REJECTED |
| F. Primary vs secondary | PRIMARY_AUTHORITY_RETAINED |
| G. Two primaries 10 vs 11 | TRUE_CONFLICT / CONFLICT |
| H. AI vs primary | AI_CLAIM_REJECTED; AI not VERIFIED |
| I. Stale EOD vs required date | REFRESH_REQUIRED |
| J. Split between two prices | CORPORATE_ACTION_CONTEXT |
| K. NSE + AI same document hash | DEDUPLICATED |

## INVARIANTS

1. No verified field without evidence.
2. No verified field with identity mismatch.
3. No verified field with unresolved semantic mismatch (WA shares, EOD-as-live).
4. No stale field marked current (`freshness_status=FAIL` → REFRESH_REQUIRED).
5. No AI-only field becomes verified.
6. No secondary source overrides primary.
7. No conflicting primary evidence becomes a single verified value.
8. No weighted-average share count becomes outstanding shares.
9. Standalone and consolidated remain separate dimensions.
10. EOD cannot promote as `last_price`.
11. RAW cannot `verify()`; only the judge writes VERIFIED.
12. Duplicate AI+NSE rows do not create two primaries.

## PERFORMANCE

Mock reconciliation, 24 repetitions, 2 candidates (NSE million vs IR crore):

| Step | p50 | p95 |
|---|---|---|
| dedup | 0.008 ms | 0.017 ms |
| normalize / annotate | 0.052 ms | 0.081 ms |
| reconcile | 0.044 ms | 0.068 ms |
| judge select | <0.001 ms | <0.001 ms |

Largest contributor: **normalize/annotate**. Not optimized.

## SECURITY

Retrieved text and AI output remain untrusted. `prompt_guard` now also matches override-authority / change-source-policy / rewrite-verification-rules. Injection strings cannot alter `SourcePolicy`, authority tiers, or verification. Fake hosts such as `evil.example/nseindia.com/...` do not classify as primary. No credentials in traces or EvidenceItems. User input cannot override provider authority.

## TEST RESULTS

Focused run after changes:

| Suite | Result |
|---|---|
| SIMPLE-16 | **19 passed** |
| SIMPLE-14N-E | **16 passed** |
| SIMPLE-14N-F | **17 passed** |
| SIMPLE-15 | **12 passed** |
| EvidenceJudge (`test_official_research_engine`) | **29 passed** |
| NSE MCP OpenAI | **22 passed** |
| OpenAI Responses | **5 passed** |
| SIMPLE-14N acquisition + 14N-D (extra) | **48 passed** |
| Failed / skipped / xfail | **0 / 0 / 0** |

Combined focused SIMPLE-16 + 14N-E/F + 15 + judge + MCP + Responses: **120 passed**.

No pre-existing failures were hidden. Live OpenAI/NSE tests were not enabled.

## FILES CHANGED

| File | Role |
|---|---|
| `packages/data_engine/src/data_engine/official_research/judge.py` | Multi-candidate `reconcile_candidates`, conflict classes, graph |
| `packages/data_engine/src/data_engine/official_research/source_policy.py` | Field policy matrix, authority tiers |
| `packages/data_engine/src/data_engine/official_research/models.py` | `REJECTED`; additive identity/conflict/semantic/tier/freshness labels |
| `packages/data_engine/src/data_engine/official_research/extraction.py` | Numeric + period normalization |
| `packages/data_engine/src/data_engine/official_research/currentness.py` | `evaluate_freshness` |
| `packages/data_engine/src/data_engine/official_research/evidence_identity.py` | Identity classes |
| `packages/data_engine/src/data_engine/official_research/field_acquisition.py` | Uses canonical judge for candidate reconciliation |
| `packages/data_engine/src/data_engine/official_research/dsp_gate.py` | Block `REJECTED` |
| `packages/data_engine/src/data_engine/official_research/prompt_guard.py` | Extra injection phrases |
| `packages/data_engine/src/data_engine/official_research/__init__.py` | Exports |
| `packages/data_engine/tests/test_simple16.py` | Adversarial + invariant tests |
| `docs/releases/SIMPLE_16_EVIDENCE_RECONCILIATION_FORENSIC.md` | This report |

SIMPLE-15 files remain in the working tree from the prior forensic.

## PRODUCTION IMPACT

**NO PRODUCTION DEPLOYMENT**

No production OpenAI activation. No production NSE MCP activation. No `/api/v1/analyse` change. No valuation formula change. No frontend navigation change. No production environment change.

Research/evidence changes remain behind existing MOCK/LIVE and `production=` gates. MOCK still cannot enter production.

## COMMERCIAL STATUS

NSE MCP:

**COMMERCIAL_USE_PENDING**

Unchanged.

## LIMITATIONS

1. Live OpenAI / live NSE MCP were not executed (no production keys; not this stage).
2. Acquisition still reports non-outstanding share labels as `UNKNOWN` + `SEMANTIC_FAILURE` for 14N-F compatibility; the judge classifies the same rows `REJECTED`. Both fail closed.
3. FCF, market cap, and enterprise value are derived; this stage does not invent them.
4. No FX translation; currency mismatch stays `CURRENCY_DIFFERENCE`.
5. Evidence graph is structured tuples, not a persistent store.
6. Bank vs ordinary equity depends on planner capability / explicit `capability=` at the judge; catalog `security_type` for listed banks remains `equity`.

## DECISION

The single EvidenceJudge is now the universal reconciliation layer. Authority is field-specific and deterministic. AI cannot become financial truth. Secondary sources cannot override primaries. Primary conflicts fail closed.

Do **not** mark SIMPLE-16 CLOSED until a product decision is recorded on (a) live bounded qualification and/or (b) unifying acquisition's `UNKNOWN` vs judge `REJECTED` for semantic share rejection.

## NEXT FORENSIC

SIMPLE-17 (suggested): verified derived fields (FCF / market cap / EV) from already-VERIFIED inputs only, still without changing valuation formulas or `/api/v1/analyse`. Alternatively: bounded live OpenAI/NSE evidence through this judge, still `COMMERCIAL_USE_PENDING`.

FORENSIC → FIND → PROVE → FIX → TEST → VERIFY → CLOSE → NEXT.
