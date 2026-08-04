# ADR-CV-002…010 — Tier-0 Constitutional Core Values

| Field | Content |
|---|---|
| **Status** | **Accepted** |
| **Date** | 2026-07-28 |
| **ID** | ADR-CV-002-010 |
| **Related** | [CV_002_TO_010_TIER0_CORE_VALUES.md](../CV_002_TO_010_TIER0_CORE_VALUES.md) · [CORE_VALUES.md](../CORE_VALUES.md) · [ADR-CV-001](ADR-CV-001-data-authenticity-first.md) |

## Context

CV-001 established Data Authenticity First. Institutional trust further requires
ordered constraints on scoring, explainability, determinism, uncertainty,
provenance, audit, research-before-advice, and governance-over-convenience.

## Decision

Adopt **CV-002 … CV-010** as permanent **Tier-0 Architecture Governance**
(Constitutional Core Values):

| ID | Name |
|---|---|
| CV-002 | Source Before Score |
| CV-003 | Explainability Before Recommendation |
| CV-004 | Determinism Before Intelligence |
| CV-005 | Transparency Over Confidence |
| CV-006 | Traceability By Design |
| CV-007 | Auditability First |
| CV-008 | Research Before Recommendation |
| CV-009 | Governance Over Convenience |
| CV-010 | Quality Over Speed |

Violation **MUST FAIL** architecture review and all enforcement gates
(architecture, code review, DoD, quality, release, production, package health,
research report validation).

## Consequences

- Checklists, constitution, Bible, contributing, developer guide, research/report
  specs, and Cursor rules cite CV-001…CV-010.  
- **No** engine, scoring, API, model, determinism implementation, or package
  boundary changes are authorized by this ADR — governance documentation only.  
- Future emitters / presentation layers must respect these rules when producing
  production research output.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Soft product guidelines | Insufficient — must fail review |
| Apply only to SEBI Mode | Research Mode needs equal rigor |
| Encode immediately in engines | Out of scope; engines frozen; governance first |

## India / Research Mode

Research Mode remains default. CV-008 reinforces research-before-recommendation.
SEBI flags do not waive CV-002…CV-010.
