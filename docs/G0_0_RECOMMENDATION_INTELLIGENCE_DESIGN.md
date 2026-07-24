# Phase G0.0 — Recommendation Intelligence Architecture & Design

**Status:** Design review complete · **Not an architecture freeze** (freeze = G0.0A)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative stack frozen · Quantitative Risk **E2.4 FROZEN**  
**Suite gate:** **1281 / 1281** passing (2026-07-21)

## Verdict

**YES WITH CONDITIONS** — Recommendation Intelligence is sufficiently
well-defined to proceed to **G0.0A Architecture Freeze**, then models.

Conditions (must be locked in G0.0A before G1.0 implementation):

1. Independent package / ownership boundary vs legacy Sprint 7.1 mapper.  
2. Cite-only consumption of all frozen upstream reports.  
3. No primary analysis, optimization, execution, or OMS inside the domain.  
4. Transparent rationale + conflict + confidence artifacts required on every
   recommendation option.  
5. Explicit non-ownership of Decision / Evidence / Comparison / Portfolio /
   Risk / Research / Quant metric engines.

---

## 1. Recommended architecture

```text
Decision Intelligence ──── DecisionPack ─────────────┐
Industry Evidence ──────── EvidenceBundle ───────────┤
Comparison ─────────────── ComparisonReport ─────────┤
Portfolio ──────────────── Portfolio / Monitoring ───┼── citations only
Qualitative Risk ───────── RiskReport ───────────────┤   (never owned /
Research ───────────────── ResearchReport ───────────┤    never re-analyzed)
Quantitative Risk ──────── QuantitativeRiskReport ───┘
                │
                ▼
    Recommendation Intelligence
    (independent bounded context · action posture)
                │
                ├── RecommendationIdentity / Profile
                ├── RecommendationOption
                ├── RecommendationScore (categorical / transparent)
                ├── RecommendationRationale
                ├── RecommendationConflict
                ├── RecommendationSummary
                │
                ▼
        RecommendationReport
```

**Consumer pattern (not a stack extension):**

```text
Frozen qualitative + quantitative outputs
        │
        ▼
Recommendation Intelligence  →  RecommendationReport
        │
        ├──► Workflow (H) — approval / investigation steps (outside)
        ├──► Optimizer / OMS — search / execution (outside)
        └──► UI / API / Copilot — presentation adapters (outside)
```

Legacy note: `packages/recommendation/` today hosts Sprint 7.1
`RecommendationMapper` (CommitteeReport → `contracts.Recommendation`).
That mapper is a **narrow committee adapter**, **not** Recommendation
Intelligence. G0.0A must decide whether G evolves that package under a
clear domain façade or introduces a dedicated package name — without
absorbing committee voting / orchestration into the new domain.

---

## 2. Design questions — decisions

### Q1 — Independent bounded context?

**Yes — independent bounded context.**

| Option | Verdict |
|---|---|
| Extend Research (`packages/research/`) | **Reject** — Research answers investigation, not action (F1.4) |
| Extend Qualitative or Quantitative Risk | **Reject** — Risk freezes forbid recommendations |
| Extend Portfolio | **Reject** — Portfolio owns structure / monitoring, not action posture |
| Fold into Decision Intelligence | **Reject** — DI answers instrument-level decision packs, not cross-stack action synthesis |
| Grow only the Sprint 7.1 committee mapper | **Reject as the domain** — mapper is wire translation, not evidence-backed recommendation |
| Independent Recommendation Intelligence package | **Accept** |

**Rationale:**

1. Baseline v1.0 already reserves **Epic G** as a separate consumer of frozen
   reports.  
2. Analysis / DI / Risk / Research / Quant answer **truth / posture /
   investigation / measurable risk** — Recommendation answers **what should
   be done**, which must not leak into those freezes.  
3. Future Optimizer / OMS / Workflow must consume a stable
   `RecommendationReport` without owning upstream engines.  
4. Independence preserves one-way dependency and cite-don’t-embed discipline.

---

### Q2 — What should Recommendation Intelligence own?

| Artifact | Own? | Notes |
|---|---|---|
| `RecommendationIdentity` | **Yes** | Session / thesis / mandate identity |
| `RecommendationProfile` | **Yes** | Aggregate root — cites upstream; owns recommendation artifacts only |
| `RecommendationOption` | **Yes** | Candidate action posture (e.g. hold / reduce / increase / investigate) — **not** an OMS order |
| `RecommendationScore` | **Yes** | Transparent confidence / preference artifact — method-bound; **not** a hidden ML score |
| `RecommendationRationale` | **Yes** | Cite-backed explanation linking options to upstream reports |
| `RecommendationConflict` | **Yes** | Declared tension between upstream signals (e.g. Research gap vs Quant drawdown) |
| `RecommendationSummary` | **Yes** | Counts / coverage / limitations |
| `RecommendationReport` | **Yes** | Canonical immutable presentation snapshot |

