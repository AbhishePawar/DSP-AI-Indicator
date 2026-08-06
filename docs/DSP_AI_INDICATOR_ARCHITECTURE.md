# DSP AI Indicator — Platform Architecture Specification

| | |
|---|---|
| **Document type** | Software Architecture Specification |
| **Status** | Approved baseline for platform evolution |
| **Audience** | Engineering, future maintainers, technical stakeholders |

---

## 1. Vision

**DSP AI Indicator is not a technical indicator library. It is an Institutional AI Investment Research Platform.**

The indicator computation engine that exists in the codebase today is one component of a much larger system. The platform's purpose is to replicate — and augment — the research process of an institutional investment committee: ingesting market, fundamental, economic, and behavioral data; deriving quantitative and qualitative insight from it; constructing and risk-managing portfolios; synthesizing all of that into an explainable, evidence-backed investment recommendation; and delivering it through a professional research report and dashboard.

Every architectural decision in this document is made in service of that end state, not in service of "a library that computes SMA/EMA/RSI." Code that is correct but only optimized for the indicator-library use case (e.g., ad hoc arrays instead of typed domain objects, no explanation metadata, no provider abstraction) is considered technical debt against this vision, even if it passes tests today.

---

## 2. Design Principles

These six principles are non-negotiable constraints on every package added to the platform. Any pull request that violates one of these should be treated as an architecture defect, not a style preference.

### 2.1 Modular Architecture
Every engine in the platform is an independent, separately versioned package with an explicit, declared dependency list. No engine's internals may be imported by another engine — only its published public API (its `__init__.py` surface) may be used. Modularity is what allows engines to be built, tested, deployed, and replaced independently as the platform grows from 2 packages to 13+.

### 2.2 Clean Architecture
Business/domain logic must never depend on a data provider, a specific API, a specific LLM vendor, a database, or a UI framework. Every engine's core logic depends only on **ports** (abstract interfaces) for anything external; concrete integrations live in **adapters**, isolated at the edges of the system. Swapping a market data vendor, a database, or an LLM provider must be an adapter change, never a rewrite of business logic.

### 2.3 Explainable AI
Every computed value that can influence a recommendation — an indicator reading, a valuation estimate, a risk metric, a behavioral signal, a final AI Investment Committee recommendation — must carry an explanation of *why* it has that value: which inputs were used, which model or rule produced it, and a human-readable rationale. Explainability is a **type**, defined once in `contracts`, not a feature bolted onto the AI layer at the end.

### 2.4 Production Quality
Code in this platform must be suitable for institutional use: full type coverage checked by static analysis, comprehensive automated tests (unit, contract, and integration), consistent formatting and linting enforced in CI, deterministic and reproducible outputs, and audit-traceable behavior. "It works" is not sufficient; "it is correct, tested, typed, documented, and reproducible" is the bar.

### 2.5 Extensibility
Adding a new indicator, a new valuation model, a new AI agent persona, or a new data provider must never require modifying existing code — only registering a new implementation against an existing interface. Every extension point in the platform (indicators, valuation models, AI agents, data providers) follows the same registry-based pattern.

### 2.6 Scalability
The platform must scale along three independent axes without architectural rework: **data volume** (more instruments, longer history, higher frequency), **computational load** (vectorized/compiled computation where Python loops would bottleneck), and **organizational scale** (more engines, more contributors, more concurrent workstreams). Architectural decisions should be evaluated against all three, not just correctness at today's scale.

---

## 3. Overall Platform Architecture

```
Contracts
   ↓
Core
   ↓
Data Engine
   ↓
Indicator Engine
   ↓
Fundamental Engine
   ↓
Economic Engine
   ↓
Valuation Engine
   ↓
Behavioral Engine
   ↓
Portfolio Intelligence Engine
   ↓
Risk Engine
   ↓
AI Investment Committee
   ↓
Research Engine
   ↓
Professional Dashboard
```

This diagram represents both the **conceptual data flow** (each stage builds on the outputs of the stages above it) and the **maximum allowed dependency direction** (formalized in Section 4). It does not mean every engine literally calls the one immediately above it — for example, the AI Investment Committee reads from most upstream engines directly, and Risk Engine reads from Data Engine as well as Portfolio Engine. The diagram fixes the *ordering*: nothing above a given engine may depend on it, directly or indirectly.

