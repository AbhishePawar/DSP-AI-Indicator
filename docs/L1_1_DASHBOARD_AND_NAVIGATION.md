# L1.1 — Dashboard & Navigation

**Package:** `apps/web` **0.2.0**  
**Backend:** `v1.0.0-rc1` (frozen, unchanged)  
**Role:** Primary dashboard and navigation shell; thin client only.

## Navigation Map

| Route | Label | Notes |
|---|---|---|
| `/dashboard` | Dashboard | Widget home |
| `/analysis` | Company Analysis | API analyze form |
| `/search` | — | Redirects to `/analysis` |
| `/compare` | Compare Companies | Stub workspace |
| `/portfolio` | Portfolio | Stub workspace |
| `/copilot` | AI Copilot | Stub workspace |
| `/reports` | Reports | Local recent ids + list |
| `/reports/[id]` | Report | `GET /api/v1/report/{id}` |
| `/settings` | Settings | Theme mode |
| `/health` | Health | Detail page (linked from widget) |
| `/platform` | Platform | Detail page (linked from widget) |
| `/login` | Login | Outside AppLayout chrome |
| Logout | — | Account dropdown → clears JWT session |

Primary nav is defined in `src/lib/navigation.ts` (`PRIMARY_NAV`).

## Component Tree

```
RootLayout
├── ThemeProvider (light | dark | system)
├── QueryProvider
├── AuthProvider
├── ErrorBoundary
└── AppLayout
    ├── Sidebar (desktop, collapsible)
    ├── Topbar
    │   ├── Breadcrumbs
    │   ├── Theme select
    │   └── Account Dropdown (Logout)
    ├── ContentArea → page
    └── Mobile drawer (Sidebar)
```

### Design system (`src/components/ui`)

Button, Card, Badge, Alert, Input, SearchBox, Spinner, Skeleton, EmptyState, ErrorState, Modal, Dropdown, Table, Tabs, Tooltip.

### Layout (`src/components/layout`)

AppLayout, Sidebar, Topbar, ContentArea, WidgetGrid, PageHeader, Breadcrumbs.

## Widget Architecture

Dashboard widgets are presentational shells that either:

1. Call `/api/v1` via TanStack Query (`PlatformHealth`, `PlatformInfo`, `RecentReports`), or
2. Navigate / deep-link (`QuickActions`, `CompanySearch`, `AiCopilotCard`), or
3. Show explicit placeholders (`RecentActivity`, `Favorites`).

No widget performs valuation, recommendation, or AI reasoning.

| Widget | Data source |
|---|---|
| Quick Actions | Static links |
| Platform Health | `GET /health` |
| Platform Information | `GET /platform` |
| Recent Reports | localStorage ids + `GET /report/{id}` |
| Recent Activity | Placeholder |
| Company Search | Navigates to `/analysis?symbol=` |
| AI Copilot Card | Link to `/copilot` |
| Favorites | Placeholder |

## Responsive Behaviour

| Viewport | Behaviour |
|---|---|
| Desktop (`md+`) | Persistent sidebar; Collapse/Expand control; max content width |
| Tablet | Same as desktop with narrower sidebar when collapsed |
| Mobile (`< md`) | Sidebar hidden; Menu opens drawer dialog; topbar breadcrumbs |

## API Usage

All HTTP via `src/lib/api/client.ts` — no `dsp_platform` imports.

| Method | Path | Used by |
|---|---|---|
| GET | `/api/v1/health` | Health widget + `/health` |
| GET | `/api/v1/platform` | Platform widget + `/platform` |
| GET | `/api/v1/report/{id}` | Recent reports widget + report detail |
| POST | `/api/v1/analyze/company` | Analysis page (envelope display) |
| POST | `/api/v1/auth/login` | Login (L1.0) |

TanStack Query keys: `["health"]`, `["platform"]`, `["report", id]`.

## Theme System

- Modes: **light**, **dark**, **system**
- Storage key: `dsp.theme.v2`
- Resolved theme applied as `document.documentElement.dataset.theme`
- CSS variables in `globals.css` (teal/slate Fraunces+Sora identity)
- Controls: Topbar select + Settings page

## Accessibility Notes

- Semantic landmarks: `aside`, `nav`, `main`, `header`, breadcrumbs `nav`
- Skip link to `#main-content`
- Focus-visible rings on interactive controls
- Modal/drawer: Escape + backdrop dismiss; `aria-modal`
- Dropdown: `aria-expanded` / `role="menu"`
- Tabs: `role="tablist"` / `aria-selected`
- Loading: `role="status"` / `aria-busy` skeletons
- Errors: `role="alert"`

## Non-goals (enforced)

- No valuation / recommendation / financial calculation in the browser
- No workflow engine or AI reasoning client-side
- Backend and regression suite unchanged for this phase

## Validation checklist

- [x] Navigation map + logout
- [x] Theme light/dark/system
- [x] Collapsible sidebar + mobile drawer
- [x] Health / platform / report API wiring
- [x] ErrorBoundary retained
- [x] Loading skeletons / spinners
- [x] Design system components
- [ ] `npm run build` (requires Node on the machine)
- [ ] Visual pass on real devices (operator)

## Readiness for L1.2

Dashboard & navigation shell is complete as a thin client over frozen `/api/v1`.  
Company Analysis Workspace (L1.2) can deepen `/analysis` without restructuring the shell.
