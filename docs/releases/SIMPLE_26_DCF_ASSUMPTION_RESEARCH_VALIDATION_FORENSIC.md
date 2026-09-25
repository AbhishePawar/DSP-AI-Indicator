# SIMPLE-26 — DCF Assumption Research & Validation Forensic

## 1. STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-25 = **PASS WITH LIMITATIONS** was not redone.

The architecture now answers:

> Can a defensible DCF assumption pack be established for this security?

It does **not** force every stock to produce a DCF.

```text
VERIFIED FACT
      ↓
DERIVED METRIC
      ↓
ASSUMPTION CANDIDATE
      ↓
DSP VALIDATOR
      ↓
ACCEPTED
      ↓
canonical DcfMethod
```

or:

```text
MISSING / CONFLICT / STALE / WRONG COMPANY / AI WITHOUT EVIDENCE
      ↓
UNKNOWN | REJECTED | REVIEW_REQUIRED
      ↓
DCF_BLOCKED
```

Never: `AI GUESS → DCF`.  
Never: `MISSING DATA → DEFAULT → DCF`.  
Never: `CONFLICT → AVERAGE → DCF`.  
Never: `ONE COMPANY → SPECIAL CASE`.

Live production `analyse()` still has **no accepted WACC or terminal growth** unless a candidate pack is supplied and the validator accepts it. That is the remaining limitation: approved external research/AI channels for forward-looking inputs are **NOT_CONFIGURED**.

**NO PRODUCTION DEPLOYMENT.** Frontend remains PARKED. NSE MCP remains `COMMERCIAL_USE_PENDING`. OpenAI/Gemini were not activated.

---

## 2. BASELINE

