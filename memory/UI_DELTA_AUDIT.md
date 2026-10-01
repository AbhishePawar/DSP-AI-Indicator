# UI Delta & Parity Audit: Figma ZIP (.figma_latest) vs Next.js Web App (/apps/web)

## Latest live-reference clarification and current delta
The user supplied https://cel-bacon-55476680.figma.site/ as exact visual authority. Live HTML and desktop screenshot confirm Fraunces headings, a centered homepage hero, public top navigation (NO homepage app sidebar), 560px search/depth-choice panel, and compact capability strip. The source ZIP agrees. Demo account/coverage/financial fixtures are not production data and are not copied.

This table records BEFORE status, not a claim of implementation or full visual acceptance. Current delta: home presentation replaced; Company Directory placeholders replaced with search/sector filter/cards; Research Hub added using existing stored analysis/report history with the full old workspace preserved via explicit link/query; analysis TOC reconnected to existing deterministic-result sections; Fraunces restored; shared PageHeader made compact. All other working page interiors remain unchanged in this batch. Only CompanyCategory/CompanyStats placeholder components deleted after repository-wide zero-reference check; no API/business logic removed. Validation reports live under test_reports/ui_delta.


## 1. Executive Summary & Audit Constraints

- **Scope:** Read-only audit comparing the authoritative reference ZIP extracted at `/app/.figma_latest` (55 source/design files, byte-identical to `/app/.figma_ref`) with the Next.js 16 + React 19 web application in `/app/apps/web/src`.
- **Target Typography Authority:** Source ZIP `index.css` is the sole typography authority:
  - **Headings / Display:** `Fraunces`, Georgia, serif (`--font-heading: 'Fraunces', Georgia, serif;`)
  - **Body / Sans:** `Inter`, system-ui, sans-serif (`--font-body: 'Inter', system-ui, sans-serif;`)
  - **Monospace / Financial Data:** `JetBrains Mono`, monospace (`--font-data: 'JetBrains Mono', monospace;`)
  - *(Correction from prior stale handoff which incorrectly specified Inter for headings).*
- **Architecture Principle:** The live Next.js application structure, server actions, route handlers, real backend `/api/v1` integrations, cookie/enterprise auth, RBAC permissions, and deterministic DSP research methodology must remain intact. Vite demo mock auth, static local storage fake stores, or hardcoded dummy research loops from the ZIP must **never** overwrite or replace working backend logic.
- **Categorization Taxonomy:**
  - `KEEP`: Existing functionality, backend integration, or presentation matches reference specifications or represents core protected engine logic.
  - `PRESENTATION DELTA`: Route exists with functional logic, but styling, layout, typography (`Fraunces` headings), color tokens, spacing, or card layouts deviate from the Figma ZIP.
  - `FUNCTIONAL GAP`: Reference ZIP provides interactions, modals, views, or tabs missing in the current Next.js page, or current page lacks live hookup to corresponding feature.

---

## 2. Global Shell & Theme Token Audit

