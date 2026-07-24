# Phase E0.0 — Risk Intelligence Architecture & Design

**Status:** Design review complete · **Superseded on conflicts by** [E0.0A Architecture Freeze](E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md)  
**Prerequisite stack:** AIMF · IEF · DecisionPack · Comparison · Portfolio (C4.1–C4.6)  
**Suite gate:** **1126 / 1126** passing

## Verdict

**YES WITH CONDITIONS** (at design time) — conditions satisfied by E0.0A freeze.
See [E0.0A](E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md) for the authoritative
lock and **YES** to begin E1.0 implementation.


---

## 1. Recommended architecture

```text
DecisionPack ──────────────┐
EvidenceBundle ────────────┤
ComparisonReport ──────────┼── citations only (never owned)
Portfolio ─────────────────┤
Portfolio Monitoring ──────┘
                │
                ▼
        Risk Intelligence   (independent subsystem · pure consumer)
                │
                ├── RiskAssessment / RiskProfile
                ├── RiskObservation / RiskDescriptor
                ├── RiskCoverage / RiskConstraint (descriptors)
                └── RiskSummary
                        │
                        ▼
                   RiskReport
```

**Decision (Q1):** Risk Intelligence is an **independent subsystem**, not a
Portfolio package extension.

| Option | Verdict |
|---|---|
| Portfolio extension (`packages/portfolio/`) | Reject — Portfolio is frozen as structure / qualitative / history; risk would violate C4.5 boundaries |
| Independent subsystem (`packages/risk/` proposed) | **Accept** |

**Rationale:** Portfolio already owns structure, qualitative descriptors,
citation aggregation, and monitoring. Risk evaluates **implications** of that
state for portfolio-level risk postures. Keeping Risk separate preserves the
frozen Portfolio contracts and mirrors Comparison / IEF as peer consumers.

Risk Intelligence is a **pure consumer**. It never replaces Portfolio,
Decision Intelligence, IEF, Comparison, or Monitoring.

---

## 2. Design questions — decisions

### Q1 — What is Risk Intelligence?

**Independent subsystem** that produces portfolio-level risk observations and
reports from existing DSP contracts.

It is **not**:
- a Portfolio module
- a security-analysis engine
- an optimizer or OMS
- a classical market-risk calculator in E1.x (see Q6)

### Q2 — What should Risk Intelligence own?

| Artifact | Own? | Notes |
|---|---|---|
| `RiskObservation` | **Yes** | Qualitative / structured risk notes |
| `RiskDescriptor` | **Yes** | Human-readable risk labels |
| `RiskSummary` | **Yes** | Coverage / posture counts |
| `RiskReport` | **Yes** | Canonical presentation artifact |
| `RiskProfile` | **Yes** | Declared risk posture / mandate lens |
| `RiskConstraint` | **Yes** | Risk-policy descriptors (unevaluated or gap-noted) |
| `RiskCoverage` | **Yes** | Evidence / decision / comparison risk-coverage surface |
| `RiskAssessment` | **Yes** | Assembled assessment for one portfolio as-of |
| Portfolio / DecisionPack / Evidence / Comparison | **No** | Cite only |

Ownership = risk **interpretation surface** over cited portfolio state.
Not ownership of upstream truth.

### Q3 — What must Risk never own?

| Forbidden ownership | Why |
|---|---|
| Portfolio | Frozen aggregate root; Risk consumes |
| DecisionPack | Decision Intelligence owns |
| Evidence / Methodology | Industry / IEF owns |
| ComparisonReport | Comparison owns |
| Trading / OMS | Future execution subsystems |
| Optimization | Future Optimizer |
| Single-name valuation / technical / fundamental engines | Upstream engines |

**Boundary rule:** cite-don’t-embed; cite-don’t-reinterpret IEF observations;
never re-run Comparison eligibility.

### Q4 — What inputs should Risk consume?

| Input | Required? | Rule |
|---|---|---|
| `Portfolio` (or snapshot) | **Required** | Structure + weights + constraints |
| `PortfolioMonitoringResult` / timeline / changes | Optional | Change implications over time |
| DecisionPack references | Via holdings | Coverage / decision-posture risk only |
| EvidenceBundle references | Optional | Evidence-coverage risk only |
| ComparisonReport references | Optional | Peer-set coverage risk only |

**Dependency rules (proposed package):**

Allowed: `contracts`, `core`, `portfolio`, and **citation types only** from
`industry` / local refs. Prefer portfolio-local citation types already frozen.

Forbidden: `dsp`, `fundamental`, `economic`, `valuation`, engine packages,
`data_engine` providers, IEF interpreters, Comparison engine, `recommendation`,
`orchestration`, Optimizer/OMS.

No reverse imports from Portfolio → Risk.

### Q5 — What types of risk belong here (E1.x qualitative train)?

| Risk type | In Risk Intelligence? | Nature |
|---|---|---|
| Concentration risk | **Yes** | Single-name / top-weight posture |
| Diversification risk | **Yes** | Holding-count / sector-spread posture |
| Single-holding risk | **Yes** | Degenerate portfolio |
| Cash concentration | **Yes** | Cash posture extremes |
| Sector / industry concentration | **Yes** | When allocation sectors declared |
| Evidence coverage risk | **Yes** | Missing / partial evidence citations |
| Decision coverage risk | **Yes** | Missing / stale DecisionPack citations |
| Constraint risk | **Yes** | Gap notes vs declared constraints (not optimizer) |
| Liquidity risk | **Yes** | **Qualitative only** (declared liquidity notes / gaps) |
| Exposure risk | **Yes** | Descriptive exposure labels from declared weights |

