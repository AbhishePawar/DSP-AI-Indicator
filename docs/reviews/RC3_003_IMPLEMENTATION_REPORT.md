# RC3-003 — Product Coherence & Information Architecture

| Field | Value |
|---|---|
| Programme | RC-3 remediation from FINAL_PRODUCT_UX_CERTIFICATION_RC2 |
| Scope | Frontend only — Product Coherence & IA |
| Date | 2026-08-01 |
| Branch | `cursor/p6-1-commercial-readiness` |
| Decision | **COMPLETE for RC3-003 scope** — ready to merge with remaining RC2 CRITICAL items tracked separately |

---

## 1. Executive Summary

RC3-003 closes the product-coherence and information-architecture gaps called out in RC2: silent demo tickers (AAPL/ACM), fragmented research journey links (`/reports`, `/health`), marketing portfolio labels (Health / Compounders / Confidence), AUX palette leakage, and empty executive dashboard widgets.

Primary shell journey is now **Dashboard → Company Analysis → Research Workspace → Portfolio**, with **Research Reports** and **Research Panels (IRD)** as Research children. Company Analysis, Institutional Reports, and IRD require an explicit ticker — no silent analyse defaults.

---

## 2. Implementation Scope

| In scope | Out of scope (other RC items) |
|---|---|
| Kill demo company defaults on research surfaces | BQ ontology aliasing (Finding 1) |
| Portfolio coverage terminology | Auth/commerce theatre (Findings 3, 9, 12) |
| Research journey link alignment | Trust ladder on every analytical page (Finding 2) |
| Shell nav + palette RBAC/AUX hide | Visual QA matrix (Finding 7) |
| Dashboard default-hidden widgets + tests | DS migration / fake lazy (Finding 28) |
| Typed portfolio/IRD error copy | Backend/API/engine changes |

---

## 3. Navigation Changes

- `SHELL_NAV` primary order: Dashboard → Company Analysis → Research Workspace → Portfolio.
- Research children: **Research Reports** (`/research/institutional`), **Research Panels** (IRD supporting).
- AUX routes (Advisor, Launch, Screening, Copilot, `/reports`, `/health`, …) marked `searchable: false`.
- `searchableRoutes()` RBAC-filters like the sidebar; `ShellCommandPalette` uses the same allow-list.
- Quick Actions widget reinforces the research journey and respects nav RBAC.

---

## 4. Research Journey

- AttentionBrief / Tasks / Recent Reports widgets no longer deep-link into legacy `/reports` or `/health` as primary CTA destinations.
- Journey destinations: Company Analysis, Research Reports, Portfolio, Dashboard.
- Report id rows with a known symbol open `/research/institutional?symbol=…`.
- Empty-state UX on CA / Reports / IRD when no ticker: require explicit selection; no “Analyze ” / invent ACM.

---

## 5. Dashboard Improvements

- `DEFAULT_HIDDEN_WIDGETS` hides empty/placeholder executive cards by default.
- Prefs store initializes from those defaults.
- Dashboard tests align with production hidden defaults.
- Quick Actions titled as Research journey.

---

## 6. Portfolio Improvements

- Renamed marketing labels to factual coverage language:
  - Portfolio Health → Research coverage status
  - Research Confidence → Research coverage / Intelligence API status
  - Quality Compounders → Research-available holdings
  - Confidence contributors/changes → Coverage contributors/changes
- Removed “Example: add AAPL to watchlist”.
- Typed error mapping for portfolio intelligence: 401, 403, 404, timeout, network, 5xx.

---

## 7. Validation Results

| Suite | Result |
|---|---|
| `shell.test.tsx` | PASS (14) |
| `dashboard.test.tsx` | PASS (6) |
| `portfolio-intelligence.test.tsx` | PASS (8) |
| `company-analysis.test.tsx` | PASS (7) |
| `institutional-reports.test.tsx` | PASS (7) |
| `institutional-dashboard.test.tsx` | PASS (3) |
| **Total** | **45 / 45 PASS** |

Searches:

- No remaining `|| "ACM"` / `|| "AAPL"` / `useState("AAPL")` / ACM sample links in `apps/web/src/components`.
- No remaining `href="/reports"` or `href="/health"` in journey widgets under `components/`.
- Portfolio flagship no longer contains Health / Compounders / Research Confidence marketing labels.

Typecheck (`tsc --noEmit`): pre-existing errors remain in portfolio fake-`lazy` casts and an unrelated e2e login import — not introduced by RC3-003.