### 3.1 Contracts
The shared domain vocabulary for the entire platform: entities and value objects (`Instrument`, `PriceBar`, `FundamentalStatement`, `EconomicSeries`, `ValuationResult`, `BehavioralSignal`, `PortfolioPosition`, `RiskMetric`, `Recommendation`, `ResearchReport`), shared enumerations, the shared exception hierarchy, and — critically — the `Explanation`/`Evidence` type that every downstream engine attaches to its output. Contracts contains **no business logic and no I/O**. It is the only package every other package in the platform is allowed to depend on unconditionally.

### 3.2 Core
Generic, domain-agnostic infrastructure: input validation, numeric/array utilities, and foundational abstractions with **zero knowledge of finance, tickers, or portfolios**. Core exists so that generic utility logic isn't duplicated or re-derived inside every engine. Contracts may use Core internally for validation of its value objects.

### 3.3 Data Engine
Owns acquisition, validation, and normalization of every category of raw data the platform consumes: market prices, fundamental statements, macroeconomic series, and alternative/behavioral data feeds. Defines provider **ports** (`MarketDataPort`, `FundamentalsDataPort`, `EconomicDataPort`, `AlternativeDataPort`) with vendor-specific **adapters** behind them, plus a `DataProviderRegistry` so new vendors can be added without touching consuming engines. Responsible for the bronze/silver/gold normalization pipeline, caching, retries, and rate limiting. Its output is always a validated `Contracts` object — never a raw vendor payload — so every downstream engine works against one stable shape regardless of vendor.

### 3.4 Indicator Engine
Computes technical and digital-signal-processing–derived indicators (moving averages, momentum oscillators, and eventually more advanced DSP techniques such as filtering, spectral, and denoising methods) from Data Engine's price/volume series. Built on the existing `Indicator` abstract base class and registry pattern. Every computed indicator series is accompanied by an `Explanation` describing what the reading implies (e.g., "RSI(14) = 72 → overbought regime").

### 3.5 Fundamental Engine
Analyzes company financial statements sourced from Data Engine: profitability, growth, leverage, and quality ratios; statement-quality checks; multi-period trend analysis. Produces a `FundamentalAssessment` per instrument with the reasoning behind each derived score.

### 3.6 Economic Engine
Analyzes macroeconomic data (rates, inflation, yield curve, employment, GDP, credit conditions) to establish the macro/regime context that conditions valuation assumptions and portfolio decisions downstream. Produces an `EconomicContext` object consumed by Valuation, Portfolio, and Risk engines.

### 3.7 Valuation Engine
Produces intrinsic and relative value estimates (DCF, dividend discount, comparables/multiples, residual income) by combining Fundamental Engine output, Indicator Engine market data, and Economic Engine macro assumptions (discount rates, risk-free rate, growth environment). Exposes a `ValuationModelRegistry` so new valuation methodologies can be added independently. Every `ValuationResult` carries its assumptions and derivation reasoning explicitly.

### 3.8 Behavioral Engine
Captures market psychology and crowd-behavior signals that pure fundamental/technical analysis misses: sentiment analysis (news, analyst revisions, social/media), positioning data (options flow, insider activity), and behavioral-bias indicators (overreaction, herding, momentum/mean-reversion asymmetries). Produces `BehavioralSignal` objects that give the platform a "market psychology" lens — this is a key differentiator of an AI investment research platform versus a pure quant or fundamental system.

### 3.9 Portfolio Intelligence Engine
The first engine that operates at the **portfolio level** rather than the single-instrument level. Synthesizes Indicator, Fundamental, Economic, Valuation, and Behavioral output across the investable universe into portfolio construction, optimization, position sizing, diversification, and rebalancing recommendations.

### 3.10 Risk Engine
Quantifies position- and portfolio-level risk against Portfolio Intelligence Engine's output and Data Engine's market data: VaR/CVaR, drawdown analysis, factor exposure, correlation/concentration risk, and scenario/stress testing. Enforces risk limits and constraints that feed back into portfolio decisions.

### 3.11 AI Investment Committee
The reasoning and synthesis layer. A registry of AI agents (potentially specialized personas — e.g., a bull-case agent, a bear-case agent, a risk-officer agent) reviews the `Explanation`-bearing outputs of every upstream engine and produces a final recommendation (position, conviction, rationale, and dissenting views), modeling the deliberation of an actual institutional investment committee. This engine is deliberately built last among the analytical engines so that it always reasons over real, validated, explainable upstream signals rather than synthetic placeholders.

### 3.11a Recommendation + Decision Intelligence (frozen spine extension)
Above the committee, a pure **Recommendation** mapper emits `contracts.Recommendation`. Above that, **Decision Intelligence** (Phase B2) synthesizes the investor-facing **Decision Pack**:

