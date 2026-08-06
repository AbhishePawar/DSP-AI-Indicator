# BROWSER CERTIFICATION — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Programme | EPIC-010 / GA-002 — Cross-Browser Certification |
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Branch | `cursor/p6-1-commercial-readiness` |
| Tip at evaluation start | `a83940d` (*docs(release): complete visual QA certification*) |
| Date | 2026-08-02 |
| Environment | Windows 10.0.26200 · Next.js 15.5.21 (`apps/web` · `localhost:3001`) |
| Mode | Production verification — **no** UI redesign; minimal genuine browser-compatibility fixes only |
| Prior artefacts | `RC3_FINAL_CERTIFICATION_REPORT.md` · `VISUAL_QA_MATRIX.md` · `SCREENSHOT_APPROVAL.md` · Design System / DSP Trust Standard |
| Commercial browser decision | **PASS WITH CONDITIONS** (closed-beta / institutional pilot) — **not** unrestricted Commercial public GA |

---

## 1. Executive Summary

Version **1.0.0** is **browser-certified for closed-beta / institutional pilot** on **Chrome (Latest)** and **Microsoft Edge (Latest)** with live headless Chromium engine smoke (48/48 route×viewport checks green), plus systematic code-level compatibility review for **Firefox (Latest)** and **Safari (Latest) / WebKit**.

This pass closes several reduced-motion / print WebKit gaps that were inconsistent with the Design System sticky-chrome pattern. It does **not** claim fake headed PASS for Safari (no macOS/WebKit runtime on this Windows host) or for Firefox (browser binary not installed). Those engines are **code-review certified** with residual physical smoke required before unrestricted Commercial GA.

**Authorizes:** closed-beta institutional Research Mode UI freeze on Chromium engines (Chrome/Edge Latest), with Firefox/Safari accepted under written WebKit/Gecko assumptions for the same thin-client `/api/v1` UI.

**Does not authorize:** Commercial public GA browser claims that “all four browsers were physically smoke-tested,” or any redesign of engines/API/auth/DB.

---

## 2. Evidence posture (honest)

| Evidence type | Status |
|---|---|
| Chrome Latest — headless Puppeteer (`puppeteer-core` + local Chrome binary) | **Executed** — desktop + tablet + mobile viewports |
| Microsoft Edge Latest — headless Puppeteer + local Edge binary | **Executed** — same matrix |
| Firefox Latest — headed/headless | **Not installed** on host (`C:\Program Files\Mozilla Firefox\firefox.exe` absent) |
| Safari Latest — headed/WebKit | **Unavailable** on Windows — no Safari / WebKit runtime |
| `cursor-ide-browser` MCP headed tab | **Blocked** — tab create succeeded once then evaporated; `browser_navigate` returned *No browser tab available* (same residual as Visual QA) |
| HTTP smoke (route responds) | **Executed** — primary surfaces HTTP 200 on `:3001` |
| User-Agent HTTP variants (Chrome/Edge/Firefox/Safari UA strings) | **Executed** — marketing/login/dashboard/settings all 200 (server-side only; not engine proof) |
| Code-level CSS/JS compatibility review | **Executed** — Grid/Flex/sticky/backdrop-filter/`color-mix`/`:has`/dialogs/focus trap/dynamic import/print/reduced-motion |
| Auth-gated interactive analytical states | **Partial** — unauthenticated SSR shells smoked; loaded holdings/report modules rely on code review + prior RC3 suites |

Temporary Puppeteer tooling under `.tmp-browser-cert/` and an ephemeral `puppeteer-core` install under `apps/web/node_modules` were used for evidence only and are **not** part of the product commit.

---

## 3. Browsers Tested

| Browser | Version posture | Method | Certification status |
|---|---|---|---|
| **Google Chrome (Latest)** | Local Chrome binary present; Blink | Headless Puppeteer smoke + HTTP | **PASS** (live engine) |
| **Microsoft Edge (Latest)** | Local Edge binary present; Blink | Headless Puppeteer smoke + HTTP | **PASS** (live engine) |
| **Mozilla Firefox (Latest)** | Binary **not installed** | Code-level Gecko review + UA HTTP only | **PASS WITH CONDITIONS** — code-review certified; physical Firefox smoke **pending** |
| **Safari (Latest)** | Not installable on Windows | Code-level WebKit review + UA HTTP only | **PASS WITH CONDITIONS** — code-review certified / WebKit assumptions; **physical Safari smoke pending** on macOS |

