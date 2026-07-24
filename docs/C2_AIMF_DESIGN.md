# Phase C2 — Adaptive Industry Methodology Framework (AIMF)

**Status:** Design audit COMPLETE · **Architecture FROZEN** — see canonical freeze doc  
**Audience:** CIO / Equity Research Head / Chief Software Architect  
**Depends on:** Decision Pack (canonical), Multi-Stock Foundation (C1)

> **Authoritative frozen architecture:**  
> **[C2_AIMF_ARCHITECTURE_FREEZE.md](C2_AIMF_ARCHITECTURE_FREEZE.md)**  
> This file retains the capability audit, data-gap matrix, and design history.  
> Where wording conflicts, the freeze document wins.

---

## 0. Executive recommendation

DSP can support every listed and future industry **without redesigning a comparison engine**, if and only if comparison remains a **methodology consumer**, not an industry switchboard.

**Design freeze:** AIMF domain model is stable for multi-year methodology growth.

Primary rules (see freeze doc for full matrix):

1. Industry identity is taxonomy-mapped and stable — not free-text alone.
2. Comparison consumes **IndustryMethodology + DecisionPack + ComparableSummary** only.
3. Peer eligibility gates comparison; characteristics never imply peers.
4. Industry-specific metrics often require new data — declare gaps honestly.
5. Valuation Engine stays method-agnostic; AIMF selects/prefers methods only.

---

## 1. Current capability audit

### Exists today

| Capability | Where | Notes |
|---|---|---|
| Free-text `sector`, `industry` on `Instrument` | `contracts` | Optional strings; **no taxonomy, no ID, no hierarchy, no versioning** |
| `AssetClass` enum | `contracts` | Equity/FI/… — not industry |
| Universe filter/group by sector/industry/tags | `universe` | Explicit metadata only; no inference |
| `DecisionPack` | `decision_intelligence` | Action, conviction, brief, assurance, MoS, valuation summary |
| `ComparableDecisionSummary` | `universe` | Flattened decision snapshot — **no industry metrics, no ranking** |
| Valuation methods | `valuation` | DCF, Owner Earnings, Earnings Multiple, Book Value, Residual Income |
| `ValuationMethod` registry | `valuation` | Engine-local; not industry-aware |
| Fundamental metrics | `fundamental` | Profitability / leverage / quality style analyzers — **generic corporate**, not bank/insurance specific |
| MoS + `ValuationSummary` | `contracts` | Propagated; not recalculated downstream |
| Frozen spine | platform | Engines → Committee → Recommendation → DI → DecisionPack → Universe |

### Missing (critical for AIMF)

| Gap | Impact |
|---|---|
| Stable industry identity (code + taxonomy + version) | Cannot version methodologies safely |
| Business-model / sub-industry / peer-set metadata | Banks vs NBFC vs life insurance look alike as “Financials” |
| Industry methodology objects | No place for preferred valuation / metrics / dimensions |
| Metric registry with applicability + explanation | Metrics exist as engine outputs, not industry-declared requirements |
| Peer eligibility policy | Risk of comparing incompatible businesses |
| Comparison engine contract | Not designed yet (correct — this phase) |
| Industry data (NIM, combined ratio, AUM, NAV, load factor, etc.) | Mostly absent from contracts / providers |
| Mapping layer NSE/BSE/GICS/ICB → internal industry ID | Absent |

### What Decision Packs expose (usable by comparison later)

- Recommendation action / conviction / MoS / valuation summary  
- Assurance level / guidance / agreement / dissent / fragilities  
- Brief attribution and invalidators  

**They do not expose industry-normalized metric vectors.** That is correct today; AIMF must define how metrics attach **beside** packs, not inside engines.

### What Instrument metadata contains

Only optional display/classification strings (`sector`, `industry`) plus identity fields. **Insufficient as the sole industry key for a 20-year framework.**

---

## 2. Architecture (conceptual)