| Asset / Component | Reference ZIP (`.figma_latest`) | Current Implementation (`apps/web/src`) | Category | Audit Findings & Surgery Guidance |
|---|---|---|---|---|
| **Typography Scale & Fonts** | `index.css`: Fraunces (400, 500, 600), Inter (300-600), JetBrains Mono (400, 500) | `globals.css`: `--font-display: "Inter", sans-serif;` | `PRESENTATION DELTA` | Correct `--font-display` and `--font-heading` to load and use `Fraunces`. Retain `Inter` for body and `JetBrains Mono` for tabular figures/stats. |
| **Color System & Spacing Tokens** | `index.css`: `--bg: #080b12`, `--card: #111520`, `--primary: #7c6af7`, `--c-cashflow: #2dd4bf`, `--sp-1` to `--sp-10` (4px base) | `globals.css`: matching hex variables declared; utility classes `.dsp-card`, `.section-label`, `.stat-value` defined | `KEEP` | Color variables align. Ensure classes use Fraunces for display headings and JetBrains Mono for `.stat-value`. |
| **Global App Layout & Shell** | `src/layouts/AppLayout.tsx`: 48px sticky header (`var(--card)`), 220px fixed/drawer sidebar, profile chip top-right | `components/layout/AppLayout.tsx`, `Sidebar.tsx`, `Topbar.tsx`: 48px topbar, 220px sidebar, command palette, feedback context | `KEEP` / `PRESENTATION DELTA` | AppShell and responsive drawer match 220px/48px structure. Replace heading font inside topbar and sidebar logo with Fraunces. Preserve session & command palette. |
| **Navigation Items** | `src/components/Nav.tsx`: Dashboard, Research (Hub, Institutional, Canvas, Intelligence), Companies, Compare, Portfolio, AI Copilot, Advisor, Profile, Coupons, Pricing, Settings, Admin | `components/layout/Sidebar.tsx`: Includes primary items, nested research groups, and RBAC filtered "More" group | `KEEP` | Keep RBAC filtering and dynamic active states. Add `/coupons` link to sidebar bottom items to match reference. |

---

## 3. Route-by-Route & Component BEFORE → AFTER Map

### 3.1 Marketing Routes

| Route | Reference File (`.figma_latest`) | Current File (`apps/web/src`) | Category | Differences & Surgical Changes | Safe Deletion Conditions |
|---|---|---|---|---|---|
| `/` | `pages/LandingPage.tsx` (435 lines) | `app/(marketing)/page.tsx` + `components/marketing/MarketingLanding.tsx` | `PRESENTATION DELTA` | Reference has: radial hero gradient, dual search choices ("Simple Research" vs "DSP Buffett Analysis" card popup), trending ticker pills (`getTrending`), 4 stats cards, 4 feature cards (`/copilot`, `/analysis`, `/compare`), and bottom CTA. Current page has basic single search and prompt pills. Retain Next.js metadata and SSR structure; update `MarketingLanding.tsx` to match the two-column analysis depth preview and Fraunces typography. | Do not delete `apps/web/src/components/marketing/content.ts` if used by tests. |
| `/about` | `pages/marketing/About.tsx` (70 lines) | `app/(marketing)/about/page.tsx` (41 lines) | `PRESENTATION DELTA` | Reference has 3-pillar narrative ("Evidence First", "Deterministic Pipeline", "Designed for Trust") with Fraunces serif headings and JetBrains Mono markers. Current uses generic marketing layout. Align presentation to reference grid. | None. |
| `/contact` | `pages/marketing/Contact.tsx` (56 lines) | `app/(marketing)/contact/page.tsx` (111 lines) | `KEEP` | Current implementation already implements robust accessible contact form with validation, status handling, and contact details. Retain current functional logic with minor spacing alignment. | None. |
| `/faq` | `pages/marketing/FAQ.tsx` (38 lines) | `app/(marketing)/faq/page.tsx` (49 lines) | `KEEP` | Both use collapsible accordion for core research questions. Current implementation supports keyboard accessibility and search filters. | None. |
| `/pricing` | `pages/marketing/Pricing.tsx` (213 lines) | `app/(marketing)/pricing/page.tsx` (141 lines) | `PRESENTATION DELTA` | Reference includes monthly/annual billing toggle, 3 tiers (Starter ₹0, Professional ₹4,999/mo, Institutional ₹24,999/mo), FAQ strip, and feature comparison matrix. Current page has enterprise-gated contact CTA. Keep gating/disclaimer notice while updating visual card tiers to match Figma styling. | None. |

---

### 3.2 Authentication Routes

