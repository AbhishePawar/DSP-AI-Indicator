# SIMPLE-14N-F — Universal Planned-Field Acquisition Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED. Not production-deployed. Not a company-by-company repair.

The generic acquisition loop exists and is proven on mocked evidence for ordinary listed equity and bank equity:

DISCOVER → RETRIEVE → EXTRACT → NORMALIZE → RECONCILE → VERIFY

TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS, and one catalog-discovered listing are **test fixtures only**. The engine has no `if ticker ==` / `if company ==` / `if ISIN ==` production branches.

## BASELINE

Recorded before 14N-F edits:

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `bdf4f1ed6ea4bd72b11224a026694e14f6efe6f8` |
| HEAD subject | Reconstruct official annual-report tables from PDF coordinates |
| Working tree | Dirty. SIMPLE-14N-E planner/loop (untracked) preserved. NSE-MCP-OPENAI forensic files remain staged/modified. Parking noise (`.bytecode_backup/`, nested `DSP-AI-Indicator/`, `demoAuth*`, `artifacts/`) is not part of this forensic. |
| SIMPLE-14N-E regression | **16/16 green** (`test_simple14ne.py`) |
| Focused suite before edits | **79 passed** (`test_simple14ne.py` + `test_simple14n_acquisition.py` + `test_official_research_engine.py`) |

Existing architecture reused, not replaced:

- `research_plan.py` — capability-driven `ResearchPlan`
- `research_loop.py` — bounded discover-only loop (does not download)
- `acquisition.py` / `documents.py` / `extraction.py` / `statement_tables.py` — document retrieve + extract
- `judge.py` — RAW → RECONCILED → VERIFIED
- `dsp_gate.py` — only VERIFIED inputs enter DSP
- `source_policy.py` — Tier 1A/1B/1C/2/3 hierarchy
- Share semantics + corporate-action attack already generic

## ARCHITECTURE

Security-first, provider-neutral:

```
ResearchRequest (ISIN + MIC + field groups)
        ↓
ResearchPlan (capability, required fields, source priority, freshness)
        ↓
acquire_planned_fields
        ↓
per field: DISCOVER → RETRIEVE → EXTRACT → NORMALIZE → RECONCILE → VERIFY
        ↓
EvidenceItem (RAW)
        ↓
EvidenceJudge.promote
        ↓
VERIFIED_DATA → dsp_gate
```

Forbidden paths remain closed:

- RAW_PROVIDER_DATA → DSP
- AI answer → DSP
- Screener → VERIFIED
- NSE MCP → production VERIFIED (`COMMERCIAL_USE_PENDING`)

Partial research is first-class. A missing share count blocks DCF/earnings; it does not fail the whole company.

No `/api/v1/analyse` change. No production provider selection. No frontend pages. No user-facing research controls.

## RESEARCH PLAN

`ResearchRequest` accepts provider-neutral groups:

IDENTITY, PRICE, FINANCIALS, SHARES, CORPORATE_ACTIONS, MANAGEMENT, BUSINESS_QUALITY, MOAT, RISK, VALUATION_INPUTS, EVIDENCE

`expand_requested_fields` maps groups onto DSP contract names. The planner still decides which mapped fields are applicable for the **security class**:

| Capability | How selected | DCF |
|---|---|---|
| `equity` | default listed equity | UNAVAILABLE until required VERIFIED inputs exist |
| `bank_equity` | name token `\bbank\b`, not a ticker table | UNAVAILABLE (ordinary-equity DCF not forced) |
| unsupported (`etf`, warrant, bond, …) | `security_type` | CAPABILITY_UNAVAILABLE / `UNSUPPORTED_SECURITY_TYPE` |

`plan_report_block` now also dumps:

FIELD_CAPABILITIES, SOURCE_PRIORITY, RETRIEVAL_STRATEGY, FRESHNESS_REQUIREMENT, DOCUMENT_REQUIREMENTS, CORPORATE_ACTION_REQUIREMENTS, CROSS_CHECK_REQUIREMENTS, VERIFICATION_REQUIREMENTS

A plan is not evidence.

## FIELD ACQUISITION

New module: `official_research/field_acquisition.py`

