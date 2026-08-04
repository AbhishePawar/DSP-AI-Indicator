# EPIC-F003 — Application Shell Architecture

## Structure

```
┌────────────┬──────────────────────────────────────┐
│  Sidebar   │  Sticky Header (search, crumbs, …)   │
│  (collapsible│────────────────────────────────────│
│   / drawer)│  Main #main-content (PageContainer)  │
│            │──────────────────────────────────────│
│            │  Footer / StatusBar                  │
└────────────┴──────────────────────────────────────┘
```

Public auth routes (`/login`, recovery, etc.) skip the shell (F002).

## Navigation registry

Source: `apps/web/src/lib/shell/navigationRegistry.ts`

| Item | Path | Access |
|---|---|---|
| Dashboard | `/dashboard` | Authenticated shell |
| Company Analysis | `/analysis` | `read_research` (legacy soft-open) |
| Portfolio | `/portfolio` | `read_research` / PM roles |
| Research Workspace | `/research` (+ nested Institutional) | `read_research` |
| Administration | `/admin` | admin permissions / `administrator` |
| Settings | `/settings` | All |
| Profile | `/profile` | All |

Command palette searches shell + auxiliary routes (no backend search).

## State

`useUiStore` (`dsp.shell.ui.v1`): sidebar collapsed, recent pages, favourites
(UI only), command palette / mobile drawer flags.

Theme persistence remains in `ThemeProvider` (F001/F002).

## Layout primitives

- `PageContainer` / `ContentArea`
- `LoadingLayout` / `ErrorLayout` / `EmptyLayout`
- Skip link → `#main-content` (root layout)

## Thin client

No valuation, scoring, or AI reasoning in the shell. Menu visibility is
permission presentation only — route guards remain F002 / existing.
