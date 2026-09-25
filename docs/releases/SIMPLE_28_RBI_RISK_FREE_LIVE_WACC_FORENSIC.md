# SIMPLE-28 — RBI Risk-Free Data Acquisition & Live WACC Qualification Forensic

## 1. STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-25, SIMPLE-26, and SIMPLE-27 were **not** redone.

The architecture remains:

```text
RBI
 ↓
risk-free observation
 ↓
raw evidence
 ↓
EvidenceJudge
 ↓
VERIFIED observation (not a WACC quote)
 ↓
existing DSP compute_wacc   ← only if a tenor policy binds the observation
 ↓
AssumptionValidator
 ↓
canonical DcfMethod
```

RBI is **not** the WACC authority. Live NSDP retrieval succeeded. The labeled government-yield observation is a **Treasury Bill Rate** whose tenor is **unspecified** on the source page. Canonical CAPM/DCF has **no maturity policy**. Binding that T-bill as `risk_free_rate` would be a silent tenor choice. It is **not** bound.

```text
RBI VERIFIED (Treasury Bill Rates, maturity UNSPECIFIED)
+
BETA UNKNOWN
+
ERP UNKNOWN
        ↓
WACC INCOMPLETE
        ↓
DCF BLOCKED
```

That is correct.

**NO PRODUCTION DEPLOYMENT.** Frontend PARKED. No FMP, Kite, NSE MCP, OpenAI, Gemini, or FBIL.

---

## 2. BASELINE

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA (pre-SIMPLE-28 work) | `d11c82777caa5bfa70f266848475508bfd1c5a11` |
| SIMPLE-27 | `docs/releases/SIMPLE_27_LIVE_DCF_COMPONENT_RESEARCH_FORENSIC.md` — PASS WITH LIMITATIONS |
| SIMPLE-27 gap | Architecture proved. Live rf / β / ERP not auto-acquired. `live_macro_acquisition_status()` remained UNKNOWN. |
| Existing HTTP | `retrieve_official_document`, `NsePublicHttp`, now also `retrieve_approved_https` (HTTPS, timeout, bound, approved redirects; no NSE cookie-warm) |
| Source allowlist | `rbi.org.in` already Tier 1A in `PRIMARY_HOST_SUFFIXES` |
| EvidenceJudge | Unchanged promotion rules plus forbidden `risk_free_rate` semantics (repo, CRR, SLR, bank rate, inflation, …) |
| WACC engine | One canonical engine: `valuation.dcf_intelligence.wacc.compute_wacc` via `calculate_dsp_wacc`. No `compute_rbi_wacc()`. |
| Prior RBI connector | None. Do not duplicate a vendor connector. |

---

## 3. RBI SOURCE

Approved host for this forensic: **`rbi.org.in`**.

Canonical retrieval URL (same for every listing):

`https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx`

National Summary Data Page (NSDP). SDDS interest-rate block.

Also inspected and **not** used as risk-free authority:

| URL | Why not used as rf |
|---|---|
| `https://www.rbi.org.in/Scripts/BS_ViewPolicyInterestRate.aspx` | Policy rates (repo / MSF class). Rejected as risk-free. |
| `https://www.rbi.org.in/Scripts/WSSViewDetail.aspx?...` | ~3.5 MB; exceeds the 2 MB bound. Not fetched as evidence. |
| `fbil.org.in` | Not on the allowlist. New provider. Not added. |

No FMP, Kite, Yahoo, BSE paid, or NSE MCP.

---

## 4. RBI OBSERVATION SEMANTICS

Live NSDP Interest Rates block (retrieved 2026-09-11):

| Instrument | Kind | Yield (decimal) | Observation date | Classification |
|---|---|---|---|---|
| Bank Rate | `bank_rate` | 0.055 (5.50% p.a.) | 2026-09-04 | **REJECTED_AS_RISK_FREE** |
| MCLR (1-Year) | `mclr` | 0.084 (8.40% p.a.) | 2026-09-04 | **REJECTED_AS_RISK_FREE** |
| Treasury Bill Rates | `treasury_bill` | **0.052089** (5.2089% p.a.) | **2026-09-09** | GOVERNMENT_YIELD_CANDIDATE |

