# Phase C3.0 — Industry Evidence Framework (IEF)

**Status:** DESIGN REVIEW COMPLETE · Superseded on conflicts by **[C3.0A Architecture Freeze](C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md)**  
**Date:** 2026-07-21  
**Depends on:** AIMF C2.1–C2.5 (Identity → Characteristics → Methodology → Peer Eligibility → Qualitative Comparison)  
**Non-goals:** Metric registry implementation, evidence registry, comparison updates, portfolio/risk/research, scoring, ranking, ML/LLM

> **Canonical source of truth:** [C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md](C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md)  
> This file remains as the design-review record that led to the freeze.

---

## 1. Recommended architecture

```
Taxonomy / IndustryIdentity
        ↓
IndustryMethodology  (policy: which evidence applies)
        ↓
Industry Evidence Framework
   ├── EvidenceDefinition      (schema / meaning)
   ├── EvidenceApplicability   (methodology binding)
   ├── EvidenceProvider        (produce facts — deterministic)
   ├── EvidenceInterpreter     (turn facts into investor language)
   └── EvidenceObservation     (immutable cited artifact)
        ↓
Decision Intelligence (optional attachment / references)
        ↓
Comparison Engine  (consumes DecisionPack + EvidenceSnapshot)
        ↓
Portfolio / Risk / Research Intelligence (future consumers)
```

**Invariant:** Industry Evidence is a **consumer of analysis outputs and data**, not a valuation engine and not a replacement for DecisionPack.

```
DecisionPack  = investment decision artifact (action, MoS, assurance, brief)
Evidence      = structured industry-aware supporting facts + interpretations
Metric        = typed measurable quantity (often feeds evidence; is not evidence)
```

### Placement relative to C2.5

C2.5 comparison correctly used DecisionPack fields as a **minimum viable signal**.
C3.0 defines how richer, industry-aware evidence enters the same qualitative path
without inventing ranks or scores.

---

## 2. Domain model proposal

### 2.1 Separate Metric vs Evidence — **YES**

| Concept | Role | Example |
|---|---|---|
| **Metric** | Typed measurement (value + unit + as-of + provenance) | `ROE = 0.23` for FY2024 |
| **Evidence** | Interpreted, citable claim grounded in metrics/facts | “ROE has remained above 20% for five consecutive years.” |

**Why separate:**

1. Metrics can exist without being comparison-ready (no interpretation / peer-use policy).
2. Evidence can cite multiple metrics, time series, or qualitative facts.
3. AIMF already sketched `MetricDefinition` / `MetricApplicability`; Evidence sits **above** that layer.
4. Contracts already have a generic `Evidence` (engine-cited claim). IEF evidence is **industry-scoped, methodology-gated**, and must not be conflated with committee `contracts.Evidence` without an adapter.

**Recommendation:** Keep both. Name IEF types distinctly (`IndustryEvidence`, `IndustryMetric` or reuse planned Metric* names under industry ownership) to avoid colliding with `contracts.Evidence`.

### 2.2 Core types (proposed)

```text
IndustryMetricDefinition
  id, display_name, category, unit, calculation_owner,
  required_inputs, availability, version, status

IndustryMetricReading          # instance for one instrument / period
  metric_id, instrument_key, as_of, value, provenance, quality_flags

EvidenceCategory
  FINANCIAL | BUSINESS_MODEL | INDUSTRY_KPI | MANAGEMENT |
  REGULATORY | CAPITAL_ALLOCATION | COMPETITIVE_POSITION |
  ECONOMIC | MARKET_STRUCTURE | RISK | ESG (optional, deferred default OFF)

EvidenceDefinition
  id, name, category, description,
  related_metric_ids[], interpretation_template,
  dimension_hints[], version, status

EvidenceApplicability          # owned via Methodology (policy)
  evidence_id, industry_id / methodology_id,
  requirement: REQUIRED | OPTIONAL | UNSUPPORTED | MINIMUM_SET_MEMBER,
  peer_use: ALLOWED | CAUTION | FORBIDDEN,
  interpretation_notes[]

EvidenceProvider               # port
  provide(instrument, methodology, context) → IndustryMetricReading[] / raw facts

EvidenceInterpreter            # pure / deterministic
  interpret(definition, readings, context) → IndustryEvidenceObservation

IndustryEvidenceObservation    # immutable artifact
  evidence_id, instrument_key, claim, category,
  supporting_metric_refs[], confidence_band (qualitative, not a score),
  limitations[], as_of, methodology_id+version, provenance

EvidenceSnapshot               # bundle for one instrument under one methodology
  instrument_key, methodology_id, version,
  observations[], gaps[], generated_at

EvidenceBundle                 # multi-instrument for comparison
  methodology_id, snapshots[], shared_gaps[]
```