Recorded before SIMPLE-26 implementation. SIMPLE-25 was **not** redone.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d11c82777caa5bfa70f266848475508bfd1c5a11` |
| HEAD subject | fix: restore production data-unavailable error contract |
| SIMPLE-25 | `docs/releases/SIMPLE_25_UNIVERSAL_DCF_COMPLETION_FORENSIC.md` — PASS WITH LIMITATIONS |
| SIMPLE-25 live | Identity 21/21; capex VERIFIED 18/21; production `analyse()` DCF **0/21 CALCULATED**; replay RUN 12/21 with test-only fixture pack |
| Canonical DCF | `packages/valuation/src/valuation/methods/dcf.py` (`DcfMethod`) applied by `dsp_calculation.run_dsp_calculations` |
| Pre-SIMPLE-26 gap | `analyse_listing()` validated inbound `CanonicalAssumption` tuples, but production `ResearchOrchestrator.analyse()` never researched or passed WACC/growth. Empty pack → DCF BLOCKED. No universal candidate contract, identity/freshness/currency screen, or no-AI research path. |
| Offline regression before this report (14N-E…25, `not network`) | 171 passed, 5 skipped, 7 deselected (SIMPLE-26 tests not yet included) |
| Production revision | **Not queried. Not changed.** |
| Production image | **Unchanged / not inspected.** |
| Production environment | **Not modified.** |
| Production feature flags | RESEARCH_MODE unchanged; RECOMMENDATION_MODE/SEBI locked; production OpenAI off; NSE MCP pending |

Frontend parked items from the mission were **not** implemented.

---

## 3. EXISTING DCF CONTRACT

Inspected. **No second DCF engine. No methodology change.**

Canonical `DcfMethod` (`packages/valuation/src/valuation/methods/dcf.py`) requires:

| Input | Class | Required for ordinary-equity DCF? | Notes |
|---|---|---|---|
| operating_cash_flow | VERIFIED FACT | Yes | Snapshot latest |
| capital_expenditures | VERIFIED FACT | Yes | Snapshot latest |
| discount_rate | ASSUMPTION | Yes | WACC proxy |
| fcf_growth_rate | ASSUMPTION | Yes | Explicit-period growth |
| terminal_growth_rate | ASSUMPTION | Yes | Must be `< discount_rate` |
| projection_years | ASSUMPTION | Optional in DSP path | Library default 5; see §4 |

DSP application (`dsp_calculation._run_dcf`) maps:

- `wacc` **or** `discount_rate` (ACCEPTED)
- `fcf_growth_rate` (ACCEPTED)
- `terminal_growth_rate` (ACCEPTED)
- `projection_years` if ACCEPTED, else **horizon default 5**

FCF₀ is already derived: `CFO − |Capex|` (SIMPLE-17 / SIMPLE-25). Net debt is not subtracted again (equity FCF after interest).

**Optional / absent from current DcfMethod (not invented):**

risk-free rate, ERP, beta, cost of equity as a separate observed field, pre-tax cost of debt, tax rate, capital weights, explicit WACC as a market quote.

**Already validated:** `AssumptionValidator` bounds, WACC > terminal, AI synthesis without `evidence_ids` → REJECTED, pack conflicts → REVIEW_REQUIRED (SIMPLE-25).

**Already supplyable through `analyse_listing(assumptions=...)`:** replay/test path only. Production `ResearchOrchestrator.analyse()` does **not** accept client assumption kwargs.

**Not used by official `analyse()`:** `ValuationAssumptions()` Python defaults (`discount_rate=0.10`, `fcf_growth_rate=0.03`, `terminal_growth_rate=0.02`). DSP uses ACCEPTED `CanonicalAssumption` rows, not that dataclass.

---

## 4. HIDDEN DEFAULT FORENSIC

Searched the repository for WACC / terminal growth / `0.08`…`0.18` tokens that could reach official DCF.

| Location | Value | Classification | Reaches official `analyse()` DCF? |
|---|---|---|---|
| `valuation/assumptions.py` `ValuationAssumptions` | 0.10 / 0.03 / 0.02 / years=5 | LIBRARY DEFAULT | **No** — official path does not construct this object |
| `dsp_gate.default_unverified_assumptions()` | names only, `value=None`, status `UNAVAILABLE` | DEAD AS DCF INPUT | **No** — UNAVAILABLE cannot be ACCEPTED |
| `dsp_calculation._run_dcf` `years = 5` | 5 | ASSUMPTION HORIZON DEFAULT | **Yes, only after WACC/growth/terminal are ACCEPTED** |
| `assumption_validator` terminal bound | `[0, 0.08]` | VALIDATION BOUND | Rejects out-of-bound; does not supply a value |
| `dcf_intelligence` CAPM / 0.08 perpetual cap | DCF INTELLIGENCE ENGINE | SEPARATE ENGINE | **Not invoked** by official research DCF |
| Quality/moat weights `0.15` | DERIVED WEIGHTS | Not DCF rates | No |
| Test fixtures `0.08` / `0.10` / `0.18` | TEST FIXTURE | Tests / replay packs | Only when explicitly passed through validator |
| Docs / comments | DOCUMENTATION | — | No |
| `assumption_research.py` | none of `0.08`…`0.18` | — | **No hidden WACC/growth invented** |

**Defect standard:** any production DCF default that bypasses validation is a defect.

- Hidden **WACC / forecast growth / terminal growth** on the official path: **none found**.
- Remaining horizon default `years = 5` is documented, not a WACC. It is a SIMPLE-26 limitation (see §31), not a silent 8%/10%/12% discount rate.

---

## 5. WACC RESEARCH

Canonical DCF does **not** require WACC to be retrieved as a primary-source quote.

SIMPLE-26 research path:

1. Inbound proposals (replay, guidance, AI, user) are screened (identity, freshness, currency, data class).
2. If evidenced `risk_free_rate`, `beta`, and `equity_risk_premium` exist and no explicit WACC/discount_rate was proposed, DSP **derives** `discount_rate = rf + β × ERP`.
3. That derived required-return is still an **ASSUMPTION candidate**, not an observed fact.
4. `AssumptionValidator` is the only acceptance authority.
5. Missing components → `UNKNOWN` → `DCF_BLOCKED`. No 8%/10%/12% fallback.

Live `analyse()` has no RBI/macro/AI feed configured → WACC stays `UNKNOWN`.

---

## 6. WACC COMPONENTS

| Component | Required by current DcfMethod? | Class | Source in SIMPLE-26 | as_of / retrieved_at / currency / unit / identity / freshness / confidence |
|---|---|---|---|---|
| risk-free rate | No | ASSUMPTION (macro) | inbound evidenced proposal only | carried on candidate; stale → STALE |
| equity risk premium | No | ASSUMPTION | inbound evidenced proposal only | same |
| beta | No | ASSUMPTION | inbound evidenced proposal only | same |
| cost of equity | No as a named DCF input | DERIVED from accepted components, then proposed as `discount_rate` ASSUMPTION | `rf + β×ERP` | evidence_ids union of components |
| pre-tax cost of debt | No | UNKNOWN unless proposed | not manufactured | UNKNOWN |
| tax rate | Optional assumption field exists | ASSUMPTION | inbound only; not required for current DCF | — |
| debt | No for this DCF (equity FCF) | VERIFIED FACT | `VerifiedDataset` | identity-bound |
| equity | No | VERIFIED FACT | `VerifiedDataset` | identity-bound |
| capital weights | No | DERIVED if debt+equity verified | **not computed into WACC** without cost of debt | UNKNOWN |
| WACC / discount_rate | **Yes (one of)** | ASSUMPTION entering DcfMethod | accepted candidate only | provenance retained |

A calculated WACC is **never** labeled a directly observed fact.

---

## 7. TERMINAL GROWTH RESEARCH

Terminal growth is **never** auto-set to:

- last-year growth
- GDP
- a fixed default
- an AI number without evidence

Historical CAGRs are **DERIVED METRICS**. Using them as terminal growth would still be an assumption; SIMPLE-26 **does not** auto-propose `terminal_growth_rate` from CAGR.

A terminal candidate is accepted only if proposed (guidance / research / user / AI-with-evidence) and the validator accepts it, including `WACC > terminal_growth` and canonical bounds `[0, 0.08]`. Invalid → REJECTED → `DCF_BLOCKED`. No silent clamp.

---

## 8. HISTORICAL GROWTH

From verified, identity-bound, currency/unit/basis-compatible observations:

| Metric | Status when possible | Interpolation |
|---|---|---|
| Revenue CAGR | DERIVED / CALCULATED | none |
| Net income CAGR | DERIVED / CALCULATED | none |
| CFO CAGR | DERIVED / CALCULATED | none |
| FCF CAGR | DERIVED from same-period `CFO − \|Capex\|` | none; missing years stay missing |
| FCF margin trend | UNKNOWN unless a later forensic defines it | none |

FCF CAGR may **propose** `fcf_growth_rate` (`proposed_by=DETERMINISTIC_RESEARCH`) with evidence_ids. The validator still must ACCEPT it. It is not terminal growth.

---

## 9. ASSUMPTION CANDIDATE CONTRACT

New provider-neutral model: `DcfAssumptionCandidate` in `assumption_research.py`.

Required fields: `name`, `value`, `unit`, `currency`, `scenario`, `rationale`, `evidence_ids`, `source`, `source_type`, `as_of`, `retrieved_at`, `confidence`, `proposed_by`, plus identity (`isin`, `mic`, `ticker`, `security_type`) and `freshness`.

`proposed_by` may be `DETERMINISTIC_RESEARCH` | `COMPANY_GUIDANCE` | `AI_RESEARCH` | `MARKET_DATA` | `USER` (and existing agent names).

`accepted_by` is **only** set to `assumption_validator.v1` after ACCEPTED. `proposed_by` never equals `accepted_by`.

---

## 10. VALIDATION

Unchanged canonical `AssumptionValidator`, plus a pre-validator screen:

| Check | Failure |
|---|---|
| finite numeric | REJECTED |
| WACC > 0 (existing bounds) | REJECTED |
| WACC > terminal_growth | REJECTED, DCF_BLOCKED |
| existing canonical bounds | REJECTED, no clamp |
| AI / `ai_synthesis` without evidence_ids | REJECTED |
| facts / derived fields as assumptions | REJECTED |
| identity ISIN+MIC | IDENTITY_FAIL, REJECTED |
| currency vs dataset | REJECTED, DCF_BLOCKED |
| stale retrieved_at | STALE, RESEARCH_REQUIRED, DCF_BLOCKED |

Only `ACCEPTED` rows enter `DcfMethod` via `run_dsp_calculations`.

---

## 11. CONFLICT HANDLING

If two materially different candidates exist for the same field/scenario (example WACC 8% vs 18%):

- **not averaged**
- **not picked for a nicer valuation**
- pack validator returns `REVIEW_REQUIRED`
- research result: `status=REVIEW_REQUIRED`, `dcf_eligibility=DCF_BLOCKED`

Primary evidence wins over AI for **facts** (revenue, CFO, capex, shares, debt, cash). AI fact candidates are `PRIMARY_WINS; AI_REJECTED`. The `VerifiedDataset` is unchanged.

---

## 12. PROVENANCE

Every candidate and accepted assumption retains: name/value, source, evidence_ids, as_of, retrieved_at, rationale/reasoning, validation status/detail, `validator_version`.

Public `assumption_research` block distinguishes:

| Label | Where |
|---|---|
| Observed Fact | `VerifiedDataset` / historical observations `status=VERIFIED` |
| Calculated Value | historical CAGRs `data_class=DERIVED_VALUE` |
| Research Proposal | `candidate_assumptions` with `status=PROPOSED` / rejected / stale |
| Accepted Assumption | `accepted_assumptions` + `accepted_by=assumption_validator.v1` |

Attached on `EndToEndResult.assumption_research` and `to_public_dict()`.

---

## 13. FRESHNESS

`ASSUMPTION_FRESHNESS_DAYS = 365`.

| Label | Rule |
|---|---|
| CURRENT | `now - retrieved_at ≤ 365 days` |
| STALE | older → cannot enter DCF; `RESEARCH_REQUIRED` |
| UNKNOWN | missing timestamps treated via retrieved_at; stale if dated |

A CURRENT label is not trusted if `retrieved_at` is actually stale.

---

## 14. IDENTITY

Assumptions are bound to **ISIN + MIC + security type**.

| Case | Result |
|---|---|
| correct company | may proceed to validator |
| wrong company (other ISIN) | IDENTITY_FAIL, REJECTED |
| same ticker, different MIC (dual listing) | IDENTITY_FAIL, REJECTED |
| CanonicalAssumption replay | bound to the resolved listing (cannot smuggle a foreign ISIN through the dataclass) |

No ticker-named branches in production research code (AST-checked).

---

## 15. CURRENCY

Financial facts, assumption `currency`, and DCF inputs must match `dataset.identity.currency`.

Mismatch → REJECTED, `DCF_BLOCKED`. No silent FX conversion (no authorized evidenced FX path on this pipeline).

---

## 16. PERIOD

Historical CAGR uses only compatible periods, units, currencies, and consolidation basis.

FCF points require **same `as_of`** for CFO and capex. FY26 CFO is not paired with FY25 capex.

Canonical DCF still uses the **current** verified snapshot FCF₀, not a mix of years, once assumptions are accepted.

---

## 17. AI STATUS

Official `analyse_listing` calls research with `ai_configured=False`.

Result: `ai_status=NOT_CONFIGURED`.

OpenAI / Gemini / NSE MCP were **not** activated to obtain a green test. `load_llm_config()` was not used to invent results.

---

## 18. AI BOUNDARY

```text
AI = RESEARCHER / PROPOSER / ATTACKER
DSP = JUDGE
```

AI may propose WACC components and terminal growth **with evidence_ids**.

AI may **not**:

- invent facts
- overwrite primary evidence
- write `VerifiedDataset` (`EvidenceJudge` demotes `source_type=llm` and `agent=openai_nse_mcp`)
- write accepted WACC/terminal directly (`validation_status=ACCEPTED` is forced back to PROPOSED and re-validated)
- calculate authoritative IV
- bypass EvidenceJudge or AssumptionValidator

`refuse_ai_fact` remains in force for revenue/shares/etc.

---

## 19. NO-AI PATH

Verified history → deterministic CAGRs → optional `fcf_growth_rate` candidate → validator.

Without evidenced WACC components or inbound WACC/terminal:

```text
UNKNOWN → DCF_BLOCKED
```

Completion is not forced. This is the honest production path today.

---

## 20. PRODUCTION ANALYSE INTEGRATION

```text
/api/v1/analyse  (composition HTTP; no WACC fields — extra=forbid)
ResearchOrchestrator.analyse
  → analyse_user_query
    → analyse_listing
      → ResearchPlan / acquisition / EvidenceJudge / VerifiedDataset
      → research_dcf_assumptions
      → AssumptionValidator
      → run_dsp_calculations(accepted_pack only)
      → DcfMethod
