# EPIC-014 + EPIC-015 — Institutional Research Canvas & Portfolio Intelligence 2.0

**Branch:** `cursor/p6-1-commercial-readiness`  
**Scope:** Frontend orchestration / workspace unification — composition only  
**Date:** 2026-08-02

---

## Architecture Impact

- **No redesign** of valuation, BQ, management, moat, risk, AI Committee, explainability, Research Intelligence calculations, Company Comparison calculations, API contracts, or REP-002.
- Research Canvas is a **composition shell** that deep-links existing Company Analysis / Comparison / RI / Evidence / Committee surfaces.
- Portfolio Intelligence 2.0 **extends** the existing `/portfolio` workspace (no parallel product).
- Thin client preserved: frozen `/api/v1` only; missing fields → **Data unavailable.** / **Analysis unavailable.**
- Notes remain local-only (`dsp.research-canvas.notebook.v1`) and never overwrite institutional research.

## Components Added

| Path | Role |
|------|------|
| `apps/web/src/lib/research-canvas/*` | Tabs, notebook store, search, timeline, export, quick actions |
| `apps/web/src/components/research-canvas/*` | Canvas shell (Left / Center / Right / Bottom) |
| `apps/web/src/app/research/canvas/page.tsx` | Route |
| `apps/web/src/components/portfolio-intelligence/PortfolioV2Sections.tsx` | Scenarios, Drift, Timeline, Integrations, Overview extras |
| `apps/web/src/components/dashboard/widgets/ResearchCommandCenterWidget.tsx` | Command Center dashboard widget |

## Pages Updated

- `/research/canvas` — Research OS hub (new)
- `/portfolio` — V2 sections wired into existing workspace
- `/dashboard` — Research Command Center widget + Quick Actions include Canvas
- Shell nav + Ctrl+K Quick Actions

## Feature Flags Used

| Flag | Env | Default |
|------|-----|---------|
| `researchCanvas` | `NEXT_PUBLIC_RESEARCH_CANVAS` | `true` |
| `portfolioIntelligenceV2` | `NEXT_PUBLIC_PORTFOLIO_INTELLIGENCE_V2` | `true` |

Existing flags continue to gate RI / Comparison tabs and links.

## Accessibility Validation

- Tablist / tabpanel semantics on canvas center tabs
- `aria-label` on navigator, notebook, bottom dock
- Panel toggles with `aria-pressed`
- `min-h-11` touch targets on primary controls
- `motion-reduce:` for backdrop blur / transitions
- Keyboard shortcuts deferred to existing workspace patterns; canvas uses button/tab focus

## Performance Validation

- Route uses `next/dynamic` + `ssr: false` for canvas workspace
- Portfolio V2 sections lazy-loaded via `React.lazy`
- Command Center widget lazy in dashboard registry
- Timeline / search capped (slice limits) to avoid large local lists

## Responsive Validation

- Left/right panels collapse below `lg` via `useCollapsePanelsBelowLg`
- Bottom dock grids `md:grid-cols-2` / `xl:grid-cols-4`
- Notebook shown in center when tab=`notes` on small screens

## Known Limitations

- Center pane **deep-links** existing surfaces rather than iframe-embedding full interactive analyse UIs (avoids dual-state / double-fetch complexity).
- Portfolio value, industry/mcap/country/cash allocation, drift %, Bull/Base/Bear scenarios: **honest unavailable** until API fields exist.
- Native DOCX unavailable; PDF via browser print / HTML package only.
- Committee alerts at portfolio/dashboard level have no dedicated feed — link to Company Analysis AI section.
- Version history dock links to Research archive; full version diffs require existing archive/diff APIs.

## Future Enhancements

- Optional in-canvas embedding of analysis section components when a single `ResearchView` is already loaded
- Server-synced notebook (still isolated from institutional artifacts)
- Portfolio scenario / drift fields when backend emits them
- IC memo template polish on HTML export

## Regression Summary

| Area | Result |
|------|--------|
| Notebook isolation | Covered by unit tests — local store only |
| Canvas tabs / routing | Tab registry + URL sync + shell nav |
| Portfolio honesty | Scenarios/Drift/Overview unavailable copy |
| Palette RBAC | `filterResearchQuickActions` + existing `filterShellNav` |
| Engines / APIs | Untouched |

## Implementation Return Format

| Field | Value |
|-------|-------|
| Architecture Impact | Composition-only Research OS + Portfolio 2.0; no engine changes |
| Components Added | research-canvas lib/UI, PortfolioV2Sections, Command Center widget |
| Pages Updated | `/research/canvas`, `/portfolio`, `/dashboard`, shell palette |
| Feature Flags Used | `researchCanvas`, `portfolioIntelligenceV2` |
| Accessibility Validation | Tabs, labels, reduced motion, touch targets |
| Performance Validation | Dynamic import + lazy sections |
| Responsive Validation | Collapsible 3-panel + dock grid |
| Known Limitations | Deep-link composition; portfolio value/scenario gaps |
| Future Enhancements | Embed mode; server notebook; scenario API fields |
| Regression Summary | Targeted vitest for canvas + portfolio v2 + shell nav |

---

## Governance checklist

- CV-001…CV-010 — honesty preserved for missing metrics  
- Thin client — no browser scoring  
- GOV-001 — no governance bypass  
- Notes never overwrite system research  
- Immutable timeline/history — compose only, no mutation of institutional artifacts  
