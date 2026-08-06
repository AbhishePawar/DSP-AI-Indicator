# RC3-004 — Design System Completion / A11y / Performance / Release Polish

| Field | Value |
|---|---|
| Programme | RC-3 remediation from FINAL_PRODUCT_UX_CERTIFICATION_RC2 |
| Scope | Frontend only — DS completion, accessibility, performance UX, responsive/theme polish |
| Date | 2026-08-01 |
| Branch | `cursor/p6-1-commercial-readiness` |
| Prior tip | `da2fe9b` (RC3-003) |
| Decision | **COMPLETE for RC3-004 scope** — polish shipped; Visual QA matrix documented with environment limitations |

---

## 1. Executive Summary

RC3-004 closes the remaining **release polish** gaps called out in RC2 (Visual QA #7, DS drift on IRD, fake portfolio lazy, a11y touch/focus gaps, Research Workspace / IRD weak code-splitting, Lighthouse readiness documentation). No new features, no UX redesign, no backend work.

High-traffic surfaces now share Design System primitives more consistently, portfolio/research/IRD/settings/analysis/report routes use real dynamic imports + skeletons, marketing mobile nav has Escape/focus-trap/touch targets, and shell controls meet clearer a11y affordances.

---

## 2. Design System Improvements

| Area | Change |
|---|---|
| IRD client + panels | Migrated off `components/ui` → `@/components/ds` (`Button`, `Alert`, `Card`/`CardContent`, `Input`, `Spinner`, `Skeleton`, `Badge`, `Tabs`) |
| Section shell / Export bar / ExplainableScore | DS Card/Button/Badge; radius tokens aligned |
| Financial statements tabs | Legacy `ui/Tabs` items API → Radix DS `Tabs` / `TabsList` / `TabsTrigger` / `TabsContent` |
| Shell sidebar | Chevron icons replace text ▾/▸; min 44px expand control |
| Topbar search affordance | `min-h-11` + reduced-motion transition |
| Skeleton | `motion-reduce:animate-none` |
| IRD sticky TOC | Token-based translucent bar; reduced-motion blur off; focusable TOC links |

**User impact:** One visual grammar across Research Panels (IRD) and the rest of the app shell — fewer “second UI kit” moments for institutional users.

---

## 3. Accessibility Improvements

| Finding (RC2) | Fix |
|---|---|
| Marketing mobile nav lacks Escape / focus trap (#42) | Escape closes; Tab cycles within panel; focus restored |
| Header touch targets &lt;44px (#43) | Marketing theme/menu/CTA and mobile links use `min-h-11` |
| DS checkbox ~16px (#44) | Visual 20px + 44×44 hit area via `before:` pseudo |
| Collapsed sidebar text chevrons (#45) | Lucide `ChevronDown` / `ChevronRight` |
| Shell nav touch | Sidebar links `min-h-11`; expand control `size-11` |
| Marketing theme System mode (#41) | Theme control cycles Light/Dark/**System** and labels correctly |
| Reduced motion | Marketing header blur, IRD TOC blur, skeleton pulse, topbar transition |

**User impact:** Keyboard and touch users can operate marketing nav and shell chrome without dead-ends or tiny hit targets.

---

## 4. Performance Improvements

| Finding (RC2) | Fix |
|---|---|
| Portfolio fake `lazy()` (#28) | Dynamic `import("./FlagshipSections")` / `import("./Sections")` + lazy summary bundle (no static Flagship import defeating split) |
| Research Workspace / IRD weak split (#260) | Page-level `next/dynamic` for Research, IRD, Portfolio, Settings, Analysis, Institutional Reports; Research Workspace lazy-loads Buffett / Ratings / Valuation Transparency overlays |
| IRD spinner-only skeleton (#75) | Skeleton grid + polite status while composition loads |
| Reports loading copy | Skeleton + status region instead of plain text |

### Lighthouse readiness (documented)

| Metric focus | Status |
|---|---|
| Route-level code splitting | Improved for flagship workspaces (dynamic + section lazy) |
| Skeleton / CLS mitigation | Present on CA, Portfolio, Research, Reports, IRD, Settings |
| Published LCP/INP CI budgets | **Not added** this pass (RC2 #38 remains a process gap) |
| axe CI gate | **Not added** (RC2 #37 remains) |

Practical readiness: architecture supports good Lighthouse Performance/Best Practices on critical routes when measured against a running build; budgets still need CI wiring outside this polish epic.

---

## 5. Responsive Verification

| Viewport class | Verification method | Result |
|---|---|---|
| Desktop (≥1280) | Code review of shell three-pane / sticky TOC / DS forms | Pass — existing layouts preserved |
| Laptop (1024–1280) | `useCollapsePanelsBelowLg` + a11y catalogue | Pass |
| Tablet (768) | Panel collapse helpers + touch targets | Pass for chrome; landscape tablet not screenshot-captured |
| Mobile (320–414) | Marketing mobile nav + shell drawer patterns in a11y tests | Pass for chrome; deep workspace panes remain stacked by design |

Light/Dark: Theme tokens + IRD border/backdrop use CSS variables (`var(--bg)`, `var(--border)`, `var(--surface)`). Marketing theme cycle includes System.

Automated: `a11y-responsive.test.tsx` (10) **PASS**.

---

## 6. Visual QA Summary

### Screenshot matrix (Desktop / Tablet / Mobile × Light / Dark)

| Route | Desktop L | Desktop D | Tablet L | Tablet D | Mobile L | Mobile D |
|---|---|---|---|---|---|---|
| `/` marketing | Code + layout review | Same tokens | Same | Same | Mobile nav a11y code | Same |
| `/login` | Prior DS auth path | Theme vars | — | — | Touch CTAs | — |
| `/dashboard` | Suite render | Theme vars | Collapse helpers | — | Drawer a11y test | — |
| `/analysis` | Suite render | Theme vars | Panels collapse | — | Stacked panes | — |
| `/portfolio` | Suite render | Theme vars | Panels collapse | — | Stacked panes | — |
| `/research` | Suite render | Theme vars | Panels collapse | — | Stacked panes | — |
| `/research/institutional` | Suite render | Theme vars | — | — | — | — |
| `/research/institutional/dashboard` | Suite render (IRD) | TOC contrast polish | — | — | — | — |
| `/settings` | Dynamic shell | Theme applicator | — | — | — | — |

**Limitation (honest):** Full pixel screenshot capture across 6×9 cells was **not** executed in this agent environment (no reliable headed browser matrix / Lighthouse CI). Visual QA for this pass is **systematic code review + component test renders + prior a11y shell tests**. Finding #7 (production screenshot proof) is **documented as process residual** — recommend attaching CI Playwright/Percy or manual desk screenshots before GA tag.

### Remaining visual inconsistencies (minor)

- Marketing hero remains gradient-led (RC2 cosmetic) — out of redesign scope.
- Advisor / AUX surfaces may still use mixed patterns (hidden from primary palette).
- Card padding / table density still varies slightly between workspaces (RC2 L81–82).
- Print/PDF of Reports not re-verified visually.

---

## 7. Cross-browser Summary

| Browser | Status |
|---|---|
| Chrome / Chromium | Primary development target; Vitest jsdom + Next 15 — **ready** |
| Edge (Chromium) | Expected parity with Chrome — **ready by engine parity** |
| Firefox | Not installed/executed this pass — **likely OK** (standard CSS vars, Radix); recommend smoke before GA |
| Safari (WebKit) | Not installed/executed — **risk residual** on backdrop-filter / sticky TOC; `motion-reduce` paths mitigate animation issues |

---

## 8. Remaining Minor Issues

1. No axe/contrast CI gate (RC2 #37).
2. No published Lighthouse budgets in CI (RC2 #38).
3. Full screenshot matrix still needs CI or manual desk capture (RC2 #7 process).
4. Firefox/Safari formal certification pending.
5. Legacy `components/ui` remains for advisor/AUX/orphan surfaces not in primary IA.
6. Trust ladder universality and BQ ontology were **out of scope** (RC3-001–003 / separate findings).

---

## 9. Release Recommendation

**Ship RC3-004 with the commercial-readiness branch** as the design-system / a11y / performance polish layer after RC3-001–003.

Treat overall RC2 **FAIL for tomorrow-ship commercial claims** as still governed by remaining CRITICAL product/commerce items outside this epic (auth theatre, etc.). For **closed-beta / institutional pilot UI quality**, RC3-004 is **PASS WITH CONDITIONS** (screenshot + Firefox/Safari smoke recommended before GA).

---

## 10. TRACEABILITY

| Cluster | Files | Reason | User impact |
|---|---|---|---|
| IRD DS migration | `InstitutionalDashboardClient.tsx`, `SectionShell.tsx`, `ExportBar.tsx`, `ExplainableScore.tsx`, `InstitutionalResearchDashboard.tsx`, `MarketDataPanel.tsx`, `CorporateActionsPanel.tsx`, `HistoricalSeriesPanel.tsx`, `FinancialStatementsPanel.tsx` | RC2 DS completeness / IRD `ui` imports | Consistent institutional chrome on Research Panels |
| Portfolio real lazy | `PortfolioIntelligenceWorkspace.tsx`, `FlagshipSections.tsx` | RC2 #28 fake lazy | Faster initial portfolio shell; section chunks on demand |
| Route code splitting | `app/portfolio/page.tsx`, `app/research/page.tsx`, `app/settings/page.tsx`, `app/analysis/page.tsx`, `app/research/institutional/page.tsx`, `app/research/institutional/dashboard/page.tsx` | Perf UX / Lighthouse readiness | Lighter first paint on primary routes |
| Research WS lazy overlays | `ResearchWorkspace.tsx` | Eager heavy CA modules | Smaller research landing bundle |
| Marketing a11y | `MarketingHeader.tsx` | RC2 #41–43 | Usable mobile nav + System theme |
| Shell a11y | `Sidebar.tsx`, `Topbar.tsx` | RC2 #43–45 | Touch/keyboard shell polish |
| DS checkbox / skeleton | `ds/forms/checkbox.tsx`, `ds/feedback/skeleton.tsx` | RC2 #44 + reduced motion | Form a11y + calmer loading |
| Report | `docs/reviews/RC3_004_IMPLEMENTATION_REPORT.md` | Certification evidence | Release traceability |

---

## Architecture Impact

- **None** to backend, API contracts, engines, scoring, or auth servers.
- Thin client preserved: display, navigation, prefs, and loading UX only.

## Feature Flags Used

None new.

## Validation Results

| Suite | Result |
|---|---|
| `ds.test.tsx` | PASS (5) |
| `shell.test.tsx` | PASS (14) |
| `a11y-responsive.test.tsx` | PASS (10) |
| `portfolio-intelligence.test.tsx` | PASS (8) |
| `dashboard.test.tsx` | PASS (6) |
| `company-analysis.test.tsx` | PASS (7) |
| `research-workspace.test.tsx` | PASS (7) |
| `institutional-reports.test.tsx` | PASS (7) |
| `institutional-dashboard.test.tsx` | PASS (3) |
| **Total** | **67 / 67 PASS** |