These are **portfolio-structure and citation-completeness risks**, not
security-level fundamental/technical risks.

### Q6 — What remains outside Risk (future ownership)?

| Concern | Owner (future) |
|---|---|
| Expected return / alpha | Research / Performance Intelligence |
| Valuation | Valuation engine / DI |
| Trading / execution | OMS |
| Optimization / rebalancing algorithms | Optimizer |
| Performance attribution | Performance Intelligence |
| Beta / Sharpe / Sortino / VaR / stress testing | **Quantitative Risk** (later train; not E1.x) |

**E0.0 decision:** Classical market-risk metrics (Beta, Sharpe, Sortino, VaR,
stress tests) are **explicitly out of E1.x**. They may appear in a later
**E2.x Quantitative Risk** increment only after a separate freeze. This keeps
Risk Intelligence aligned with DSP’s qualitative-first stack (Comparison,
Portfolio Analyzer, Monitoring).

### Q7 — Relationship to Portfolio Monitoring

| Layer | Role |
|---|---|
| **Monitoring** | Detects / records **what changed** (history) |
| **Risk** | Evaluates **what those states/changes imply** for risk posture |

Monitoring remains history-only (C4.6 freeze). Risk may consume
`PortfolioChange` / timeline as optional inputs to emit risk observations
such as “concentration increased after holding removal” — still descriptive,
not a trade recommendation.

### Q8 — Recommended domain models

| Model | Role |
|---|---|
| `RiskProfile` | Mandate / posture lens (identity + risk preferences descriptors) |
| `RiskObservation` | Qualitative risk note (`code`, `text`, `subjects`, citations) |
| `RiskDescriptor` | Dimension + label (concentration, coverage, …) |
| `RiskSummary` | Counts / coverage / limitation notes |
| `RiskConstraint` | Risk-policy descriptor (not an optimizer constraint engine) |
| `RiskCoverage` | Evidence / decision / comparison coverage risk surface |
| `RiskAssessment` | Assembled assessment for portfolio + as-of |
| `RiskReport` | Canonical presentation artifact |

Assembler / analyzer split (proposed):

- `RiskAssembler` — construct immutable `RiskAssessment` from citations  
- `RiskAnalyzer` — produce observations / descriptors (qualitative)  
- Never: returns, VaR, BUY/SELL

---

## 3. Ownership model (summary)

| Domain | Owns |
|---|---|
| Decision Intelligence | DecisionPack |
| Industry (IEF) | Evidence / Methodology |
| Comparison | ComparisonReport |
| Portfolio | Holdings, Constraints, Snapshots, Observations, Monitoring history |
| **Risk Intelligence** | RiskProfile, RiskObservation, RiskDescriptor, RiskSummary, RiskCoverage, RiskConstraint, RiskAssessment, RiskReport |
| Quantitative Risk (later) | Classical market-risk metrics |
| Optimizer / OMS | Allocation search / execution |

---

## 4. Dependency graph

```text
DI / IEF / Comparison / Portfolio / Monitoring
                    │  (citations + Portfolio aggregate only)
                    ▼
            packages/risk/   ← proposed
                    │
                    ▼
            dsp_platform (re-export)
```

No cycles. Portfolio must not import Risk.

---

## 5. Responsibilities

| May | Must not |
|---|---|
| Read Portfolio / snapshots / monitoring | Own Portfolio |
| Read citation refs | Interpret EvidenceBundle observation payloads |
| Emit risk observations / descriptors | Run Comparison |
| Summarize coverage / concentration posture | Analyze single securities |
| Note constraint gaps descriptively | Optimize / recommend trades |
| Produce RiskReport | Compute returns, Sharpe, VaR, beta (E1.x) |

---

## 6. Future roadmap

| Phase | Scope |
|---|---|
| **E0.0** | Design (this document) |
| **E0.0A** | Architecture freeze (package name, banned metrics, citation contracts) |
| **E1.0** | Domain models |
| **E1.1** | RiskAssembler |
| **E1.2** | Qualitative RiskAnalyzer (concentration / coverage / constraint) |
| **E1.3** | RiskReport + platform exports |
| **E1.4** | Monitoring-change → risk implication observations |
| **E1.x** | Validation & freeze |
| **E2.x** | Optional quantitative risk train (VaR / beta / stress) — separate freeze |
| **C5 / Optimizer / OMS** | Downstream consumers of RiskReport |

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Risk becomes a scoring/ranking engine | Forbid composite attractiveness scores in freeze |
| Risk reinterprets IEF evidence | Cite status/gaps only; no interpreter calls |
| Risk absorbs Portfolio qualitative analyzer | Portfolio Analyzer stays descriptive; Risk adds risk-posture vocabulary |
| Premature VaR/Sharpe scope creep | Ban classical metrics until E2.x freeze |
| Monitoring/Risk blur | Monitoring = history; Risk = implication |

---

## 8. Technical debt / open conditions

1. Final package name (`risk` vs `risk_intelligence`) — lock in E0.0A.  
2. Whether `RiskConstraint` duplicates `PortfolioConstraint` or only cites it.  
3. Quantitative risk train (E2.x) intentionally undefined beyond “out of E1.x”.  
4. Liquidity risk remains qualitative until market-liquidity data contracts exist.

---

## 9. PASS / FAIL

**PASS** — Design complete for E0.0; ready for E0.0A freeze before coding.

---

## Final question

Is Risk Intelligence sufficiently well-defined to become the next major DSP
subsystem?

**YES WITH CONDITIONS**

Conditions: complete E0.0A freeze (independent package, qualitative-first
scope, classical metrics deferred, citation/ownership locks) before E1.0
implementation.
