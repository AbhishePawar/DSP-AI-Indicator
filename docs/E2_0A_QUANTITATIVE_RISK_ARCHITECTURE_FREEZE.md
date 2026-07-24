# Phase E2.0A — Quantitative Risk Architecture Freeze

**Status:** **FROZEN**  
**Date:** 2026-07-21  
**Preceded by:** [E2.0 Quantitative Risk Design](E2_0_QUANTITATIVE_RISK_INTELLIGENCE_DESIGN.md)  
**Prerequisite:** [DSP Architecture Baseline v1.0](DSP_ARCHITECTURE_BASELINE_v1_0.md) · Qualitative Risk E1.5 frozen · Research F1.4 frozen · **1242 tests green**  
**This phase:** Architecture lock only — **no code, no packages, no package modifications**

---

## Freeze declaration

The following are **authoritative** until an explicit freeze amendment:

1. Quantitative Risk Intelligence is an **independent bounded context** — it
   **complements** Qualitative Risk and **never extends** `packages/risk/`.  
2. Target package: **`packages/quantitative_risk/`** (create in E2.1).  
3. Quantitative Risk owns **only** the artifacts listed in §3.  
4. Upstream Portfolio / Monitoring / benchmarks are **cite / port only**.  
5. Market data is accessed **only** through abstract ports — **no vendor SDKs**
   inside the domain package.  
6. No BUY/SELL/OPTIMIZE/TRADE recommendations from Quantitative Risk.  
7. No reverse imports into Portfolio, qualitative Risk, Research, DI, IEF, or
   Comparison.  
8. Pipeline is frozen as **Models → Quantitative Engine → Reporter** (no
   mandatory Assembler).  
9. Initial metric catalog and numeric policy are frozen in §8–§9.

Conflicts with this document lose unless a later dated freeze amendment
supersedes them. On conflicts with E2.0 design prose, **this freeze wins**.

---

## 1. Frozen architecture

```text
Portfolio ─────────────────┐
Portfolio Monitoring ──────┤
Benchmark references ──────┼── citations / ports only
MarketDataPort ────────────┤
HistoricalReturnsPort ─────┤
BenchmarkDataPort ─────────┘
                │
                ▼
    packages/quantitative_risk/   ← FROZEN target (create in E2.1)
                │
                ├── QuantitativeRiskIdentity
                ├── QuantitativeRiskProfile
                ├── RiskMetric / RiskExposure / RiskConcentration
                ├── RiskCorrelation / RiskVolatility
                ├── DrawdownProfile / RiskDistribution
                ├── StressScenario / ScenarioResult
                ├── QuantitativeRiskSummary
                │
                ▼
        QuantitativeRiskReport
```

**Sibling relationship (frozen):**

```text
Portfolio / Monitoring
        │
        ├──► Qualitative Risk (packages/risk/)     → RiskReport
        │
        └──► Quantitative Risk (packages/quantitative_risk/)
                                                → QuantitativeRiskReport

Research — independent (no Quant dependency in Baseline v1.0)
Recommendation (Epic G) — consumes both reports independently
```

| Quantitative Risk **is** | Quantitative Risk **is not** |
|---|---|
| Independent DSP bounded context | An extension of qualitative `risk` |
| Producer of `QuantitativeRiskReport` | Owner of Portfolio / Monitoring |
| Measurable / statistical risk calculator | Optimizer, OMS, or Recommendation engine |
| Port-based market-data consumer | Vendor-coupled SDK package |
| Sibling of Qualitative Risk | A layer above or below Research |

### Boundary one-liners (frozen)

| Subsystem | Answers |
|---|---|
| **Qualitative Risk** | “What business and structural risks exist?” |
| **Quantitative Risk** | “What measurable statistical risks exist?” |
| **Research** | “What deserves further investigation?” |
| **Recommendation** (future) | “What action is recommended?” |

---

## 2. Ownership matrix

| Domain | Owns | Must not own |
|---|---|---|
| **Portfolio** | Holdings, constraints, snapshots, monitoring history | Quant metrics |
| **Qualitative Risk** | Qualitative risk artifacts (E1 frozen) | Quant metrics / `QuantitativeRiskReport` |
| **Research** | Research artifacts (F1 frozen) | Quant metrics |
| **Quantitative Risk** | Artifacts in §3 | DecisionPack, Evidence, Comparison, Portfolio, Monitoring, qualitative Risk, Research, recommendations, vendor adapters |
| **Market adapters** | Vendor I/O implementing ports | Domain aggregates |
| **Recommendation (G)** | Actions (future) | Quant ownership of Portfolio |

### §3 Canonical ownership (closed set for E2.x)

Quantitative Risk owns **ONLY**:

