# EPIC-F010 — Validation Report

## Responsive Validation

Critical routes: `/login` · `/dashboard` · `/analysis` · `/portfolio` · `/research` · `/admin` · `/settings`

Viewports catalogued: 320 · 375 · 390 · 414 · 768 · 1024 · 1280 · 1440 · 1920

Fixes:
- Mobile drawer max-width + Escape / focus trap / focus restore
- Workspace side panels auto-collapse below `lg` on mount
- Mobile command-palette icon in Topbar (center search remains `md+`)
- Page titles scale `text-2xl → md:text-4xl`; overflow-auto on main regions

## Accessibility Audit

| Item | Status |
|---|---|
| Skip link → `#main-content` on auth + app shells | PASS |
| Single document `<main>` (workspaces use `role="region"`) | PASS |
| Mobile nav dialog Escape + Tab trap | PASS |
| Header `aria-label` | PASS |
| PageHeader no longer duplicate `<header>` banner | PASS |
| Customize panel Escape | PASS |
| Reduced motion / high contrast / focus datasets (F009) | PASS |
| Full axe CI scan | Remaining (see Remaining Issues) |

## Design System Audit

- Shell + F005–F009 workspaces use `@/components/ds`
- Legacy `@/components/ui/*` still present on institutional-dashboard / advisor surfaces (scoped remaining)
- Typography / spacing tokens unchanged; responsive title scaling tightened

## Performance Audit

- No new polling
- Panel collapse is one-shot mount effect
- Query caching unchanged
- Bundle: no new dependencies

## Browser Validation

Target matrix: Chrome · Edge · Firefox · Safari — uses standard CSS + Radix patterns already shipping. Automated jsdom covers behaviour; device browser matrix remains manual for F011.

## Remaining Issues

1. Full axe-core CI gate not wired (launch checklist a6)
2. Legacy `components/ui` migration for institutional-dashboard / advisor
3. Manual visual QA checklist across all 9 viewport widths in real browsers
4. Focus trap is basic (first/last) — DS Drawer adoption optional later