| Route | Reference File (`.figma_latest`) | Current File (`apps/web/src`) | Category | Differences & Surgical Changes | Safe Deletion Conditions |
|---|---|---|---|---|---|
| `/login` | `pages/auth/Login.tsx` (77 lines) | `app/(auth)/login/page.tsx` + `LoginForm.tsx` | `PRESENTATION DELTA` | Reference has clean single-card layout with email/password, "Demo login" button, and links to signup/forgot-password. Current has enterprise cookie session, MFA, passkey, and rate-limiting. **PRESERVE ALL REAL AUTH INTEGRATION**. Only align outer container styles and Fraunces heading ("Welcome back"). | Never delete real auth hooks or MFA/Passkey logic. |
| `/signup` | `pages/auth/Signup.tsx` (61 lines) | `app/(auth)/signup/page.tsx` | `PRESENTATION DELTA` | Reference is clean card with name, email, password, role select. Current has full password strength meter, email verification gate, and terms acceptance. Preserve registration API mutation, restyle container to match reference card padding (`var(--card-padding)`). | None. |
| `/forgot-password` | `pages/auth/ForgotPassword.tsx` (30 lines) | `app/(auth)/forgot-password/page.tsx` | `PRESENTATION DELTA` | Reference has simple email reset dispatch. Current has token tracking, resend countdown, and delivery provider handling. Keep functional logic, align visual card. | None. |
| `/reset-password` | `pages/auth/ResetPassword.tsx` (22 lines) | `app/(auth)/reset-password/page.tsx` | `PRESENTATION DELTA` | Reference has new password + confirm form. Current has token validation from query params. Preserve token handling. | None. |
| `/verify-email` | `pages/auth/VerifyEmail.tsx` (18 lines) | `app/(auth)/verify-email/page.tsx` | `PRESENTATION DELTA` | Reference has static "Check your inbox" card. Current connects to verification token API and resend trigger. Retain backend connection. | None. |

---

### 3.3 Core Application & Research Workspaces

