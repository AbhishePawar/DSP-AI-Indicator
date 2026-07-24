# Phase E0.0A — Risk Intelligence Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [E0.0 Risk Intelligence Design](E0_0_RISK_INTELLIGENCE_DESIGN.md)  
**Prerequisite stack:** AIMF · IEF · DecisionPack · Comparison · Portfolio (C4.1–C4.6) · **1126 tests green**  
**This phase:** Architecture lock only — **no code, no packages, no package modifications**

---

## Freeze declaration

The following are **authoritative** until an explicit freeze amendment:

1. Risk Intelligence is an **independent subsystem** (not a Portfolio extension).  
2. Risk Intelligence is a **pure consumer** of Portfolio, Monitoring, and citations.  
3. Risk owns **only risk artifacts** listed in §3.  
4. **E1.x is qualitative only** — classical quantitative market-risk metrics are reserved for **E2.x**.  
5. Cite-don’t-embed; cite-don’t-reinterpret Evidence; never re-run Comparison.  
6. No BUY/SELL/OPTIMIZE/TRADE recommendations from Risk.  
7. No composite attractiveness scores or rankings.

Conflicts with this document lose unless a later dated freeze amendment supersedes them.  
On conflicts with E0.0 design prose, **this freeze wins**.

---

## 1. Frozen architecture

```text
DecisionPack ──────────────┐
EvidenceBundle ────────────┤
ComparisonReport ──────────┼── citations only (never owned by Risk)
Portfolio ─────────────────┤
Portfolio Monitoring ──────┘
                │
                ▼
        Risk Intelligence   ← independent package (proposed: packages/risk/)
                │
                ├── RiskProfile
                ├── RiskAssessment
                ├── RiskObservation / RiskDescriptor
                ├── RiskCoverage / RiskConstraint
                ├── RiskSummary
                ├── RiskReport
                └── IntegratedRiskContext
```

| Risk Intelligence **is** | Risk Intelligence **is not** |
|---|---|
| Independent DSP subsystem | A Portfolio package module |
| Portfolio-level risk posture consumer | A security-analysis engine |
| Producer of `RiskReport` | Owner of Portfolio / DI / IEF / Comparison |
| Qualitative risk observer (E1.x) | VaR / Sharpe / beta calculator (E1.x) |
| Implication layer over Monitoring | A change log (that is Monitoring) |

### Boundary one-liners (frozen)

| Subsystem | Answers |
|---|---|
| **Decision Intelligence** | “Should I own it?” (single name) |
| **Portfolio Monitoring** | “What changed?” |
| **Risk Intelligence** | “What does this imply?” (portfolio risk posture) |

---

## 2. Dependency graph

```text
contracts / core
        ▲
        │
portfolio (Portfolio, Monitoring, local citation types)
industry (EvidenceBundleReference only — optional)
        ▲
        │  one-way consume
        │
packages/risk/   ← FROZEN target location (create in E1.0)
        │
        ▼
dsp_platform (additive re-exports only)
```

### Allowed dependencies (E1.x)

`contracts`, `core`, `portfolio`, and citation façades only (`industry` for
`EvidenceBundleReference` if needed). Prefer Portfolio-local citation types
where already frozen.

### Forbidden dependencies (E1.x)

`dsp`, `fundamental`, `economic`, `valuation`, `data_engine`,
`snapshot_bridge`, `orchestration`, `recommendation`, `ai_committee`,
Comparison **engine** (consume reports/refs only), IEF **providers/interpreters**,
Optimizer/OMS packages.

### Cycle ban

- Risk may import Portfolio.  
- Portfolio must **never** import Risk.  
- DI / IEF / Comparison must **never** import Risk.

---

## 3. Canonical contracts (closed set for E1.x)

| Model | Role |
|---|---|
| **RiskProfile** | Mandate / posture lens (identity + descriptive risk preferences) |
| **RiskAssessment** | Assembled assessment for one portfolio as-of |
| **RiskObservation** | Qualitative risk note (no scores / ranks) |
| **RiskDescriptor** | Dimension + human-readable label |
| **RiskCoverage** | Evidence / decision / comparison coverage risk surface |
| **RiskSummary** | Counts, coverage notes, limitations |
| **RiskReport** | Canonical presentation artifact |
| **RiskConstraint** | Risk-policy descriptor (not an optimizer engine) |

**Closed:** this set is frozen for E1.x unless a freeze amendment adds a root.  
Supporting enums/status/context/result types may be added additively without
new aggregate roots.

### Proposed construction split (not yet implemented)

| Component | Owns |
|---|---|
| `RiskAssembler` | Immutable `RiskAssessment` construction from citations |
| `RiskAnalyzer` | Qualitative observations / descriptors / summaries |

---

## 4. Ownership matrix

| Domain | Owns | Must not own |
|---|---|---|
| **Decision Intelligence** | DecisionPack | Portfolio, Risk |
| **Industry (IEF)** | Evidence, Methodology, providers, interpreters | Portfolio, Risk |
| **Comparison** | ComparisonReport | Portfolio, Risk |
| **Portfolio** | Holdings, Constraints, Snapshots, Monitoring history, PortfolioReport | Risk artifacts, engines |
| **Risk Intelligence** | RiskProfile, RiskAssessment, RiskObservation, RiskDescriptor, RiskCoverage, RiskSummary, RiskConstraint, RiskReport | Portfolio, DecisionPack, Evidence, Methodology, Comparison, Trading, Optimization |
| **Quantitative Risk (E2.x)** | Classical market-risk metrics (future) | Portfolio identity |
| **Optimizer / OMS (future)** | Allocation search / execution | Risk ownership of Portfolio |