**No scores. No ranks.** `confidence_band` if used must be categorical (e.g. HIGH/MODERATE/LOW/UNKNOWN) describing **data quality**, not investment attractiveness.

### 2.3 Evidence categories — **support as controlled vocabulary**

Support all listed categories as an enum. **ESG default OFF** until data program exists.

Do **not** require every methodology to populate every category. Applicability is methodology-owned.

---

## 3. Ownership model

| Concern | Owner | Must NOT own |
|---|---|---|
| Evidence / metric **definitions** & registries | **`industry`** (or future `packages/evidence` extracted from industry when size warrants) | Comparison logic; DecisionPack mutation |
| Evidence **applicability** | **IndustryMethodology** | Characteristics; peer membership |
| Evidence **providers** | Data/engine adapters behind ports (data_engine, fundamental, future industry data programs) | Policy |
| Evidence **interpretation** | Industry Evidence Framework (deterministic rules-as-data) | LLM generation |
| DecisionPack | **decision_intelligence** | Industry metric calculation |
| Comparison observations | **comparison** | Evidence definition ownership |
| Generic committee evidence | **contracts.Evidence** | Industry policy |

**Centralization:** Definitions + applicability centralized under AIMF/industry. Production of readings decentralized via providers. Comparison remains industry-agnostic consumer.

**Package recommendation (conservative):**

- **C3.1–C3.2:** Keep inside `packages/industry/` (definitions, applicability, snapshot assembly) to preserve AIMF freeze ownership.
- **C3.3+:** Extract `packages/evidence/` only if industry package grows too large — same ownership rules, new physical package.

Do **not** put IEF inside `comparison` (would make comparison own industry policy).  
Do **not** put IEF inside `decision_intelligence` (would overload DecisionPack with industry economics).

---

## 4. Package structure (proposed)

```
packages/industry/          # C3.1 preferred home
  evidence/
    definitions.py
    metrics.py              # definitions only; calcs later
    applicability.py
    snapshot.py
    registry.py
  … existing AIMF …

packages/comparison/        # C3.2 consumer update
  # accepts optional EvidenceBundle; no ownership

packages/decision_intelligence/  # C3.2 optional refs only
  # DecisionPack may gain evidence_refs / optional snapshot id — not raw dumps

(future) packages/evidence/ # extract if needed
```

---

## 5. Dependency graph

```
contracts ← core
     ↑
 industry (IEF definitions, applicability, snapshot assembly)
     ↑
 data providers (ports implemented outside industry)
     ↑
 decision_intelligence ──optional refs──► EvidenceSnapshot id
     ↑
 comparison ──consumes──► DecisionPack + EvidenceBundle
     ↑
 (future) portfolio / risk / research
```

**Forbidden edges:**

- evidence → comparison (ownership inversion)
- evidence → valuation engine recalculation
- comparison → invent evidence when missing (must record **gap**)

---

## 6. Responsibilities

### Evidence Registry
Register / lookup / list / deprecate `EvidenceDefinition` and `IndustryMetricDefinition`. Prevent duplicate ids. Semver.

### Evidence Definition
Canonical meaning of an evidence type: category, related metrics, interpretation intent, dimension hints.

### Evidence Applicability
Methodology-bound policy: required / optional / unsupported / minimum set; peer-use flags. **Never** from Characteristics alone.

### Evidence Provider
Port: fetch or derive metric readings / factual inputs for an instrument. Deterministic. May return unavailable.

### Evidence Interpreter
Map definition + readings → `IndustryEvidenceObservation` with claim text and limitations. No ranking language.

### Evidence Observation
Immutable, citable output. Comparison and Research cite these — they do not re-interpret ad hoc.

---

## 7. Lifecycle

```
DRAFT → ACTIVE → DEPRECATED → (optional) RETIRED
```

1. **Define** definition + related metrics (may be `REQUIRES_NEW_DATA`).
2. **Bind** applicability on one or more IndustryMethodologies.
3. **Validate** registry integrity (unknown metric refs, conflicting applicability).
4. **Produce** readings via providers when data exists.
5. **Interpret** into observations; record gaps when production fails.
6. **Deprecate** definition versions; methodologies pin versions; no silent swap.
7. **Never delete** historically cited observation artifacts in stored reports (append-only citations).

---

## 8. Versioning approach

- Semver on `EvidenceDefinition`, `IndustryMetricDefinition`, and snapshot schema.
- Methodology pins evidence applicability by `(evidence_id, version)` or “active at assemble time” with pin recorded on `EvidenceSnapshot`.
- ComparisonResult / future reports store **methodology version + evidence snapshot digest** for reproducibility.
- Same rule as AIMF: new versions register beside old; no destructive migrate in-place.