```
CommitteeReport + Recommendation
        ↓
Decision Intelligence
   ├── Decision Brief
   └── Decision Assurance  (deterministic rule tables only)
        ↓
   Decision Pack  = Recommendation + Brief + Assurance
```

Decision Intelligence may consume only committee and recommendation artifacts. It must not import engines/providers, recalculate MoS/valuation, cast votes, or mutate the recommendation. Assurance bands and investor guidance are fully deterministic and auditable. `DSPPlatform.analyze()` remains the Recommendation-compatible API; `DSPPlatform.analyze_decision_pack()` returns the Decision Pack.

### 3.11b Investment Universe & Multi-Stock Foundation (Phase C1)
Above Decision Packs, the **`universe`** package maintains an investment universe (watchlist / research set — membership is not ownership) and runs the canonical single-name Decision Pack pipeline once per instrument. Results are aggregated into `MultiStockDecisionResult` with explicit SUCCESS / PARTIAL_SUCCESS / FAILURE semantics. Comparable summaries and metadata filters prepare Sector Intelligence without ranking or peer-relative claims. `DSPPlatform.analyze_universe()` is the additive façade API.

### 3.11c Adaptive Industry Methodology Framework (AIMF) — DESIGN FROZEN
Industry-aware investment methodology is modeled in the additive `industry` domain (C2.1–C2.5 implemented), not inside engines or the comparison switchboard:

```
Taxonomy → IndustryIdentity → IndustryProfile
                │
                └─► InvestmentCharacteristics (defaults only)
                ▼
         IndustryMethodology (per identity; versioned)
                ├── ValuationProfile
                ├── MetricApplicability
                ├── ComparisonDimensions
                ├── PeerEligibility
                ├── EvidenceApplicability
                ▼
         Industry Evidence Framework (definitions, interpreter, snapshots)
                ▼
         ComparisonEngine (industry-agnostic; DecisionPack + EvidenceBundle)
```

`InvestmentCharacteristics` may supply valuation/dimension defaults only. It never defines peers or industry-specific metrics. Methodologies are never shared directly across industries. See [C2_AIMF_ARCHITECTURE_FREEZE.md](C2_AIMF_ARCHITECTURE_FREEZE.md).

### 3.11d Industry Evidence Framework (IEF) — DESIGN FROZEN
**Metric ≠ Evidence.** Metrics are typed measurements; evidence is interpreted, citable, methodology-gated claims. IEF owns definitions, providers (ports), interpreters, and observations inside `packages/industry/` (extract later only if needed). IndustryMethodology owns applicability policy. DecisionPack carries **evidence snapshot references only**. Comparison consumes **DecisionPack + EvidenceBundle** (C2.5 path remains when evidence is absent). No scores or ranks. Canonical freeze: [C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md](C3_0A_INDUSTRY_EVIDENCE_ARCHITECTURE_FREEZE.md). Next implementation: C3.1 Evidence Registry.

### 3.12 Research Engine
Transforms the AI Investment Committee's recommendation and all supporting evidence from upstream engines into a structured, professional research report. Every statement in a generated report must be traceable to an `Explanation` object from a specific upstream engine — this is what makes the report audit-ready rather than a plausible-sounding narrative.

### 3.13 Professional Dashboard
The presentation and delivery layer for institutional users (portfolio managers, analysts, compliance): interactive views of reports, recommendations, risk metrics, and full drill-down into the reasoning chain behind any number the platform has produced. Preferred primary artifact: **Decision Pack** (Recommendation + Brief + Assurance).

---

## 4. Package Dependency Rules

The platform's dependency graph is constrained to match the pipeline ordering in Section 3. This keeps the system reasoning-tractable as it grows: at any point, "what can this package legally depend on" is answered by "everything above it in the diagram, and nothing below it."

### 4.1 The core rule

> **A package may depend only on packages that appear at or above its own position in the Section 3 pipeline. A package must never depend on a package that appears below it. Circular dependencies between packages are forbidden.**

### 4.2 Dependency table