What the selected observation **is**:

- Instrument: RBI NSDP **Treasury Bill Rates**
- Unit on page: **Per cent per annum** → stored as decimal `0.052089`
- Currency: **INR** (Indian government bills; no FX conversion)
- Maturity: **UNSPECIFIED** (the NSDP row does not label 91-day / 182-day / 364-day)
- Source document: RBI NSDP, Date of Publish **2026-09-11**
- Source URL: `https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx`
- Evidence locator: `Treasury Bill Rates`

What it is **not**:

- Not the policy repo rate
- Not reverse repo, CRR, SLR, MSF, SDF
- Not Bank Rate
- Not MCLR
- Not inflation / CPI
- Not a corporate bond yield
- Not a 10-year G-sec (that series is not on this page)
- **Not WACC**

---

## 5. MATURITY POLICY

```text
POLICY GAP
```

Canonical `CapmInputs` has `risk_free_rate`, `beta`, `equity_risk_premium`. It has **no tenor**. Official DCF / SIMPLE-27 WACC has **no** required 91-day T-bill, 5-year G-sec, or 10-year G-sec.

Constants (explicit, not a silent default):

```text
RBI_RISK_FREE_MATURITY_POLICY = POLICY_GAP
RBI_RISK_FREE_REQUIRED_MATURITY = None
```

Binding rule:

| Policy | Observed maturity | Decision |
|---|---|---|
| POLICY_GAP / required `None` | any, including 10-year G-sec | **POLICY_GAP** — not bound |
| required `10-year` | `91-day` | REJECTED |
| required `10-year` | UNSPECIFIED | REVIEW_REQUIRED |
| required `10-year` | `10-year` | BOUND |

Live T-bill is therefore **retrieved and judged**, not auto-fed to `compute_wacc`.

A future forensic may set an explicit DCF tenor. This forensic must not invent one.

---

## 6. LIVE HTTP ACQUISITION

Infrastructure: `retrieve_approved_https` (existing official HTTPS stack: approved host, `_ApprovedRedirectHandler`, timeout, bounded body). Not `NsePublicHttp` cookie-warming. Not a new vendor client.

| Field | Live value |
|---|---|
| source | RBI |
| URL | `https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx` |
| retrieved_at | 2026-09-11T17:27:50.812126+00:00 |
| HTTP status | 200 |
| content type | `text/html` |
| document/publication date | 2026-09-11 (Date of Publish) |
| observation date | 2026-09-09 (Treasury Bill Rates row) |
| HTTPS | yes |
| timeout | 20 s |
| max bytes | 2_000_000 |
| robots/CAPTCHA/auth bypass | none used |

RBI did **not** block this automated GET.

`http://` RBI URLs are rejected. Yahoo / secondary hosts are not retrieved as truth.

---

## 7. EXTRACTION

Deterministic **labeled-row** regex on sanitized HTML text. No positional “third table cell” guessing.

Extracted only rows whose labels are known (`Bank Rate`, `MCLR (1-Year)`, `Treasury Bill Rates`, policy repo, reverse repo, CRR, SLR, MSF, 5-year / 10-year G-sec if present).

Percent-per-annum values `> 1` are converted to decimal. Prompt-injection spans are neutralized by `sanitize_document_text` before extraction.

---

## 8. EVIDENCE JUDGE

Checks applied:

| Gate | Live T-bill |
|---|---|
| identity | PASS (listing ISIN+MIC stamped; market observation is not company-specific) |
| source authority | TIER_1A `rbi.org.in` |
| semantics | PASS as `treasury_bill` observation; Bank Rate / MCLR FAIL as `risk_free_rate` |
| freshness | CURRENT |
| period/date | observation_date 2026-09-09 ≤ valuation_date 2026-09-11 |
| unit | decimal (from % p.a.) |
| currency | INR |
| provenance | URL, locator, retrieved_at, document_date, as_of |

Promotion:

- Bank Rate / MCLR as `risk_free_rate` → **not VERIFIED** (`semantic_status=FAIL`; repo-class kinds → **REJECTED**)
- Treasury Bill as `rbi_interest_rate_observation` → **VERIFIED** observed fact
- `risk_free_rate` **not** VERIFIED for WACC while binding is POLICY_GAP

AI / llm `source_type` still cannot write VERIFIED.

---

## 9. FRESHNESS

Forensic window (explicit, not a hidden DCF default): observation is **STALE** if `valuation_date − as_of > 30` calendar days.

| Label | Meaning |
|---|---|
| CURRENT | as_of ≤ valuation_date and age ≤ 30 days |
| STALE | age > 30 days → `RESEARCH_REQUIRED`; not used |
| UNKNOWN | as_of missing; `retrieved_at` is **not** as_of |

Live: as_of 2026-09-09, valuation_date 2026-09-11 → **CURRENT**.

---

## 10. VALUATION DATE

Recorded separately:

| Field | Live |
|---|---|
| valuation_date | 2026-09-11 |
| observation_date / as_of | 2026-09-09 |
| retrieved_at | 2026-09-11T17:27:50Z |

`as_of > valuation_date` → REJECTED / REVIEW_REQUIRED (adversarial G).

---

## 11. CURRENCY

| Side | Value |
|---|---|
| risk-free observation | INR |
| Indian equity listing | INR |

USD listing vs INR observation → **REJECTED**. No silent FX conversion.

---

## 12. SOURCE CONFLICTS

No second approved live rf series is fetched. FBIL is not allowlisted.

If AI claims a different rate at the same RBI URL: **primary extraction wins**; values are **not averaged**. Recorded as `PRIMARY_AUTHORITY_RETAINED` / `REVIEW_REQUIRED` class via `record_source_clash`.

Genuine unresolved multi-yield conflict (two government-yield rows, no tenor policy) → **REVIEW_REQUIRED**.

---

## 13. WACC INTEGRATION

```text
Verified RBI observation
        ↓
binding_decision (POLICY_GAP → not BOUND)
        ↓
analyse() does not inject risk_free_rate into compute_wacc
```

Replay (fixture T-bill 7.00% + verified β + ERP + debt/equity/rd/tax) calls existing `calculate_dsp_wacc` → `compute_wacc`. **One engine.**

Live `analyse_listing` / `/api/v1/analyse` still cannot complete WACC: rf not bound **and** β/ERP absent.

---

## 14. COST OF EQUITY

Canonical formula unchanged:

```text
Cost of Equity = Risk-free Rate + Beta × ERP
```

Live: rf observation exists but is unbound; beta UNKNOWN; ERP UNKNOWN → cost of equity UNKNOWN.

Replay: rf 0.07, β 1, ERP 0.05 → **0.12**.

---

## 15. WACC CALCULATION

WACC is a **DERIVED VALUE**, not an observed RBI fact.

Replay (same SIMPLE-27 levered example, using extracted fixture 7.00% T-bill as the numeric ingredient):

| Input | Value |
|---|---|
| rf | 0.07 |
| β | 1 |
| ERP | 0.05 |
| E, D | 100, 100 |
| rd | 0.10 |
| tax | 0.25 |
| engine | `valuation.dcf_intelligence.wacc.compute_wacc` |
| WACC | **0.0975** |

Live: WACC incomplete. Formula/version still `dsp_wacc.v1` when DSP later calculates.

---

## 16. ASSUMPTION VALIDATION

Unchanged. Finite, numeric, `> 0` for discount_rate; rf bounds `[-0.05, 0.25]`; provenance required. No weakening.

Live path never proposes an ACCEPTED WACC from RBI alone.

---

## 17. AI RETRIEVAL

OpenAI / Gemini remain **NOT_CONFIGURED**. That does **not** invalidate the RBI test: HTTP + labeled extraction + EvidenceJudge run without AI.

If an AI locator supplies a non-RBI or unapproved URL → REJECTED.

If an AI locator supplies a real RBI URL but a wrong rate → extraction is primary.

AI cannot override primary evidence. AI cannot write WACC.

