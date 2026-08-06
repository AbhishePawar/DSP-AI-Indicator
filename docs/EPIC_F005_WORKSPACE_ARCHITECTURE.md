# EPIC-F005 — Workspace Architecture

## Layout

```
┌──────── Toolbar (sticky) ─────────────────────────────┐
├──────────┬──────────────────────────┬─────────────────┤
│ Left nav │ Main analysis sections   │ Right context   │
│ search   │ summary / research / …   │ notes · tags    │
│ sections │ valuation · quality · AI │ related · nav   │
│ recent   │ compliance · timeline    │                 │
│ pinned   │ export                   │                 │
└──────────┴──────────────────────────┴─────────────────┘
```

Mobile: stacked panels; toolbar toggles nav/context visibility.

## Data flow

1. URL `?symbol=` → company selection
2. `buildAnalyseRequestForTicker` → `api.analyse`
3. `mapResearchView` → display model (no scoring)
4. Optional `api.marketQuote` → market status label only
5. Local prefs: pins/searches (`dashboardPrefs`), notes/tags/panels (`workspacePrefs`)

## Sections

| Section | Source |
|---|---|
| Summary / header | ResearchView + catalogue metadata |
| Research | Payload metadata; archive/diff empty when no API |
| Valuation | Request signals + recommendation_summary / valuation stage |
| Quality | Stage summaries (moat, management, strength, earnings) |
| AI | Committee summary, strengths, minority notes; Copilot link |
| Compliance | Feature flags + errors/warnings/limitations |
| Timeline | `stage_summaries` + `execution_order` |
| Export | JSON / CSV / Excel-CSV / Print-PDF of mapped fields |

## Trust

Missing fields → **Data unavailable.** Never invent intrinsic value, MoS, or scores.
