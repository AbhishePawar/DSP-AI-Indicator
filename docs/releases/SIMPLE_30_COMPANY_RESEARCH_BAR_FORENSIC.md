# SIMPLE-30 — COMPANY RESEARCH BAR MISSING — FRONTEND FORENSIC

## 1. Verdict

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-29 remains **PASS WITH LIMITATIONS**. It was not reopened. No DSP / DCF / EvidenceJudge / WACC / RBI / beta / ERP / provider changes were made.

The missing Company Research bar is a **frontend placement defect**, not a missing resolver. The Security Master search (`GET /api/v1/securities/search`) and analysis identity path already existed. They were not mounted in the primary main-content pane.

This forensic restores **one** canonical Company Research bar in main content, removes the header lookalike search, and keeps dashboard clutter from becoming a second company search.

Live browser and local Vitest could not be completed in this environment (Next.js did not stay listening; Vitest `@vitest/runner/utils` failed under Node 24). Until that verification runs, the stage cannot be CLOSED.

**NO PRODUCTION DEPLOYMENT.**

---

## 2. User-Reported Defect

The primary client entry point — the **Company Research / Company Search bar** — is missing from the frontend. The user cannot search a company/ticker, select a listing, and enter analysis from a prominent main-content control.

---

## 3. Expected Behavior

```text
USER
  ↓
COMPANY RESEARCH (one bar, main content)
  ↓
IDENTIFY SECURITY (existing Security Master)
  ↓
ANALYSE COMPANY (existing /analysis pipeline)
  ↓
DSP RESULT
```

Header: **no** duplicate research search.

Main content: prominent Company Research bar, usable without scrolling through internal widgets.

Identity retained from the existing resolver contract: company, ticker, ISIN, exchange, MIC, security type.

---

## 4. Repository Forensic

| Role | Path | Classification |
|---|---|---|
| Canonical resolver API | `GET /api/v1/securities/search` + `resolve` (`packages/api_platform/.../securities.py`, `api.searchSecurities`) | **ACTIVE** / reused |
| Identity helpers | `apps/web/src/lib/securities/identity.ts` (`analysisPath`) | **ACTIVE** |
| New canonical UI | `apps/web/src/components/securities/CompanyResearchBar.tsx` | **ACTIVE / CLIENT-FACING** |
| Flagship page | `/analysis` → `CompanyAnalysisWorkspace` | **ACTIVE** (now hosts the bar in main pane) |
| Authenticated landing | `/dashboard` → `InstitutionalDashboard` | **ACTIVE** (hero bar above widgets) |
| Left-nav search | `WorkspaceLeftNav` | Was the only workspace search; **removed** to avoid duplicate |
| Dashboard widget | `dashboard/widgets/SearchWidgets.tsx` `CompanySearchWidget` | **DUPLICATE** — excluded from the widget grid |
| Header “Search pages…” | `Topbar.tsx` | **DUPLICATE / not company search** — removed |
| Command palette | `ShellCommandPalette.tsx` (Ctrl+K) | **INTERNAL-ONLY** page navigation; Commands button remains |
| `/search` | redirects to `/analysis` | **ACTIVE** alias |
| `widgets/CompanySearchWidget.tsx` | ticker-only, no Security Master | **LEGACY / DEAD** |
| `/companies` `CompanySearch` | static catalogue, not resolver | **LEGACY** |
| `ResearchHome` ticker form | navigates `/research/{ticker}` without ISIN+MIC | **LEGACY** |

No new backend endpoint. No parallel company resolver.

---

## 5. Git Forensic

| Item | Evidence |
|---|---|
| Last known good search wiring | `97d7a0f` — “Restore provider-neutral Security Master search so analysis receives exact ISIN and MIC identity.” Wired search into **left nav** and the **dashboard widget**, not the main analysis pane. |
| Collapse behavior | `29f8042` (workspace introduction) already called `useCollapsePanelsBelowLg`, which sets `leftOpen=false` below 1024px. |
| Empty main pane | Since workspace creation: “Select a ticker to begin…” **with no search input** in `Main analysis area`. |
| Header search | Always command-palette “Search pages…”, never Security Master. |
| Blind revert? | **No.** Reverting `97d7a0f` would destroy identity-safe search. The defect is placement, not that commit’s resolver work. |
| Intentional vs accidental | Accidental product outcome of putting the only company search in a **collapsible aside** plus a **buried widget**, then treating header Ctrl+K as “search.” Not a dedicated “delete the bar” commit. |

---

## 6. Root Cause Proof

Exact mechanism:

