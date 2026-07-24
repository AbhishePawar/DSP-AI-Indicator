# Epic V2.0 Sprint 7.1 — Team Collaboration Foundation

**Web:** `2.0.0`

## Mission

Presentation-layer foundation for Team Collaboration: shell, navigation, shared workspace layout, and session-based collaboration state.

## Surfaces

- `/advisor/team` — Workspace Overview (cards · activity · session summary)
- `/advisor/team/my-work`
- `/advisor/team/shared-research`
- `/advisor/team/shared-reviews`
- `/advisor/team/shared-portfolios`
- `/advisor/team/discussions` — placeholder shell
- `/advisor/team/assignments`
- `/advisor/team/activity`

## Session state (`CollaborationSession`)

Selected workspace · sidebar collapse · expanded panels · pinned items · recent navigation · filters · main panel width — **in-memory only**.

## Trust

Reuses existing DSP advisor demos only. Never modifies research conclusions, Evidence, Confidence, Methodology, or Limitations.

## Non-goals

Persistence · authentication · real-time · chat · CRM · calendar · notifications · broker APIs

## Enable

`NEXT_PUBLIC_ADVISOR_DEMO=true`