**No ownership leakage** into upstream domains is permitted.

---

## 5. Responsibility matrix

| May | Must not |
|---|---|
| Read Portfolio / snapshots | Own or mutate Portfolio |
| Read Monitoring timeline / changes | Replace Monitoring |
| Read DecisionPack / Evidence / Comparison **references** | Embed payloads; reinterpret IEF observations; run Comparison |
| Produce qualitative risk observations | Security / valuation / technical analysis |
| Produce descriptive concentration / diversification / exposure / cash posture | Compute returns, alpha, beta, Sharpe, Sortino, VaR, stress tests (E1.x) |
| Produce coverage summaries (evidence / decision / comparison) | Score or rank portfolios |
| Note constraint / coverage risk descriptively | Optimize allocation; recommend trades |
| Produce `RiskReport` | Trading, OMS, performance attribution |

### E1.x in-scope risk types (frozen)

Concentration · Diversification · Single-holding · Cash concentration ·
Sector/industry concentration (when declared) · Evidence coverage risk ·
Decision coverage risk · Constraint risk · Exposure risk · Liquidity risk
(**qualitative only**).

### E1.x non-goals (frozen)

Valuation · Security analysis · Technical analysis · Trading · Optimization ·
Returns · Alpha · Beta · Sharpe · Sortino · VaR · Stress testing · Factor models ·
Statistical market-risk models · Performance analytics.

---

## 6. Future extension points

| Extension | How (no redesign of E1 freeze) |
|---|---|
| **E2.x Quantitative Risk** | New models/metrics package train; separate freeze; still consumer of Portfolio |
| Factor / statistical / market risk | Under E2.x only |
| Performance analytics | Separate future subsystem; may cite RiskReport |
| Optimizer | Consumes RiskReport / constraints; never owned by Risk |
| OMS | Execution only; never owned by Risk |
| Research Intelligence | Narratives over RiskReport citations |

E1 remains **qualitative-only**. E2 is reserved, not specified beyond this lock.

---

## 7. Validation results

| Check | Result |
|---|---|
| Ownership | **PASS** — Risk owns only risk artifacts |
| Dependencies | **PASS** — one-way consumer graph; cycle ban stated |
| Future compatibility | **PASS** — E2 / Optimizer / OMS / Performance can extend by citation |
| No cyclic imports | **PASS** (architectural; no Risk package yet) |
| No responsibility overlap | **PASS** — Monitoring=history; Risk=implication; DI=single-name decision |
| Portfolio freeze intact | **PASS** — Risk is external consumer |

**Overall:** **PASS**

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Risk becomes a scoring engine | Ban composite attractiveness scores / rankings |
| Premature VaR/Sharpe | E1 qualitative-only; E2 separate freeze |
| IEF reinterpretation | Citations / coverage gaps only |
| Blur with Portfolio Analyzer | Portfolio = descriptive; Risk = risk-posture vocabulary |
| Blur with Monitoring | Monitoring = what changed; Risk = implications |
| `RiskConstraint` vs `PortfolioConstraint` duplication | Prefer cite/gap-note over forking policy engines |

---

## 9. Technical debt

1. Package directory name (`risk` vs `risk_intelligence`) — choose at E1.0 start; default **`packages/risk/`**.  
2. Exact wiring of `RiskConstraint` to `PortfolioConstraint` citations — decide in E1.0 models.  
3. Liquidity remains qualitative until market-liquidity contracts exist.  
4. E2.x quantitative surface intentionally underspecified.

---

## 10. Implementation roadmap (post-freeze)

| Phase | Scope | Status |
|---|---|---|
| **E0.0** | Design | **DONE** |
| **E0.0A** | Architecture freeze (this document) | **DONE** |
| **E1.0** | Domain models | **DONE** |
| **E1.1** | RiskAssembler | **DONE** |
| **E1.2** | Qualitative RiskAnalyzer | **DONE** |
| **E1.3** | RiskReport + platform exports | **DONE** |
| **E1.4** | Risk Integration (artifact coordination) | **DONE** |
| **E1.5 / E1.x** | Validation & freeze | **DONE / FROZEN** |
| **E2.x** | Quantitative risk train | Later |

**E1.0 acceptance gate:**

1. This freeze remains in force.  
2. New work lives in `packages/risk/` (or freeze-amended name) with dependencies ⊆ allowed set (§2).  
3. Existing **1126+** tests stay green; Risk changes are additive.  
4. No ranking/scoring types; no engine/provider/interpreter imports; no classical metrics in E1.x.

---

## 11. PASS / FAIL

**PASS** — Risk Intelligence architecture is frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Risk Intelligence architecture freeze** |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | **Qualitative E1 validation & freeze (implemented surface)** |
| [E0_0_RISK_INTELLIGENCE_DESIGN.md](E0_0_RISK_INTELLIGENCE_DESIGN.md) | Design review (historical; superseded on conflicts) |
| [C4_0A_PORTFOLIO_INTELLIGENCE_ARCHITECTURE_FREEZE.md](C4_0A_PORTFOLIO_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Portfolio freeze (Risk = external consumer) |
| [C4_6_PORTFOLIO_MONITORING.md](C4_6_PORTFOLIO_MONITORING.md) | Monitoring = history only |

---

## Final question

Is the Risk Intelligence architecture frozen and stable enough to begin
implementation?

**YES**