**Supporting (citation-only, not ownership):** local reference types for
DecisionPack, EvidenceBundle, ComparisonReport, Portfolio, Monitoring,
RiskReport, ResearchReport, QuantitativeRiskReport (digests / ids only).

**Scoring policy (design constraint for G0.0A):** Prefer categorical or
explicitly method-bound scores with full provenance. Avoid opaque single
floats without method_id / limitations. If numeric preference is used,
apply Decimal policy consistent with Quant (no silent float).

---

### Q3 — What must Recommendation Intelligence never own?

| Artifact / concern | Why forbidden |
|---|---|
| `DecisionPack` | Owned by Decision Intelligence |
| `EvidenceBundle` | Owned by Industry Evidence Framework |
| `ComparisonReport` | Owned by Comparison |
| `Portfolio` / Monitoring payloads | Owned by Portfolio Intelligence |
| Qualitative Risk engines / `RiskReport` ownership | Owned by qualitative Risk |
| Research engines / `ResearchReport` ownership | Owned by Research |
| Quantitative metrics / Quant engines | Owned by Quantitative Risk |
| Execution / orders / fills | OMS / brokerage |
| Trading strategies / portfolio optimization | Optimizer (future) |
| Primary analysis (indicators, valuation, peers) | Analysis / DI / IEF / Comparison |
| Workflow state machines | Epic H |
| LLM prompts / agent loops | Copilot / adapters outside domain |
| Knowledge graph storage | Epic I |

---

### Q4 — Which frozen outputs should it consume?

| Upstream | Consume? | How |
|---|---|---|
| Decision Intelligence (`DecisionPack`) | **Yes** | Local reference / digest citation |
| Industry Evidence (`EvidenceBundle`) | **Yes** | Citation only |
| Comparison (`ComparisonReport`) | **Yes** | Citation only |
| Portfolio / Monitoring | **Yes** | Citation only |
| Qualitative Risk (`RiskReport`) | **Yes** | Citation only |
| Research (`ResearchReport`) | **Yes** | Citation only |
| Quantitative Risk (`QuantitativeRiskReport`) | **Yes** | Citation only |

**Dependency rules (proposed for G0.0A):**

1. **One-way only** — Recommendation may cite upstream; upstream must **never**
   import Recommendation domain.  
2. **Cite, don’t embed** — no re-ownership of upstream aggregates.  
3. **No primary analysis** — never recompute indicators, risk metrics, or
   research insights; only synthesize action posture from cited outputs.  
4. **Runtime deps** — prefer `{core}` (+ optional frozen façade imports only
   if G0.0A explicitly allows); never `data_engine` vendor SDKs, never
   OMS/broker SDKs.  
5. **Partial inputs allowed** — missing upstream citations → conflicts /
   limitations / lower confidence — never invent missing analysis.  
6. **Independent consumption of Qual + Quant Risk** — both reports cited
   separately; Recommendation does not merge their ownership.

---

### Q5 — Responsibilities

| Responsibility | In scope? | Notes |
|---|---|---|
| Evidence / report synthesis for **action** | **Yes** | Structural / citation-based; not new research claims |
| Trade-off evaluation | **Yes** | Between cited options / constraints — transparent |
| Conflict identification | **Yes** | Across upstream reports |
| Confidence assessment | **Yes** | Method-bound; explicit limitations |
| Recommendation generation | **Yes** | Produce options + preferred posture in `RecommendationReport` |
| Action rationale | **Yes** | Every option requires cite-backed rationale |
| Primary security analysis | **No** | DI / Analysis |
| Evidence interpretation engines | **No** | IEF |
| Peer comparison engines | **No** | Comparison |
| Portfolio construction / monitoring | **No** | Portfolio |
| Qualitative / quantitative risk calculation | **No** | Risk / Quant Risk |
| Research investigation agenda | **No** | Research (may *cite* agenda gaps) |
| Optimization / rebalancing search | **No** | Optimizer |
| Order routing / execution | **No** | OMS |

**Proposed pipeline (design; freeze in G0.0A):**

```text
Models → (optional Assembler) → Recommendation Engine → Reporter
                                              → RecommendationReport
```

Assembler optional (citation attachment). Engine owns synthesis of options /
conflicts / confidence. Reporter is presentation-only (no new scores).

---

### Q6 — What remains outside this subsystem?

| Outside | Owner |
|---|---|
| Portfolio optimization / efficient frontier | Future Optimizer |
| Execution / OMS / brokerage | OMS / brokers |
| Workflow / approvals / human gates | Epic H Workflow |
| LLM orchestration / agents | Copilot / app adapters |
| Knowledge graph indexing | Epic I |
| Market-data vendor adapters | data_engine / adapters |
| Committee vote mapping to wire DTOs | Existing Sprint 7.1 mapper (adapter) |
| Charts / UI | Application layer |