1. Canonical company search lived in `WorkspaceLeftNav` (`aside[aria-label=Company navigation]`).
2. That aside uses `className={leftOpen ? "block" : "hidden"}`.
3. `useCollapsePanelsBelowLg` **forces `leftOpen=false` on viewports ≤ 1023px**.
4. Persisted workspace prefs can also keep the left panel closed on desktop.
5. The **main analysis region** had no search control — only an empty state telling the user to “Select a ticker.”
6. Dashboard `company_search` existed but sat after Welcome / Attention / Quick Actions / Research Command Center / Market Overview, so it was not the primary action and required scrolling through internal widgets.
7. The header control labeled like a search bar opened the **page command palette**, not Security Master.

Therefore the bar “disappeared” whenever the left nav was closed — which is the default on tablet/mobile — and was never the prominent main-content entry the product requires.

CSS `display:none` on the aside (`hidden` when `!leftOpen`) is the visibility mechanism. Feature flags did not disable the component. The component was not deleted.

---

## 7. Fix

| File | Why |
|---|---|
| `apps/web/src/components/securities/CompanyResearchBar.tsx` | Canonical client-facing bar: debounce → `searchSecurities` → identity list → `analysisPath` / `onSelect`. |
| `apps/web/src/components/securities/CompanyResearchBar.test.tsx` | Rendering, empty input, suggestions, selection, unknown/unsupported/error, no hardcoded universe. |
| `CompanyAnalysisWorkspace.tsx` | Mount the bar at the **top of main content**. Hero when no ticker; compact after identity. |
| `WorkspaceLeftNav.tsx` | Remove company search so there is **one** primary search. Keep Analyze / sections / recents. |
| `InstitutionalDashboard.tsx` | Hero bar immediately under the page header. Never render `company_search` / `global_search` widgets. |
| `widgetRegistry.ts` | Hide those widgets by default. |
| `Topbar.tsx` | Remove the center “Search pages…” field and extra Search input. Keep a Commands button for Ctrl+K. |
| `app/analysis/page.tsx` | Title **Company Research**. |
| `a11y-responsive.test.tsx`, `company-analysis.test.tsx`, `dashboard.test.tsx` | Align assertions with one primary bar / no header search field. |

Not restored: Intelligence widgets, screening, portfolio, Copilot, Trust Ladder as a product surface, workflow, platform health, alerts. Dashboard widgets that already existed remain below the bar; they were not brought back from a parked state.

---

## 8. Search Data Flow

```text
input (Company search)
  → empty: no request
  → debounce 200ms
  → GET /api/v1/securities/search?q=…  (Bearer token required)
  → candidate list (ticker, company, exchange, ISIN, MIC, security type)
  → selection
  → analysisPath({ ticker, exchange, isin, mic })
  → /analysis?symbol=&exchange=&isin=&mic=
  → existing CompanyAnalysisWorkspace auto-run when identity is exact
```

AI does not write identity. The thin client does not invent a listing.

---

## 9. Universal Coverage

The bar contains **no** hardcoded tickers (`TCS`, `INFY`, `RELIANCE`, `WIPRO`, `20MICRONS`, `21STCENMGM` are test fixtures only).

Intended live checks (existing catalog, not a supported-universe hardcode):

| Security | Role |
|---|---|
| TCS | fixture |
| INFY | fixture |
| RELIANCE | fixture |
| WIPRO | fixture |
| 20MICRONS | fixture |
| 21STCENMGM | fixture |
| + dynamic NSE equities | same `searchSecurities` path |

Unit tests cover INFY selection identity URL, UNKNOWN, UNSUPPORTED, multi-candidate list, and source AST for no ticker constants.

Live catalog hits were **not** executed in this session (no listening Next/API).

---

## 10. Duplicate Search Check

| Surface | After fix |
|---|---|
| Header search field | **Removed** |
| Header Commands (palette) | Kept — not company research |
| Main `/analysis` bar | **Canonical** |
| Dashboard hero bar | **Same component** (one implementation) |
| Dashboard Quick Company Search widget | **Not rendered** |
| Dashboard Global Search widget | **Not rendered** |
| Left nav search | **Removed** |

Target: **ONE PRIMARY COMPANY SEARCH** (shared `CompanyResearchBar`).

---

## 11. Error-State Validation

| Case | Behavior (implemented) |
|---|---|
| Empty input | No request |
| Unknown | “No matching company. The platform does not invent a security.” |
| Multiple listings | Listbox with identity; user must choose; no silent pick |
| UNSUPPORTED | Explicit unsupported copy |
| API failure | Alert: “Search failed. Check the connection and retry.” |
| Slow request | “Searching…” |
| Unauthenticated | “Sign in required for Security Master search.” — auth not bypassed |

---

## 12. Browser Validation

**Not completed in this session.**

Attempts:

