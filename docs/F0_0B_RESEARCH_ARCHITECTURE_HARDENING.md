# Phase F0.0B — Research Architecture Hardening

**Status:** **HARDENED** · Documentation only  
**Date:** 2026-07-21  
**Preceded by:** [F0.0A Architecture Freeze](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Prerequisite:** F0.0A remains authoritative for ownership, dependency graph, and responsibilities  
**This phase:** Harden invariants, claim language, traceability, and guardrails — **no code, no packages, no implementation**

---

## Purpose

Apply approved hardening recommendations to the frozen Research architecture
**without** changing:

- ownership
- dependency direction
- responsibilities
- bounded contexts
- the F0.0A dependency graph

On conflicts about ownership / dependencies / responsibilities, **F0.0A wins**.  
On conflicts about synthesis invariants / claim language / traceability /
guardrails in this document, **this hardening wins** as additive constraint.

---

## 1. Domain Invariants (Frozen)

### Invariant 1 — No computation of value, allocation, or risk metrics

Research **NEVER** computes:

- intrinsic value  
- fair value  
- margin of safety  
- expected return  
- portfolio allocation  
- portfolio optimization  
- risk score  
- probability estimates  
- valuation metrics  

These remain owned by their respective domains (Valuation, Portfolio, Risk,
Recommendation / Optimizer as applicable). Research may **cite** upstream
artifacts that already contain such concepts; it must not derive them.

### Invariant 2 — Read-only consumer

Research is **read-only** with respect to upstream artifacts.

It consumes DecisionPack, EvidenceBundle, ComparisonReport, Portfolio,
Portfolio Monitoring, RiskReport, and IntegratedRiskContext citations.

It **never modifies** those artifacts.

### Invariant 3 — Insights require evidence provenance

Every `ResearchInsight` **MUST** trace back to one or more Evidence references
(directly or via observations that themselves cite Evidence).

No free-floating insights are allowed.

```text
Evidence
    ↓
Observation
    ↓
Insight
```

Insights may additionally cite DecisionPack, Comparison, Portfolio, Monitoring,
or Risk artifacts for cross-subsystem synthesis, but Evidence provenance remains
mandatory for insight validity under this hardening.

### Invariant 4 — Conflicts are descriptive only

`ResearchConflict` objects are **descriptive only**.

- Research **records** conflicts between cited subsystem outputs.  
- Research **never resolves** them.  

Resolution belongs to analysts or future workflow layers (outside the frozen
domain).

### Invariant 5 — Agenda items are investigative only

`ResearchAgenda` items are **investigative**.

They may recommend research activities only (e.g. gather evidence, validate a
citation, reconcile a conflict, inspect coverage).

They may **never** recommend:

- Buy  
- Sell  
- Hold  
- Portfolio actions  
- Position sizing  

### Invariant 6 — ResearchReport immutability

`ResearchReport` is **immutable**.

It represents a snapshot in time.

Later monitoring events (or new synthesis runs) generate **new** reports rather
than mutating previous ones.

---

## 2. Claim Language Policy

### Approved vocabulary (preferred)

| Prefer |
|---|
| Observe |
| Suggest |
| Indicate |
| Appears |
| Evidence supports |
| Evidence contradicts |
| Requires validation |
| Needs investigation |
| Potentially |
| Likely |
| Possible |

### Forbidden vocabulary (avoid)

| Avoid |
|---|
| Proves |
| Guaranteed |
| Certain |
| Definitely |
| Must buy |
| Must sell |
| Risk-free |
| Impossible |

F1.0 models **shall** align claim-language guards with Portfolio / Risk and
extend them to cover this Research policy (implementation detail deferred to
F1.0 — this document freezes the policy only).

---

## 3. Traceability Rules

Every synthesized object must preserve traceability / provenance.

No synthesized object may exist without provenance.

### Required provenance shape (illustrative)

```text
Insight
 ├── Observation IDs
 ├── Evidence IDs
 └── Citation references
     (DecisionPack / Comparison / Portfolio / Monitoring / Risk as applicable)
```

| Synthesized object | Minimum provenance |
|---|---|
| `ResearchObservation` | Upstream citation refs (and Evidence when evidence-derived) |
| `ResearchInsight` | Observation IDs **and** Evidence IDs (Invariant 3) |
| `ResearchConflict` | Cited artifact refs on each side of the conflict |
| `ResearchGap` | Coverage dimension + missing citation / artifact refs |
| `ResearchAgenda` item | Gap / conflict / observation / insight refs that motivate it |

Assemblers may construct citation structure without synthesis. Synthesizers
must attach provenance to every insight, conflict, gap, and agenda item they
emit.

---

## 4. Decision Boundary

Research must **never** become a decision engine.

| Subsystem | Answers |
|---|---|
| **Research** | “What should be investigated next?” |
| **Risk** | “What could happen?” / qualitative implication & posture |
| **Recommendation** | “What action is recommended?” |
| **Portfolio** | “What should be owned?” (structure / holdings / mandate) |

Research may surface investigation priorities. It must not authorize trades,
allocations, or action recommendations.

---

## 5. Architectural Guardrails

Explicitly **prohibited** inside the frozen Research domain (`packages/research/`
when created):

| Prohibited | Belongs instead |
|---|---|
| Reverse imports (upstream importing Research) | Cycle ban — F0.0A |
| Circular dependencies | F0.0A dependency graph |
| Embedded LLM logic | App / LLM adapters (extension point) |
| API providers | Data engine / IEF providers |
| Database persistence | Infrastructure / research memory services |
| Workflow orchestration | Workflow automation layer |
| Agent logic | Application / agent runtime |
| Automatic trading decisions | OMS / Recommendation |

These remain **outside** the frozen domain model. F0.0A ownership and
dependency direction are unchanged.

---

## 6. PASS Criteria

| Criterion | Status |
|---|---|
| Research remains a pure synthesis bounded context | ✓ |
| No ownership overlap exists | ✓ |
| Every synthesized artifact is traceable | ✓ |
| Decision authority remains outside Research | ✓ |
| Architecture freeze from F0.0A remains unchanged | ✓ |

---

## Related documents

| Doc | Role |
|---|---|
| [F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | **Authoritative architecture freeze** (ownership / deps / responsibilities) |
| **This file** | Additive hardening (invariants / claim language / traceability / guardrails) |
| [F0_0_RESEARCH_INTELLIGENCE_DESIGN.md](F0_0_RESEARCH_INTELLIGENCE_DESIGN.md) | Design review (historical) |

---

## STATUS

**PASS — Architecture hardened and ready for F1.0 implementation.**