---

## 9. Validation strategy

Reject / fail closed:

| Rule | Outcome |
|---|---|
| Duplicate definition ids | reject register |
| Applicability → unknown evidence/metric | reject |
| REQUIRED evidence missing at snapshot build | gap + degrade comparison dimension; do not invent |
| UNSUPPORTED evidence present | reject or strip with limitation |
| Observation without claim / provenance | reject |
| Ranking/score language in interpreter templates | reject at definition validate |
| Characteristics supplying MetricApplicability/EvidenceApplicability | forbidden (architecture test) |

Comparison behavior when evidence incomplete: **DEGRADED** with explicit gaps (aligns with C2.5 philosophy: refusal/degrade > misleading completeness).

---

## 10. Answers to design questions (summary)

| # | Question | Decision |
|---|---|---|
| 1 | Metric ≠ Evidence? | **Yes — separate** |
| 2 | Categories? | **Yes — controlled enum; ESG optional/off by default** |
| 3 | Ownership? | **Industry/AIMF owns definitions+applicability; comparison consumes** |
| 4 | Lifecycle? | **Versioned registry; deprecate; pin on snapshots** |
| 5 | Methodology specifies required/optional/unsupported/minimum? | **Yes** |
| 6 | DecisionPack contents? | **Evidence references / optional snapshot id — not raw bulk evidence** |
| 7 | Comparison consumes? | **DecisionPack + EvidenceBundle (or pack with resolved refs)** — prefer explicit bundle injection for engine purity |
| 8 | Portfolio reuse? | **Same EvidenceSnapshot / Observation citations; portfolio aggregates citations, does not redefine evidence** |
| 9 | Registry/Definition/Applicability/Provider/Interpreter/Observation? | **Yes — all six roles; see §6** |

### DecisionPack recommendation (detail)

Prefer:

```text
DecisionPack
  …existing fields…
  evidence_snapshot_ref?: { snapshot_id, methodology_id, version, digest }
```

Avoid embedding large raw evidence arrays in the pack (size, churn, industry coupling).  
Research UI resolves refs via Evidence Registry / store.

Comparison Engine preferred signature (future):

```text
compare(request: {
  packs: DecisionPack[],
  evidence?: EvidenceBundle,   # optional in C3.1; required for industry dimensions later
  eligibility_options,
})
```

If `evidence` absent → current C2.5 behavior (DecisionPack-only observations) + limitation “industry evidence not supplied”.

---

## 11. Future roadmap

| Phase | Scope |
|---|---|
| **C3.0** | This design (done as review) |
| **C3.1** | Metric + Evidence definition registries + applicability on Methodology (no providers) |
| **C3.2** | EvidenceSnapshot assembly + gap model; DecisionPack optional ref; Comparison accepts EvidenceBundle |
| **C3.3** | First providers (reuse fundamental/valuation outputs; no new formulas in IEF) |
| **C3.4** | Industry KPI data programs (banking NIM/NPA, etc.) behind ports |
| **C3.5** | Portfolio/Risk consume EvidenceObservation citations |
| **Later** | Optional extract `packages/evidence` |

---

## 12. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Conflating `contracts.Evidence` with IEF | High | Distinct type names; explicit adapter |
| Evidence becomes hidden scoring | High | Ban numeric attractiveness scores; architecture tests on language |
| Methodology required-evidence makes all comparisons REFUSED | Medium | MINIMUM sets; degrade per-dimension; start OPTIONAL-heavy |
| DecisionPack bloat | Medium | Refs only |
| Provider sprawl / industry `if` in comparison | High | Keep interpretation in IEF; comparison stays agnostic |
| Premature package extract | Low | Start in `industry/` |
| Data unavailability masquerading as weak business | High | Mandatory gaps/limitations on missing REQUIRED evidence |

---

## 13. PASS / FAIL

**PASS** (architecture review complete; framework not implemented; not design-frozen until C3.1 spike validates registry ergonomics).

---

## Final question

Is the Industry Evidence Framework sufficiently well-defined to become the next major DSP subsystem?

**YES WITH CONDITIONS**

Conditions:

1. Keep Metric and Evidence separate; do not collapse into DecisionPack fields.
2. Ship C3.1 as registries + applicability only (no provider sprawl) before expanding comparison.
3. Freeze naming relative to `contracts.Evidence` before coding.
4. Comparison must remain valid with **evidence absent** (C2.5 path) until providers exist.
5. Do not design-freeze IEF until one banking + one utility evidence applicability example is written as data (still no runtime providers required).
