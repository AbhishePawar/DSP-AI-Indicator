# P2.1 — Institutional Report Transparency

Status: **COMPLETE** · Frontend **v1.3.0** · Backend **unchanged**

## Architecture

Presentation-only **Report Information** card. No pipeline, API, engine, or
recommendation changes. Fields remap existing `ResearchView` / analyse metadata.

## Fields

| Field | Source |
|---|---|
| Analysis Date | `analysedAt` |
| Frontend / Backend versions | `env.frontendVersion`, `platformVersion` |
| Buffett / Institutional framework versions | Presentation constants `1.0.0` |
| Report ID | Deterministic FNV hash of ticker, exchange, analysedAt, correlationId, pipeline, platform, frontend |
| Company | name / exchange / symbol from request mapping |
| Primary Data Source | Fixed: frozen `/api/v1/analyse` |
| Financial Period Used | **Unavailable** (not on AnalyseResponse) |
| Latest Available Data Date | `analysedAt` or Unavailable |
| Data Freshness | Only when market status explicitly contains live/delay keywords; else Unavailable |
| Confidence | Existing recommendation confidence |
| Pipeline / Recommendation engine versions | pipeline + `package_versions.investment_recommendation` when present |

## Rendering Rules

- Shown immediately below Executive Summary (Company Analysis Summary)
- Shown above Institutional Dashboard (Ratings section)
- Shown in Research Viewer after the object header card
- Responsive two-column layout on desktop; stacked on mobile
- Quality badges use outline DS badges (theme tokens)

## Unavailable Rules

Never estimate. Unknown → **Unavailable**.

## Testing

`apps/web/src/lib/report-transparency/report-transparency.test.tsx`