| Package | May depend on |
|---|---|
| `contracts` | *(nothing — leaf dependency for the whole platform)* |
| `core` | `contracts` |
| `data-engine` | `contracts`, `core` |
| `indicator-engine` | `contracts`, `core`, `data-engine` |
| `fundamental-engine` | `contracts`, `core`, `data-engine` |
| `economic-engine` | `contracts`, `core`, `data-engine` |
| `valuation-engine` | `contracts`, `core`, `data-engine`, `indicator-engine`, `fundamental-engine`, `economic-engine` |
| `behavioral-engine` | `contracts`, `core`, `data-engine` |
| `portfolio-engine` | `contracts`, `core`, `data-engine`, `indicator-engine`, `fundamental-engine`, `economic-engine`, `valuation-engine`, `behavioral-engine` |
| `risk-engine` | `contracts`, `core`, `data-engine`, `portfolio-engine` |
| `ai-committee` | `contracts`, `core`, and the public output of every engine above it |
| `recommendation` | `contracts`, `core`, `ai-committee` |
| `decision-intelligence` | `contracts`, `core`, `ai-committee` (consumes Recommendation types from contracts; no engine imports) |
| `industry` | `contracts`, `core` (Industry Identity / taxonomy mappings; AIMF C2.1+) |
| `universe` | `contracts`, `core`, `decision-intelligence` (aggregates Decision Packs only) |
| `research-engine` | `contracts`, `core`, `ai-committee` (and, transitively, its supporting evidence) |
| `orchestration` (application layer) | every engine's public interface — the *only* package permitted to depend on the entire platform |
| `dsp_platform` (façade) | `orchestration`, `recommendation`, `decision-intelligence`, `universe`, `contracts` |
| `services/*` (API, dashboard backend) | `dsp_platform` / `orchestration` only — never an individual engine directly |

### 4.3 Supplementary rules

- **Cross-engine communication happens only through `contracts` types.** No engine may pass another engine a raw dict, tuple, DataFrame, or NumPy array across a package boundary — only typed domain objects.
- **No engine imports another engine's adapters.** Adapters (vendor-specific integrations) are private to the engine that owns them; other engines interact only through ports and contracts.
- **Only `orchestration` is allowed to know the shape of the full pipeline.** Individual engines must remain testable and deployable in isolation, with no knowledge of what calls them or what they will be composed with.
- **UI and API services depend on `orchestration`, never on engines directly.** This keeps the presentation layer decoupled from internal engine reshuffling.
- **New engines must declare their position in the pipeline explicitly** and may not introduce a dependency that violates the ordering above, even temporarily "to unblock" a feature.

---

## 5. Coding Standards

These rules apply to every current and future module in the platform. They extend the formatting/linting/testing conventions already in place (`black`, `ruff`, `pytest`) with architecture-level rules specific to this platform's vision.

1. **Every engine is an independently packaged, independently versioned module** with its own explicit dependency declaration. No engine may be structured as "just another folder" sharing an implicit global namespace with unrelated engines.
2. **Every engine follows a consistent internal layout**: `domain/` (entities and business rules specific to that engine), `application/` (use-case orchestration within the engine), `ports/` (interfaces for anything the engine needs from outside itself), `adapters/` (concrete implementations of those ports), and `registry/` where the engine exposes an extension point.
3. **All cross-package communication uses `contracts` types exclusively.** Introducing a new cross-engine data shape requires adding it to `contracts`, not inventing an ad hoc structure inside the consuming engine.
4. **Every output that can influence a recommendation carries an `Explanation`.** A PR that adds a new indicator, valuation model, risk metric, or agent output without an accompanying explanation is incomplete, regardless of test coverage.
5. **Anything designed to be extended must use a registry.** Indicators, valuation models, AI agents, and data providers are registered against a shared interface; consuming code discovers implementations through the registry, never through a growing `if/elif` chain of concrete types.
6. **Business logic never imports a concrete adapter.** Domain and application code depend only on ports; only the engine's own composition/wiring code is allowed to reference concrete adapters.
7. **Full type coverage is mandatory**, verified by static type checking
   (**mypy**) in CI with zero tolerated errors on covered packages. Type
   hints are a contract, not documentation. See `docs/TYPING.md` for the
   Phase A5 adoption path (boundary packages first, engines gradual).

8. **Docstrings follow the existing Google style** (Args/Returns/Raises) on every public class and function, consistent with the current `core`/`dsp` codebase.
9. **Formatting and linting are non-negotiable and automated.** `black` and `ruff` (or their future equivalents) run in CI and as pre-commit hooks; no manually-formatted exceptions.
10. **Every engine ships unit tests for its domain logic and contract tests for its ports**, following the existing convention of class-based test suites with edge-case coverage (empty input, invalid parameters, boundary conditions). No engine merges without tests.
11. **No circular imports, ever.** The dependency table in Section 4 is enforced, not aspirational; a proposed change that requires a backward dependency is a sign the architecture — not just the code — needs revisiting.
12. **Configuration and secrets are never hardcoded.** They are loaded through a dedicated configuration layer, injected into adapters at composition time.
13. **All errors derive from the shared exception hierarchy** rooted in `contracts`/`core` (as `DSPAIError` does today), never bare built-in exceptions, so error handling can be centralized at the orchestration layer.
14. **Outputs must be deterministic and reproducible wherever possible.** Given identical inputs, an engine must produce identical outputs. Where true non-determinism is unavoidable (e.g., LLM-based reasoning in the AI Investment Committee), the engine must log its inputs and outputs so that the *reasoning*, if not the exact wording, can be audited and reproduced.
15. **A version number is single-sourced per package**, not duplicated across a package's metadata and its code.