---

### Q7 — Relationship with existing subsystems

| Subsystem | Answers |
|---|---|
| **Analysis / DI / IEF / Comparison** | “What is true about this name / peer set?” |
| **Portfolio** | “What do we hold, and how is it structured / changing?” |
| **Qualitative Risk** | “What business and structural risks exist?” |
| **Quantitative Risk** | “What measurable statistical risks exist?” |
| **Research** | “What deserves further investigation?” |
| **Recommendation** | **“What should be done?”** (action posture + rationale) |
| **Optimizer / OMS** (future) | “How do we search / execute that action?” |

**Boundary one-liner:** Recommendation translates **frozen truth and posture
reports** into **transparent, evidence-backed action options** — it does not
discover new truth, and it does not execute trades.

---

## 3. Ownership matrix (summary)

| Domain | Owns | Recommendation relationship |
|---|---|---|
| Decision / IEF / Comparison / Portfolio / Risk / Research / Quant | Their frozen reports | Cited only |
| **Recommendation Intelligence** | Identity, Profile, Option, Score, Rationale, Conflict, Summary, Report | Aggregate owner of action artifacts |
| Optimizer / OMS / Workflow / Copilot | Search / execution / process / UX | Consume `RecommendationReport` externally |

---

## 4. Dependency graph (proposed)

```text
contracts / core
        ▲
        │
frozen upstream packages (DI, industry, comparison, portfolio,
risk, research, quantitative_risk) — cite via local refs preferred
        ▲
        │  one-way consume
        │
packages/recommendation_intelligence/   ← proposed domain name
   OR evolved packages/recommendation/  ← G0.0A naming lock
        │
        └── models / engine / reporter
                │
                ▼
        RecommendationReport

dsp_platform → additive re-exports only

Optimizer / OMS / Workflow / UI
        ▲
        │ consume RecommendationReport
        │ (never owned by Recommendation)
```

**Hard rules:**

- No reverse imports into frozen upstream domains.  
- No cycles.  
- No vendor / broker SDKs in domain.  
- No mutation of Portfolio or upstream reports.

---

## 5. Non-goals (this phase)

- No implementation / no new models / no package creation in G0.0  
- No scoring algorithms  
- No optimization  
- No trading / execution  
- No OMS  
- No LLM orchestration inside the domain design as a required dependency  

---

## 6. Future implementation roadmap

| Phase | Scope | Status |
|---|---|---|
| **G0.0** | Architecture & design (this document) | **DONE (design)** |
| **G0.0A** | Architecture freeze (ownership, deps, pipeline, naming vs legacy mapper) | Planned |
| **G1.0** | Domain models | Planned |
| **G1.1** | Assembler (optional) / citation construction | Planned |
| **G1.2** | Recommendation Engine (options / conflicts / confidence) | Planned |
| **G1.3** | Reporter (`RecommendationReport`) | Planned |
| **G1.4** | Validation & freeze | Planned |
| Later | Optimizer / OMS / Workflow consumers | Separate epics |

---

## 7. Risks & open items for G0.0A

| Item | Severity | Notes |
|---|---|---|
| Package naming vs Sprint 7.1 `recommendation` mapper | High | Must not confuse committee mapping with Recommendation Intelligence |
| Action vocabulary (HOLD / REDUCE / … vs BUY/SELL wire types) | High | Align with `contracts.Recommendation` carefully or keep domain posture separate from OMS verbs |
| Score semantics | Medium | Categorical vs Decimal; method_id mandatory |
| Minimum upstream citation set | Medium | Which reports are required vs optional for COMPLETE status |
| Relationship to Research agenda | Medium | Recommendation may cite gaps; must not own ResearchAgenda |
| Premature optimization leakage | High | Engine must not become a portfolio optimizer |

---

## 8. PASS / FAIL

**PASS** — Recommendation Intelligence architecture is sufficiently designed
for G0.0A freeze. No implementation performed in this phase.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | Recommendation Intelligence design (G0.0) |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |
| [F1_4_RESEARCH_VALIDATION_AND_FREEZE.md](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) | Research freeze (upstream consumer boundary) |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | Qualitative Risk freeze |
| [E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md](E2_4_QUANTITATIVE_RISK_VALIDATION_AND_FREEZE.md) | Quantitative Risk freeze |
| `packages/recommendation/README.md` | Legacy committee → contracts mapper (not G domain) |

---

## Final question

Is Recommendation Intelligence sufficiently well-defined to become the next
bounded context of the DSP AI Indicator platform?

**YES WITH CONDITIONS**
