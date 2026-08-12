# VISUAL QA MATRIX — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Programme | EPIC-010 / GA-001 — Institutional Visual QA Certification |
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Branch | `cursor/p6-1-commercial-readiness` |
| Tip at evaluation start | `97b81eb` (*docs(release): certify production version 1.0.0*) |
| Date | 2026-08-02 |
| Mode | Certification — **not** redesign; minimal HIGH visual defect fixes only |
| Prior artefacts | `RC3_FINAL_CERTIFICATION_REPORT.md` · `RC3_004_IMPLEMENTATION_REPORT.md` · Design System `docs/design/` |
| Evidence method | **Hybrid:** systematic code-level Visual QA + HTTP smoke on running Next.js 15.5.21 (`localhost:3001`); headed browser MCP tab creation unavailable in this agent environment |
| Commercial Visual QA decision | **PASS WITH CONDITIONS** (closed-beta / institutional pilot) — **not** unrestricted Commercial GA |

---

## 1. Evidence posture (honest)

| Evidence type | Status |
|---|---|
| Code-level layout / DS / theme / touch-target review | **Executed** across certified surfaces |
| HTTP smoke (route responds) | **Executed** — `/`, `/login`, `/signup`, `/docs/privacy`, `/docs/terms`, `/docs/disclaimer`, `/session-expired`, `/forbidden`, `/dashboard`, `/analysis` → HTTP 200 |
| Headed screenshot matrix (Desktop/Laptop/Tablet/Mobile × Light/Dark) | **Unavailable** — `cursor-ide-browser` could not create a browser tab (`No browser tab available`); prior stale `:3000` process was unhealthy; fresh `next dev` on `:3001` served pages but MCP capture blocked |
| Auth-gated interactive states (loaded analysis, portfolio holdings, report modules) | **Not headed-verified** — client ProtectedRoute / session required; documented from code + prior RC3 suites |
| Print (Institutional Reports) | **Code-verified** (`globals.css` print rules + `print:hidden` / `break-inside` on report chrome) — not printer-preview captured |
| Firefox / Safari | **Not executed** this pass (RC3 residual) |

**Screenshot Reference legend used below**

| Value | Meaning |
|---|---|
| `code-review` | Systematic static review of page + primary components + DS tokens |
| `http-smoke` | Route returned HTTP 200 from running local Next server |
| `unavailable` | Headed pixel capture not possible in this environment (see §1) |
| `fix-applied` | Defect fixed during this certification (minimal) |

---

## 2. Classification rules

| Severity | Blocks Commercial GA? | Blocks closed-beta freeze? |
|---|---|---|
| **CRITICAL** | Yes | Yes |
| **HIGH** | Yes for public GA claim | No if remediated or accepted with written condition |
| **MEDIUM** | Condition | Prefer fix or track |
| **LOW / COSMETIC** | Track | Accept |

Only **CRITICAL** layout breakers (unusable primary path, white-on-white, systematic clipping of main content) would fail closed-beta Visual QA. None found after HIGH remediations in this pass.

---

## 3. Full matrix

Status values: **PASS** · **PASS WITH CONDITIONS** · **FAIL** · **BLOCKED** (auth/headed capture).

### 3.1 Marketing `/`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS WITH CONDITIONS | code-review + http-smoke · unavailable headed | Gradient-led hero (RC2 cosmetic); brand cream tokens intentional | COSMETIC | Accept — out of redesign scope |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Theme cycle Light/Dark/System present; token-driven | COSMETIC | Accept |
| Laptop 1280 | Light | PASS WITH CONDITIONS | code-review · unavailable headed | Same composition; primary CTAs `min-h-11` | — | Accept |
| Laptop 1280 | Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Token vars | — | Accept |
| Tablet 768 | Light | PASS WITH CONDITIONS | code-review · unavailable headed | Mobile nav Escape/focus-trap/touch (RC3-004) | — | Accept |
| Tablet 768 | Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Same | — | Accept |
| Mobile 390 | Light | PASS WITH CONDITIONS | code-review · unavailable headed | Header theme/menu/CTA `min-h-11`; footer links denser | COSMETIC | Accept footer density |
| Mobile 390 | Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Same | COSMETIC | Accept |

### 3.2 Login `/login`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS | code-review + http-smoke · unavailable headed | DS Input `h-11`, default submit, AuthShell | — | Approved for closed-beta |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review + fix-applied · unavailable headed | Warning Alert previously hardcoded cream (VQA-01) — **fixed** to `--warning-*` | HIGH→fixed | Fixed this pass |
| Laptop 1280 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | AuthShell theme chip &lt;44px | MEDIUM | Accept closed-beta; track |
| Tablet 768 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Same AuthShell | MEDIUM | Accept |
| Mobile 390 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Forms stack; focus rings present | MEDIUM | Accept |

