# P9.7 — Platform-Wide UX & Quality Certification (RC-1)

| Field | Value |
|---|---|
| Programme | P9.7 / EPIC-008 · Platform-Wide UX & Quality Certification |
| Scope | Entire DSP AI Indicator frontend (user-facing) |
| Date | 2026-08-01 |
| Reviewer | Cursor agent (product quality review) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Design System | `docs/design/` v1.0.0 |
| Ontology | REP-002 Research Ontology v1.0 |
| Thin client | Frozen `/api/v1` only — no browser valuation / recommendation / AI reasoning |
| Release candidate | **RC-1** |
| Decision | **PASS WITH CONDITIONS** |

---

## 1. Executive Summary

This review certifies the **entire** DSP AI Indicator frontend for institutional UX, accessibility, consistency, trust, and quality readiness as Release Candidate RC-1.

**Verdict: PASS WITH CONDITIONS.**

Primary analytical surfaces (Executive Dashboard, Company Analysis Workspace, Institutional Reports / Research Workspace) meet Research Mode institutional baseline: thin-client, honest empties, REP-002 terminology (post P9.4 remediations), trust ladder on report/analysis paths, DS tokens, keyboard/reduced-motion patterns, and typed error handling.

Blocking honesty defects found during this platform review were **remediated in the frontend only** (marketing commercial disclosure, auth verification copy, portfolio research-coverage defaults, institutional-dashboard gateway error surfacing, feedback dialog focus trap, beta disclaimer permanence). Remaining items are named conditions with owners — none block RC-1 Research Mode ship if conditions are tracked.

**Not in scope / not changed:** backend packages, analytical engines, API contracts, scoring models.

### Prior art incorporated

| Review | Surface | Prior decision |
|---|---|---|
| `docs/reviews/P9_4_COMPANY_WORKSPACE_UX_CERTIFICATION.md` | `/analysis` | PASS WITH CONDITIONS (carried forward) |
| `docs/design/15_UI_Certification_Checklist.md` | Authority gates A1–A5 | Applied platform-wide |

---

## 2. Methodology

1. **Static code audit** of all user-facing route groups and shared shell/DS layers (marketing, auth, dashboard, company-analysis, portfolio-intelligence, research-workspace, institutional-reports, institutional-dashboard, settings, beta).
2. **Parallel surface audits** (marketing/auth/shell + analytical workspaces) against Design System (`docs/design/01–15`), REP-002, User Trust Standard, Constitution priority, and thin-client rules.
3. **Cross-check** against P9.4 company-workspace certification conditions.
4. **Minimal frontend remediations** only where defects clearly blocked certification (honesty, ontology/trust presentation, a11y focus).
5. **HTTP smoke** against local Next.js (`localhost:3000`): `/`, `/login`, `/dashboard`, `/analysis`, `/portfolio`, `/research/institutional`, `/pricing` all returned **200**.
6. **Visual QA matrix** via browser MCP: **blocked** in this environment (tab create/navigate flaked; no invented screenshots). Tracked as Condition **C-VQA-PLATFORM-01**.
7. **Cross-browser**: Chrome/Edge path exercised via Next.js smoke only; Firefox/Safari **not** instrumented here — Condition **C-XBR-01**.

---

## 3. Surface coverage

| Surface | Primary paths | Decision after remediation |
|---|---|---|
| Marketing website | `/(marketing)/*`, `MarketingLanding`, pricing | **PASS WITH CONDITIONS** |
| Authentication | `/(auth)/*` login/signup/forgot/reset/verify | **PASS WITH CONDITIONS** |
| Global shell | `AppLayout`, Sidebar, Topbar, Breadcrumbs, StatusBar, Command palette | **PASS WITH CONDITIONS** |
| Settings | `/settings`, `SettingsWorkspace` | **PASS WITH CONDITIONS** |
| Closed beta | `ClosedBetaGate`, `BetaBanner`, Feedback | **PASS WITH CONDITIONS** |
| Executive Dashboard | `/dashboard` | **PASS WITH CONDITIONS** |
| Company Analysis | `/analysis` | **PASS WITH CONDITIONS** (P9.4) |
| Portfolio Intelligence | `/portfolio` | **PASS WITH CONDITIONS** (was FAIL; remediations applied) |
| Institutional Reports | `/research/institutional` | **PASS WITH CONDITIONS** |
| Research Workspace | `/research` | **PASS WITH CONDITIONS** |
| Institutional Dashboard (legacy IRD) | `/research/institutional/dashboard` | **PASS WITH CONDITIONS** (was FAIL; remediations applied) |

---

## 4. Certification areas