For every planned field:

1. **DISCOVER** candidate URLs from the ISIN IR registry + generic NSE locators, ordered by `field_source_priority`
2. **RETRIEVE** injected `EvidenceItem`s, supplied `DocumentRecord`s, or an optional `retrieve_fn` adapter. A failed URL is never retried. The next approved source is tried.
3. **EXTRACT** via the generic labeled-field extractor (no issuer PDF parser)
4. **NORMALIZE** to `EvidenceItem` stage=RAW with provenance
5. **RECONCILE** primary vs primary → CONFLICT (no silent pick). Screener may cross-check; it cannot override or become VERIFIED.
6. **VERIFY** exclusively through `EvidenceJudge`

Outcomes: `VERIFIED` | `UNKNOWN` | `CONFLICT` | `REFRESH_REQUIRED` | `UNAVAILABLE` | `UNSUPPORTED_SECURITY_TYPE`

Missing values are never invented.

## DOCUMENT ACQUISITION

`identify_document_characteristics` / `select_extraction_strategy` record:

document type, reporting period, publication/document date, consolidated/standalone, audited/unaudited, currency, units, URL, content hash, retrieval timestamp, extraction strategy

Unknown attributes stay unknown. Strategy is chosen from document characteristics (`native_pdf_text`, `coordinate`, `table`, `plain_text`, `unavailable`), not from ticker.

OCR is **not** auto-run. A PDF with no text layer is `unavailable`.

Default `acquire_planned_fields` does not perform live HTTP. Live retrieve remains an injected adapter so tests do not depend on provider availability. `acquire_primary_documents` remains the existing live document path.

## EXTRACTION

Generic labeled extraction plus the existing statement-table / coordinate reconstructors.

Fail closed:

| Unknown | Outcome |
|---|---|
| units | UNKNOWN (`UNIT_UNKNOWN`) |
| consolidated/standalone | UNKNOWN (`BASIS_UNKNOWN`) |
| period | UNKNOWN (`PERIOD_UNKNOWN`) |
| ambiguous number | not silently reinterpreted |

Evidence locator (label / page row) is preserved on the `EvidenceItem`.

## NORMALIZATION

`normalize_extracted_field` converts `ExtractedField` → RAW `EvidenceItem`:

- identity check against ISIN in document text
- share semantic classification
- `retrieved_at` distinct from `as_of`
- `raw_value` / `raw_unit` kept separate from normalized value
- `document_hash`, `source_url`, `evidence_locator` preserved

## RECONCILIATION

- Two primary values that differ → `CONFLICT` / `RECONCILIATION_CONFLICT`. No winner is invented.
- Primary vs Screener clash → primary retained, clash recorded, `silent_overwrite=False`.
- Screener-only → not VERIFIED.
- Secondary (Yahoo / IBEF) remains discovery-only.
- AI / `llm` / `gemini_find` / `openai_nse_mcp` cannot verify.

## SHARE COUNT

`classify_share_semantic_type` distinguishes:

TOTAL_OUTSTANDING, ISSUED, PAID_UP, LISTED, FREE_FLOAT, PROMOTER, WEIGHTED_AVERAGE, DILUTED_EPS_DENOMINATOR, TRANCHE, AUTHORIZED, TREASURY, OTHER, UNKNOWN

**Only `TOTAL_OUTSTANDING` may feed the basic valuation share denominator.** Paid-up, listed, free-float, promoter, EPS-weighted, and dilutive tranche counts fail `SEMANTIC_FAILURE` and stay UNKNOWN.

## CORPORATE ACTIONS

Generic CA attack (bonus, split, rights, QIP, FPO, preferential, ESOP, warrants, conversion, new issue, buyback, cancellation, capital reduction, merger, demerger, scheme, share swap, acquisition).

An **acquisition does not automatically mean shares changed.**

`classify_acquisition_consideration` → `CASH` | `SHARE_SWAP` | `MIXED` | `UNKNOWN`

Only `SHARE_SWAP` / `MIXED` mark an acquisition as `capital_changing`. Cash/unknown acquisitions do not stale the share count. Buybacks still do.

## CURRENTNESS