---

## 18. ADVERSARIAL TESTS

| ID | Case | Result |
|---|---|---|
| A | AI says RBI rate is 10% without evidence | **REJECTED** (missing source_url). Agent `NOT_CONFIGURED` does not fabricate. |
| B | AI real RBI URL, rate 0.10 vs extracted 0.07 | **primary evidence wins** (`PRIMARY_AUTHORITY_RETAINED`) |
| C | Repo / Bank Rate / MCLR as risk-free | **REJECTED** |
| D | Wrong maturity vs a stated required tenor | **REJECTED**; unspecified vs required → **REVIEW_REQUIRED**; POLICY_GAP → unbound |
| E | Stale observation (>30d) | **STALE** / **RESEARCH_REQUIRED** |
| F | Listing currency USD | **REJECTED** |
| G | observation_date after valuation_date | **REJECTED** |
| H | Yahoo URL, `http://`, unapproved 302 | **REJECTED** |

---

## 19. SECURITY

| Control | Status |
|---|---|
| RBI URL allowlist | `rbi.org.in` already primary |
| HTTPS | required |
| Redirect validation | `_ApprovedRedirectHandler`; secondary hosts rejected |
| Bounded response | 2 MB |
| Timeout | 20 s |
| Secret logging | none added |
| Arbitrary URL fetch | unapproved host → RetrievalFailure |
| Prompt sanitization | `sanitize_document_text` before extract |
| Evidence provenance | URL, hash, locator, timestamps |
| Identity binding | ISIN+MIC stamped; extractor does not branch on ticker |

---

## 20. PERFORMANCE

Live (one NSDP GET, 2026-09-11). Not optimized.

| Stage | Seconds |
|---|---|
| DNS/connect + HTTP | 0.839 |
| extraction | 0.150 |
| EvidenceJudge | 0.00037 |
| DSP WACC | 0.0 (not bound / not calculated) |

---

## 21. UNIVERSALITY

Tested through: **TCS, INFY, RELIANCE, WIPRO, 20MICRONS, 21STCENMGM**.

Same URL, same extractor, same T-bill decimal. **ZERO company-specific RBI logic** (AST: no named tickers in `rbi_risk_free.py`; no `if ticker ==`).

---

## 22. COMPLETE WACC REPLAY

Fixture NSDP T-bill **7.00%** + verified β 1 + ERP 5% + E=D + rd 10% + tax 25% → existing `compute_wacc` → **WACC 0.0975**, cost of equity **0.12**. No AI calculation. No second engine.

Live auto-bind is still POLICY_GAP, so this replay proves **DSP mathematics**, not live DCF completion.

---

## 23. LIVE ANALYSE

Canonical path:

```text
analyse_listing / acquire_rbi_risk_free
→ Security Master
→ ResearchPlan (unchanged; rf not a required equity filing field)
→ RBI HTTPS NSDP
→ EvidenceJudge
→ verified T-bill observation (unbound)
→ existing WACC path (incomplete)
→ AssumptionValidator
→ DcfMethod (blocked)
```

`AnalyseRequest` still `extra=forbid`: no client `wacc`, `risk_free_rate`, or terminal growth injection.

Network test `test_live_rbi_https_acquisition` **PASSED** (HTTP 200, HTML, POLICY_GAP, WACC not ACCEPTED).

No-AI: RBI path independent of LLM.

---

## 24. REGRESSION

Command (markers `not network`):

SIMPLE-14N-E, 14N-F, 15, 16, 17, 18, 19, 19A, 20, 21, 22, 23, 24, 25, 26, 27, **28**, 14N acquisition, 14ND, P1-10 (`test_p101_authenticated_valuation`), P1-11 (`test_p111_hard_release_gates`).

| | Count |
|---|---|
| passed | **299** |
| skipped | **5** (pre-existing live-network skips inside 21–25) |
| deselected | **8** (`not network`, including SIMPLE-28 live) |
| failed | **0** |
| xfail | **0** |
| new failures | **0** |
| pre-existing failures | **0** |