### 3.3 Request Access `/signup`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS | code-review + http-smoke · unavailable headed | Honest Request Access / admin messaging (RC3) | — | Approved closed-beta |
| Desktop ≥1440 | Dark | PASS | code-review · unavailable headed | Token shell | — | Approved |
| Laptop / Tablet / Mobile × L/D | — | PASS WITH CONDITIONS | code-review · unavailable headed | AuthShell theme control density (shared) | MEDIUM | Accept |

### 3.4 Dashboard `/dashboard`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS WITH CONDITIONS | code-review + http-smoke · unavailable headed · auth UI not headed | No Trust Ladder / SourceBadge on widgets (RC3 residual) | HIGH (process/trust chrome) | Document — not redesign |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Token widgets; Research Mode banner expected in code | HIGH residual | Document |
| Laptop 1280 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Panel collapse helpers; Quick Actions default Button height OK | — | Accept chrome |
| Tablet 768 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Drawer / collapse patterns | — | Accept |
| Mobile 390 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Topbar Menu now `min-h-11` (**fixed** VQA-03) | HIGH→fixed | Fixed shell chrome |

### 3.5 Company Analysis `/analysis`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS WITH CONDITIONS | code-review + http-smoke · unavailable headed | TrustLadderCard on summary; primary Run analysis was `sm` 36px — **fixed** to `min-h-11` | HIGH→fixed | Fixed this pass |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review + fix-applied · unavailable headed | Warning/SourceBadge theme tokens fixed via Badge/Alert | HIGH→fixed | Fixed |
| Laptop 1280 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Three-pane + `max-w-6xl` density risk | MEDIUM | Document — no layout redesign |
| Tablet 768 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Panels collapse below lg | — | Accept |
| Mobile 390 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Stacked panes by design; recent-row truncate without title | MEDIUM | Document |
| Print | — | PASS WITH CONDITIONS | code-review | Light print helpers on valuation transparency only | LOW | Accept |

### 3.6 Portfolio Intelligence `/portfolio`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS WITH CONDITIONS | code-review · unavailable headed · auth | No Trust Ladder/SourceBadge; primary Refresh/Analyze were `sm` — **fixed** `min-h-11` | HIGH residual + HIGH→fixed | Ladder document; CTA fixed |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review + fix-applied · unavailable headed | Warning tokens fixed | HIGH→fixed | Fixed |
| Laptop / Tablet / Mobile × L/D | — | PASS WITH CONDITIONS | code-review · unavailable headed | Coverage language honest; skeletons present | HIGH residual ladder | Document |

### 3.7 Research Reports `/research/institutional`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS WITH CONDITIONS | code-review · unavailable headed | Best trust surface (TrustLadderCard); Load report was `sm` — **fixed** | HIGH→fixed | Fixed CTA |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review + fix-applied · unavailable headed | Token + print CSS | — | Accept |
| Laptop / Tablet / Mobile × L/D | — | PASS WITH CONDITIONS | code-review · unavailable headed | Mode `<select>` density; recommendation truncate sans `title` | MEDIUM | Document / track |
| Print | Light (forced) | PASS WITH CONDITIONS | code-review | `globals.css` print hide chrome; white/black body; module break-inside | — | Code-approved; no printer preview |

### 3.8 Research Workspace `/research`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS WITH CONDITIONS | code-review · unavailable headed | No Trust Ladder; Load research was `sm` — **fixed** `min-h-11` | HIGH residual + HIGH→fixed | Ladder document; CTA fixed |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review + fix-applied · unavailable headed | Token shell | — | Accept chrome |
| Laptop / Tablet / Mobile × L/D | — | PASS WITH CONDITIONS | code-review · unavailable headed | Lazy overlays; skeletons | HIGH residual ladder | Document |

### 3.9 Research Panels / IRD `/research/institutional/dashboard`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light | PASS WITH CONDITIONS | code-review · unavailable headed | DS migrated (RC3-004); SourceBadge used legacy warning cream — **fixed** via `ui/Badge` tokens; primary Run research already `md`/`min-h-11` | HIGH→fixed | Fixed badge theme |
| Desktop ≥1440 | Dark | PASS WITH CONDITIONS | code-review + fix-applied · unavailable headed | Warning Alert/Toast/Badge now `--warning-*` under `data-theme` | HIGH→fixed | Fixed |
| Laptop / Tablet / Mobile × L/D | — | PASS WITH CONDITIONS | code-review · unavailable headed | Sticky TOC focusable; full ladder deferred to Reports | HIGH residual | Document |
| Print | — | N/A | — | IRD not primary print surface | — | Accept |

