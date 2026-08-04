# EPIC-F004 — Dashboard Architecture

## Page

`/dashboard` → `InstitutionalDashboard`

Lives inside the F003 application shell (`AppLayout`). Does not redefine chrome.

## Widget framework

| Layer | Responsibility |
|---|---|
| `lib/dashboard/widgetRegistry.ts` | Widget ids, sections, default order |
| `lib/dashboard/dashboardPrefsStore.ts` | Order, visibility, pins, searches (local) |
| `components/dashboard/*` | Widget UI (F001 only) |

## API integration (existing only)

| Widget | Source |
|---|---|
| Welcome / last login | `rbacAuthApi.me` |
| Platform health | `api.health`, `api.marketHealth`, `api.dataHealth` |
| API status | `api.health`, `api.version`, `api.capabilities` |
| Research reports | local report ids + `api.getReport` |
| Copilot activity | `api.copilotProviders` |
| Recent / pinned companies | local analysis history + prefs |
| Portfolio / watchlist / jobs / committee / archive / diff | Empty — no client API |

## Personalization

- Widget order + visibility → `dsp.dashboard.prefs.v1`
- Theme → existing Theme Switcher / ThemeProvider
- Recent & saved searches → local UI only

## Trust rules

- Never invent portfolio totals, scores, or recommendations
- Empty copy uses **Data unavailable.** plus a next investigation step
- Research Mode / compliance flags are presentation only