- Existing `next start :3000` from 2026-09-10 is **no longer listening**.
- `next dev :3001` exited without a Ready line; no TCP listener on 3000/3001/8000.
- Vitest CLI failed (`ERR_MODULE_NOT_FOUND` `@vitest/runner/utils` under Node 24.18) / hung on OneDrive `node_modules`.

Therefore: **no** live proof of type TCS → suggestions → select → analysis in a real browser this turn.

That is why the verdict is not CLOSED.

---

## 13. Responsive Validation

Designed (not live-measured):

- Bar is in **main content**, so `useCollapsePanelsBelowLg` can no longer hide it.
- Input `min-h-11` (≥44px).
- Hero `max-w-3xl` centered; compact full width of the main pane.
- Results list `z-20`, `max-h-72`, overflow-y auto — intended to avoid clipping behind widgets.
- Header no longer uses a dual search field that competed at small widths.

Live desktop / tablet / mobile screenshots: **not captured**.

---

## 14. Accessibility Validation

Implemented:

- Visible “Company Research” name (heading on hero; label on compact).
- `<label class="sr-only">` + `aria-label="Company search"` (matches P1-09 `/Company search/i`).
- `role="combobox"` + `aria-expanded` + `aria-controls` + `aria-activedescendant`.
- Listbox options with `aria-selected`.
- Keyboard: typing, ArrowUp/Down, Enter, Escape.
- `focus-visible` ring on input and options.
- Result names include ticker, company, exchange, ISIN, MIC.

Full-site a11y redesign: not done. Live screen-reader pass: not done.

Header a11y test updated from “Open search and command palette” → “Open command palette”.

---

## 15. Performance Validation

Implemented controls:

- 200ms debounce (same as prior left-nav search).
- Generation counter drops stale responses (no request-storm display).
- Empty query cancels in-flight generation and does not call the API.
- No polling loop.

Live timings `input → request → suggestions → navigation`: **not measured**.

---

## 16. Tests

Authored:

- `CompanyResearchBar.test.tsx` — render, empty, debounce/select, UNKNOWN, UNSUPPORTED, error, ambiguous, analysisPath, no hardcoded universe.
- Updates: company-analysis workspace, dashboard (bar present; Quick Company Search / Search pages widget absent), a11y Topbar.

**Runner result this session:** Vitest did not execute successfully (Node 24 + `@vitest/runner/utils` resolution). Counts:

| | Count |
|---|---|
| passed | **unknown (runner failed)** |
| failed | **unknown** |
| skipped | — |
| deselected | — |

Do not mask this as green.

Backend SIMPLE-14N-E…SIMPLE-29 suites were **not** re-run (out of scope; no backend edits).

---

## 17. Backend/DSP Impact

**Untouched.**

No edits to `compute_wacc`, `DcfMethod`, financial acquisition, share-count, EvidenceJudge, RBI, beta/ERP, provider hierarchy, NSE MCP, FMP, Kite, or BSE feeds.

SIMPLE-29 report remains **PASS WITH LIMITATIONS**.

Existing `/securities/search` and `/securities/resolve` reused. `require_auth` not weakened. Client still sends the session Bearer token.

---

## 18. Production State

**NO PRODUCTION DEPLOYMENT.**

Local source restored. A stale `next start` is not production. Do not claim production is fixed until a current build is served and browser-verified.

---

## 19. Known Limitations

1. Live browser journey (TCS / INFY / RELIANCE / WIPRO + dynamic names) **not proven** this session.
2. Vitest did not run in this Node/OneDrive environment.
3. `/companies` catalogue search and `ResearchHome` ticker-only form remain **legacy** (not the primary door; not deleted to avoid a redesign).
4. Dashboard widgets below the hero bar still exist; they were not used to “solve” search.
5. Command palette (Ctrl+K) still searches **pages**, not companies — by design after removing the fake header search.
6. Analysis still requires authentication; search does not bypass it.

---

## 20. Closure Decision

**Not CLOSED.**

Proven: root cause (main pane empty + left nav `hidden` + header not company search) and a smallest restoration of one canonical bar on the existing resolver.

Unproven: live browser, responsive screenshots, Vitest green, production rebuild.

---

## 21. Next Forensic

Candidate **SIMPLE-31** (frontend verification only):

1. Run `apps/web` from a current build (not a stale `next start`).
2. Authenticated browser: dashboard + `/analysis` → type TCS, INFY, RELIANCE, WIPRO, 20MICRONS, 21STCENMGM + two dynamic catalog names → select → identity URL → existing analyse.
3. Desktop / tablet / mobile; keyboard; no duplicate bar.
4. Run Vitest on a Node version that resolves `@vitest/runner/utils`.

Optional later (separate scope): retire `/companies` catalogue search and `ResearchHome` ticker-only navigation so they cannot be mistaken for the primary door.

Permanent rule:

> **Restore the front door. Do not restore the machinery.**
