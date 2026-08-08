# ARCH-002 — Unified Institutional Rating Framework

Status: **COMPLETE** · Frontend **v1.2.0** · Backend **unchanged**

## Architecture Review

Presentation & aggregation only. Existing `/api/v1/analyse` pipeline, engines,
recommendation, and AI Committee are untouched. Ratings remap stage summaries,
valuation signals, committee summaries, and the ARCH-001 Buffett report.

## Rating Framework

Every module exposes: Score (/10) · Grade (A+–F) · Confidence · Evidence ·
Strengths · Weaknesses · Explanation.

Missing fields (ROE, moat sub-dimensions, dedicated risk score, etc.) stay
**Unavailable** — never estimated.

Overall Investment Rating averages available module letter bands /10 displays
for presentation only.

## UI

- Company Analysis → **Institutional Ratings**
- Research Workspace → **Institutional Ratings**
- One-page dashboard + Investment Scorecard + module accordions

## Exports

JSON (`institutionalRatings`), CSV overall fields, HTML scorecard block.
Server PDF institutional export unchanged (no backend).

## Tests

Vitest coverage for scale helpers, action mapping, framework completeness,
determinism.