Every time-sensitive field carries `as_of`, `retrieved_at`, `current_through`, `last_verified_at`.

`currentness_label` → `CURRENT` | `STALE` | `UNKNOWN` | `CONFLICT`

Retrieval time is never treated as data-as-of time. Annual fields with `freshness_status=PASS` remain CURRENT after later retrieval. Share currentness is a corporate-action review, not “retrieved today”.

## EVIDENCE JUDGE

`EvidenceJudge` remains the only promotion authority.

Every accepted candidate is an `EvidenceItem` with: evidence_id, security identity (ISIN+MIC), field, value, as_of, retrieved_at, source, source_type, source_url, document_date, evidence_locator, agent, identity/semantic/freshness/CA status, confidence.

Three-state architecture is enforced: RAW → RECONCILED → VERIFIED. Only VERIFIED_DATA may feed deterministic DSP.

## UNIVERSAL SECURITY TEST

Same `acquire_planned_fields` engine, mocked official statement + EOD candidate:

| Fixture | Role |
|---|---|
| TCS, INFY, RELIANCE, WIPRO, 20MICRONS | ordinary listed equity |
| HDFCBANK | bank equity (revenue not required) |
| first other eligible NSE equity from Security Master | dynamically discovered |

No custom parser per issuer. Forbidden-token scan covers `field_acquisition.py` and `research_plan.py`.

## SECURITY-TYPE TEST

- Ordinary listed equity → equity capability
- Bank equity → `bank_equity`; ordinary-equity DCF inputs are not forced
- ETF fixture → `UNSUPPORTED_SECURITY_TYPE`; no ordinary-equity valuation model is applied

## FAILURE TESTS

Typed taxonomy separates transport from domain:

| Transport | Domain |
|---|---|
| NETWORK, HTTP, AUTH, RATE_LIMIT, MCP_* transport | EXTRACTION_FAILURE, IDENTITY_FAILURE, SEMANTIC_FAILURE, FRESHNESS_FAILURE, RECONCILIATION_CONFLICT, UNSUPPORTED_SECURITY, MISSING_REQUIRED_DATA, UNIT/PERIOD/BASIS_UNKNOWN, DOCUMENT_NOT_FOUND, … |

`is_transport_failure` is the breaker predicate. Domain/data errors do not trip provider breakers.

Covered: timeout → next source, no retry of the same URL; two primaries CONFLICT; Screener cannot verify; AI cannot verify; paid-up shares cannot be the denominator; missing units/basis/period → UNKNOWN.

## PERFORMANCE

Mock-path wall-clock for one TCS FINANCIALS+SHARES+PRICE run (no live HTTP):

| Stage | Seconds |
|---|---|
| plan | 0.0012 |
| discover | 0.0001 |
| retrieve | 0.0051 |
| extract | 0.0118 |
| normalize | 0.0018 |
| reconcile | 0.0001 |
| verify | 0.0003 |
| **wall** | **0.021** |

Bottleneck on the mock path is **extract** (labeled scan). Live HTTP retrieve was not measured here and would likely dominate. No premature optimization.

## FILES CHANGED

Additive / extended (no production API):

- `packages/data_engine/src/data_engine/official_research/field_acquisition.py` **(new)**
- `packages/data_engine/src/data_engine/official_research/research_plan.py`
- `packages/data_engine/src/data_engine/official_research/research_failures.py`
- `packages/data_engine/src/data_engine/official_research/extraction.py`
- `packages/data_engine/src/data_engine/official_research/documents.py`
- `packages/data_engine/src/data_engine/official_research/currentness.py`
- `packages/data_engine/src/data_engine/official_research/__init__.py`
- `packages/data_engine/tests/test_simple14nf.py` **(new)**
- `docs/releases/SIMPLE_14N_F_UNIVERSAL_PLANNED_FIELD_ACQUISITION.md` **(this file)**

SIMPLE-14N-E files (`research_loop.py`, `provider_router.py`, `forensic_artifacts.py`, `test_simple14ne.py`) were not discarded.

## TEST RESULTS

