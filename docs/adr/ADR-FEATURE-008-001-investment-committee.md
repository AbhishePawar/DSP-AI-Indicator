# ADR-FEATURE-008-001: Investment Committee Consensus (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-008 |
| **Related** | FEATURE-001…007 · `packages/investment_committee/` |

## Title

Introduce top-level `investment_committee` package (FEATURE-008) as a
deterministic multi-reviewer consensus layer; keep frozen G-era `ai_committee`
unchanged; defer platform composition.

## Decision

Create `investment_committee` **0.1.0** with five deterministic reviewers
consuming public IR, BQA, domain analyses, and valuation signals. Register in
monorepo tooling. Do not wire platform/API/frontend. No LLM/ML.

## Consequences

- Public class: `InvestmentCommitteeEngine` (not `ai_committee.InvestmentCommittee`)
- Risk soft veto and escalation flags are documented heuristics (TD-F015 / TD-F016)

## Rollback

Unregister and remove/revert `packages/investment_committee/`.