```
Taxonomy Mapping (NSE/BSE/GICS/ICB/custom)
        ↓
IndustryIdentity  →  IndustryProfile
                          │
                          ├── references → InvestmentCharacteristics (reusable economic archetype)
                          │                      │
                          │                      └── default ValuationProfile / dimension emphasis
                          ▼
                 IndustryMethodology (versioned; bound to IndustryIdentity)
                          │
     ┌────────────────────┼────────────────────┐
     ▼                    ▼                    ▼
ValuationProfile    MetricApplicability   ComparisonDimensions
(defaults from      (industry-owned)      (defaults + overrides)
 characteristics,
 industry overrides)
     │
     └──────────► PeerEligibilityPolicy (industry / business-model owned)
                          ▼
               ComparisonEngine (industry-agnostic)
         inputs: Methodology + DecisionPack[] + Summaries
         output: ComparisonResult (refusal allowed; no required rank)
```

**Hard rule:** Comparison engine contains **zero** `if industry == …` branches. All industry knowledge is injected via registered methodology.

**Hard rule (C2 refinement):** `InvestmentCharacteristics` may supply **defaults**. It must **never** imply peer comparability. Peer eligibility remains industry/business-model owned.

**Dependency direction (additive):**

```
contracts  ←  industry (AIMF domain models + registries)
                  ↑
         universe / future comparison  (consumers)
                  ↑
         dsp_platform (wiring / façade later)
```

Engines remain unaware of AIMF. Valuation Engine is **not** modified; methodologies only declare preferred method *names* that already exist (or are marked `REQUIRES NEW ENGINE`).

---

## 2a. Design refinement — InvestmentCharacteristics

**Recommendation:** Introduce as a first-class concept — **YES WITH CONDITIONS**.

### Why (and why not Option A alone)

Industries are legal/taxonomic labels. Investment behavior often clusters by **economic archetype** (regulated cash-flow compounder, pricing-power franchise, deposit franchise, cyclical commodity producer). Putting every economic field only on `IndustryProfile` forces either:

- duplication across many profiles, or
- dangerously shared full methodologies (e.g. one “Financial Institution Methodology” for Banks + Insurance + Exchanges) which is **financially invalid**.

`InvestmentCharacteristics` is the correct reuse grain for **defaults** (valuation philosophy, cash-flow shape, capital intensity). `IndustryMethodology` remains the correct binding grain for **policy** (metrics, peers, overrides), always keyed to `IndustryIdentity`.

### Conceptual shape

```text
InvestmentCharacteristics
  id, display_name, version, status
  # descriptive economics (examples — not mandatory checklist)
  capital_intensity, cash_flow_profile, growth_profile, cyclicality
  regulatory_dependence, pricing_power, network_effects, switching_costs
  asset_intensity, capital_allocation_character
  valuation_philosophy_notes
  common_risk_themes[]          # descriptive, not Risk Engine output
  default_valuation: ValuationProfile | null
  default_dimensions: DimensionRef[]   # emphasis order, not weights
  # explicitly does NOT own:
  #   MetricApplicability, PeerEligibilityPolicy, industry-specific regulatory metrics
```

### Ownership

| Concern | Owner |
|---|---|
| Economic archetype descriptors | **InvestmentCharacteristics** |
| Default ValuationProfile / dimension emphasis | **InvestmentCharacteristics** (defaults only) |
| Industry facts, taxonomy binding, business models | **IndustryProfile** |
| Assembled versioned policy | **IndustryMethodology** (bound to IndustryIdentity) |
| MetricApplicability | **IndustryMethodology** (industry-owned; may *cite* characteristic defaults only as documentation) |
| PeerEligibility | **IndustryMethodology / PeerEligibilityPolicy** — never Characteristics |
| DecisionPack / Universe / Engines | **unchanged** |

### Valid reuse vs invalid reuse

| Shared characteristics | Share defaults? | Share full methodology / DIRECT peers? |
|---|---|---|
| Utilities, pipelines, towers, some InvITs (“regulated/stable cash flow”) | Yes (valuation philosophy) | **No** — operating metrics differ; eligibility RELATED/LIMITED at best |
| Luxury, premium consumer, alcohol (“pricing power franchise”) | Yes (quality/ROCE framing) | **No** as blanket DIRECT peers |
| Banks + Insurance + Exchanges (“financial institution”) | **No** as one archetype | **Invalid** — different balance sheets and capital regimes |

### Backward compatibility

