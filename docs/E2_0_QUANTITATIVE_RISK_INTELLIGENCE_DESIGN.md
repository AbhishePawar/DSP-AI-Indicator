# Phase E2.0 — Quantitative Risk Intelligence Architecture & Design

**Status:** Design review complete · **Superseded on conflicts by** [E2.0A Architecture Freeze](E2_0A_QUANTITATIVE_RISK_ARCHITECTURE_FREEZE.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative Risk E1.5 frozen · Research F1.4 frozen  
**Suite gate:** **1242 / 1242** passing (2026-07-21)

## Verdict

**YES WITH CONDITIONS** (at design time) — conditions satisfied by E2.0A freeze.
See [E2.0A](E2_0A_QUANTITATIVE_RISK_ARCHITECTURE_FREEZE.md) for the authoritative
lock and **YES** to begin E2.1 implementation.

---

## 1. Recommended architecture

```text
Portfolio ─────────────────┐
Portfolio Monitoring ──────┤
Benchmark references ──────┼── citations / ports only (never owned)
Market-data abstractions ──┤
Historical-return abstractions ┘
                │
                ▼
    Quantitative Risk Intelligence
    (independent bounded context · measurable risk)
                │
                ├── QuantitativeRiskProfile / Identity
                ├── RiskMetric / RiskExposure / RiskConcentration
                ├── RiskCorrelation / RiskVolatility
                ├── DrawdownProfile / RiskDistribution
                ├── StressScenario / ScenarioResult
                ├── QuantitativeRiskSummary
                │
                ▼
        QuantitativeRiskReport
```

**Sibling relationship (not a stack extension of Research):**

```text
Portfolio / Monitoring
        │
        ├──────────────► Qualitative Risk ──► RiskReport
        │
        └──────────────► Quantitative Risk ──► QuantitativeRiskReport
                                    │
                                    ▼
              Recommendation Intelligence (future Epic G)
                 consumes BOTH reports independently

Research Intelligence remains completely independent
(consumes qualitative stack; does not own or require Quant Risk).
```

### Q1 — Independent bounded context?

**Yes — independent bounded context.** Do **not** extend Qualitative Risk
(`packages/risk/`).

| Option | Verdict |
|---|---|
| Extend Qualitative Risk (`packages/risk/`) | **Reject** — E1.5 freezes qualitative-only contracts; quant metrics would violate the freeze |
| Module inside Portfolio | **Reject** — Portfolio freeze forbids risk engines |
| Independent package (proposed: `packages/quantitative_risk/`) | **Accept** |

**Rationale:**

1. Baseline v1.0 and E0.0A already reserve **E2 as a separate train**.  
2. Qualitative and Quantitative Risk answer different questions; merging them
   creates responsibility overlap and claim-language / metric creep.  
3. Future Recommendation must consume both reports **independently** — sibling
   ownership enables that without redesign.  
4. Market-data / returns ports belong in a quantitative context, not in the
   frozen qualitative `risk` package (deps ⊆ core/portfolio/industry).

Neither owns the other. Neither imports the other’s engine. Optional future
**citations** between reports (e.g. Quant citing a RiskReport digest) require
an explicit freeze amendment — not required for E2.0 design.

---

## 2. Design questions — decisions

### Q2 — What should Quantitative Risk own?

| Artifact | Own? | Notes |
|---|---|---|
| `QuantitativeRiskIdentity` | **Yes** | Stable identity for a quant risk session / profile |
| `QuantitativeRiskProfile` | **Yes** | Aggregate root — cites Portfolio; owns quant artifacts |
| `RiskMetric` | **Yes** | Named measurable metric instance (value + unit + method id) |
| `RiskExposure` | **Yes** | Exposure decomposition (asset / sector / factor as declared) |
| `RiskConcentration` | **Yes** | Concentration measures (weights / HHI-style — method-bound) |
| `RiskCorrelation` | **Yes** | Correlation / covariance summary artifacts |
| `RiskVolatility` | **Yes** | Volatility measures (realized / estimated — method-bound) |
| `DrawdownProfile` | **Yes** | Drawdown path / max drawdown descriptors |
| `StressScenario` | **Yes** | Declared scenario definition (inputs, not market ownership) |
| `ScenarioResult` | **Yes** | Scenario output bound to a scenario + method |
| `RiskDistribution` | **Yes** | Distributional summary (e.g. quantiles) — method-bound |
| `QuantitativeRiskSummary` | **Yes** | Counts / method notes / limitations |
| `QuantitativeRiskReport` | **Yes** | Canonical immutable presentation |

**Ownership rule:** Quant Risk owns **measurable risk artifacts and method
metadata** only. Metric **values** are computed by the Quantitative Engine
against abstract market/return ports — never by mutating Portfolio.

Exact metric catalog (which `RiskMetric` kinds ship in E2.1 vs later) is an
**E2.0A / E2.1 freeze item**. Design accepts the candidate set above as the
closed *family*; E2.0A may defer individual kinds (e.g. full Monte Carlo
distributions) to later increments without redesigning the aggregate.

### Q3 — What must Quantitative Risk never own?

| Forbidden | Why |
|---|---|
| `DecisionPack` | DI owns |
| `EvidenceBundle` | IEF owns |
| `ComparisonReport` | Comparison owns |
| `Portfolio` / Monitoring | Portfolio owns |
| Qualitative Risk artifacts | `packages/risk/` owns (E1 frozen) |
| Research artifacts | Research owns (F1 frozen) |
| Recommendation artifacts | Epic G |
| Raw vendor market feeds as domain types | Provider adapters outside domain |
| Optimizer / OMS state | External |

### Q4 — Inputs and dependency rules

**May consume:**

| Input | Use |
|---|---|
| `Portfolio` (+ snapshot citations) | Weights, holdings structure, cash, mandate context |
| Portfolio Monitoring (citations) | Change triggers / as-of alignment — not reinterpretation of history ownership |
| Benchmark references | Relative risk / tracking context |
| **Market-data abstractions** | Prices / series via ports |
| **Historical-return abstractions** | Return series via ports |

**Dependency rules (proposed E2.x):**

```text
Allowed:   core, portfolio, (+ contracts if shared ports live there)
Optional:  thin citation façades only
Forbidden: risk (qualitative package) as owner/engine import*,
           research, recommendation, dsp_platform,
           vendor SDKs (Yahoo/NSE/BSE/Bloomberg/AlphaVantage/Polygon/…),
           optimizer/OMS, LLM SDKs
```

\*Qualitative `risk` must not be a **required** runtime dependency for Quant
Risk core. Optional digest citations may be added later by freeze amendment
without importing qualitative analyzers.

**Cycle ban:** Quant Risk may import Portfolio. Portfolio / qualitative Risk /
Research / DI / IEF / Comparison must **never** import Quant Risk.

### Q5 — Primary responsibilities

| Responsibility | In Quant Risk? | Notes |
|---|---|---|
| Portfolio concentration (measurable) | **Yes** | Weight / concentration metrics |
| Sector / asset allocation exposure | **Yes** | From declared classifications + weights |
| Correlation analysis | **Yes** | Via return abstractions |
| Volatility analysis | **Yes** | Method-bound |
| Maximum drawdown | **Yes** | Method-bound |
| Scenario analysis / stress testing | **Yes** | Declared scenarios + results |
| Risk decomposition / attribution | **Yes** | Contribution-style metrics — not trading advice |
| Classical market-risk metrics (VaR, etc.) | **Later increments** | Allowed family; not implemented in E2.0 |
| Qualitative posture / RiskLevel narratives | **No** | Qualitative Risk |
| Investigation agendas | **No** | Research |
| Actions / BUY·SELL | **No** | Recommendation |

### Q6 — Explicit non-responsibilities

Quantitative Risk **never** performs:

- Portfolio optimization  
- Execution / trading  
- Recommendation generation  
- Workflow orchestration  
- LLM reasoning  
- Knowledge graph creation  
- Evidence reinterpretation  
- DecisionPack production  
- Mutation of Portfolio / Monitoring / qualitative Risk / Research  

### Q7 — Relationship triangle (+ Recommendation)

| Subsystem | Answers |
|---|---|
| **Qualitative Risk** | “What business and structural risks exist?” |
| **Quantitative Risk** | “What measurable statistical risks exist?” |
| **Research** | “What deserves further investigation?” |
| **Recommendation** (future) | “What action is recommended?” |

Qualitative and Quantitative Risk are **complements**, not layers of each other.
Research stays independent of Quant Risk in Baseline v1.0 (may cite Quant
reports later only via freeze amendment). Recommendation consumes
`ResearchReport` and `QuantitativeRiskReport` (and may also consume qualitative
`RiskReport`) independently.

### Q8 — Market data / provider abstraction

Design for **ports**, not vendors.

```text
Quantitative Engine
        │
        ▼
┌─────────────────────────┐
│ MarketDataPort          │  ← abstract
│ HistoricalReturnsPort   │  ← abstract
│ BenchmarkDataPort       │  ← abstract (optional)
└─────────────────────────┘
        ▲
        │ adapters (outside domain package)
 Yahoo / NSE / BSE / Bloomberg / …   ← NEVER imported by domain
```

**Hard rule:** Domain package defines interfaces / DTOs only. Vendor HTTP SDKs
and API keys live in adapters (`data_engine` extensions or dedicated adapter
packages) — never inside `quantitative_risk` domain models or engine core.

### Q9 — Recommended implementation phases

| Phase | Scope | Status |
|---|---|---|
| **E2.0** | Architecture & design (this document) | **DONE (design)** |
| **E2.0A** | Architecture freeze | **DONE / FROZEN** — see [E2.0A](E2_0A_QUANTITATIVE_RISK_ARCHITECTURE_FREEZE.md) |
| **E2.1** | Domain models | Planned |
| **E2.2** | Quantitative Engine (against ports) | Planned |
| **E2.3** | Reporter (`QuantitativeRiskReport`) | Planned |
| **E2.4** | Validation & freeze | Planned |

Follow Baseline v1.0 lifecycle: Design → Freeze → Models → Engine/Assembler →
Reporter → Validation. An Assembler stage may be introduced in E2.1/E2.2 if
needed for citation construction; E2.2 is the calculation boundary.

---

## 3. Domain ownership (summary)

| Domain | Owns |
|---|---|
| Portfolio | Structure, monitoring history |
| Qualitative Risk | Posture / qualitative artifacts |
| Research | Investigation / knowledge orchestration |
| **Quantitative Risk** | Measurable metrics, scenarios, quant report |
| Market adapters | Vendor I/O |
| Recommendation (G) | Actions |

---

## 4. Dependency graph

```text
contracts / core
        ▲
        │
portfolio (frozen)
        ▲
        │  one-way consume + ports
        │
packages/quantitative_risk/   ← proposed
        │
        ├── domain models / report
        └── engine (uses MarketDataPort / ReturnsPort)
                ▲
                │ adapters (external)
         vendor market providers

dsp_platform → additive re-exports only
```

Research / qualitative Risk / Recommendation do **not** sit under Quant Risk
in the import graph.

---

## 5. Responsibility matrix

| Component (future) | Owns | Must not |
|---|---|---|
| Domain models | Metric / scenario / report contracts | Vendor I/O, trading |
| Assembler (optional) | Profile construction from Portfolio citations | Computing VaR/etc. |
| Quantitative Engine | Metric & scenario computation via ports | Owning Portfolio; optimizing; recommending |
| Reporter | `QuantitativeRiskReport` presentation | New calculations beyond assembled results |

---

## 6. Future extension model

| Extension | How |
|---|---|
| VaR / Expected Shortfall / Monte Carlo | Additive metric kinds + methods under E2 freezes |
| Factor models / beta / CAPM-style | Additive; still port-based returns |
| Performance attribution | May share ports; prefer separate package if ownership diverges |
| Recommendation (G) | Consumes `QuantitativeRiskReport` |
| Research | Remains independent; optional later citations only |
| Optimizer | Consumes reports externally — never owned by Quant Risk |

---

## 7. Architectural principles

1. Single ownership.  
2. Immutable contracts.  
3. Reference-only upstream consumption.  
4. Provider abstraction (ports, not vendors).  
5. No reverse imports / no cycles.  
6. Quantitative calculations isolated in the Quant Engine.  
7. Future Recommendation consumes outputs only.  
8. Do not break Qualitative Risk or Research freezes.

---

## 8. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Quant metrics leak into `packages/risk/` | High | Independent package; E1 freeze intact |
| Vendor lock-in | High | Ports only; adapters outside |
| Premature full metric zoo | Medium | E2.0A closes initial catalog; defer Monte Carlo/etc. |
| Blur with Recommendation | High | No BUY/SELL/optimize in Quant Risk |
| Blur with Qualitative Risk | High | Separate questions + packages |
| Fake precision / claim language | Medium | Method ids, limitations, units required on metrics |

---

## 9. Technical debt / open freeze items (E2.0A)

1. Exact package name (`quantitative_risk` vs `qrisk` vs `market_risk`).  
2. Initial E2.1 metric catalog (concentration / volatility / drawdown first?).  
3. Whether Assembler is mandatory before Engine.  
4. Shared location of `MarketDataPort` / `HistoricalReturnsPort` (`contracts` vs package-local).  
5. Benchmark reference model shape.  
6. Whether Quant may cite qualitative `RiskReport` digests in v1.  
7. Numeric policy (decimal types, annualization conventions) — freeze in E2.1.

---

## 10. Non-goals (this phase)

Do **not** implement: VaR, Monte Carlo, CAPM, Beta, Sharpe, Sortino,
Black-Litterman, optimization, persistence, API adapters, pricing engines,
execution, packages, models, or statistical engines.

---

## 11. PASS / FAIL

**PASS** — Design complete for architecture freeze.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | Quantitative Risk design review |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline (E2 reserved) |
| [E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md](E0_0A_RISK_INTELLIGENCE_ARCHITECTURE_FREEZE.md) | Qualitative Risk freeze (E2 reserved) |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | Qualitative Risk implemented freeze |
| [F1_4_RESEARCH_VALIDATION_AND_FREEZE.md](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) | Research freeze (independent of Quant) |

---

## Final question

Is Quantitative Risk Intelligence sufficiently well-defined to become the
first quantitative bounded context of the DSP AI Indicator platform?

**YES WITH CONDITIONS** (design-time)

**Resolved by E2.0A:** architecture frozen — begin E2.1 per
[E2.0A](E2_0A_QUANTITATIVE_RISK_ARCHITECTURE_FREEZE.md).