SIMPLE-28 unit tests: **18 passed** (`not network`) + **1 passed** live network.

SIMPLE-26: 16 passed. SIMPLE-27: 21 passed. Unchanged.

---

## 25. FILES CHANGED

| File | Change |
|---|---|
| `packages/data_engine/src/data_engine/official_research/rbi_risk_free.py` | **Added.** NSDP acquisition, labeled extraction, maturity POLICY_GAP, judge wiring. |
| `packages/data_engine/src/data_engine/official_research/documents.py` | `retrieve_approved_https`; bounded read; redirect-safe non-NSE primary fetch. |
| `packages/data_engine/src/data_engine/official_research/judge.py` | Reject forbidden `risk_free_rate` semantic kinds (repo, CRR, inflation, …). |
| `packages/data_engine/src/data_engine/official_research/end_to_end.py` | `analyse_listing` acquires RBI (LIVE or supplied document/retrieve); `rbi_risk_free` on result. MOCK skips HTTP unless document/retrieve provided. |
| `packages/data_engine/src/data_engine/official_research/__init__.py` | Exports. |
| `packages/data_engine/tests/test_simple28.py` | **Added.** Adversarial A–H, universality, replay, live network. |
| `docs/releases/SIMPLE_28_RBI_RISK_FREE_LIVE_WACC_FORENSIC.md` | This report. |

Frontend: none. DCF formulas: none. No `compute_rbi_wacc()`.

---

## 26. PRODUCTION IMPACT

**None deployed.**

- OpenAI / Gemini not activated
- NSE MCP remains `COMMERCIAL_USE_PENDING`
- FMP / Kite / BSE paid / FBIL not added
- MOCK `analyse_listing` does not hit RBI unless a test supplies document text or retrieve_fn
- LIVE / explicit retrieve fetches NSDP only from `rbi.org.in`

---

## 27. LIMITATIONS

1. **POLICY_GAP** — DCF has no G-sec / T-bill tenor. Live T-bill is not bound as WACC `risk_free_rate`.
2. NSDP **does not label T-bill maturity**.
3. **Beta** still unavailable on the approved architecture. Yahoo is not used.
4. **ERP** still unavailable. GDP / inflation / AI opinion are not used.
5. Therefore **WACC remains incomplete** and **DCF_BLOCKED** on live `analyse()`.
6. Terminal growth is unrelated to RBI and remains SIMPLE-26/27 methodology (still typically unavailable live).
7. Bank valuation / share-count / capex / FMP / frontend / NSE MCP — **deferred** (out of scope).
8. WSS / DBIE G-sec tables were not adopted (size bound / not required once POLICY_GAP is explicit).

---

## 28. DECISION

**PASS WITH LIMITATIONS.**

RBI was accessed with existing HTTPS infrastructure. Observation semantics are proven. Maturity policy is explicit (`POLICY_GAP`). Dates and provenance are preserved. EvidenceJudge verifies the T-bill **observation** and rejects policy rates. Stale / wrong instrument / wrong currency / wrong date / malicious redirect fail closed. DSP WACC remains a single engine. AI cannot override primary evidence. No company-specific RBI logic. Adversarial tests pass. Regression is green.

SIMPLE-28 is **not CLOSED** because a defensible DCF risk-free **input** still cannot be auto-bound: tenor policy is missing, and β/ERP remain UNKNOWN.

Do not circumvent that by treating Bank Rate, repo, or an unlabeled T-bill as “the” DCF rf.

---

## 29. NEXT FORENSIC

Candidate **SIMPLE-29**: an **explicit DCF risk-free tenor policy** (methodology document, not a convenience scrape), then bind only a matching RBI/approved government-security observation.

Independently: approved **beta** and **ERP** acquisition — still through EvidenceJudge, still into existing `compute_wacc`. Do not invent ERP. Do not use Yahoo beta. Do not activate commercial NSE MCP / FMP / Kite.

Do not solve terminal growth, bank DCF, or frontend in that forensic unless separately scoped.

Permanent rule:

> **Research retrieves the ingredients. Evidence proves the ingredients. DSP performs the mathematics.**