| Route | Reference File (`.figma_latest`) | Current File (`apps/web/src`) | Category | Differences & Surgical Changes | Safe Deletion Conditions |
|---|---|---|---|---|---|
| `/dashboard` | `pages/Dashboard.tsx` (140 lines) | `app/dashboard/page.tsx` + `components/dashboard/ResearchOverview.tsx` | `KEEP` / `PRESENTATION DELTA` | Current `ResearchOverview.tsx` already mirrors the 4 market index cards (`NIFTY 50`, `SENSEX`, `NIFTY IT`, `NIFTY BANK`), live market health check, device watchlist with pin/unpin, and recent research history. Ensure market card typography uses Fraunces/JetBrains Mono and sparkline aesthetics match reference. | Do not delete `useDashboardPrefsStore`. |
| `/analysis` | `pages/CompanyAnalysis.tsx` (1,569 lines) | `app/analysis/page.tsx` + `components/company-analysis/CompanyAnalysisWorkspace.tsx` + `ModernAnalysisResult.tsx` | `PRESENTATION DELTA` / `FUNCTIONAL GAP` | Reference contains: 14-section grouped sticky TOC sidebar (`s01`–`s14`), Buffett-style dimension matrix (10 criteria with status pills), 5 domain scorecards (Moat, Management, Financials, Earnings, Growth), DCF Valuation slider/gauge, 10-step staged loader, and interactive "Ask DSP" side drawer. Current `CompanyAnalysisWorkspace` has modern summary and backend `/api/v1/analyse` integration. Surgically map the 14 reference sections to render authoritative backend payload data from `ResearchView` and `reportTransparency`. | Old unused partial sub-views in `components/analysis/` can be archived if not referenced. |
| `/compare` & `/analysis/compare` | `pages/SecurityCompare.tsx` (939 lines) | `app/compare/page.tsx` + `components/company-comparison/CompanyComparisonWorkspace.tsx` | `PRESENTATION DELTA` | Reference has dual-ticker selector (TCS vs INFY default), side-by-side metric table across 6 domains (Quality, Valuation, Profitability, Growth, Financial Health, Dividend), and winner indicator badges. Current `CompanyComparisonWorkspace` already connects to backend comparative analysis. Surgically style comparison table to match reference borders and typography. | None. |
| `/portfolio` | `pages/Portfolio.tsx` (141 lines) | `app/portfolio/page.tsx` + `components/portfolio-intelligence/PortfolioIntelligenceWorkspace.tsx` | `PRESENTATION DELTA` | Reference has: Summary bar (Total Value, Total Gain/Loss, DSP Health Score), Holdings Table with ticker, allocation %, shares, avg buy price, current price, and DSP Rating pill, plus "+ Add Position" modal. Current implementation is a deep enterprise portfolio intelligence workspace. Wrap or style the main view with the clean reference summary cards and holdings table while preserving backend persistence. | None. |
| `/research` | `pages/ResearchHub.tsx` (100 lines) | `app/research/page.tsx` + `components/research-workspace/ResearchWorkspace.tsx` | `PRESENTATION DELTA` | Reference has search header, quick filter chips (All, Technology, Financials, Consumer), and research report grid with company card, summary, tags, and date. Current page has workspace primitives. Update layout to display the research report directory card grid. | None. |
| `/research/institutional` | `pages/InstitutionalResearch.tsx` (114 lines) | `app/research/institutional/page.tsx` + `components/institutional-dashboard/InstitutionalResearchDashboard.tsx` | `PRESENTATION DELTA` | Reference includes coverage breakdown by sector, institutional ratings distribution bar chart (Recharts), and institutional tear-sheet download cards. Current page already has comprehensive institutional analysis. Align header and distribution chart styling. | None. |
| `/research/canvas` | `pages/ResearchCanvas.tsx` (130 lines) | `app/research/canvas/page.tsx` + `components/research-canvas/ResearchCanvasWorkspace.tsx` | `PRESENTATION DELTA` | Reference has 3-column layout: Left (pinned notes & tickers), Center (freeform research editor/canvas with block cards), Right (live reference quotes & citations). Current workspace already has docking and notebook store. Style borders and typography to match reference. | None. |
| `/research/intelligence` | `pages/ResearchIntelligence.tsx` (85 lines) | `app/research/intelligence/page.tsx` + `components/research-intelligence/ResearchIntelligenceWorkspace.tsx` | `PRESENTATION DELTA` | Reference provides market-wide signal feed: Quality upgrades, Valuation alerts, Risk warnings, and Moat expansions. Current `ResearchIntelligenceWorkspace` has deterministic timeline and evidence validation. Connect real signal facts into the feed UI. | None. |
| `/companies` | `pages/CompanyDirectory.tsx` (87 lines) | `app/companies/page.tsx` + `components/companies/CompanyGrid.tsx` | `KEEP` / `PRESENTATION DELTA` | Both implement directory search, sector filters, and company card grid (symbol, name, sector, price, change, rating). Current page already draws from `COMPANY_CATALOGUE`. Apply `.dsp-card` styling and JetBrains Mono badges. | None. |
| `/advisor` | `pages/Advisor.tsx` (73 lines) | `app/advisor/page.tsx` + `components/advisor/AdvisorWorkspace.tsx` | `PRESENTATION DELTA` | Reference provides Client Directory cards, meeting notes summary, and portfolio review status. Current implementation has deep multi-tenant advisor workspace with demo gating. Preserve backend RBAC/demo gate; ensure the top-level overview matches the clean Figma cards. | None. |
| `/copilot` | `pages/AICopilot.tsx` (94 lines) | `app/copilot/page.tsx` + `components/copilot/CopilotLayout.tsx` | `PRESENTATION DELTA` | Reference has clean chat shell: Suggested prompt pills at top, conversation bubble list with evidence citations, and bottom sticky composer with disclaimer. Current `CopilotLayout` connects to real deterministic backend answers. Ensure UI chat bubbles match reference spacing and colors. | None. |
| `/control-center` | `pages/ControlCenter.tsx` (94 lines) | `app/control-center/page.tsx` + `components/control-center/ControlCenter.tsx` | `PRESENTATION DELTA` | Reference provides settings toggles (Dark Theme, Real-time quotes, Email alerts, Research Mode, API access key). Current has system observability and permission panels. Retain all admin controls, adopt toggle UI switch styling. | None. |
| `/admin` | `pages/AdminPanel.tsx` (147 lines) | `app/admin/page.tsx` + `components/admin-console/AdminConsole.tsx` | `PRESENTATION DELTA` | Reference has user management table, API quota monitors, system health badges, and audit log. Current `AdminConsole` has RBAC guards and live telemetry. Preserve RBAC/auth guards; align table padding and typography. | None. |
| `/diagnostics` | `pages/Diagnostics.tsx` (68 lines) | `app/diagnostics/page.tsx` + `components/observability/DiagnosticsDashboard.tsx` | `KEEP` | Both present latency metrics, backend health checks, cache status, and version manifest. Current implementation is connected to live `/api/health` and timing stores. | None. |
| `/profile` | `pages/ClientProfile.tsx` (410 lines) | `app/profile/page.tsx` + `components/profile/UserProfile.tsx` | `PRESENTATION DELTA` / `FUNCTIONAL GAP` | Reference contains comprehensive client financial profile: Financial Health Score gauge (84/100), Net Worth summary, Asset Allocation chart, Risk Profile radar, Goal progress bars, and linked accounts. Current page has basic profile card. Integrate reference financial profile layout with backend user session data. | None. |
| `/coupons` | `pages/Coupons.tsx` (583 lines) | Missing in `apps/web/src/app` | `FUNCTIONAL GAP` | Reference page presents institutional voucher management, promo discount codes, referral links, and partner offer redemptions. Route needs to be created under `apps/web/src/app/coupons/page.tsx` mounting the corresponding component. | None. |