### 3.10 Settings `/settings`

| Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Desktop ≥1440 | Light/Dark | PASS WITH CONDITIONS | code-review · unavailable headed | Tokenized workspace; section nav rows denser than 44px | MEDIUM | Accept density |
| Laptop / Tablet / Mobile × L/D | — | PASS WITH CONDITIONS | code-review · unavailable headed | Dynamic shell + skeletons | — | Accept |

### 3.11 Error pages

| Screen | Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Forbidden `/forbidden` | All | L/D | PASS | code-review + http-smoke · unavailable headed | AuthShell + DS Empty/Error pattern | — | Approved |
| Unauthorized `/unauthorized` | All | L/D | PASS | code-review · unavailable headed | Same AuthShell pattern | — | Approved |
| Session expired `/session-expired` | All | L/D | PASS WITH CONDITIONS | code-review + http-smoke + fix-applied | Warning Alert theme (VQA-01) fixed | HIGH→fixed | Fixed |
| Not found `not-found` | All | L/D | PASS WITH CONDITIONS | code-review · unavailable headed | Legacy `ui/Button` + `ui/Card` vs Auth/DS EmptyState drift | MEDIUM | Document — not CRITICAL; track before GA |
| Global error | All | — | PASS WITH CONDITIONS | code-review | Hardcoded `#3d8bfd` (CSS vars unavailable in fatal shell) | LOW | Accept |

### 3.12 Legal pages

| Screen | Viewport | Theme | Status | Screenshot Reference | Issues Found | Severity | Disposition |
|---|---|---|---|---|---|---|
| Privacy `/docs/privacy` | Desktop/Laptop | L/D | PASS WITH CONDITIONS | code-review + http-smoke · unavailable headed | Dual `h1` (PageHeader + DocArticle) | MEDIUM | Document / track |
| Terms `/docs/terms` | Desktop/Laptop | L/D | PASS WITH CONDITIONS | code-review + http-smoke · unavailable headed | Same dual heading | MEDIUM | Document |
| Disclaimer `/docs/disclaimer` | Desktop/Laptop | L/D | PASS WITH CONDITIONS | code-review + http-smoke · unavailable headed | Same | MEDIUM | Document |
| Risk disclosure `/docs/risk-disclosure` | Desktop/Laptop | L/D | PASS WITH CONDITIONS | code-review · unavailable headed | Same | MEDIUM | Document |
| Cookie / data-usage (related) | — | — | PASS WITH CONDITIONS | code-review · unavailable headed | Shared DocArticle pattern | MEDIUM | Document |
| Tablet / Mobile × L/D (all legal) | — | — | PASS WITH CONDITIONS | code-review · unavailable headed | Readable Card prose; no overflow patterns found | — | Accept |

---

## 4. Cross-cutting checks

| Check | Result | Notes |
|---|---|---|
| Typography (Fraunces/Sora tokens) | PASS WITH CONDITIONS | Marketing/display fonts via CSS vars; body tokenized |
| Spacing / alignment | PASS WITH CONDITIONS | No systematic clipping; 3-pane density at ~1024–1280 noted |
| Icons | PASS | Lucide on shell/marketing; chevrons replace text glyphs (RC3-004) |
| Buttons (primary) | PASS after fix | Flagship Analyse/Load/Menu ≥44px |
| Buttons (secondary toolbar `sm`) | ACCEPT | Density intentional for Hide nav / Pin / Favourite |
| Forms | PASS | Auth inputs `h-11`; focus-visible rings |
| Tables | PASS WITH CONDITIONS | `overflow-x-auto` on analytical tables |
| Cards | PASS WITH CONDITIONS | Flat + border DS; slight padding variance between workspaces (cosmetic) |
| Headers / footers / nav | PASS WITH CONDITIONS | Shell Topbar Menu fixed; marketing header OK; footer density cosmetic |
| Theme switching | PASS after fix | Warning tones follow `data-theme` via CSS vars (no broken `dark:` dependency) |
| Responsive | PASS WITH CONDITIONS | Code + prior `a11y-responsive.test.tsx` (10); headed matrix open |
| Overflow / truncation | PASS WITH CONDITIONS | Reports recommendation truncate without `title` (MEDIUM) |
| Empty / loading / error / skeletons | PASS | Present on CA, Portfolio, Reports, IRD, Research, Settings |
| Trust Ladder visibility | PARTIAL | Strong on Reports + CA summary; weak on Dashboard / Portfolio / Research Workspace |
| Source badges | PARTIAL after fix | IRD SourceBadge theme fixed; not universal on all analytical cells |
| Focus rings | PASS | Widespread `focus-visible:ring-[var(--accent)]` |
| Touch targets (primary) | PASS after fix | Primary CTAs + Topbar Menu ≥44px |
| Purple / non-brand accents | PASS | None on certified surfaces |
| Print (Reports) | PASS WITH CONDITIONS | Code rules present; no printer-preview capture |