No changes required to DecisionPack, Universe, DSPPlatform, Valuation Engine, Committee, or Recommendation. AIMF-only additive domain.

---

## 3. Industry hierarchy

```
TaxonomySource (GICS | ICB | NSE | BSE | CUSTOM)
      ↓
ClassificationNode  (external code + label + source + version)
      ↓
IndustryIdentity    (DSP-stable ID, immutable once published)
      ↓
IndustryProfile     (industry facts + business models)
      │
      ├── references InvestmentCharacteristics (reusable economic archetype; defaults)
      ↓
IndustryMethodology (versioned policy bound to IndustryIdentity; overrides defaults)
```

### Abstraction principles

- **External codes are mappings, not identity.** GICS `4010` and NSE “Banks” can both map to `dsp.industry.banks.commercial`.
- **DSP IndustryIdentity is stable.** External taxonomies can churn without rewriting methodologies.
- **Hierarchy is advisory for navigation;** eligibility and methodology bind to `IndustryIdentity` (and optional `BusinessModelVariant`), not to raw sector strings.
- **Unknown is allowed.** Unmapped instruments → methodology `UNKNOWN` → peer eligibility `UNKNOWN` → comparison refused or limited.

Conceptual types (design only):

```text
TaxonomySource: enum { GICS, ICB, NSE, BSE, CUSTOM }
ClassificationRef: { source, code, label, version }
IndustryIdentity: { id, display_name, parent_id?, status }
IndustryMapping: { classification_ref → industry_id, effective_from, effective_to? }
BusinessModelVariant: { id, industry_id, label }
```

---

## 4. IndustryProfile

Defines the **economics of the business**, not scores.

```text
IndustryProfile
  identity: IndustryIdentity
  parent_id: IndustryIdentity.id | null
  business_models: BusinessModelVariant[]
  cyclicality: LOW | MODERATE | HIGH | STRUCTURAL
  capital_intensity: LOW | MODERATE | HIGH
  regulatory_intensity: LOW | MODERATE | HIGH
  typical_capital_structure: narrative + expected_leverage_band (descriptive, not formula)
  cash_flow_character: e.g. deposit_franchise | subscription | project | commodity | fee
  quality_dimensions: DimensionRef[]
  growth_dimensions: DimensionRef[]
  comparison_dimensions: DimensionRef[]
  valuation: ValuationProfile
  metrics: MetricApplicability[]
  data_requirements: DataRequirement[]
  decision_interpretation_notes: str[]   # how to read DecisionPack in this industry
  peer_default_policy_id: PeerEligibilityPolicy.id
  version: semver
  status: ACTIVE | DEPRECATED
```

**No formulas. No weights. No rankings.**

Illustrative profiles (identity only — not implementations):

| IndustryIdentity | Valuation preference sketch | Distinctive metric families |
|---|---|---|
| Commercial Banks | Book / Residual Income preferred; classic DCF limited | NIM, NPA, PCR, CASA, capital ratios |
| NBFC | Book / earnings; DCF conditional | AUM growth, stage-3, leverage, ALM |
| Life / General Insurance | Embedded value / P/EVish concepts; DCF limited | Combined ratio, solvency, persistency |
| Asset Management | AUM multiples / DCF on fees | AUM, realization, operating margin |
| SaaS / Software | DCF / owner earnings; ARR multiples acceptable | ARR, NRR, Rule-of-40 proxies |
| Cement / Metals | EV/EBITDA / replacement; DCF cyclical caution | Utilization, realization, cost curve |
| REIT / InvIT | NAV / DDM preferred | NAV, yield, occupancy, WALE |
| Airlines | Cyclical EV/EBITDA; DCF fragile | Load factor, yield, ASK/RPK, fuel |
| Pharma | DCF / earnings; pipeline qualitative | Margins, R&D, ANDA/concentration |

---

## 5. ValuationProfile

```text
ValuationMethodRef: stable name (aligns with valuation.ValuationMethod where possible)
  examples today: dcf, owner_earnings, earnings_multiple, book_value, residual_income
  future refs:   dividend_discount, ev_ebitda, nav, sotp, asset_replacement, embedded_value, …

ValuationProfile
  preferred: ValuationMethodRef[]      # ordered preference
  acceptable: ValuationMethodRef[]
  unsupported: ValuationMethodRef[]    # explicit refusals (e.g. naive DCF for banks)
  interpretation_notes: str[]          # e.g. "MoS on book vs FCFF is not interchangeable"
  requires_engine_extension: ValuationMethodRef[]  # honest gap list
```

