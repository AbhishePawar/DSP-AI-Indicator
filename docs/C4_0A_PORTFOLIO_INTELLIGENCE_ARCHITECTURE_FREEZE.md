# Phase C4.0A — Portfolio Intelligence Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [C4.0 Portfolio Intelligence Design](C4_0_PORTFOLIO_INTELLIGENCE_DESIGN.md)  
**Prerequisite stack:** AIMF · IEF · DecisionPack · Comparison (through C3.7) · **1068 tests green**  
**This phase:** Architecture lock only — **no code, no packages, no package modifications**

---

## Freeze declaration

The following are **authoritative** until an explicit freeze amendment:

1. Portfolio is an **independent aggregate root** (canonical multi-security contract).  
2. Portfolio Intelligence is a **consumer only**.  
3. Cite-don’t-reinterpret for DecisionPack / Evidence / Comparison citations.  
4. Risk models and portfolio optimization are **out of Portfolio**.  
5. Rebalancing = **constraint-gap observations only** (never BUY/SELL/ROTATE/OPTIMIZE).  
6. Domain model set in §5 is closed unless a freeze amendment adds a root.

Conflicts with this document lose unless a later dated freeze amendment supersedes them.

---

## 1. Frozen architecture

### Canonical contracts (platform-wide)

| Contract | Role |
|---|---|
| **DecisionPack** | Canonical **single-security** contract |
| **EvidenceBundle** (+ `EvidenceBundleReference`) | Canonical **evidence** contract |
| **ComparisonReport** | Canonical **peer-comparison** contract |
| **Portfolio** (+ `PortfolioReport`) | Canonical **multi-security** contract |

### What Portfolio is / is not

| Portfolio **is** | Portfolio **is not** |
|---|---|
| Independent aggregate root | A bag of DecisionPacks |
| Multi-security identity + holdings + policy | A ComparisonReport |
| Citation aggregator + qualitative descriptors | An EvidenceBundle |
| Producer of `PortfolioReport` | An analysis engine |

```text
Universe metadata
        │
        ▼
Portfolio  (aggregate root)
        │
        ├── PortfolioHolding ──► DecisionPack digest (required)
        │                   └──► EvidenceBundleReference (optional)
        ├── PortfolioConstraint / PortfolioAllocation
        ├── PortfolioSnapshot (immutable as-of)
        │         └── ComparisonReport citation (optional, peer subsets)
        ▼
Portfolio Intelligence (consumer / aggregator)
        │
        ▼
PortfolioReport
```

### Consumer-only rule (frozen)

Portfolio Intelligence **consumes** finished upstream artifacts.  
It **never** runs providers, interpreters, engines, or comparison logic as owner.

---

## 2. Dependency graph (frozen)

```text
contracts / core
      ↑
industry (AIMF + IEF)          ── definitions, bundles, observations
      ↑
decision_intelligence          ── DecisionPack
      ↑
comparison                     ── ComparisonReport (optional input)
      ↑
universe                       ── multi-stock pack production / metadata
      ↑
portfolio  (future package)    ── aggregate root + PortfolioReport
      ↑
dsp_platform                   ── façade only
```

### Allowed inbound edges (future `portfolio`)

| May depend on | For |
|---|---|
| `contracts`, `core` | Shared types / validation |
| `decision_intelligence` | DecisionPack / digests |
| `industry` | EvidenceBundleReference, industry/sector vocabulary (citation only) |
| `comparison` | ComparisonReport digests (optional) |
| `universe` | Universe metadata / successful pack sets (optional) |

### Forbidden edges (frozen)

| Must not depend on | Why |
|---|---|
| `dsp`, `fundamental`, `economic`, `valuation` | Stock analysis / valuation ownership |
| `data_engine`, `snapshot_bridge` | Data plane |
| `orchestration`, `recommendation`, `ai_committee` | Single-name pipeline ownership |
| Industry **Providers** / **Interpreters** (execution) | Evidence production stays in Industry |
| Cyclic edge back into DI / Comparison / Industry as owner | Keeps Portfolio consumer-only |

**No cyclic dependencies** among DI ↔ Comparison ↔ Portfolio ↔ Industry ownership roles.

---

## 3. Ownership matrix (frozen)