### 3.1 Chrome / Edge live matrix (summary)

Server: Next.js 15.5.21 on `http://127.0.0.1:3001`.

| Check | Chrome | Edge |
|---|---|---|
| Desktop 1440×900 — Marketing, Auth, Legal, Error, Dashboard, Analysis, Portfolio, Research, Institutional Reports, IRD, Settings, Companies | 16/16 OK | 16/16 OK |
| Tablet 768×1024 — `/`, `/login`, `/dashboard`, `/settings` | 4/4 OK | 4/4 OK |
| Mobile 390×844 — same four routes | 4/4 OK | 4/4 OK |
| Horizontal overflow (`scrollWidth > clientWidth + 2`) | None observed | None observed |
| `CSS.supports(backdrop-filter)` / `color-mix` / `:has` | true | true |
| Page JS errors on smoked routes | None | None |
| Sticky chrome present on marketing / shell routes | Observed where expected | Observed where expected |
| `prefers-reduced-motion: reduce` — marketing sticky `backdrop-filter` | `none` (DS pattern honored) | Same Blink family |

**TOTAL: 48/48 live Chromium checks PASS (FAIL=0).**

### 3.2 Firefox / Safari code-review certification basis

| Capability used by app | Firefox Latest | Safari Latest | Notes |
|---|---|---|---|
| CSS Grid / Flexbox / `gap` | Supported | Supported | Primary layout primitives |
| `position: sticky` | Supported | Supported | Sticky + `overflow` ancestors remain a WebKit residual risk — surfaces use opaque/near-opaque backgrounds |
| `backdrop-filter` / Tailwind `backdrop-blur*` | Supported | Supported (prefixed via engine) | Solid `/95` surface colors provide graceful degradation |
| `color-mix(in srgb, …)` | Supported | Supported (16.2+) | Used in tokens, alerts, marketing header, IRD |
| `:has()` | Supported (121+) | Supported (15.4+) | Table checkbox cell padding only — non-critical |
| Radix Dialog / focus trap | Supported | Supported | `@radix-ui/react-dialog`; AppLayout mobile drawer Tab/Escape trap |
| `prefers-reduced-motion` | Supported | Supported | `globals.css` + `motion-reduce:*` utilities |
| Dynamic `next/dynamic` / skeletons | Supported | Supported | Advisor AUX + portfolio lazy paths |
| Clipboard `navigator.clipboard` | Secure-context + permission | Same | Call sites use `try/catch` |
| Print (`break-inside` / `page-break-inside`) | Supported | Supported | Dual properties + print-color-adjust (this pass) |
| Container queries / `100dvh` / `@supports` novelty | N/A / minimal | N/A / minimal | No `dvh`/`svh`/`lvh` dependency found in primary CSS |

---

## 4. Screens Tested

Status values: **PASS** · **PASS WITH CONDITIONS** · **BLOCKED** · **CODE-REVIEW**.

