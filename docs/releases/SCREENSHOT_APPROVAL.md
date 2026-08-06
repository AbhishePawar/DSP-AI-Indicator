# SCREENSHOT APPROVAL — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Programme | EPIC-010 / GA-001 — Institutional Visual QA Certification |
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Branch | `cursor/p6-1-commercial-readiness` |
| Base tip | `97b81eb` (*docs(release): certify production version 1.0.0*) |
| Date | 2026-08-02 |
| Companion artefact | [`VISUAL_QA_MATRIX.md`](./VISUAL_QA_MATRIX.md) |
| RC3 alignment | [`RC3_FINAL_CERTIFICATION_REPORT.md`](./RC3_FINAL_CERTIFICATION_REPORT.md) — **PASS WITH CONDITIONS** |

---

## 1. Commercial readiness decision

### **PASS WITH CONDITIONS** — closed-beta / institutional pilot Visual QA

**Approved for:** Version 1.0.0 **closed-beta / institutional pilot UI freeze** Visual QA posture — Research Mode, admin-provisioned access, thin-client `/api/v1`, with known limitations documented.

**Not approved for:** Unrestricted **Commercial public GA** screenshot certification. Headed Desktop/Laptop/Tablet/Mobile × Light/Dark pixel proof was **not** captured in this environment (`cursor-ide-browser` could not open a tab). Claiming full Commercial GA Visual QA would be false.

This decision matches RC3 final certification: process residual #7 (Visual QA matrix / headed proof) remains a **condition before public GA claims**, even though the formal matrix document now exists and HIGH theme/touch defects found in code were remediated.

---

## 2. Approved screens (closed-beta Visual QA)

Approval below means: **no open CRITICAL visual defects** on the certified surface after this pass’s minimal fixes; residual items are MEDIUM/LOW/COSMETIC or known HIGH process residuals accepted for closed-beta.

| Screen | Route | Closed-beta approval | Headed screenshots | Notes |
|---|---|---|---|---|
| Marketing | `/` | **Approved with conditions** | Unavailable (HTTP 200 smoke) | Gradient hero cosmetic accepted |
| Login | `/login` | **Approved** | Unavailable (HTTP 200 smoke) | Warning theme fixed |
| Request Access | `/signup` | **Approved** | Unavailable (HTTP 200 smoke) | Honest access messaging |
| Dashboard | `/dashboard` | **Approved with conditions** | Unavailable (HTTP 200; auth UI not headed) | Trust ladder residual |
| Company Analysis | `/analysis` | **Approved with conditions** | Unavailable | Primary CTA ≥44px fixed; summary Trust Ladder present |
| Portfolio Intelligence | `/portfolio` | **Approved with conditions** | Unavailable | Primary CTAs fixed; ladder residual |
| Research Reports | `/research/institutional` | **Approved with conditions** | Unavailable | Strongest trust/print surface; Load report fixed |
| Research Workspace | `/research` | **Approved with conditions** | Unavailable | Load research fixed; ladder residual |
| Research Panels (IRD) | `/research/institutional/dashboard` | **Approved with conditions** | Unavailable | SourceBadge warning theme fixed; DS migration retained |
| Settings | `/settings` | **Approved with conditions** | Unavailable | Dense nav accepted |
| Forbidden | `/forbidden` | **Approved** | Unavailable (HTTP 200) | AuthShell pattern |
| Unauthorized | `/unauthorized` | **Approved** | Unavailable | AuthShell pattern |
| Session expired | `/session-expired` | **Approved** | Unavailable (HTTP 200) | Warning theme fixed |
| Not found | `not-found` | **Conditional** | Unavailable | Legacy ui Card/Button drift (MEDIUM) — not CRITICAL |
| Privacy | `/docs/privacy` | **Approved with conditions** | Unavailable (HTTP 200) | Dual h1 MEDIUM |
| Terms | `/docs/terms` | **Approved with conditions** | Unavailable (HTTP 200) | Dual h1 MEDIUM |
| Disclaimer | `/docs/disclaimer` | **Approved with conditions** | Unavailable (HTTP 200) | Dual h1 MEDIUM |
| Risk disclosure | `/docs/risk-disclosure` | **Approved with conditions** | Unavailable | Dual h1 MEDIUM |

**Print (Institutional Reports):** Code-approved (`globals.css` + component `print:` utilities). Printer-preview / PDF raster **not** attached — condition for Commercial GA packaging.

---

## 3. Outstanding cosmetic / non-blocking items

Track before unrestricted Commercial GA; **do not** block closed-beta freeze:

1. Marketing gradient-led hero (RC2 cosmetic) — redesign out of scope.  
2. Marketing footer link density (&lt;44px) — secondary chrome.  
3. Secondary toolbar `sm` controls (Hide nav / Pin / Favourite / Export) — intentional density.  
4. ThemeSwitcher / AuthShell theme chip segment height (~36px).  
5. Settings left-nav row density.  
6. Legal DocArticle dual `h1` with PageHeader.  
7. `not-found` legacy `ui` Card/Button vs Auth/DS EmptyState.  
8. Reports recommendation truncate without native `title` tooltip.  
9. Reports mode `<select>` density.  
10. Analysis recent-company row truncate / hit area.  
11. Three-pane workspaces inside `ContentArea` `max-w-6xl` density at laptop widths.  
12. Card padding / table density variance across workspaces.  
13. `global-error` hardcoded blue CTA (fatal shell without CSS vars).  
14. **Trust Ladder / SourceBadge universality** on Dashboard, Portfolio, Research Workspace (HIGH process residual — product chrome, not a pixel clip).  
15. **Headed screenshot archive** (Desktop ≥1440, Laptop 1280, Tablet 768, Mobile 390 × Light/Dark) via Playwright/Percy or manual desk capture.  
16. Firefox + Safari formal visual smoke.

---

## 4. Defects fixed during this certification (visual only)

| ID | Fix |
|---|---|
| VQA-01 / VQA-04 | Warning Alert/Toast/Badge use `var(--warning-bg|fg|border)` so `data-theme` dark works without broken Tailwind `dark:` |
| VQA-02 | Primary Run analysis / Analyze / Refresh intelligence / Analyze company / Load research / Load report → ≥44px |
| VQA-03 | Topbar Menu / Collapse → `min-h-11` |

No redesign. No backend. No new features.

---

## 5. Evidence limitations (explicit)

| Item | Fact |
|---|---|
| Headed MCP screenshots | **Not captured** — browser tool could not create a tab |
| Live server | `next dev` on `http://localhost:3001` (port 3000 previously occupied by unhealthy process) |
| HTTP smoke | Public auth/marketing/legal + some app routes returned 200 |
| Authenticated loaded states | Code-review based; not headed-approved with real holdings/report modules |
| Fabricated screenshots | **None** |

---

## 6. Sign-off

| Role | Decision |
|---|---|
| Visual QA (this pass) | **PASS WITH CONDITIONS** for closed-beta / institutional pilot |
| Commercial public GA Visual QA | **Not certified** until headed matrix + outstanding HIGH process residuals close |
| RC3 production cert posture | Unchanged in spirit — Visual QA matrix artefact now present; headed proof still a GA condition |

**Integrity:** Prefer conditional approval over false full GA PASS. Aligns with RC3 “PASS WITH CONDITIONS” and User Trust Standard honesty.