| Owner | Owns | Must not own |
|---|---|---|
| **Decision Intelligence** | DecisionPack | Portfolio aggregation |
| **Industry (AIMF + IEF)** | Methodology, evidence defs, providers, interpreters, bundles, observations | Portfolio policy / holdings |
| **Comparison** | ComparisonReport | Portfolio construction |
| **Portfolio Intelligence** | Holdings, constraints, allocation descriptors, portfolio observations / summaries / reports, monitoring state, snapshots | Engines, IEF interpretation, comparison logic, risk models |
| **Risk Intelligence** (future) | Risk models, portfolio risk analytics | Portfolio identity / holdings registry |
| **Research Intelligence** (future) | Research presentation / narratives over citations | Re-interpretation of evidence or packs |

---

## 4. Responsibility matrix (frozen)

### IN SCOPE (Portfolio)

| Responsibility | Form |
|---|---|
| Holdings | Identity, weights/units, pack/bundle citations |
| Cash position | Declared cash posture |
| Allocation descriptors | Target vs actual (declared, not optimized) |
| Diversification descriptors | Qualitative only |
| Concentration descriptors | Qualitative only |
| Constraint-gap observations | Policy breach notes |
| Decision citation aggregation | Across holdings’ DecisionPack digests |
| Evidence citation aggregation | Coverage / gaps / shared digests — no reinterpretation |
| Monitoring state | Watchlists, review flags (non-trading) |
| Portfolio snapshots | Immutable as-of freezes |
| Portfolio reports | Canonical multi-security investor artifact |

### OUT OF SCOPE (Portfolio must never)

| Forbidden | Belongs to |
|---|---|
| Stock / technical / fundamental analysis | Engines / DI pipeline |
| Valuation | Valuation Engine / DI |
| Industry methodology | Industry |
| Evidence interpretation / provider resolution | IEF |
| Comparison ownership | Comparison |
| Risk calculations | Risk Intelligence |
| Portfolio optimization / mean-variance / CAPM / beta / frontier | Never in C4 Portfolio; future Risk/optimizer charters only |
| Trading logic / execution | Out of DSP C4 |
| Ranking / scoring / attractiveness composites | Banned platform-wide for Portfolio |

### Rebalancing (frozen)

| Allowed | Forbidden |
|---|---|
| “Technology allocation exceeds preferred limit.” | BUY / SELL / ROTATE / OPTIMIZE recommendations |
| Constraint-gap `PortfolioObservation` | Trade lists, order sizing, tax-lot logic |

BUY/SELL/ROTATE/OPTIMIZE — if ever needed — require a **separate** charter (Recommendation / Risk / OMS), not a quiet Portfolio expansion.

---

## 5. Domain model freeze

**Closed set of canonical models** (no additional aggregate roots without freeze amendment):

| Model | Aggregate role | Responsibility |
|---|---|---|
| **PortfolioIdentity** | Identity facet | Stable id / name / mandate label / currency |
| **Portfolio** | **Aggregate root** | Holdings refs, constraint refs, monitoring hooks |
| **PortfolioHolding** | Entity under Portfolio | Instrument, weight/units, DecisionPack digest, optional EvidenceBundleReference |
| **PortfolioSnapshot** | Immutable freeze | As-of holdings + citation digests |
| **PortfolioAllocation** | Value object | Declared target vs actual weights |
| **PortfolioConstraint** | Policy | Caps/floors (weight, sector/industry, cash) — descriptive |
| **PortfolioObservation** | Value object | Qualitative note — no scores/ranks/winners |
| **PortfolioSummary** | Value object | Counts, coverage, concentration/cash descriptors |
| **PortfolioReport** | Output artifact | Summary + observations + limitations + citations |

### Citation rules (frozen)

1. Holdings **require** a DecisionPack citation (digest / ref).  
2. EvidenceBundleReference is **optional** per holding.  
3. ComparisonReport citation is **optional** at snapshot/report level for peer subsets.  
4. Payloads are **not** embedded; digests pin versions.  
5. No portfolio-local evidence types — reuse IEF vocabulary only (IEF §11).

---

## 6. Extension points (frozen)

| Future system | How it plugs in without redesign |
|---|---|
| **Risk Intelligence** | Consumes `PortfolioSnapshot` / `PortfolioReport` citations; adds risk analytics; does not redefine holdings |
| **Research Intelligence** | Renders PortfolioReport + pack/evidence/comparison citations; no reinterpretation |
| **Portfolio Monitoring** | Extends monitoring state / watchlists on Portfolio; emits observations; no trading |
| **New industries** | Via Industry methodology/evidence versions only — Portfolio unchanged |
| **Real IEF adapters** | Improve cited bundles upstream — Portfolio citation surface unchanged |
| **Optimizer / OMS** (if ever chartered) | Separate package; reads constraints + snapshots; **never** merges into Portfolio ownership |