---

## 5. Issues ledger (this certification)

| ID | Severity | Screen(s) | Description | Disposition |
|---|---|---|---|---|
| VQA-01 | HIGH | Login, session-expired, IRD, toasts | Warning UI hardcoded cream; `dark:` not wired to `data-theme` | **FIXED** — DS Alert/Toast + legacy ui Alert/Badge → `var(--warning-*)` |
| VQA-02 | HIGH | Analysis, Portfolio, Research, Reports | Primary Analyse/Load CTAs `size="sm"` (36px) | **FIXED** — promoted to default + `min-h-11` |
| VQA-03 | HIGH | Shell Topbar | Menu / Collapse `size="sm"` | **FIXED** — `min-h-11` |
| VQA-04 | HIGH | IRD SourceBadge | Legacy Badge warning cream | **FIXED** with VQA-01 |
| VQA-05 | HIGH | Dashboard, Portfolio, Research Workspace | Trust Ladder / SourceBadge incomplete | **DOCUMENT** — RC3 known residual; no redesign |
| VQA-06 | MEDIUM | AuthShell | Theme cycle control &lt;44px | Accept closed-beta |
| VQA-07 | MEDIUM | ThemeSwitcher | Segments `min-h-9` | Accept density |
| VQA-08 | MEDIUM | Flagship workspaces | 3-pane inside `max-w-6xl` density | Document |
| VQA-09 | MEDIUM | Legal docs | Dual `h1` | Document / track |
| VQA-10 | MEDIUM | not-found | Legacy ui Card/Button DS drift | Document / track |
| VQA-11 | MEDIUM | Reports RightPanel | Recommendation truncate without `title` | Document / track |
| VQA-12 | MEDIUM | Analysis LeftNav | Recent row truncate / small hit | Document |
| VQA-13 | MEDIUM | Reports toolbar | Mode select density | Document |
| VQA-14 | MEDIUM | Settings LeftNav | Section rows denser | Accept |
| VQA-15 | LOW | Topbar legal links | `text-[11px]` | Accept |
| VQA-16 | COSMETIC | Marketing footer | Link density | Accept |
| VQA-17 | COSMETIC | Toolbars | Secondary `sm` controls | Accept |
| VQA-18 | LOW | global-error | Hardcoded blue CTA | Accept |
| VQA-19 | COSMETIC | Marketing hero | Gradient-led (RC2) | Accept — no redesign |

**CRITICAL open:** none.

---

## 6. Files changed during Visual QA (minimal)

| File | Change |
|---|---|
| `apps/web/src/components/ds/feedback/alert.tsx` | Warning → CSS vars |
| `apps/web/src/components/ds/feedback/toast.tsx` | Warning → CSS vars |
| `apps/web/src/components/ui/Alert.tsx` | Warning → CSS vars |
| `apps/web/src/components/ui/Badge.tsx` | Warning → CSS vars |
| `apps/web/src/components/layout/Topbar.tsx` | Menu/Collapse ≥44px |
| `apps/web/src/components/company-analysis/WorkspaceChrome.tsx` | Run analysis ≥44px |
| `apps/web/src/components/company-analysis/WorkspaceLeftNav.tsx` | Analyze ≥44px |
| `apps/web/src/components/portfolio-intelligence/PortfolioIntelligenceWorkspace.tsx` | Refresh / Analyze company ≥44px |
| `apps/web/src/components/research-workspace/ResearchWorkspace.tsx` | Load research ≥44px |
| `apps/web/src/components/institutional-reports/InstitutionalReportsWorkspace.tsx` | Load report ≥44px |

No backend changes. No redesign. No new features.

---

## 7. Alignment with RC3 final cert

| RC3 condition | Visual QA posture |
|---|---|
| Screenshot matrix before public GA | Still **open** — this document is the formal matrix; headed cells remain `unavailable` |
| Trust ladder universality | Still **open** (HIGH residual) — documented, not redesigned |
| Closed-beta UI freeze | Supported by Visual QA **PASS WITH CONDITIONS** |
| Unrestricted commercial GA | **Not approved** by Visual QA (missing headed proof + residual HIGH process items) |

---

## 8. Integrity statement

No screenshots were fabricated. Headed browser MCP capture was attempted and failed (no tab). Public routes were HTTP-smoked against a live `next dev` on port 3001. Authenticated analytical states were certified by code review and prior RC3 automated suites, not by headed pixel approval. Commercial GA is not claimed.
