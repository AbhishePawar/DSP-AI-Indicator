# Phase F1.0 — Research Domain Models

**Status:** Implemented · Structure only · No synthesis / business logic

**Package:** `packages/research/` **0.1.0**  
**Freezes:** [F0.0A](F0_0A_RESEARCH_INTELLIGENCE_ARCHITECTURE_FREEZE.md) ·
[F0.0B](F0_0B_RESEARCH_ARCHITECTURE_HARDENING.md)

## Research ownership

Research owns **only** research artifacts:

| Model | Role |
|---|---|
| `ResearchIdentity` | Session / thesis identity |
| `ResearchProfile` | Aggregate root — cites upstream; owns research artifacts |
| `ResearchObservation` | Knowledge-state observation |
| `ResearchInsight` | Cite-backed synthesis statement (Evidence required) |
| `ResearchConflict` | Descriptive conflict record (never resolved here) |
| `ResearchGap` | Knowledge gap |
| `ResearchAgenda` | Ordered investigative plan |
| `ResearchPriority` | Categorical agenda priority (not a score) |
| `ResearchCoverage` | Knowledge-coverage posture |
| `ResearchSummary` | Descriptive counts / limitations |
| `ResearchReport` | Immutable presentation snapshot |

Upstream DecisionPack, Evidence, Comparison, Portfolio, Monitoring, and Risk
remain **outside** Research ownership.

## Reference model

Research cites upstream via reference-only types (never embeds payloads):

| Reference | Cites |
|---|---|
| `DecisionReference` | DecisionPack |
| `EvidenceReference` | EvidenceBundle |
| `ComparisonReference` | ComparisonReport |
| `PortfolioReference` | Portfolio |
| `MonitoringReference` | Portfolio Monitoring |
| `RiskReference` | RiskReport / RiskProfile |
| `IntegratedRiskReference` | IntegratedRiskContext |

## Domain model descriptions

- **Observations** describe knowledge state; they do not create new facts.  
- **Insights** synthesize over observations and **must** include Evidence refs.  
- **Conflicts** record inconsistencies; they do not resolve them.  
- **Gaps** record incompleteness; resolution is external.  
- **Agenda / Priority** propose investigation only — never Buy/Sell/Hold.  
- **Report** is an immutable as-of snapshot.

## Validation rules

Rejects:

- missing identity  
- missing citations on `ResearchProfile`  
- duplicate observations / insights / conflicts / gaps / priorities / coverage  
- broken references (invalid digests, missing observation/insight/gap links)  
- foreign Monitoring vs Portfolio ownership  
- insights without EvidenceReference  
- insights referencing unknown observation ids  
- agenda priorities without provenance  
- forbidden claim language (buy/sell/hold/score/proves/guaranteed/…)

## Domain invariants

Aligned with F0.0B:

1. Never computes valuation, allocation, risk scores, or probabilities.  
2. Read-only toward upstream artifacts.  
3. Insight → Observation → Evidence provenance chain.  
4. Conflicts descriptive only.  
5. Agenda investigative only.  
6. ResearchReport immutable.

## Traceability rules

```text
ResearchInsight
 ├── Observation IDs
 ├── Evidence IDs / EvidenceReference
 └── optional Decision / Comparison / Risk citations
```

No synthesized insight may exist without Evidence provenance and observation
links that resolve on the owning profile/report.

## Dependencies

Runtime: `core` only (F1.0). Upstream systems are cited via local reference
types — no Portfolio / Risk / Industry imports in this phase.

Forbidden: engines, providers, interpreters, LLM SDKs, `dsp_platform`,
recommendation, optimizer/OMS.

## Extension guidance

- **F1.1** ResearchAssembler — construction from citations  
- **F1.2** ResearchSynthesizer — gaps / conflicts / agenda (structural)  
- **F1.3** ResearchReporter — presentation  
- LLM adapters / workflow / memory remain **outside** the domain package  

## Non-goals (this phase)

Assembler, synthesizer, reporter, conflict detection logic, agenda generation,
priority scoring, workflow, recommendation, LLM, forecasting, trading,
optimization, portfolio/risk calculations, persistence.