---

## 6. Development Roadmap

The build order optimizes for de-risking the hardest and most novel components last, and for validating the cross-engine architecture early via a thin end-to-end slice, rather than strictly following the pipeline's semantic order.

**Phase 0 — Platform Foundations**
Establish `contracts` and `core`, set up a real multi-package workspace with enforced dependency rules, baseline CI/CD across all packages, and foundational observability/configuration conventions. Nothing else should begin until this exists.

**Phase 1 — Data Engine**
Build provider ports/adapters and the normalization pipeline that turns vendor data into validated `contracts` objects. Every downstream engine is blocked on this existing in real form.

**Phase 2 — Indicator Engine (harden the existing foundation)**
Evolve the current `dsp` package into `indicator-engine`: vectorize the loop-based computations, expand the indicator set, attach `Explanation` metadata, and switch its input source from ad hoc arrays to Data Engine's typed price series.

**Phase 3 — Walking Skeleton**
Wire `orchestration` end-to-end through Data Engine → Indicator Engine → stubbed placeholders for every remaining engine → a placeholder report. This validates the contracts and composition model while only two real engines exist, surfacing integration issues cheaply.

**Phase 4 — Fundamental Engine and Economic Engine**
Build these two in parallel where practical — both depend only on Data Engine, not on each other. Fundamental Engine covers statement analysis and ratio scoring; Economic Engine covers macro regime/context.

**Phase 5 — Valuation Engine**
Build once Fundamental and Economic engines are stable, since it consumes both plus Indicator Engine's market data.

**Phase 6 — Behavioral Engine**
Build once Data Engine can supply alternative/sentiment data feeds; can proceed independently of Valuation Engine since it depends only on Data Engine, but is sequenced here to align with the platform's growing analytical maturity before portfolio-level synthesis begins.

**Phase 7 — Portfolio Intelligence Engine**
The first engine that synthesizes Indicator, Fundamental, Economic, Valuation, and Behavioral outputs together — a strong test of whether `contracts` and `orchestration` were designed well.

**Phase 8 — Risk Engine**
Built once Portfolio Intelligence Engine produces real positions to evaluate.

**Phase 9 — AI Investment Committee**
Built last among the analytical engines, deliberately, so it always reasons over mature, explainable upstream signals rather than synthetic placeholders.

**Phase 10 — Research Engine**
A templating layer over AI Investment Committee output and upstream `Explanation` evidence; low complexity once upstream contracts are stable.

**Phase 11 — Professional Dashboard**
Built last, once report and data contracts are stable enough that UI work isn't chasing a moving target.

---

## 7. Long-Term Vision

DSP AI Indicator's architecture is designed so that today's engine additions are steps toward a genuinely institutional-grade research platform, not a series of disconnected features. Over the long term, the platform is expected to evolve along several dimensions without requiring architectural rework, because each is anticipated by the design principles and dependency rules already established:

- **Real-time and streaming data.** Data Engine's port/adapter design allows a batch REST-based provider to be swapped or supplemented with a streaming/event-driven provider without changing any downstream engine, enabling intraday and eventually real-time research and signal generation.
- **Multi-asset-class and global coverage.** Because `contracts` defines instrument and data shapes generically rather than around a single asset class, the platform can expand from equities into fixed income, derivatives, or multi-currency portfolios by extending contracts and adding adapters, not by rewriting engines.
- **Deeper AI Investment Committee sophistication.** The `AgentRegistry` pattern allows the committee to grow from a small set of agent personas into a larger multi-agent deliberation system (bull/bear/quant/macro/risk officer perspectives, debate and consensus mechanisms) purely by registering new agents, with the orchestration and explainability contracts unchanged.
- **Model governance and MLOps.** As Valuation, Behavioral, and AI Committee components incorporate more machine learning, the registry pattern and explanation contracts already in place give the platform a natural foundation for model versioning, A/B evaluation, and governance — new model versions are new registry entries, auditable via the same `Explanation` mechanism used everywhere else.
- **Feedback and calibration loops.** Because every recommendation is stored with the evidence and reasoning that produced it (Section 2.3, 3.11), the platform can eventually compare AI Investment Committee recommendations against realized market outcomes and feed that signal back into model calibration — an institutional-grade capability that depends entirely on the auditability built in from Phase 0 onward.
- **Regulatory and compliance readiness.** The explainability-first design and audit-traceable pipeline (every report claim traces to an `Explanation` from a specific engine) position the platform to meet institutional compliance requirements around investment recommendation transparency as those requirements are formalized.
- **External extensibility.** Because data providers, indicators, valuation models, and agents are all registry-based extension points behind stable ports, the platform can eventually expose selected extension points to external quants or partners (e.g., a marketplace of third-party valuation models or data adapters) without compromising the integrity of the core engines.
- **Deployment flexibility.** The strict package boundaries and dependency rules make it feasible to later split engines across services (e.g., running the AI Investment Committee and Research Engine as separately scaled services from the numerically intensive Indicator/Risk engines) if operational scale demands it, without having to first untangle an entangled codebase.

The unifying theme across all of these growth paths is that they are extensions **within** the architecture defined in this document, not departures from it. Preserving the dependency rules, the explainability contract, and the registry-based extensibility pattern as the platform grows is what keeps "institutional-grade" a property of the system rather than a marketing description.

---

## 8. Addendum — Institutional Company Workspace & the Risk Composition Stage

This addendum records two additions made when the platform's already-built engines were unified into a single flagship Company Workspace (`/analysis`). See `docs/COMPANY_WORKSPACE.md` for the full component/API/sequence-diagram treatment; this section only records where the additions sit within the architecture defined above.

### 8.1 Risk as a real Composition stage

Section 3.10 describes the Risk Engine (`risk`, `quantitative_risk`) as portfolio-centric. For single-company research, `dsp_platform.composition.pipeline` now includes a **Risk** stage (`PipelineStage.RISK`), positioned in `EXECUTION_ORDER` after `economic_moat`/`financial_strength` complete, alongside the other structural composition stages (Section 3.7–3.11). It does not add a new risk-scoring algorithm — it is a `dsp_platform.composition.risk_view.build_company_risk_view` aggregator that maps already-computed `financial_strength` and `economic_moat` ratings onto the requested risk taxonomy (Business, Financial, Regulatory, Technology, Currency, Customer Concentration). Categories with no connected upstream signal are reported `available: false` with an explicit message rather than a fabricated value — consistent with the explainability principle in Section 2.3. `PipelineResult.risk` and `pipeline_result_public_dict()["risk"]` expose it the same way existing stage summaries are exposed.

### 8.2 Institutional Company Workspace as the flagship UI

The Professional Dashboard (Section 3.13) is realized today as the Next.js `/analysis` route (`CompanyAnalysisWorkspace`). This is an orchestration-only consumer: it composes existing engine outputs into one workspace and introduces no new business logic. Per the dependency rules in Section 4, all new server-side work for this effort was either:

1. **Composition-root wiring** inside `dsp_platform` (the Risk stage above; `QualitativeComparisonEngine` default-engine resolution + short-TTL caching for peer comparison in `DSPPlatform.compare_companies`), or
2. **Re-mounting already-implemented, already-tested API routers** (`market`, `fundamentals`, `historical`, `corporate_actions`, `data`, `research`, `decision_workspace`, and several institutional/committee/workflow routers) that existed in `packages/api_platform` but were never imported into `app.py`, or
3. **New serializers**, not new calculations — `docx`/`pptx` writers in `dsp_platform.institutional_export.formats` sit beside the existing `pdf_export.py`/`xlsx` writers and render the same frozen `InstitutionalResearchReport`.

No engine package gained new algorithms as part of this work. Sections of the workspace with no connected data source anywhere in the platform (Ownership/insider transactions, News, filings/Documents) render an honest "Data unavailable — no data source connected." state rather than mocked data, matching the platform-wide convention described in Section 2.3. See Section 8.3 for the connector framework that lets these sections light up once a real provider is configured.

### 8.3 Data Connector Framework — News, Filings, Ownership, Insider Trading, ESG, Transcripts