**Rules:**

- AIMF **does not** call or modify Valuation Engine.
- Preferred methods that exist today may be selected in a future orchestration policy.
- Methods marked `requires_engine_extension` block “industry-correct” valuation claims until built.
- MoS remains the Valuation Engine’s artifact; AIMF only documents **how MoS should be interpreted** for that industry.

---

## 6. Metric Registry

```text
MetricCategory:
  QUALITY | GROWTH | PROFITABILITY | EFFICIENCY | CAPITAL | RISK |
  VALUATION | LIABILITY | AUM | REGULATORY | OPERATING | OTHER

MetricDefinition
  id: stable string                 # e.g. metric.nim
  display_name: str
  category: MetricCategory
  unit: ratio | percent | currency | count | years | other
  explanation: str                  # WHY it matters (CIO-facing)
  calculation_owner:
    FUNDAMENTAL_ENGINE | VALUATION_ENGINE | ECONOMIC_ENGINE |
    DATA_ENGINE | EXTERNAL | FUTURE_ENGINE | DERIVED
  required_inputs: DataRequirement[]
  availability: AVAILABLE_TODAY | DERIVABLE | REQUIRES_NEW_DATA | REQUIRES_NEW_ENGINE
  importance_default: CORE | SECONDARY | CONTEXTUAL
  version: semver

MetricApplicability
  metric_id
  industry_id
  importance: CORE | SECONDARY | CONTEXTUAL | NOT_APPLICABLE
  interpretation_notes: str[]
  peer_use: ALLOWED | CAUTION | FORBIDDEN
```

**Principle:** DSP must know *why* a metric matters before it can display or compare it. A metric without `explanation` + `applicability` is not comparison-ready.

---

## 7. Comparison dimensions (unweighted)

Dimensions are **axes**, not scores:

| Dimension | Typical evidence sources |
|---|---|
| Quality | Fundamentals, industry metrics, brief strengths |
| Growth | Fundamentals / operating metrics |
| Capital Allocation | Fundamentals, fragilities |
| Financial Strength | Leverage/capital metrics |
| Valuation | MoS, valuation summary, method fit |
| Efficiency | Industry operating metrics |
| Profitability | Margins / returns (industry-appropriate) |
| Predictability | Cyclicality profile + assurance resilience |
| Decision Robustness | Assurance level / agreement / dissent |
| Risk Characteristics | Industry regulatory/capital intensity + fragilities |
| Industry Leadership | Requires future data (share, capacity) — often gap |

**Weights are deferred.** Recording dimensions without weights prevents fake precision.

---

## 8. Methodology Registry

```text
IndustryMethodology
  id
  industry_id
  business_model_id?: optional specialization
  version: semver
  status: ACTIVE | DEPRECATED | EXPERIMENTAL
  profile_ref: IndustryProfile.version
  valuation: ValuationProfile
  metrics: MetricApplicability[]
  dimensions: DimensionRef[]          # ordered for presentation, not weighted
  peer_policy_id
  decision_interpretation: rules-as-data (narrative + optional deterministic guards later)
  changelog: str

IndustryMethodologyRegistry
  register(methodology)
  get(industry_id, *, version="active")
  list(industry_id?)
  deprecate(id, version, reason)
  resolve_for_instrument(instrument_classification) → Methodology | UNKNOWN
```

**Upgrade path:** new methodology versions register beside old; comparison engine binds to a version pin or “active”. No engine code change.

---

## 9. Peer Eligibility model

```text
PeerEligibility: DIRECT | RELATED | LIMITED | NOT_COMPARABLE | UNKNOWN

PeerEligibilityPolicy
  id
  rules: ordered deterministic predicates on
    IndustryIdentity, BusinessModelVariant, AssetClass, country?, listing?
  outputs: PeerEligibility + rationale

Examples (policy data, not code branches in comparison engine):
  Banks × Banks (same business model) → DIRECT
  Banks × NBFC → RELATED or LIMITED
  Banks × Software → NOT_COMPARABLE
  REIT × Hotel OpCo → NOT_COMPARABLE (asset vs operator)
  Unmapped × anything → UNKNOWN
```