| Suite | Result |
|---|---|
| `test_simple14nf.py` | 17 passed |
| `test_simple14ne.py` | 16 passed |
| `test_simple14n_acquisition.py` | 34 passed |
| `test_official_research_engine.py` | 29 passed |
| `test_nse_mcp_openai.py` | 22 passed (mocked; no live OpenAI) |
| `test_simple14nd.py` | 14 passed |
| **Focused total** | **132 passed** |

Deterministic mocks only in 14N-F. No test depends on live NSE/Screener/OpenAI availability. OpenAI live integration was not activated.

## PRODUCTION IMPACT

**NONE.**

Not changed:

- `/api/v1/analyse`
- production environment
- production provider selection
- production valuation behavior
- frontend production
- user-facing navigation / provider pickers / research orchestration UI

## COMMERCIAL STATUS

| Component | Status |
|---|---|
| Planned-field acquisition architecture | Forensic / research |
| EvidenceJudge | Authoritative (unchanged) |
| Screener | Cross-check only |
| Yahoo / IBEF | Discovery-only |
| AI research agents | OFF for production; provider-neutral stubs remain |
| NSE MCP | `TECHNICALLY_QUALIFIED` from prior forensic; **`COMMERCIAL_USE_PENDING`** |
| OpenAI | Not activated in this forensic |

## LIMITATIONS

1. **Live retrieve is an adapter.** `acquire_planned_fields` does not download by default; callers inject documents, text, candidates, or `retrieve_fn`. Automatic live PDF fetch still lives in `acquire_primary_documents`, not inside this loop.
2. **OCR is not implemented.** Scanned PDFs with no text layer stay UNKNOWN / unavailable.
3. **Coordinate/table reconstructors are not auto-wired** into every field step. Strategy is identified; default extract is labeled text. 14N-D coordinate reconstruction remains available separately.
4. **Qualitative groups** (MANAGEMENT, BUSINESS_QUALITY, MOAT, RISK, EVIDENCE) become plan tasks. They are not scored. Inventing those scores would violate CV-001.
5. **IR registry gaps** remain (`DISCOVERY_REQUIRED` for unregistered issuers). The engine will not guess `/investors`.
6. **DCF stays blocked** when discount/growth assumptions are not VERIFIED (`dsp_gate` existing rule), even if cash-flow fields verify.
7. **NSE MCP is not production-approved.**
8. **No production deployment.**

## ROOT CAUSE OF LIMITATIONS

This forensic proved a **generic planned-field machine**, not a live crawler and not a commercial data license.

The remaining gaps are missing **runtime wiring** (inject live retrieve into the planned-field loop), missing **document-character extract routing** (coordinate/table when labeled text is insufficient), incomplete **IR registry coverage**, and **deliberate commercial/AI holds**. They are not ticker bugs.

## DECISION

**PASS WITH LIMITATIONS.**

Do not declare CLOSED.

Do not deploy.

Do not treat TCS working as platform-complete. The same engine ran across the fixture set; live universe coverage still depends on discovery + retrieve adapters + official documents.

## NEXT FORENSIC

**SIMPLE-14N-G — wire generic live retrieve into planned-field acquisition without production activation.**

Suggested scope:

1. Use `acquire_primary_documents` / `retrieve_official_document` as the default `retrieve_fn` behind a non-production flag.
2. Select extract strategy from `DocumentCharacteristics` (labeled text → table → coordinate; OCR only if no text layer and explicitly enabled).
3. Keep EvidenceJudge, source hierarchy, and share/CA gates unchanged.
4. Bounded live tests on a small fixture set; mocks remain the CI contract.
5. Still no `/api/v1/analyse` change, no OpenAI activation, no NSE MCP commercial approval.

Operating sequence remains: FORENSIC → FIND → PROVE → FIX → TEST → VERIFY → CLOSE → NEXT.

---

Architecture Impact: additive research-engine loop only; no API/UI/engine redesign.
Components Added: `field_acquisition.py`, `test_simple14nf.py`, this report.
Pages Updated: none.
Feature Flags Used: none.
Accessibility / Performance / Responsive Validation: N/A (no UI).
Known Limitations: listed above.
Future Enhancements: SIMPLE-14N-G live retrieve wiring.
Regression Summary: SIMPLE-14N-E 16/16 green; focused official-research family 132 passed.
