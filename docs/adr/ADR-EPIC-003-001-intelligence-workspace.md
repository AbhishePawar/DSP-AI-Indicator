# ADR-EPIC-003-001: Intelligence Workspace Frontend

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | EPIC-003 |

## Title

Integrate /api/v1 composition endpoints into pps/web as a presentation-only Intelligence Workspace.

## Decision

1. Add /intelligence route and reusable intelligence components.
2. Extend the existing HTTP client with nalyse, alidate, ersion, capabilities.
3. Map API payloads to view-models without scoring or recommendation logic.
4. Add Vitest coverage and an architecture import ban for backend packages.

## Consequences

- dsp-web bumps to **2.5.0**
- Backend / API contracts unchanged
- Mobile and auth redesign remain deferred

## Rollback

Remove /intelligence route, intelligence components, and client methods; restore web package 2.4.0.
