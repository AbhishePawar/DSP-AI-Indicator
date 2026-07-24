# Epic M1.0 Sprint M1.1 — Management Intelligence Engine Foundation

**Web:** `2.1.0`

## Mission

Architecture-only foundation for the Management Intelligence Engine (MIE): domain models, evidence framework, scoring shells, timelines, risk flags, view models, and shared utilities.

## Non-goals (this sprint)

- Company-specific scoring
- AI-generated opinions / management ratings
- Dashboard UI, charts, reports
- Changes to Decision / Research / KG / Portfolio / Risk / Valuation / Copilot / Reports / Compliance / API contracts / Launch Dashboard / Advisor Platform

## Modules (`apps/web/src/lib/management/`)

| Module | Role |
|--------|------|
| `managementTypes.ts` | Domain types |
| `managementConstants.ts` | Weights, labels, methodology, trust |
| `managementValidators.ts` | Structural validation |
| `managementEvidence.ts` | Evidence factory & weighting helpers |
| `managementScoring.ts` | `ManagementScoringEngine` shells (scores null) |
| `managementTimeline.ts` | Timeline events |
| `managementRisk.ts` | Risk flags & severity |
| `managementModels.ts` | Immutable model factories |
| `managementBuilders.ts` | Analysis builders |
| `managementSelectors.ts` | Pure selectors |
| `managementFormatters.ts` | Display formatters |
| `managementUtilities.ts` | Small helpers |
| `managementViewModel.ts` | ARIA-ready view models |
| `managementEngine.ts` | Facade |
| `index.ts` | Barrel |

## Trust

Evidence-based · explainable · repeatable · auditable · transparent. No black-box AI scoring.

## Precondition

Web 2.0 Advisor Platform gate **PASS** · Regression **1551 PASS**