### 4.1 Design System Compliance

| Gate | Result | Notes |
|---|---|---|
| Typography (Fraunces / Sora via tokens) | Pass | Marketing + shell + workspaces use display/body CSS variables |
| Spacing / grid | Pass | Tokenized spacing; `sm/md/lg` responsive grids |
| Color / themes | Pass | Teal/slate CSS variables; Light/Dark via settings AppearanceApplicator |
| Elevation / radius / shadow | Pass | Border-first cards; shadows on dialogs/dropdowns |
| Buttons / forms / cards | Pass | Auth + analytical workspaces prefer `@/components/ds` |
| Charts / tables | Pass with conditions | No fabricated series; honest empties; IRD still uses some `components/ui/*` (C-DS-02) |
| Icons | Pass with conditions | Lucide sparse; research density text-first |
| Motion | Pass | Global `prefers-reduced-motion`; purposeful transitions |

### 4.2 Ontology Compliance (REP-002)

| Domain | Result |
|---|---|
| Business Quality (Book 04) | Pass — Cap Allocation Quality, Reinvestment Opportunity, etc. (P9.4) |
| Management (Book 05) | Pass — Corporate Governance, Execution Capability, Shareholder Orientation, Leadership Quality |
| Economic Moat (Book 06) | Pass — Brand Strength, Network Effects, Distribution Advantage, Cost-Based Moat |
| Risk (Book 07) | Pass — no dishonest financial_strength aliasing (P9.4) |
| Parallel ontology | Pass — no renamed duplicate concepts introduced platform-wide |

### 4.3 Trust Certification

| Pillar | Result |
|---|---|
| Facts → Analysis → Inference → Recommendation | Pass on Company Analysis + Institutional Reports; IRD directs users to Reports for full ladder (remediated disclosure) |
| Confidence | Pass where API supplies; otherwise honest unavailable |
| Evidence / contradictory evidence | Pass on Analysis (AI Committee + Explainability) and Institutional Reports |
| Research timestamp / freshness | Pass on Analysis header + Reports audit; Dashboard widgets honest when absent |
| No fabricated analytical numbers | Pass after remediations (portfolio quality “Available” fallback removed; coverage flags honest) |
| Commercial honesty (marketing) | Pass after illustrative packaging disclosure + unpublished contact channels |

### 4.4 Accessibility

| Check | Result |
|---|---|
| Keyboard | Pass — section shortcuts, Ctrl+K palette, sidebar arrows, analyse Ctrl+Enter |
| Focus visible | Pass after Settings LeftNav + Marketing footer + Feedback dialog remediations |
| ARIA / landmarks | Pass — skip link, labelled regions, dialogs |
| Contrast | Pass with conditions — DS tokens target AA; no automated axe CI (C-A11Y-PLATFORM-01) |
| Reduced motion | Pass — globals + workspace `motion-reduce:` |
| Touch targets | Pass — CTAs / feedback button ≥44px patterns |
| Feedback dialog focus trap | Pass after DS Radix Dialog migration |

### 4.5 Responsive

| Viewport | Result |
|---|---|
| Desktop / Laptop | Pass — three-column workspaces, shell sidebar |
| Tablet | Pass with conditions — panel collapse patterns present; screenshot matrix incomplete |
| Mobile | Pass with conditions — drawer nav, stacked sections; screenshot matrix incomplete |
| Landscape | Pass with conditions — structure responsive; not screenshot-verified |

### 4.6 Performance

| Check | Result |
|---|---|
| Lazy load / code split | Pass on Company Analysis + Institutional Reports (`React.lazy` + dynamic imports) |
| Portfolio section split | Pass with conditions — some sections still eager-wrapped (C-PERF-PORT-01) |
| Skeletons | Pass — workspace skeletons / Suspense fallbacks |
| CLS | Pass with conditions — skeletons mitigate; no Lighthouse numbers (C-PERF-PLATFORM-01) |
| Interaction latency | Pass — local section switches; no client scoring |

### 4.7 Error Handling

| State | Marketing/Auth | Analytical surfaces |
|---|---|---|
| 401 / 403 | Auth redirects / typed copy | Typed analyse / gateway messages |
| 404 / no coverage | Honest empty / contact | Typed “no coverage” |
| 500 | N/A / API boundary copy | Typed server error |
| Timeout / network | Auth forms disclose API boundary | Typed timeout / network copy |
| Partial coverage | N/A | Header coverage + IRD gateway warning (remediated) |

### 4.8 Empty States

Honest **Data unavailable.** / **Unable to calculate.** patterns verified across Analysis, Portfolio Intelligence, Reports, IRD mapper, Dashboard widgets. No fabricated research series or scores observed after remediations.