| Model | Role |
|---|---|
| `QuantitativeRiskIdentity` | Identity facet |
| `QuantitativeRiskProfile` | Aggregate root |
| `RiskMetric` | Named measurable metric (value + unit + method_id) |
| `RiskExposure` | Exposure decomposition |
| `RiskConcentration` | Concentration measures |
| `RiskCorrelation` | Correlation / covariance summaries |
| `RiskVolatility` | Volatility measures |
| `DrawdownProfile` | Drawdown path / extrema |
| `StressScenario` | Declared scenario definition |
| `ScenarioResult` | Scenario output bound to scenario + method |
| `RiskDistribution` | Distributional summary (method-bound) |
| `QuantitativeRiskSummary` | Counts / method notes / limitations |
| `QuantitativeRiskReport` | Canonical immutable presentation |

Supporting enums / status / context / result / port types may be added
additively without new aggregate roots.

### Never own (frozen)

`DecisionPack` · `EvidenceBundle` · `ComparisonReport` · `Portfolio` ·
Portfolio Monitoring · Qualitative Risk artifacts · Research artifacts ·
Recommendation artifacts · Market-data providers · Vendor adapters.

---

## 3. Dependency graph

```text
contracts / core
        ▲
        │
portfolio (Portfolio, Monitoring citations)
        ▲
        │  one-way
        │
packages/quantitative_risk/
        ├── domain models
        ├── ports (MarketDataPort, HistoricalReturnsPort, BenchmarkDataPort)
        ├── quantitative engine
        └── reporter
                ▲
                │ adapters OUTSIDE domain
         Yahoo / NSE / BSE / Bloomberg / Polygon / AlphaVantage / …

dsp_platform → additive re-exports only
```

### Allowed dependencies (E2.x)

`core`, `portfolio`, and (if needed) `contracts` for shared primitives only.

### Forbidden dependencies (E2.x)

- Qualitative `risk` as a **required** engine/owner import  
- `research`, `recommendation`, `dsp_platform` (except external re-export)  
- Vendor SDKs: Yahoo Finance, NSE, BSE, Bloomberg, Polygon, AlphaVantage, …  
- Optimizer / OMS / LLM SDKs  
- Comparison engine / IEF providers / interpreters  

### Cycle ban

- Quantitative Risk may import Portfolio.  
- Portfolio, qualitative Risk, Research, DI, IEF, Comparison must **never**
  import Quantitative Risk.

**Optional later:** digest-only citations of qualitative `RiskReport` require a
freeze amendment — **not** part of E2.0A required surface.

---

## 4. Responsibility matrix

### Frozen pipeline (no mandatory Assembler)

```text
Domain Models
        ↓
Quantitative Engine
        ↓
Reporter → QuantitativeRiskReport
```

| Component | Owns | Must not |
|---|---|---|
| **Domain models** | Contracts & invariants | Vendor I/O, trading |
| **Quantitative Engine** | Measurable metric / scenario computation via ports | Owning Portfolio; optimizing; recommending; mutating upstream |
| **Reporter** | Immutable `QuantitativeRiskReport` presentation | Inventing new metrics beyond engine outputs |

### Resolved open decision — Assembler

**Decision: Assembler is NOT required** for the E2 freeze.

Citation attachment and profile construction occur inside the Engine input
context / model constructors. An optional `QuantitativeRiskAssembler` may be
added later **additively** without redesign if construction complexity demands
it — it must remain construction-only (no calculations).

### Quantitative Risk SHALL

- Calculate measurable metrics (method-bound)  
- Produce immutable reports  
- Preserve provenance (portfolio / snapshot / method / port as-of)  
- Remain provider-independent  

### Quantitative Risk SHALL NEVER

- Optimize portfolios  
- Execute trades  
- Create recommendations  
- Run workflows  
- Embed LLM reasoning  
- Mutate Portfolio  
- Mutate Qualitative Risk  
- Import vendor market SDKs into the domain package  

---

## 5. Provider abstraction (frozen)

Domain defines ports only (package-local in E2.1):

| Port | Purpose |
|---|---|
| `MarketDataPort` | Price / bar / series access |
| `HistoricalReturnsPort` | Historical return series |
| `BenchmarkDataPort` | Benchmark series / metadata (optional consumer) |

Adapters implementing these ports live **outside**
`packages/quantitative_risk/` (e.g. `data_engine` extensions or dedicated
adapter packages).

**Promotion to `contracts`:** only via freeze amendment when a second bounded
context needs the same ports.

---

## 6. Initial metric catalog (frozen for E2.1–E2.2)

### E2.1 — model contracts (all owned types may exist as shells)

All §3 types are in the closed ownership set.

### E2.2 — engine must implement first

| Kind | Artifact focus |
|---|---|
| Concentration | `RiskConcentration` (+ related `RiskMetric`) |
| Exposure | `RiskExposure` (asset / sector allocation from declared structure) |
| Volatility | `RiskVolatility` (realized / estimated — method_id required) |
| Drawdown | `DrawdownProfile` (incl. maximum drawdown metric) |