**CIO rule:** If eligibility ≠ `DIRECT` (and sometimes `RELATED`), comparison must degrade or refuse — never silently produce a league table.

---

## 10. Comparison Engine contract (design)

Industry-agnostic interface:

```text
ComparisonRequest
  methodology: IndustryMethodology          # injected, never inferred inside engine
  subjects: list[{
    instrument,
    decision_pack: DecisionPack,            # canonical
    summary: ComparableDecisionSummary,     # from C1
    metric_snapshot?: IndustryMetricSnapshot  # future; may be empty
  }]
  peer_eligibility: map[pair → PeerEligibility]
  options: { allow_related: bool, allow_limited: bool }

ComparisonResult
  status: COMPLETE | DEGRADED | REFUSED
  methodology_id + version
  pair_results: [{
    left, right,
    eligibility,
    dimension_notes: [{ dimension, observation, evidence_refs }],  # qualitative first
    data_gaps: DataGap[],
    refusal_reason?: str
  }]
  # Explicitly NO overall score, NO rank order in the contract’s required fields.
  # Ranking, if ever added, is a separate optional RankView produced by a later policy module.
```

**Engine invariants:**

1. No industry conditionals.  
2. No MoS recalculation.  
3. No vote re-aggregation.  
4. Refusal is success of governance, not failure of engineering.  
5. Consumes DecisionPack as canonical single-name truth.

---

## 11. Future extension strategy

| Future module | How it plugs into AIMF without redesign |
|---|---|
| Portfolio Intelligence | Reads ComparisonResult + DecisionPacks; adds constraint overlays; does not invent industry ifs |
| Risk Intelligence | Adds risk dimensions / metrics via MetricRegistry + methodology version bump |
| Research Intelligence | Renders methodology notes + comparison observations; cites Evidence |
| Behavioral Intelligence | Optional metric family + dimension; eligibility unchanged |
| Decision Memory | Stores methodology version + comparison inputs digest for audit |
| Expert Opinion | External evidence type mapped into dimension notes — not into engine branches |
| Macro Themes | EconomicEngine signals as contextual metrics with applicability |
| ESG | New MetricCategory + optional dimension; methodology opt-in |
| Alternative Data | New calculation_owner / data requirements; availability flags |

Pattern: **extend registries and methodology versions**, never fork the comparison engine.

---

## 12. Data Gap Matrix (honest)

Legend: **A** Available today · **D** Derivable from existing statements/series · **N** Requires new data fields/providers · **E** Requires new engine/method

| Industry family | Core operating metrics | Preferred valuation fit today | Gap class |
|---|---|---|---|
| Banks | NIM, NPA, capital — **N** | Book / RI exist (**A** methods); bank-correct use **partial** | **N/E** |
| NBFC | AUM, stage assets — **N** | Book/earnings **A**; ALM **N** | **N** |
| Insurance | Combined ratio, solvency — **N** | EV methods **E**; DCF often unsupported | **N/E** |
| AMC / Brokerage | AUM, yields — **N** | Fee DCF **D/E** | **N** |
| Exchanges | ADTV, member metrics — **N** | DCF/earnings **A/D** | **N** |
| Software / IT / SaaS | Generic margins **A/D**; ARR/NRR **N** | DCF/OE **A** | **N** for SaaS KPIs |
| Semiconductors | Utilization, node — **N** | DCF/cyclical **A** with caution | **N** |
| Staples / Discretionary / Retail / Luxury | Margins, SSS — **D/N** | DCF/earnings **A** | **D/N** |
| Hotels | RevPAR, occupancy — **N** | DCF/EV **A/E** | **N** |
| Hospitals / Diagnostics | Occupancy, ARPOB — **N** | DCF/earnings **A** | **N** |
| Pharma | Margins **A/D**; pipeline **N** | DCF/earnings **A** | **N** qualitative |
| Auto OEM / Ancillary | Volumes, mix — **N/D** | DCF/EV **A/E** | **N** |
| Airlines / Logistics / Shipping / Ports | Load/yield/utilization — **N** | Cyclical methods **A/E** | **N** |
| Infra / Construction / Capital Goods | Order book — **N** | DCF/SOTP **E** | **N/E** |
| Power / Renewables / Utilities | PPA, PLF, regulated RAB — **N** | DDM/NAV-like **E** | **N/E** |
| Oil & Gas / Mining / Metals / Cement / Chemicals | Realization, cost curve — **N/D** | EV/EBITDA **E**; DCF fragile | **N/E** |
| Telecom / Media | ARPU, subscribers — **N** | DCF/earnings **A** | **N** |
| Real Estate | Completions, pre-sales — **N** | NAV/SOTP **E** | **N/E** |
| REIT / InvIT | NAV, WALE — **N** | NAV/DDM **E** | **N/E** |
| Agriculture / Education / Defence / Space | Highly idiosyncratic — **N** | Case-by-case **E** | **N/E** |