Section 3.3 describes Data Engine's classic ports (`MarketDataPort`, `FundamentalsDataPort`, etc.). EPIC-D001–D004 introduced a second, parallel port pattern for authenticated snapshot data with built-in resilience (`MarketQuotePort`, `FinancialStatementPort`, `CorporateActionPort`). The Data Connector Framework generalizes that resilient pattern across six additional domains — `NewsProviderPort`, `FilingsProviderPort`, `OwnershipProviderPort`, `InsiderTradingProviderPort`, `EsgProviderPort`, `TranscriptProviderPort` — and extracts the shared plumbing common to all of them into a new `data_engine.connector_framework` package: normalized envelope models (company identity, provenance, health, optional field), a generic `PriorityProviderRegistry`, a `FailoverGroup` that tries every configured provider in priority order with full audit logging, and reuse (not reimplementation) of the existing `RateLimiter`/`CircuitBreaker`/`RetryPolicy` primitives from `market_quote.service`. Each domain still owns its own `models.py`/`validation.py`/`service.py`/`registry.py`/`adapters.py`, keeping vendor-specific fields confined to `adapters.py`. `dsp_platform` façades (`news.py`, `filings.py`, `ownership.py`, `insider_trading.py`, `esg.py`, `transcripts.py`) build each domain's registry from environment configuration and expose it to `DSPPlatform`; thin, additive API routers mount `GET /{domain}` and `GET /{domain}/health` with no business logic. See `docs/DATA_CONNECTOR_FRAMEWORK.md` for the full provider matrix, configuration, and compliance table.

### 8.4 Portfolio Intelligence Analytics Module

Section 3.9/3.10 describe `portfolio` (EPIC-A002) and `quantitative_risk` (E2.2/E2.3) as the platform's existing portfolio-domain engines; both are marked **Production · Frozen** in their own READMEs and explicitly forbid new analytics being added to them without a new epic/ADR. The Portfolio Intelligence Analytics Module adds Sharpe/Sortino/Treynor/Jensen's Alpha/Beta/Tracking Error/Information Ratio, Risk Attribution, Factor Exposure, Correlation Matrix, Portfolio Heatmap, Sector/Country Allocation, Monte Carlo, Efficient Frontier, Scenario Analysis, Stress Testing, Position Limits, Rebalancing, and Tax Optimization as a **new, additive** package, `portfolio_analytics` — pure computation, Ports & Adapters, no I/O, depending only on `core` and `quantitative_risk` (reuse-only). It reuses Maximum Drawdown from `quantitative_risk.QuantitativeRiskEngine` via that engine's existing public `calculate()` API (a small in-process port shim, not a reimplementation), and reuses `dsp_platform.historical_series` (EPIC-D004) as its sole authenticated price-history source via `HistoricalSeriesPriceHistoryAdapter(PriceHistoryPort)`. The composition layer (`dsp_platform.portfolio_analytics`) follows the same stateless dict-in/dict-out contract as `dsp_platform.portfolio_intelligence` — holdings are supplied by the caller per request, never persisted — and adds matching `DSPPlatform.evaluate_portfolio_*` delegating methods. Thin, additive API routers mount seven stateless `POST /portfolio/analytics/{performance,risk,allocation,simulation,stress,constraints,tax}` routes plus `GET /portfolio/analytics/health`, with no business logic in `api_platform`. `portfolio_analytics` is named to avoid collision with EPIC-A002's existing "Portfolio Intelligence" module (`dsp_platform.portfolio_intelligence`), which remains untouched — that module's own `no_provider_calls`/`no_valuation_calculations`/`no_optimisation` rules made it the wrong place for this new quantitative math. See `docs/PORTFOLIO_ANALYTICS.md` for the full method catalog, reuse table, approximation-method disclosures, and compliance table.

### 8.5 Portfolio Store — server-side Portfolio/Holdings/Transactions/Watchlist persistence (RC1 Milestone 3)