---

## 4. Protected Engine Logic (STRICT NO-TOUCH)

The following services and modules are authoritative, verified, and protected from modification:
1. **Deterministic Research Engine:** `/api/v1/analyse` pipeline and underlying Python calculation methodology.
2. **Client API Composition & Envelope Mapping:** `lib/api/client.ts`, `lib/analysis/mapEnvelope.ts`, `lib/research/mapResearchView.ts`.
3. **Authentication & Session Stores:** `lib/auth/AuthProvider.tsx`, `cookieSession.ts`, `sessionStore.ts`, and RBAC route guards.
4. **Market & Fundamentals Connectors:** Real endpoints `/api/v1/market/quote`, `/api/v1/market/health`, `/api/v1/financial-statements`.
5. **Report Transparency & Evidence Ledger:** `lib/report-transparency/`, `lib/trust/surfaceTrust.ts`.

---

## 5. Summary & Action Plan for Implementation Phase

1. **Typography Update:** Add `Fraunces` font definition to Tailwind/Next.js root (`globals.css`) for display/heading hierarchy.
2. **Missing Route Addition:** Create `/app/apps/web/src/app/coupons/page.tsx` porting `Coupons.tsx` with Next.js navigation.
3. **Visual Alignment on Core Screens:**
   - Update `MarketingLanding.tsx` with dual-depth analysis modal preview.
   - Refine `CompanyAnalysisWorkspace.tsx` to surface the 14-section grouped TOC and Buffett-criteria status badges from live backend analysis view.
   - Update `UserProfile.tsx` with the Financial Health Gauge and allocation cards from `ClientProfile.tsx`.
   - Update `Sidebar.tsx` to include the Coupons navigation link and Fraunces logo font.
4. **Automated Parity & Test Protection:** Ensure all interactive elements carry `data-testid` attributes to preserve 100% test pass rate across existing unit/journey suites.
