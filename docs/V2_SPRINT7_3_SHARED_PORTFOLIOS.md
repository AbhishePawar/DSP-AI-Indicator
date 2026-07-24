# Epic V2.0 Sprint 7.3 — Shared Portfolio Collaboration

**Web:** `2.0.0`

## Mission

Collaborative Shared Portfolio Workspace for reviewing, comparing, discussing, and presenting existing DSP model portfolios. Presentation only — no Portfolio Engine changes.

## Surfaces

- `/advisor/team/shared-portfolios` — Overview dashboard + quick actions
- `/advisor/team/shared-portfolios/library` — Models · filters · pinned/recent/favorites · collections
- `/advisor/team/shared-portfolios/compare` — Compare 2–5 models (existing fields only)
- `/advisor/team/shared-portfolios/scenarios` — Conservative · Base · Bull · Bear · Stress framings
- `/advisor/team/shared-portfolios/discussion` — Session notes / thesis / concerns / follow-ups
- `/advisor/team/shared-portfolios/activity` — Activity feed buckets

## Trust

Reuses demo model portfolio library only. Never recalculates allocations, scenarios, or risk. Never modifies Evidence · Confidence · Methodology · Limitations on linked research.

## Enable

`NEXT_PUBLIC_ADVISOR_DEMO=true`