```

Desired behavior implemented:

```text
VerifiedDataset + AcceptedAssumptionPack → DcfMethod
without accepted assumptions → DCF_BLOCKED
```

`ResearchOrchestrator.analyse()` still does **not** take assumption kwargs. HTTP `AnalyseRequest` has no `wacc` / `discount_rate` / `terminal_growth_rate` / `assumptions` fields.

Replay `analyse_listing(assumptions=...)` remains for tests; every row is re-screened and re-validated.

---

## 21. DCF FORMULA INTEGRITY

**Not modified:**

- FCF formula (`CFO − |Capex|`)
- terminal value
- discounting
- enterprise/equity bridge
- shares
- IV/share
- MOS = `(IV/share − Price) / IV/share`

`dsp_calculation.py` and `valuation/methods/dcf.py` were not edited in SIMPLE-26.

---

## 22. UNIVERSAL TEST MATRIX

Offline, no company-specific production branches:

| Security | Role | Result |
|---|---|---|
| TCS | named ordinary equity | empty pack BLOCKED; fixture pack ELIGIBLE → DCF CALCULATED on fixture dataset |
| INFY | named ordinary equity | same |
| RELIANCE | named ordinary equity | same |
| WIPRO | named ordinary equity | same |
| 20MICRONS | named ordinary equity | same |
| 21STCENMGM | named ordinary equity | same |
| catalog dynamic XNSE equity | not in the named set | same |
| insufficient history | one observation | CAGR UNKNOWN; WACC UNKNOWN |
| conflicting WACC 8% vs 18% | adversarial C | REVIEW_REQUIRED, not averaged |
| FCF₀ ≤ 0 | cfo 4, capex 10 | assumptions may accept; DCF BLOCKED on FCF |
| HDFCBANK | `bank_equity` | `BANK_VALUATION_METHOD_REQUIRED` |
| NIFTYBEES ETF | unsupported | `UNSUPPORTED` |

---

## 23. ADVERSARIAL TESTS

| ID | Case | Expected | Observed |
|---|---|---|---|
| A | AI WACC, no evidence | REJECTED, DCF_BLOCKED | PASS |
| B | AI terminal growth, no evidence | REJECTED, DCF_BLOCKED | PASS |
| C | WACC 8% vs 18% | REVIEW_REQUIRED, DCF_BLOCKED, not averaged | PASS |
| D | terminal ≥ WACC | REJECTED, DCF_BLOCKED | PASS |
| E | wrong company / dual MIC | IDENTITY_FAIL, REJECTED | PASS |
| F | stale assumption | STALE, RESEARCH_REQUIRED, DCF_BLOCKED | PASS |
| G | AI vs primary (capex fact + unevidenced AI WACC) | PRIMARY_WINS, AI_REJECTED; primary WACC may accept | PASS |
| H | AI writes VerifiedDataset | EvidenceJudge ≠ VERIFIED; `refuse_ai_fact` REJECTED | PASS |
| I | missing evidence | UNKNOWN, DCF_BLOCKED | PASS |
| J | currency mismatch USD vs INR | REJECTED, DCF_BLOCKED | PASS |

---

## 24. BANK HANDLING

`classify_research_capability`: name token `\bbank\b` → `bank_equity`.

Ordinary FCF DCF is **not** forced. Result: `BANK_VALUATION_METHOD_REQUIRED`. This is correct. Bank-specific valuation remains unimplemented.

---

## 25. REPRODUCIBILITY

Same `VerifiedDataset` + same `AcceptedAssumptionPack` + same `DcfMethod` + same valuation datetime produced identical FCF, DCF IV, IV/share, and MOS across 5 repeats in `test_reproducibility_and_performance`.

---

## 26. PERFORMANCE

Measured separately in research result timings (not optimized):

| Stage | How measured |
|---|---|
| research | `research_dcf_assumptions` wall time |
| normalization | history merge + CAGR |
| assumption generation | candidates |
| assumption validation | `validate_assumption_pack` |
| DCF calculation | `run_dsp_calculations` median **< 50 ms** on fixture (threshold in test; actual is sub-millisecond class, consistent with SIMPLE-25 ~0.85 ms p50) |

No performance rewrite was attempted.

---

## 27. SECURITY

| Control | Result |
|---|---|
| AI cannot bypass validator | ACCEPTED status on inbound AI rows is stripped; no evidence → REJECTED |
| Client cannot inject accepted assumptions via HTTP | `AnalyseRequest` `extra=forbid`; no assumption fields |
| Client cannot inject via orchestrator | `ResearchOrchestrator.analyse` has no assumptions parameter |
| Client cannot inject verified facts via AI evidence | Judge demotes llm / openai_nse_mcp |
| Primary evidence not overwritten | dataset frozen; AI capex candidate rejected |
| Secrets not logged | no new logging of keys; prompts unchanged |
| Research prompts sanitized | existing `looks_like_injection` / `redact_mcp_text` unchanged |
| Provenance survives | `assumption_research` on E2E public dict |

Replay `analyse_listing(assumptions=)` is a **test/internal** seam and always re-validates.

---

## 28. REGRESSION

Offline (`-m "not network"`), this session:

| Suite | Passed | Failed | Skipped | xfail | Deselected (network) |
|---|---|---|---|---|---|
| SIMPLE-14N-E … SIMPLE-26 | **187** | **0** | **5** | **0** | **7** |
| SIMPLE-26 only | **16** | **0** | **0** | **0** | 0 |
| P1-10 authenticity hard-fail (99 tests) | **99** | **0** | **0** | **0** | — |
| P1-10 file `test_p101_authenticated_valuation` | **13** | **0** | — | — | — |
| P1-11 `test_p111_hard_release_gates` | **12** | **0** | — | — | — |

Skipped are prior **live network** tests (SIMPLE-21…25), not new SIMPLE-26 failures.

**Old vs new failures:** none. No new failures.

Live NSE assumption research was **not** run (no new providers; SIMPLE-25 already proved production DCF stays blocked without a pack).

---

## 29. FILES CHANGED

| File | Change |
|---|---|
| `packages/data_engine/src/data_engine/official_research/assumption_research.py` | **Added** — universal research/candidate/screen/pack |
| `packages/data_engine/src/data_engine/official_research/assumption_contract.py` | `STALE` added to `ASSUMPTION_STATUSES` |
| `packages/data_engine/src/data_engine/official_research/end_to_end.py` | `analyse_listing` → research → accepted pack only; public `assumption_research` |
| `packages/data_engine/src/data_engine/official_research/__init__.py` | exports |
| `packages/data_engine/tests/test_simple26.py` | **Added** — matrix + adversarial A–J |
| `docs/releases/SIMPLE_26_DCF_ASSUMPTION_RESEARCH_VALIDATION_FORENSIC.md` | this report |

DCF formula modules were **not** changed.

---

## 30. PRODUCTION IMPACT

| Item | Impact |
|---|---|
| Production deployment | **None** |
| Feature flags | Unchanged |
| OpenAI / Gemini | Not activated (`NOT_CONFIGURED`) |
| NSE MCP | `COMMERCIAL_USE_PENDING` |
| Frontend | PARKED — no UI work |
| Live `analyse()` DCF | Still **BLOCKED** without an accepted pack (correct) |
| Replay/test DCF | Unchanged: fixture pack can still reach canonical DcfMethod after validation |

---

## 31. LIMITATIONS

1. **Live WACC / terminal research is unavailable.** No configured RBI/macro primary feed and no configured AI research channel. Production remains `WACC:UNKNOWN`, `TERMINAL_GROWTH:UNKNOWN`, `DCF_BLOCKED`.
2. **`projection_years = 5`** remains a silent horizon default **after** WACC/growth/terminal are ACCEPTED. Not a hidden WACC.
3. **`ValuationAssumptions` library defaults still exist** for other valuation callers. They do not feed official `analyse()` DCF.
4. **CAPM weights / cost of debt** are not derived into a levered WACC. Missing weights stay UNKNOWN; equity required-return may be proposed only from evidenced rf/β/ERP.
5. **FCF margin trend** is not yet a calculated series.
6. **Bank valuation method** is still required and unimplemented.
7. **Frontend parked.**
8. **No production deploy.**

These are why the stage is not CLOSED.

---

## 32. DECISION

**PASS WITH LIMITATIONS**

Closure criteria that **hold**:

- universal assumption contract exists
- WACC research/proposal path exists (inbound + optional CAPM derive)
- terminal-growth research/proposal path exists (inbound only; no auto GDP/last-year)
- provenance exists
- validation is deterministic
- conflicts are not averaged
- stale / wrong-company assumptions are rejected
- AI cannot bypass validation
- no hidden WACC/growth reaches official DCF
- accepted assumptions can reach canonical DcfMethod
- missing/unaccepted assumptions block DCF
- adversarial tests pass
- dynamic securities pass
- no company-specific branches
- DCF formulas unchanged
- regression green

Closure criteria that **do not hold for CLOSED**:

- live assumption research cannot complete because required external research/AI capability is **NOT_CONFIGURED**

FAIL conditions were **not** met (AI cannot directly drive DCF; no hidden WACC; no averaging; no stale/wrong-company accept; formulas unchanged).

---

## 33. NEXT FORENSIC

**SIMPLE-27 candidate:** live WACC **component** acquisition from already-approved sources (Tier 1A RBI / regulatory macro; Tier 1B company guidance for terminal where explicitly disclosed), still through candidate → validator → ACCEPTED, with NSE MCP remaining `COMMERCIAL_USE_PENDING` and AI remaining `NOT_CONFIGURED` unless a separate activation forensic authorizes it.

Do **not** start frontend simplification, do **not** invent ERP, do **not** treat GDP as terminal growth, and do **not** deploy.

Optional adjacent: make `projection_years` an explicit ACCEPTED assumption (remove silent `years=5`) in a dedicated horizon forensic — not a DCF formula change.

---

## Implementation return (workspace gate)

- **Architecture Impact:** Additive research/validation seam only. Canonical DcfMethod unchanged. Thin client unchanged. No engine redesign.
- **Components Added:** `assumption_research.py` (`DcfAssumptionCandidate`, `research_dcf_assumptions`); `STALE` status.
- **Pages Updated:** none (frontend parked).
- **Feature Flags Used:** none.
- **Accessibility Validation:** N/A (no UI).
- **Performance Validation:** DCF calc median < 50 ms on fixtures; research timings recorded, not optimized.
- **Responsive Validation:** N/A.
- **Known Limitations:** see §31.
- **Future Enhancements:** see §33.
- **Regression Summary:** 187 passed / 5 skipped / 7 deselected (14N-E…26, not network); P1-10 99 passed; P1-11 12 passed; SIMPLE-26 16 passed. No new failures.