**Cross-cutting AVAILABLE TODAY for all equities (generic):**

- DecisionPack action / assurance / guidance / MoS (when valuation ran)  
- Generic profitability & leverage fundamentals (corporate model)  
- Price history / technical context  

**Brutal truth:** Universal industry coverage of *decision packs* is near-term feasible; universal industry coverage of *economically correct peer comparison* is not — until metric data and some valuation methods land. AIMF’s job is to make that gap **explicit and versioned**, not to hide it behind a score.

---

## 13. Package proposal

**Recommended package name: `industry`**

| Option | Verdict |
|---|---|
| `industry/` | **Preferred** — owns profiles, mappings, metric applicability, methodology registry, peer policies |
| `methodology/` | Too narrow; taxonomy + peer eligibility are not “methodology” alone |
| `comparison/` | Premature — comparison engine should be a thin consumer package later (`comparison`) depending on `industry` + `decision_intelligence` + `universe` |

Suggested future split:

```
packages/industry/          # AIMF domain + registries (this design)
packages/comparison/        # later: industry-agnostic ComparisonEngine
```

`contracts` gains only thin shared types if needed later (`IndustryIdentity` id string, taxonomy enums) — avoid stuffing full profiles into shared kernel.

---

## 14. Implementation roadmap (post-design; not this phase)

1. **C2.1 Contracts & identity** — `IndustryIdentity`, taxonomy mapping model, instrument→identity resolution (explicit mapping files, not name inference).  
2. **C2.2 Registry skeleton** — Methodology + Metric registries with version/deprecate; zero comparison.  
3. **C2.3 Seed profiles** — 3–5 industries with largest data readiness (e.g. generic Consumer, IT Services) + 1 hard case (Banks) to force honesty.  
4. **C2.4 Peer eligibility** — enforce `NOT_COMPARABLE` / `UNKNOWN` in multi-stock flows before any compare UI.  
5. **C2.5 Comparison engine v0** — qualitative dimension notes + data gaps only; **no scores, no ranks**.  
6. **C2.6 Data programs** — industry metric ingestion prioritized by gap matrix.  
7. **C2.7 Valuation method extensions** — NAV, EV/EBITDA, DDM, etc. only when data exists; wire via ValuationProfile prefs.

---

## 15. Technical risks

| Risk | Severity | Mitigation |
|---|---|---|
| Free-text sector/industry drift | High | Stable IndustryIdentity + mappings |
| Fake universality via generic ratios | Critical | Availability flags + eligibility refusals |
| Comparison engine accretes industry ifs | Critical | Architecture tests; methodology injection only |
| MoS misinterpreted across industries | High | ValuationProfile interpretation notes; never recalc |
| Methodology version chaos | Medium | Semver + pin in ComparisonResult digest |
| Data program underfunded | High | Ship refused/degraded comparisons rather than invented metrics |

---

## Final architectural question

**Can DSP support every current and future industry without redesigning its comparison architecture?**

### YES WITH CONDITIONS

Conditions: methodology-injected comparison, stable industry identity, honest data/method gaps, peer eligibility as a hard gate, and Valuation/Fundamental engines extended via registries — not via rewriting comparison.