Pattern: **extend by citation and new consumer packages**, never by forking Portfolio into engines or IEF.

---

## 7. Architecture validation

| Check | Result |
|---|---|
| No cyclic ownership DI ↔ Comparison ↔ Portfolio ↔ Industry | **PASS** (consumer DAG) |
| Clear ownership matrix | **PASS** (§3) |
| No duplicated responsibilities (evidence / comparison / packs) | **PASS** (cite only) |
| Portfolio remains consumer-only | **PASS** (§1, §2) |
| Risk Intelligence fits without redesign | **PASS** (§6) |
| Research Intelligence fits without redesign | **PASS** (§6) |
| Portfolio Monitoring fits without redesign | **PASS** (§6) |
| Independent aggregate root (not pack bag) | **PASS** |

---

## 8. Risks (frozen awareness)

| Risk | Severity | Mitigation |
|---|---|---|
| Hidden portfolio attractiveness / quality score | High | Explicit ban; descriptive summary only |
| Re-interpreting evidence at portfolio layer | High | Digests + IEF observations only; architecture tests in C4.1+ |
| Constraint notes becoming a trading engine | Medium | Rebalancing freeze (§4); separate charter required |
| Absorbing Risk into Portfolio | High | Risk Intelligence ownership locked |
| Requiring Comparison for every portfolio | Medium | Comparison optional |
| Extra aggregate roots proliferating | Medium | Closed model set (§5) |

---

## 9. Technical debt (accepted until implementation phases)

- No `packages/portfolio` yet (intentional until C4.1).  
- No assembler / persistence / monitoring implementation.  
- IEF providers/interpreters still placeholder-rich (shared upstream debt).  
- Risk Intelligence and OMS not chartered.  
- Cash/corporate-action realism deferred.  
- C4.0 design doc remains historical; **this freeze wins on conflict**.

---

## 10. Implementation roadmap (post-freeze)

| Phase | Scope | Status |
|---|---|---|
| **C4.0** | Design review | **DONE** |
| **C4.0A** | Architecture freeze (this document) | **DONE** |
| **C4.1** | Models + registries (`PortfolioIdentity` … `PortfolioReport`) | **DONE** (models; registries deferred) |
| **C4.2** | Assembler → Portfolio (citations only) | **DONE** |
| **C4.3** | Concentration / diversification / constraint-gap observations | **DONE** |
| **C4.4** | Optional ComparisonReport citation attach / enrichment | **DONE** |
| **C4.5** | Static Portfolio validation & architecture freeze | **DONE** |
| **C4.6** | Monitoring / watchlist state | **DONE** |
| **C5.x / E0+** | Risk Intelligence (independent subsystem) | **E0.0 / E0.0A DONE** · E1.x Planned |

**C4.1 acceptance gate (conditions to start coding):**

1. This freeze remains in force.  
2. New work lives in `packages/portfolio/` (or approved name) with dependencies ⊆ allowed set (§2).  
3. Existing **1068+** tests stay green; Portfolio changes are additive.  
4. No ranking/scoring types; no engine imports; no IEF interpreter calls from Portfolio.

---

## 11. PASS / FAIL

**PASS** — Portfolio Intelligence architecture is frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Portfolio Intelligence architecture freeze** |
| [C4_0_PORTFOLIO_INTELLIGENCE_DESIGN.md](C4_0_PORTFOLIO_INTELLIGENCE_DESIGN.md) | Design review (historical; superseded on conflicts) |
| [C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md](C4_5_PORTFOLIO_VALIDATION_AND_FREEZE.md) | Static Portfolio subsystem validation & freeze (C4.1–C4.4 baseline) |
| [C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md](C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md) | IEF freeze (Portfolio = cite, don’t reinterpret) |
| [C2_AIMF_ARCHITECTURE_FREEZE.md](C2_AIMF_ARCHITECTURE_FREEZE.md) | AIMF freeze |

---

## Final question

Is the Portfolio Intelligence architecture now frozen and stable enough to begin implementation without requiring future architectural redesign?

**YES**
