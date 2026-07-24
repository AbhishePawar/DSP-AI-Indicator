# Phase F0.0 — Research Intelligence Architecture & Design

**Status:** Design review complete · **Superseded on conflicts by** [F0.0A Architecture Freeze](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Prerequisite stack:** AIMF · DI · IEF · Comparison · Portfolio (C4 frozen) · Qualitative Risk (E1.5 frozen)  
**Suite gate:** **1186 / 1186** passing (2026-07-21)

## Verdict

**YES WITH CONDITIONS** (at design time) — conditions satisfied by F0.0A freeze.
See [F0.0A](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md) for the authoritative
lock and **YES** to begin F1.0 implementation.

---

## 1. Recommended architecture

```text
DecisionPack ──────────────┐
EvidenceBundle ────────────┤
ComparisonReport ──────────┤
Portfolio ─────────────────┼── citations only (never owned)
Portfolio Monitoring ──────┤
RiskReport ────────────────┤
IntegratedRiskContext ─────┘
                │
                ▼
        Research Intelligence   (independent subsystem · pure consumer)
                │
                ├── ResearchProfile / ResearchIdentity
                ├── ResearchObservation / ResearchInsight
                ├── ResearchConflict / ResearchGap
                ├── ResearchAgenda / ResearchPriority
                ├── ResearchCoverage / ResearchSummary
                │
                ▼
           ResearchReport
```

**Decision (Q1):** Research Intelligence is an **independent subsystem**, not an
extension of Risk, Portfolio, or Decision Intelligence.

| Option | Verdict |
|---|---|
| Risk package extension (`packages/risk/`) | Reject — Risk is frozen qualitative posture; research synthesis would violate E1.5 |
| Portfolio extension | Reject — Portfolio is frozen structure / history |
| Platform façade only (no package) | Reject — needs stable domain ownership and contracts |
| Independent subsystem (`packages/research/` proposed) | **Accept** |

**Rationale:** Research sits at the top of the qualitative stack. It orchestrates
**knowledge** questions across frozen peers. Keeping it independent preserves
all lower freezes and mirrors Comparison / Portfolio / Risk as peer consumers.

Research Intelligence is a **pure consumer**. It never replaces Decision
Intelligence, IEF, Comparison, Portfolio, Monitoring, or Risk.

---

## 2. Design questions — decisions

### Q1 — Independent package?

**Yes — independent package** (proposed: `packages/research/`).

| Reason | Detail |
|---|---|
| Freeze integrity | Risk / Portfolio / DI / IEF must not absorb research orchestration |
| Clear ownership | Research artifacts need a single aggregate owner |
| Extension surface | E2 Quant, Optimizer, OMS, LLM adapters can consume `ResearchReport` without redesign |
| Composition | `dsp_platform` re-exports only — Research must not import the platform |

### Q2 — What should Research own?

| Artifact | Own? | Notes |
|---|---|---|
| `ResearchIdentity` | **Yes** | Stable research-session / thesis identity |
| `ResearchProfile` | **Yes** | Aggregate root — cites upstream; owns only research artifacts |
| `ResearchObservation` | **Yes** | Descriptive notes about knowledge state (not risk posture) |
| `ResearchInsight` | **Yes** | Cross-subsystem synthesis statement (cite-backed) |
| `ResearchConflict` | **Yes** | Declared inconsistency between cited subsystem outputs |
| `ResearchGap` | **Yes** | Missing / incomplete evidence, decision, comparison, or risk coverage |
| `ResearchAgenda` | **Yes** | Ordered investigation plan |
| `ResearchPriority` | **Yes** | Categorical priority for agenda items (not a score) |
| `ResearchCoverage` | **Yes** | Knowledge-coverage posture across subsystems |
| `ResearchSummary` | **Yes** | Counts / limitation notes — descriptive only |
| `ResearchReport` | **Yes** | Canonical presentation artifact |

**Ownership rule:** Research owns **knowledge-orchestration artifacts only**.
Every insight, conflict, gap, and agenda item must **cite** upstream digests /
ids — never embed or re-derive them.

### Q3 — What must Research never own?

| Forbidden ownership | Why |
|---|---|
| `DecisionPack` | DI owns single-name decision truth |
| `EvidenceBundle` | Industry / IEF owns evidence |
| `ComparisonReport` | Comparison owns peer comparison |
| `Portfolio` / Monitoring | Portfolio owns structure and change history |
| `RiskProfile` / `RiskReport` / `IntegratedRiskContext` | Risk owns posture / qualitative risk presentation |
| Analysis engines | AIMF / domain engines stay upstream |
| Trading / Optimization | External Optimizer / OMS |
| Quantitative models | E2 Quantitative Risk (and peers) |

### Q4 — Inputs and dependency rules

**Consume (cite only):**

| Input | Use in Research |
|---|---|
| `DecisionPack` (refs) | Decision coverage / outstanding decision questions |
| `EvidenceBundle` (refs) | Evidence completeness / gaps |
| `ComparisonReport` (refs) | Peer-comparison conflicts / incompleteness |
| `Portfolio` (refs) | Scope of holdings / mandate context |
| `Portfolio Monitoring` (refs) | “What changed?” → candidate investigation triggers |
| `RiskReport` | Qualitative posture citations |
| `IntegratedRiskContext` | Coordinated risk bundle for synthesis |

**Dependency rules (proposed F1.x):**

```text
Allowed:   core, portfolio, risk, industry (citation façades only)
Forbidden: dsp, fundamental, economic, valuation, data_engine,
           snapshot_bridge, orchestration, recommendation, ai_committee,
           comparison engine, IEF providers/interpreters, optimizer/OMS,
           dsp_platform (except as external re-exporter)
```

- Research may import Portfolio / Risk.  
- Portfolio / Risk / DI / IEF / Comparison must **never** import Research.  
- No provider execution · no engine execution · no reverse ownership.

### Q5 — Primary responsibilities

| Responsibility | In Research? | Notes |
|---|---|---|
| Cross-subsystem synthesis | **Yes** | Insights citing multiple upstream artifacts |
| Research priorities | **Yes** | Categorical `ResearchPriority` on agenda items |
| Outstanding questions | **Yes** | Explicit open questions for analysts |
| Evidence gaps | **Yes** | From citation coverage — no reinterpretation |
| Coverage gaps | **Yes** | Decision / evidence / comparison / risk / monitoring |
| Conflict detection | **Yes** | Structural / declared conflicts between cited outputs |
| Research agenda generation | **Yes** | Ordered next investigations |
| Re-running DI / Comparison / Risk / Portfolio analysis | **No** | Cite only |
| Assigning RiskLevel / computing VaR | **No** | Risk / E2 |
| Trade recommendations | **No** | OMS / recommendation layers |

**Mission answers (canonical):**

| Question | Research role |
|---|---|
| What has changed? | Cite Monitoring; surface change-triggered agenda items |
| What deserves further investigation? | Prioritized agenda |
| Where is evidence incomplete? | `ResearchGap` / coverage |
| Where do subsystem outputs conflict? | `ResearchConflict` |
| What should the analyst research next? | `ResearchAgenda` → `ResearchReport` |

### Q6 — What must remain outside Research?

- Valuation  
- Security analysis  
- Risk calculations (qualitative or quantitative)  
- Trading  
- Optimization  
- Forecasting  
- Statistical models  
- **LLM-specific reasoning** as a domain dependency  

**LLM note:** Prompting / model adapters may *render* or *assist* from
`ResearchReport` in application layers. The Research **domain** must not
require a specific LLM, embed model weights, or treat model text as owned
truth. Synthesis rules stay deterministic / structural over citations.

### Q7 — Relationship with Monitoring

| Subsystem | Answers |
|---|---|
| **Portfolio Monitoring** | “What changed?” |
| **Risk Intelligence** | “What is the qualitative implication?” |
| **Research Intelligence** | “What should be investigated next?” |

Monitoring produces change history. Risk interprets posture implications.
Research turns change + gaps + conflicts into an **investigation agenda**.
Research must not become a change log or a risk engine.

### Q8 — Relationship with Risk

| Dimension | Risk | Research |
|---|---|---|
| Focus | Qualitative **posture** | **Knowledge completeness** |
| Primary output | `RiskReport` / `IntegratedRiskContext` | `ResearchReport` / agenda |
| Owns RiskLevel descriptors? | Yes (categorical) | No — cite Risk only |
| Owns gaps/conflicts across DI/IEF/Comparison/Portfolio/Risk? | Coverage within risk lens | Yes — cross-subsystem |

Risk evaluates “how exposed / covered is the portfolio qualitatively?”  
Research evaluates “what do we still need to know, reconcile, or investigate?”

### Q9 — Recommended domain models

Proposed F1.0 model set (design only — not implemented):

| Model | Purpose |
|---|---|
| `ResearchIdentity` | Id / name / created_at |
| `ResearchProfile` | Aggregate root |
| `ResearchObservation` | Knowledge-state observation |
| `ResearchInsight` | Cite-backed synthesis statement |
| `ResearchConflict` | Declared cross-artifact conflict |
| `ResearchGap` | Missing / incomplete knowledge |
| `ResearchAgenda` | Ordered investigation items |
| `ResearchPriority` | Categorical priority enum (e.g. HIGH / MEDIUM / LOW / UNKNOWN) — **not a score** |
| `ResearchCoverage` | Subsystem knowledge-coverage posture |
| `ResearchSummary` | Descriptive counts / limitations |
| `ResearchReport` | Canonical presentation |

**Suggested pipeline (future F1.x — not in this phase):**

```text
Assembler  → constructs ResearchProfile (citations)
Synthesizer / Analyzer → insights, gaps, conflicts, agenda (structural)
Reporter   → ResearchReport
Integrator → optional coordination bundle (if needed)
```

Names may be frozen in F0.0A; “Synthesizer” vs “Analyzer” is a freeze detail —
behavior must remain **synthesis over citations**, never re-analysis.

---

## 3. Domain model proposal (summary)

```text
ResearchProfile
  ├── identity: ResearchIdentity
  ├── citations: DecisionPack / Evidence / Comparison / Portfolio /
  │              Monitoring / RiskReport / IntegratedRiskContext refs
  ├── observations: ResearchObservation[]
  ├── insights: ResearchInsight[]
  ├── conflicts: ResearchConflict[]
  ├── gaps: ResearchGap[]
  ├── agenda: ResearchAgenda (items + ResearchPriority)
  ├── coverage: ResearchCoverage[]
  └── summary: ResearchSummary
        │
        ▼
   ResearchReport
```

All collections immutable; foreign ownership rejected; claim-language guards
aligned with Portfolio / Risk (no BUY/SELL/score/rank/VaR/…).

---

## 4. Ownership model

| Domain | Owns | Research relationship |
|---|---|---|
| Decision Intelligence | `DecisionPack` | Cited |
| Industry (IEF) | Evidence | Cited |
| Comparison | `ComparisonReport` | Cited |
| Portfolio | Portfolio + Monitoring | Cited |
| Risk | Risk artifacts + `IntegratedRiskContext` | Cited |
| **Research** | Research artifacts listed in Q2 | Aggregate owner |
| E2 Quant / Optimizer / OMS | Metrics / search / execution | External consumers of reports — never owned by Research |

---

## 5. Dependency graph

```text
contracts / core
        ▲
        │
portfolio (frozen) ──┐
risk (frozen E1) ────┼── one-way consume (citations)
industry (refs) ─────┘
        ▲
        │
packages/research/   ← proposed independent package
        │
        ▼
dsp_platform (additive re-exports only)
```

**Cycle ban:** nothing below Research imports Research.

---

## 6. Responsibility matrix

| Component (future) | Owns | Must not |
|---|---|---|
| Research models | Structure & invariants | Pipelines |
| Assembler | Construction / citations | Synthesis invention beyond structure |
| Synthesizer / Analyzer | Insights, gaps, conflicts, agenda | Re-running upstream engines; RiskLevel assignment; quant |
| Reporter | `ResearchReport` presentation | Creating new analysis |
| Integrator (optional) | Coordination bundle | Monitoring / Risk execution |

---

## 7. Architectural principles (locked at design)

1. Research **synthesizes**.  
2. Research never **re-analyzes** upstream.  
3. Research never **reinterprets** Evidence.  
4. Research never **recalculates** Risk.  
5. Research never **recomputes** Portfolio.  
6. Research **cites** upstream artifacts.  
7. Research never emits BUY/SELL/OPTIMIZE/TRADE.  
8. Research never owns classical quantitative models (E2).  
9. Research domain stays **LLM-agnostic**.

---

## 8. Future implementation roadmap

| Phase | Scope | Status |
|---|---|---|
| **F0.0** | Architecture & design (this document) | **DONE (design)** |
| **F0.0A** | Architecture freeze | **DONE / FROZEN** — see [F0.0A](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md) |
| **F1.0** | Domain models | Planned |
| **F1.1** | Research Assembler | Planned |
| **F1.2** | Qualitative synthesizer (gaps / conflicts / agenda) | Planned |
| **F1.3** | Research Reporter | Planned |
| **F1.4** | Integration / platform exports (as needed) | Planned |
| **F1.x** | Validation & freeze | Planned |
| **Later** | LLM presentation adapters (app layer, not domain) | Optional |

---

## 9. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Research becomes a second Risk engine | High | Freeze posture vs knowledge split (Q7–Q8) |
| Evidence reinterpretation via “insights” | High | Cite-only; no providers/interpreters |
| Agenda becomes trade recommendations | High | Claim-language bans; no action verbs as instructions |
| LLM coupling in domain models | Medium | LLM-agnostic domain; adapters outside package |
| Priority mistaken for attractiveness score | Medium | Categorical enum only; no numeric ranks |
| Scope creep into forecasting / quant | High | Explicit non-goals; E2 reservation |

---

## 10. Technical debt / open freeze items (F0.0A)

1. Exact package name (`research` vs `research_intelligence`).  
2. “Synthesizer” vs “Analyzer” naming for F1.2.  
3. Whether `ResearchPriority` is enum-only or includes mandate overlays.  
4. Depth of Monitoring citation (ref only vs change-event refs).  
5. Whether F1 needs an Integrator symmetric to Risk E1.4.  
6. Conflict detection rules: structural citation mismatches only vs
   limited declared-field comparisons (must not re-run Comparison).

---

## 11. PASS / FAIL

**PASS** — Design complete for architecture freeze.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | Research Intelligence design review |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | Qualitative Risk freeze (upstream) |
| [C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md](C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md) | Portfolio freeze |
| [E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md](E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Risk architecture (Research = future consumer) |

---

## Final question

Is Research Intelligence sufficiently well-defined to become the final
qualitative orchestration layer of the DSP AI Indicator platform?

**YES WITH CONDITIONS** (design-time)

**Resolved by F0.0A:** architecture frozen — begin F1.0 per
[F0.0A](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md).