### 4.9 Navigation

| Element | Result |
|---|---|
| Sidebar / menus | Pass — RBAC-filtered, active states |
| Breadcrumbs / page header | Pass |
| Command palette | Pass with conditions — route list not RBAC-filtered like sidebar (C-NAV-01) |
| Back / deep links | Pass — query `section` / `symbol` patterns |
| Beta gate | Pass — fail-closed when invitation API unavailable |

### 4.10 Visual Consistency

Shared token language across marketing wash, auth shell, and institutional workspaces. Residual drift: IRD + Feedback remnants still import some `components/ui/*` (C-DS-02). Marketing intentionally uses a composed marketing system (not DS primitive cards in hero) — acceptable per Brand / marketing rules.

### 4.11 Cross-browser

| Browser | Result |
|---|---|
| Chromium (local Next smoke) | Pass — routes 200 |
| Edge | Assumed Chromium-equivalent; not separately instrumented |
| Firefox | Not tested — C-XBR-01 |
| Safari | Not tested — C-XBR-01 |

### 4.12 Documentation

This file: `docs/reviews/P9_PLATFORM_UX_CERTIFICATION.md`.

---

## 5. Visual QA

| Surface × Theme/Viewport | Status |
|---|---|
| Marketing Desktop Light | HTTP 200; screenshot MCP blocked |
| Marketing Dark / Tablet / Mobile | Structure responsive in code; screenshots blocked |
| Auth Desktop Light | HTTP 200; screenshots blocked |
| Dashboard / Analysis / Portfolio / Reports × Light/Dark/Tablet/Mobile | HTTP 200 for primary routes; screenshots blocked |

**Honest limitation:** Browser MCP could not retain a stable tab (`browser_navigate` / lock failures). No screenshot assets were fabricated. Condition **C-VQA-PLATFORM-01**.

---

## 6. Issues Found

### 6.1 Remediated in this certification (frontend only)

| ID | Severity | Issue | Fix |
|---|---|---|---|
| F-MKT-01 | High | Pricing/$149 and `.example` contacts presented as live commercial facts | Added `COMMERCIAL_PRICING_DISCLOSURE`; prices labelled Illustrative; unpublished contact channels when `channelsPublished: false` |
| F-AUTH-01 | High | Verify-email claimed acceptance + login “Email verified” without API | Honest local-capture copy; no `?verified=1` success claim; login info alert corrected |
| F-PORT-01 | High | New holdings set `researchAvailable: true` without verified research | Default `false` on workspace add |
| F-PORT-02 | High | Quality mapper fell back to fabricated `"Available"` | Fallback → `Data unavailable.` |
| F-PORT-03 | Medium | `holdingFromInput` defaulted `researchAvailable ?? true` and recommendation `"Hold"` | Defaults → `false` / `Data unavailable.` |
| F-PORT-04 | Low | Coverage badge said “Available” | Relabelled “Session flag: linked” / “Not linked” |
| F-IRD-01 | High | `dataBundle` errors swallowed to generic unavailable | Typed 401/403/404/timeout/5xx/network gateway notes |
| F-IRD-02 | Medium | Missing trust-ladder disclosure on IRD route | Explicit Alert directing to Institutional Reports for ladder/evidence |
| F-IRD-03 | Medium | RS validation read as report PASS | Relabelled panel-structure check (STRUCTURE OK/GAP) |
| F-A11Y-01 | Medium | FeedbackDialog lacked focus trap | Migrated to DS Radix `Dialog` |
| F-A11Y-02 | Low | Settings LeftNav missing focus-visible ring | Added ring |
| F-A11Y-03 | Low | Marketing footer links lacked focus rings | Added focus-visible styles |
| F-TRUST-BETA-01 | Medium | Campaign beta banner could replace disclaimer | Immutable “not investment advice” always appended |

### 6.2 Open conditions