### Deferred (additive later — no redesign)

VaR · Expected Shortfall · Monte Carlo · Factor models · Beta · Sharpe ·
Sortino · full `RiskDistribution` engines · rich `StressScenario` libraries ·
Black-Litterman · optimization-linked risk.

Model types for deferred kinds may exist empty/optional in E2.1; engines for
them ship in later E2 increments under freeze amendment / additive phases.

---

## 7. Numeric precision policy (frozen)

1. Public quantitative contracts use **`decimal.Decimal`** for weights, returns,
   metric values, and monetary quantities — **not** binary floats.  
2. Every `RiskMetric` **must** carry: `method_id`, `unit`, `as_of` (or equivalent
   provenance), and limitation notes where assumptions apply.  
3. Annualization / window / frequency conventions are **method-bound** and
   documented on the method — not implied by field names alone.  
4. Rounding policy for presentation may live in Reporter; Engine preserves
   full Decimal precision in domain objects.  
5. Forbidden: silent float coercion in public constructors.

Exact quantize scales (e.g. weight `1e-8`) are an E2.1 implementation detail
within this policy.

---

## 8. Architectural principles (frozen)

1. Single ownership  
2. Immutable contracts  
3. Provider abstraction  
4. Reference-only upstream consumption  
5. No responsibility overlap with Qualitative Risk / Research / Recommendation  
6. No vendor lock-in  

---

## 9. Future extension model

| Extension | Pattern |
|---|---|
| VaR / Monte Carlo / factors / Sharpe / Sortino / Beta | Additive metric kinds + engine methods |
| Scenario libraries | Additive `StressScenario` / `ScenarioResult` content |
| Recommendation (G) | Consumes `QuantitativeRiskReport` |
| Research citations of Quant reports | Freeze amendment only |
| Optional Assembler | Additive construction helper |
| Port promotion to `contracts` | Freeze amendment |

**No redesign** of E2.0A ownership, dependency direction, or pipeline.

---

## 10. Implementation roadmap (post-freeze)

| Phase | Scope | Status |
|---|---|---|
| **E2.0** | Design | **DONE** |
| **E2.0A** | Architecture freeze (this document) | **DONE / FROZEN** |
| **E2.1** | Domain models in `packages/quantitative_risk/` | **DONE** |
| **E2.2** | Quantitative Engine (initial catalog) | **DONE** |
| **E2.3** | Reporter | **DONE** |
| **E2.4** | Validation & freeze | **DONE / FROZEN** |

**E2.1 acceptance gate:**

1. This freeze remains in force.  
2. Work lives in `packages/quantitative_risk/` with dependencies ⊆ allowed set.  
3. Existing **1242+** tests stay green; changes are additive to the platform.  
4. No vendor SDK imports in domain; no BUY/SELL/OPTIMIZE; Decimal policy held.  
5. Qualitative `risk` and Research freezes remain untouched.

---

## 11. Risks

| Risk | Severity | Status |
|---|---|---|
| Quant leaks into qualitative `risk` | High | Mitigated (independent package lock) |
| Vendor lock-in | High | Mitigated (ports only) |
| Metric sprawl before E2.2 | Medium | Mitigated (initial catalog frozen) |
| Blur with Recommendation | High | Mitigated (non-responsibilities) |
| Float precision defects | Medium | Mitigated (Decimal policy) |

---

## 12. Technical debt

1. Optional Assembler deferred.  
2. Deferred metric engines (VaR, Monte Carlo, …) intentionally underspecified.  
3. Benchmark port richness TBD in E2.1 models.  
4. Adapter packaging layout (`data_engine` vs dedicated) deferred to
   implementation — must remain outside domain.  
5. No Quant↔Qualitative digest citations in v1.

---

## 13. Freeze confirmation

**CONFIRMED.**

Quantitative Risk Intelligence architecture (independence, ownership,
dependency graph, pipeline, provider abstraction, initial catalog, numeric
policy) is fully frozen and ready for **E2.1** implementation.

---

## 14. PASS / FAIL

**PASS** — Quantitative Risk architecture is frozen.

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | **Authoritative Quantitative Risk architecture freeze** |
| [E2_0_QUANTITATIVE_RISK_INTELLIGENCE_DESIGN.md](E2_0_QUANTITATIVE_RISK_INTELLIGENCE_DESIGN.md) | Design review (historical; superseded on conflicts) |
| [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) | Platform baseline |
| [E1_5_RISK_VALIDATION_AND_FREEZE.md](E1_5_RISK_VALIDATION_AND_FREEZE.md) | Qualitative Risk freeze |
| [F1_4_RESEARCH_VALIDATION_AND_FREEZE.md](F1_4_RESEARCH_VALIDATION_AND_FREEZE.md) | Research freeze |

---

## Final question

Is the Quantitative Risk Intelligence architecture fully frozen and ready for
implementation?

**YES**