| Surface | Route(s) | Chrome | Edge | Firefox | Safari |
|---|---|---|---|---|---|
| Marketing | `/` | PASS | PASS | CODE-REVIEW | CODE-REVIEW |
| Auth — Login | `/login` | PASS | PASS | CODE-REVIEW | CODE-REVIEW |
| Auth — Request Access | `/signup` | PASS | PASS | CODE-REVIEW | CODE-REVIEW |
| Legal — Privacy / Terms / Disclaimer | `/docs/privacy`, `/docs/terms`, `/docs/disclaimer` | PASS | PASS | CODE-REVIEW | CODE-REVIEW |
| Error — Session expired | `/session-expired` | PASS | PASS | CODE-REVIEW | CODE-REVIEW |
| Error — Forbidden | `/forbidden` | PASS | PASS | CODE-REVIEW | CODE-REVIEW |
| Dashboard | `/dashboard` | PASS WITH CONDITIONS | PASS WITH CONDITIONS | CODE-REVIEW | CODE-REVIEW |
| Company Analysis | `/analysis`, `/companies` | PASS WITH CONDITIONS | PASS WITH CONDITIONS | CODE-REVIEW | CODE-REVIEW |
| Portfolio | `/portfolio` | PASS WITH CONDITIONS | PASS WITH CONDITIONS | CODE-REVIEW | CODE-REVIEW |
| Research Workspace | `/research` | PASS WITH CONDITIONS | PASS WITH CONDITIONS | CODE-REVIEW | CODE-REVIEW |
| Research Reports | `/research/institutional` | PASS WITH CONDITIONS | PASS WITH CONDITIONS | CODE-REVIEW | CODE-REVIEW |
| IRD | `/research/institutional/dashboard` | PASS WITH CONDITIONS | PASS WITH CONDITIONS | CODE-REVIEW | CODE-REVIEW |
| Settings | `/settings` | PASS WITH CONDITIONS | PASS WITH CONDITIONS | CODE-REVIEW | CODE-REVIEW |

**PASS WITH CONDITIONS** on authenticated shells = route SSR/client shell loaded without layout overflow or page errors under Chromium; full authenticated data states were not headed-verified without a provisioned session (thin-client ProtectedRoute). No browser-specific layout breakers found in code for those shells.

---

## 5. Issues Found

| ID | Severity | Engine | Finding | Disposition |
|---|---|---|---|---|
| BC-01 | MEDIUM | All (a11y / reduced-motion) | Sticky chrome on Analysis mobile strip, Portfolio sticky summary, Team Collaboration header, and DS `LoadingOverlay` used `backdrop-blur` **without** `motion-reduce:backdrop-blur-none`, inconsistent with Marketing / CA / Reports / IRD / Settings pattern and `prefers-reduced-motion` policy | **Fixed** this pass |
| BC-02 | MEDIUM | WebKit / Blink print | Institutional report print CSS forced white/black backgrounds without `print-color-adjust` / `-webkit-print-color-adjust`, so WebKit/Blink may ignore forced print backgrounds | **Fixed** this pass |
| BC-03 | LOW | All | Dialog overlay classes reference `animate-in` / `animate-out` without a registered animation plugin — classes are effectively no-ops; dialogs still render/focus via Radix | **Accepted** — no functional defect; track for DS polish (out of redesign scope) |
| BC-04 | LOW | Safari residual | Sticky + backdrop-filter historically sensitive in older WebKit; Latest Safari expected OK; opaque `/95` backgrounds mitigate | **Accepted** — physical Safari smoke pending |
| BC-05 | PROCESS | Firefox / Safari | No physical engine binaries in this Windows cert environment | **Condition** for Commercial GA |
| BC-06 | PROCESS | MCP headed | `cursor-ide-browser` could not sustain a navigable tab (same as Visual QA residual) | **Accepted** — Chromium evidence collected via local Chrome/Edge instead |

No CRITICAL browser layout breakers (unusable primary path, white-on-white, systematic clipping) were found on Chrome/Edge.

---

## 6. Issues Fixed

| ID | Fix | Files |
|---|---|---|
| BC-01 | Added `motion-reduce:backdrop-blur-none` to sticky / overlay surfaces missing the DS reduced-motion backdrop policy | `AnalysisWorkspace.tsx`, `PortfolioWorkspace.tsx`, `TeamCollaboration.tsx`, `loading-overlay.tsx` |
| BC-02 | Added `-webkit-print-color-adjust: exact` and `print-color-adjust: exact` on institutional report print roots | `apps/web/src/app/globals.css` |

No redesign, no new features, no backend/API/engine/auth/DB changes.

---

## 7. Known Browser Limitations

