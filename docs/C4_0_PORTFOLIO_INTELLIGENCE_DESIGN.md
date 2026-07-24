# Phase C4.0 — Portfolio Intelligence Architecture & Design

**Status:** Design review complete · **Superseded on conflicts by** [C4.0A Architecture Freeze](C4_0A_PORTFOLIO_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Prerequisite stack:** AIMF · IEF · DecisionPack · Comparison (C2–C3.7) · 1068 tests green

## Verdict

**YES WITH CONDITIONS** — Portfolio Intelligence is sufficiently defined to be
the next major DSP subsystem after a short **C4.0A architecture freeze** that
locks identity, citation contracts, and the Risk / rebalancing split.

---

## 1. Recommended architecture

```text
Universe / Holdings registry
        │
        ▼
Portfolio  (independent identity)
        │
        ├── PortfolioHolding ──► DecisionPack digest (required citation)
        │                   └──► EvidenceBundle digest (optional)
        │
        ├── PortfolioConstraint (mandate overlays)
        │
        └── PortfolioSnapshot (immutable as-of freeze)
                │
                ├── optional ComparisonReport citations (peer subsets)
                │
                ▼
        Portfolio Intelligence (consumer / aggregator)
                │
                ▼
        PortfolioReport
```

**Role:** Portfolio Intelligence is a **consumer only**. It never replaces
Decision Intelligence, DecisionPack, Industry Methodology, IEF, or Comparison.

---

## 2. Design questions — decisions

### Q1 — What is a Portfolio?

**Decision: Independent object**, not merely a collection of DecisionPacks.

| Option | Verdict |
|---|---|
| Collection of DecisionPacks only | Reject — no weights, cash, mandate, or stable portfolio identity |
| Independent object citing packs | **Accept** |

Holdings **reference** DecisionPack (and optional EvidenceBundle) digests.
The portfolio owns position structure and policy; single-name truth stays on packs.

### Q2 — What belongs inside Portfolio Intelligence?

| Responsibility | In PI? | Notes |
|---|---|---|
| Diversification / sector exposure / concentration | **Yes** | Qualitative descriptors + constraint checks only |
| Evidence aggregation | **Yes** | Coverage, gaps, shared citations — no reinterpretation |
| Decision aggregation | **Yes** | Action/assurance posture across holdings by citation |
| Cash allocation | **Yes** | Declared cash posture / floors |
| Watchlist / monitoring overlays | **Yes** | From pack watchlists + portfolio constraints |
| Rebalancing suggestions | **Partial** | Constraint-gap notes only — not trade algorithms |
| Formal risk models | **No** | Defer to Risk Intelligence |
| Stock / valuation / technical analysis | **No** | Upstream engines / DI |
| Industry methodology / evidence interpretation | **No** | Industry / IEF |
| Comparison ownership | **No** | Comparison Engine |

### Q3 — What does NOT belong?

Portfolio Intelligence must **avoid**:

- Stock analysis, valuation, technical analysis  
- Owning or forking Industry Methodology  
- Evidence interpretation / portfolio-local evidence types  
- Owning Comparison  
- Optimization, mean-variance, CAPM, beta, efficient frontier  
- Ranking, scoring, trading / execution algorithms  

### Q4 — Relationship to DecisionPack

**Decision: DecisionPack + optional EvidenceBundle references.**

- **Required:** each holding cites a DecisionPack digest (canonical single-name contract).  
- **Optional:** EvidenceBundle digest (same C3.6/C3.7 citation philosophy).  
- **Optional:** ComparisonReport citation for eligible peer subsets.  

Never embed pack or bundle payloads inside PortfolioReport.

### Q5 — Relationship to Comparison

**Decision: Consume ComparisonReport; do not perform comparisons.**

- Peer eligibility and qualitative peer notes remain Comparison’s job.  
- Portfolio may attach comparison digests for subsets already compared.  
- Portfolio must not invent industry peer logic or re-run eligibility as owner.

### Q6 — Evidence

**Decision: Aggregate + summarize + reference — never reinterpret.**

Aligned with IEF freeze §11:

1. Cite observations / digests already produced under a methodology version.  
2. Aggregate coverage and gaps across holdings.  
3. Reuse IEF vocabulary — no portfolio-local evidence types.  
4. Never create portfolio “scores” from evidence density.

### Q7 — Risk

**Decision: Formal risk → future Risk Intelligence.**

Portfolio may surface:

- Pack-recorded fragilities (citation)  
- Constraint breaches (weight/sector/cash)  

Portfolio must not own VaR, beta, factor models, or stress engines.

### Q8 — Rebalancing

**Decision: Portfolio owns constraint-gap observations; Recommendation stays single-name.**

| Layer | Owns |
|---|---|
| Portfolio Intelligence | “Holding X exceeds max weight 8%” style notes |
| DecisionPack / Recommendation | Single-security stance |
| Future trading / OMS | Execution (out of DSP C4) |

---

## 3. Domain model proposal

| Model | Responsibility |
|---|---|
| **Portfolio** | Identity, mandate, currency, constraint refs, holding refs |
| **PortfolioHolding** | Instrument, weight/units, DecisionPack digest, optional EvidenceBundle digest |
| **PortfolioSnapshot** | Immutable as-of freeze of holdings + citation digests |
| **PortfolioConstraint** | Max weight, sector/industry caps, cash floor — descriptive policy |
| **PortfolioAllocation** | Target vs actual weights (declared, not optimized) |
| **PortfolioObservation** | Qualitative note — no scores/ranks/winners |
| **PortfolioSummary** | Counts, coverage, concentration descriptors, cash posture |
| **PortfolioReport** | Canonical artifact: summary + observations + limitations + citations |

---

## 4. Ownership model

| Layer | Owns | Must not |
|---|---|---|
| Decision Intelligence | DecisionPack | Portfolio aggregation |
| Industry (AIMF + IEF) | Methodology, evidence, bundles, observations | Portfolio policy |
| Comparison | Peer qualitative reports | Portfolio construction |
| **Portfolio Intelligence** | Holdings, constraints, aggregation, PortfolioReport | Analysis engines, IEF interpretation, comparison logic |
| Risk Intelligence (future) | Risk measures | Portfolio identity |

---

## 5. Dependency graph

```text
contracts / core
      ↑
industry (AIMF + IEF)
      ↑
decision_intelligence (DecisionPack)
      ↑
comparison (optional peer reports)
      ↑
universe (multi-stock packs) ──┐
                               ▼
                    portfolio (future package)
                               │
                               ▼
                         dsp_platform (façade)
```

Forbidden edges (same spirit as Comparison/IEF):

- `portfolio` ↛ analysis engines (`dsp`, `fundamental`, `valuation`, …)  
- `portfolio` ↛ reinterpret IEF (no local interpreters)  
- `portfolio` ↛ mutate DecisionPack / Comparison  

---

## 6. Responsibilities (summary)

**Does:** construct/snapshot portfolios; aggregate decision & evidence citations;
describe concentration/diversification; check constraints; emit PortfolioReport.

**Does not:** analyze securities; value firms; interpret industry evidence;
own comparison; optimize; score; trade.

---

## 7. Future roadmap

| Phase | Scope |
|---|---|
| **C4.0** | Design review (this document) |
| **C4.0A** | Architecture freeze |
| **C4.1** | Portfolio / Holding / Snapshot / Constraint models + registries |
| **C4.2** | Assembler → PortfolioReport (citations only) |
| **C4.3** | Qualitative concentration / diversification / constraint observations |
| **C4.4** | Optional ComparisonReport citation attach |
| **C4.5** | Monitoring / watchlist overlays |
| **C5.x** | Risk Intelligence (separate) |
| Later | Real IEF adapters (shared with all consumers) |

---

## 8. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Hidden portfolio “quality score” | High | Ban composite attractiveness; descriptive summary only |
| Re-interpreting evidence at portfolio layer | High | Digests + IEF observations only; architecture tests |
| Turning rebalancing notes into a trading engine | Medium | Explicit non-goal; notes cite constraints only |
| Absorbing Risk into Portfolio | High | Hard split to Risk Intelligence |
| Requiring Comparison for every portfolio | Medium | Comparison optional; packs + bundles sufficient |

---

## 9. Technical debt (accepted)

- No `packages/portfolio` yet  
- No automatic pack/bundle → holding wiring  
- IEF providers/interpreters still placeholder-rich  
- Risk and execution subsystems not chartered  
- Cash/corporate-action realism deferred  

---

## 10. PASS / FAIL

**PASS** — design gate complete; ready for C4.0A freeze. No code in this phase.

---

## Final question

Is Portfolio Intelligence sufficiently well-defined to become the next major DSP subsystem?

**YES WITH CONDITIONS**

Conditions: freeze (C4.0A) must lock (1) Portfolio as independent object with pack/bundle citations, (2) cite-don’t-reinterpret evidence rules, (3) Risk and optimization remain out of Portfolio, (4) rebalancing = constraint-gap notes only.