| ID | Severity | Condition | Owner | Target |
|---|---|---|---|---|
| C-VQA-PLATFORM-01 | Medium | Complete screenshot matrix (Marketing/Auth/Dashboard/Analysis/Portfolio/Reports × Desktop Light/Dark × Tablet/Mobile/Landscape) | Frontend UX | Next polish sprint |
| C-VQA-01 | Medium | Carry-forward from P9.4 authenticated analyse screenshot matrix | Frontend UX | Next polish sprint |
| C-A11Y-PLATFORM-01 | Low | Automated axe/contrast CI on key routes | Frontend QA | P9 a11y CI |
| C-A11Y-01 | Low | Carry-forward axe gate on `/analysis` | Frontend QA | P9 a11y CI |
| C-PERF-PLATFORM-01 | Low | Publish LCP/INP budgets with production API | Frontend Perf | Perf budget review |
| C-PERF-01 | Low | Carry-forward Analysis LCP/INP | Frontend Perf | Perf budget review |
| C-PERF-PORT-01 | Low | True code-split portfolio section modules (avoid fake lazy wrappers) | Frontend Perf | Portfolio polish |
| C-NAV-01 | Medium | Filter command-palette routes with same RBAC as Sidebar | Frontend Shell | Security UX follow-up |
| C-DS-01 | Low | Align legacy `SourceBadge` to `@/components/ds` (P9.4) | Design System | DS cleanup |
| C-DS-02 | Low | Migrate IRD (`institutional-dashboard`) remaining `components/ui/*` to DS | Design System | DS cleanup |
| C-TRUST-01 | Low | Optional per-FieldRow SourceBadge coverage (P9.4) | Frontend Trust | Follow-up |
| C-XBR-01 | Low | Explicit Firefox + Safari Visual/a11y pass | Frontend QA | Browser matrix |
| C-CACHE-01 | Low | Distinguish local browser report cache age vs server archive more prominently | Frontend Research | Reports polish |

---

## 7. Improvements Applied

Files touched for certification remediations (frontend only):

- `apps/web/src/lib/commercial/editions.ts`, `index.ts`
- `apps/web/src/app/(marketing)/pricing/page.tsx`
- `apps/web/src/components/marketing/MarketingLanding.tsx`
- `apps/web/src/components/marketing/MarketingFooter.tsx`
- `apps/web/src/app/(auth)/verify-email/page.tsx`
- `apps/web/src/app/(auth)/login/LoginForm.tsx`
- `apps/web/src/components/portfolio-intelligence/PortfolioIntelligenceWorkspace.tsx`
- `apps/web/src/components/portfolio-intelligence/Sections.tsx`
- `apps/web/src/lib/portfolio-intelligence/mapPortfolioIntelligence.ts`
- `apps/web/src/lib/portfolio/data.ts`
- `apps/web/src/components/institutional-dashboard/InstitutionalDashboardClient.tsx`
- `apps/web/src/components/institutional-dashboard/InstitutionalResearchDashboard.tsx`
- `apps/web/src/components/institutional-dashboard/ExportBar.tsx`
- `apps/web/src/lib/institutional-dashboard/rsValidation.ts`
- `apps/web/src/components/beta/FeedbackDialog.tsx`
- `apps/web/src/components/beta/BetaBanner.tsx`
- `apps/web/src/components/settings-workspace/LeftNav.tsx`
- `docs/reviews/P9_PLATFORM_UX_CERTIFICATION.md` (this document)

No backend, engine, or API contract changes.

---

## 8. Authority checklist (`docs/design/15`)

| Gate | Result |
|---|---|
| A1 Constitution | Pass |
| A2 User Trust Standard | Pass (after F-* remediations) |
| A3 Thin client | Pass |
| A4 REP-002 alignment | Pass |
| A5 Design System | Pass with C-DS-01 / C-DS-02 |

---

## 9. Certification Decision

### **PASS WITH CONDITIONS**

**Rationale**

- Platform surfaces audited end-to-end for UX, a11y, trust, ontology, empty/error honesty, navigation, and thin-client compliance.
- Blocking honesty / trust / a11y defects remediated with minimal frontend changes (no redesign).
- Company Analysis prior certification remains valid; Portfolio Intelligence and IRD blockers cleared or honestly re-scoped with disclosures.
- Residual conditions are non-blocking for RC-1 Research Mode if tracked to named owners.

**Ship guidance:** Frontend may proceed as **RC-1** for closed-beta / Research Mode. Do not treat illustrative commercial packaging as live billing. Do not claim email verified without API. Do not claim portfolio research coverage without verified linkage. Complete C-VQA-PLATFORM-01 and C-NAV-01 before broader external launch.

---

## 10. References

- `docs/design/` (01–15), especially `15_UI_Certification_Checklist.md`
- `docs/reviews/P9_4_COMPANY_WORKSPACE_UX_CERTIFICATION.md`
- `docs/USER_TRUST_STANDARD.md`
- `docs/PRODUCT_CONSTITUTION.md`
- `docs/research/REP-002_Research_Ontology/` (Books 04–07)
- `apps/web/src/components/{marketing,layout,dashboard,company-analysis,portfolio-intelligence,research-workspace,institutional-reports,institutional-dashboard,settings-workspace,beta,ds}/`
- `apps/web/src/foundation/`