Before this addendum, "Portfolio" state (holdings, watchlist, benchmark selection) lived exclusively in browser `localStorage` (`apps/web/src/lib/persistence`) — invisible to the backend and lost whenever a user cleared their browser or switched devices. `packages/portfolio_store` (new, additive) adds durable, per-user-owned persistence for exactly this state, following the **same architecture `packages/enterprise` already established** for durable domain records: a `PortfolioStorePort` Protocol with an `InMemoryPortfolioStore` default and a `DatabasePortfolioStore` that hydrates from / flushes to a `production_platform.DatabasePort` (duck-typed, zero import dependency — identical convention to `enterprise.db_store.DatabaseEnterpriseStore`). No new persistence architecture was introduced; this is a second application of an already-proven pattern. Holdings are declared in the exact shape `portfolio_analytics.PositionInput` already expects, so a persisted holding requires zero translation to reach the existing Portfolio Analytics endpoints — no calculation is duplicated. Transactions (buy/sell/dividend/bonus/split/rights/fee/tax/cash_deposit/cash_withdrawal) are a genuinely append-only ledger, mirroring `enterprise`'s append-only audit log — this milestone does not reconcile transactions into holdings automatically (recorded as a scoped-out gap, not silently invented). Ownership is enforced by `user_id`, resolved via the **existing** institutional auth (`DSPPlatform.auth_current_user`, EPIC-A009) through a new `get_current_user_id` FastAPI dependency that performs the identical resolution `GET /auth/rbac/me` already does — no new auth scheme. `Portfolio.org_id` exists on the model but is intentionally unused, reserved so Organization ownership can be layered on later without a schema migration. The composition layer (`dsp_platform.portfolio_store_facade`) and seven thin, additive, authenticated API routers (`/portfolio`, `/portfolio/{id}`, `/portfolio/{id}/{holdings,transactions,watchlist}`, `/portfolio/{id}/benchmark`, `/portfolio/migrate`) follow the identical thin-router convention as every other domain in this document. On the frontend, `PersistenceProvider` and `usePortfolioIntelPrefsStore` keep their exact pre-existing public interfaces — the migration strategy (server-exists → adopt; else migrate local, never deleting the local copy) and ongoing best-effort sync are additive internal behavior only. See `docs/PORTFOLIO_GUIDE.md` for the full architecture, ownership model, migration strategy, and compliance table.

### 8.6 Portfolio Intelligence Engine (RC1 Milestone 4)

Sections 8.4/8.5 established `portfolio_analytics` (quantitative, price-history-driven) and `portfolio_store` (persistence) as new, additive layers alongside the frozen `portfolio` (EPIC-A002) and `quantitative_risk` engines. This addendum adds a third, purely **orchestrating** layer — `portfolio_intelligence_engine` — that combines the *outputs* of those existing engines into portfolio-level intelligence (Health Score, Concentration Analysis, Valuation Heatmap, Risk Summary, AI Recommendations, Sector/Style Drift, Diversification Score, Opportunity Finder, and an AI Committee Scenario Summary). Consistent with the mandate that this milestone build **zero new valuation, risk, analytics, or AI engines**, `portfolio_intelligence_engine` (new package) is pure Python with no I/O and no engine imports beyond `core`: it accepts a tuple of `HoldingSignal` (a typed carrier of already-computed per-holding values) and already-computed portfolio-level aggregates, and returns a scoring/classification/ranking result. The actual engine calls happen exactly once, in the new orchestration façade `dsp_platform.portfolio_intelligence_engine`, which (1) calls the existing `dsp_platform.portfolio_analytics.evaluate_portfolio_*` functions for every quantitative number (performance ratios, per-holding risk attribution, Monte Carlo, stress tests — all frozen, RC1 Milestone 1), and (2) calls EPIC-A002's own exported `dsp_platform.portfolio_intelligence.linker` utilities (`link_research_map`/`extract_field`/`section_available`) — not a reimplementation of that JSON-path logic — to pull margin of safety, recommendation/committee confidence, and business-quality score from caller-linked Research Objects. Two derived figures are explicitly disclosed as relabelled/aggregated rather than newly computed: Value at Risk (95%) is the already-computed Monte Carlo 5th-percentile terminal return (Conditional VaR is honestly reported unavailable — no engine exposes the full tail distribution needed to compute it), and the Scenario Summary's "Expected CAGR"/"worst-case drawdown" are the portfolio's own trailing realized annualized return/max drawdown from `portfolio_analytics`, explicitly labelled historical rather than forecast. `portfolio_intelligence_engine` is named, and its API mounted at `POST /portfolio/insights` (not `/portfolio/intelligence`), to avoid colliding with EPIC-A002's existing, frozen `/portfolio/intelligence` endpoint — the same naming-collision resolution already used for `portfolio_analytics` vs. `portfolio_intelligence` in Section 8.4. Five thin, additive API routers (`POST /portfolio/insights{,/health,/recommendations,/opportunities,/scenario}`, `GET /portfolio/insights/health-check`) contain no business logic. On the frontend, a new "AI Intelligence" navigation group adds 8 lazy-loaded sections to the existing Portfolio Intelligence Workspace (`/portfolio`) — no new page, no redesign of the existing workspace shell. See `docs/PORTFOLIO_GUIDE.md` for the full architecture diagram, reuse/data-honesty contract table, and compliance table.