---

## 8. Remaining Future Enhancements

1. Collapse classic `/research/[ticker]` and IRD further into one company research surface.
2. Replace portfolio cosmetic `lazy()` with real code-splitting (RC2 Finding 28).
3. Universal trust ladder chrome (RC2 Finding 2) — separate epic.
4. Remove orphan `AnalysisClient` / legacy analysis tree when AUX retirement completes.
5. `SAMPLE_ANALYSE_REQUEST.ticker = "ACM"` remains a request **template** for tests/fixtures — not a UI default.
6. Catalogue / seed fixtures may still contain AAPL as real company data (not silent defaults).

---

## 9. Release Recommendation

**Ship RC3-003 with the commercial-readiness branch.** It removes launch-blocking coherence defects (silent coverage implication, palette dual-product, portfolio overclaim labels).

Do **not** treat overall RC2 as PASS — CRITICAL items 1–5, 7, 9, 12 remain outside this epic.

---

## 10. TRACEABILITY (RC2 → implementation)

| RC2 Finding | Severity | Files | Reason | How satisfied |
|---|---|---|---|---|
| 6 | C | `navigationRegistry.ts`, workspaces, IRD | Multiple research products / contradictory honesty | Unified journey labels; IRD demoted to “Research Panels”; empty ticker honesty aligned |
| 8 | C | `ShellCommandPalette.tsx`, `navigationRegistry.ts`, `shell.test.tsx` | Palette without RBAC | `searchableRoutes(permissions, roles)` + AUX `searchable: false` |
| 10 | C | `FlagshipSections.tsx` | Quality Compounders = researchAvailable | Renamed to “Research-available holdings” with session-flag copy |
| 11 | C | `FlagshipSections.tsx`, `PortfolioIntelligenceWorkspace.tsx`, `PortfolioHealth.tsx` | Health / Confidence overclaim | Coverage / API status terminology |
| 20 | H | `CompanyAnalysisWorkspace.tsx`, `InstitutionalReportsWorkspace.tsx`, `prefsStore.ts`, `AnalysisClient.tsx`, `AnalysisWorkspace.tsx`, `buildAnalyseRequest.ts` | Silent AAPL default | Empty default; auto-analyse gated on non-empty symbol; no ACM invent |
| 21 | H | `navigationRegistry.ts` AUX | AUX in palette | Advisor/Launch/Screening/Copilot/… `searchable: false` |
| 26 | H | `PortfolioIntelligenceWorkspace.tsx`, `InstitutionalDashboardClient.tsx` | Untyped portfolio errors | 401/403/404/timeout/network/5xx copy |
| 27 | H | `widgetRegistry.ts`, `dashboardPrefsStore.ts`, `dashboard.test.tsx` | Empty executive widgets | `DEFAULT_HIDDEN_WIDGETS` |
| 34 | H | `navigationRegistry.ts` | “Institutional” ambiguous | Labels: Research Reports / Research Panels |
| 40 | H | AUX + palette | Advisor/legacy searchable | AUX not searchable |
| 55 | M | `FlagshipSections.tsx` | Demo add AAPL | Button removed |
| 69 | M | AUX Copilot | Searchable but not primary nav | `searchable: false` |
| 70 | M | Dashboard/CA/Portfolio widgets | `/reports` vs institutional | Links → `/research/institutional` |
| 88 | L | AUX + AttentionBrief | Health in palette / journey | `/health` not searchable; AttentionBrief CTAs retargeted |

---

## Architecture Impact

- **None** to backend, API contracts, engines, scoring, or RBAC server rules.
- Thin client preserved: display + navigation + prefs only.

## Components / Pages Updated

See git commit file list. Key surfaces: shell nav/palette, dashboard widgets, Company Analysis, Institutional Reports, IRD, Portfolio Intelligence, ResearchHome, legacy AnalysisActions/Workspace.

## Feature Flags Used

None new.

## Accessibility / Performance / Responsive

- Empty states remain text-first honest empties (no fabricated metrics).
- No layout system redesign; existing three-pane workspaces unchanged.
- Keyboard shortcuts / Ctrl+K behaviour preserved with stricter route allow-list.

## Known Limitations

- Pre-existing `tsc` errors on portfolio lazy casts.
- Fixture/template ACM in `SAMPLE_ANALYSE_REQUEST` retained for API request shape tests.
- Full RC2 CRITICAL backlog not cleared by this epic.