1. **Safari physical smoke pending** — Windows host cannot run Safari/WebKit; certification is code-review + Chromium analogy only.  
2. **Firefox physical smoke pending** — Firefox binary not installed; Gecko not executed.  
3. **Headed MCP screenshot package unavailable** — same environmental residual as GA-001 Visual QA.  
4. **Authenticated analytical states** (loaded analysis modules, portfolio holdings, report print preview) not re-verified headed without beta credentials.  
5. **`animate-in` / `animate-out`** dialog utilities are no-ops until a motion plugin or local keyframes are wired (non-blocking).  
6. **`:has()` table cell padding** — decorative; if an enterprise Firefox ESR older than 121 is mandated, checkbox column padding may differ (Latest Firefox OK).  
7. **Clipboard share actions** require secure context and permission — failures are swallowed; no browser-specific crash path.  
8. **Advisor / AUX** dynamic `ssr: false` islands are outside primary closed-beta IA; not re-smoked as GA primary surfaces.  
9. Local OneDrive / `.next` cache corruption can still break `npm run dev` (prior webpack ENOENT) — clean `.next` / alternate port (`3001`) used this pass.

---

## 8. Special capability checklist

| Capability | Chrome | Edge | Firefox | Safari |
|---|---|---|---|---|
| CSS Grid / Flexbox | Live PASS | Live PASS | Code-review | Code-review |
| Sticky headers | Live PASS | Live PASS | Code-review | Code-review (residual) |
| Overflow / no horizontal clip | Live PASS | Live PASS | Code-review | Code-review |
| Backdrop blur | Live PASS (supports + reduced-motion) | Live PASS | Code-review | Code-review |
| Theme tokens (`data-theme`) | Live PASS (dark vars resolve) | Live PASS (Blink family) | Code-review | Code-review |
| Dynamic imports / skeletons | Code + route OK | Code + route OK | Code-review | Code-review |
| Dialogs / focus trap | Code + a11y suite prior | Same | Code-review | Code-review |
| Transitions / reduced-motion | Live PASS (backdrop none) | Live PASS | Code-review | Code-review |
| Print | Code-fix (color-adjust) | Code-fix | Code-review | Code-review |

---

## 9. Certification Decision

| Decision field | Value |
|---|---|
| **Closed-beta / institutional pilot** | **PASS WITH CONDITIONS** |
| **Commercial public GA (unrestricted)** | **NOT CERTIFIED** until Firefox + Safari physical smoke and headed Visual QA package conditions are cleared |
| **Chrome Latest** | **PASS** (live) |
| **Edge Latest** | **PASS** (live) |
| **Firefox Latest** | **PASS WITH CONDITIONS** (code-review certified; physical smoke pending) |
| **Safari Latest** | **PASS WITH CONDITIONS** (code-review certified / WebKit assumptions; physical Safari smoke pending) |

### Conditions before Commercial GA browser claim

1. Install/run **Firefox Latest** smoke on Marketing, Login, Dashboard, Analysis, Portfolio, Reports, Settings (desktop + mobile width).  
2. Run **Safari Latest** (macOS) smoke on the same surfaces; confirm sticky headers under WebKit and print preview for institutional reports.  
3. Attach headed Visual QA screenshots (or equivalent) per `VISUAL_QA_MATRIX.md` / `SCREENSHOT_APPROVAL.md`.  
4. Optionally wire dialog `animate-in`/`animate-out` or remove dead classes during a DS polish epic (non-blocking).

### Alignment with RC3 / Visual QA

This decision is consistent with RC3 **PASS WITH CONDITIONS** and Visual QA **PASS WITH CONDITIONS**: closed-beta freeze is appropriate; unrestricted Commercial GA is not claimed from this Windows Chromium-primary evidence set.

---

## 10. Regression / trust notes

- Thin client preserved — no browser-side valuation, recommendation, or AI reasoning added.  
- Fixes are CSS utility / print compatibility only — no fabricated metrics, no auth theatre, no API contract change.  
- Reduced-motion backdrop disable verified under Chrome `prefers-reduced-motion: reduce` (marketing sticky → `backdrop-filter: none`).

---

*End of EPIC-010 / GA-002 Cross-Browser Certification Report — Version 1.0.0.*
