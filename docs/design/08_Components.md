# 08 — Components

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Note:** Specification only — does not modify production components in this epic.

---

## 1. Purpose

Define component inventory, variants, and layout patterns for institutional surfaces.

---

## 2. Global rules

- Flat + border default; soft shadow only for modal/dropdown.
- One primary CTA per view region.
- Every data component supports empty / loading / error / unavailable.
- Trust: source chip + epistemic category where insights appear.
- Thin client: no valuation/recommendation reasoning invented in the browser.

---

## 3. Navigation

### 3.1 Topbar

| Element | Behaviour |
|---|---|
| Wordmark | Links home / dashboard per IA |
| Primary nav | Text links; accent underline/soft for active |
| Utilities | Search, theme, profile, AI entry |
| Mobile | Collapse to menu button |

### 3.2 Sidebar

| Variant | Use |
|---|---|
| App sidebar | Persistent IA on desktop |
| Contextual TOC | Analysis sections |
| Collapsed icon rail | Optional dense mode |

Active item: `--accent-soft` fill + accent text; not neon pill clusters.

### 3.3 Breadcrumbs

Sora meta; current page non-link; landmarks announced to AT.

---

## 4. Buttons

| Variant | Use |
|---|---|
| Primary | Single primary action |
| Secondary | Alternate |
| Ghost | Toolbar / chrome |
| Danger | Destructive confirm |

Sizes: `sm` · `md` · `lg`. Focus: 2px accent ring + offset bg.

---

## 5. Forms

- Label above control  
- Helper muted  
- Error: danger alert + `aria-invalid`  
- Prefer native semantics before custom widgets  

---

## 6. Cards

| Variant | Use |
|---|---|
| Surface card | Default bordered panel |
| Metric card | Title · Rating · Value · What · Why · Takeaway · Learn More · Ask AI |
| Insight card | Conclusion with source + confidence |
| Interactive card | Only when the container itself is the interaction |

**Default:** no decorative cards in marketing heroes. In workspaces, prefer fewer deeper cards over card-in-card nesting.

---

## 7. Tables

| Rule | Spec |
|---|---|
| Header | Sticky on long lists |
| Density | Default / compact |
| Mobile | Horizontal scroll or stacked definition list |
| Empty | Empty state component |
| Sorting | Visible affordance + `aria-sort` |

---

## 8. Badges & chips

| Family | Use |
|---|---|
| Status | success · warning · danger · info · neutral |
| Source | Verified · Calculated · Estimated · AI · Consensus · User · Unknown · Unavailable |
| Rating | Text categorical rating always present |

---

## 9. Alerts & banners

| Tone | Use |
|---|---|
| Info | Research Mode / guidance |
| Success | Completed system action |
| Warning | Caution requiring review |
| Danger | System failure / destructive |

---

## 10. Dashboard layout components

| Component | Role |
|---|---|
| Widget shell | Title, optional action, body, footer meta |
| KPI strip | Sparse; labels required |
| Quick actions | Ghost/secondary buttons |

Avoid stat-strip overload in first viewport of non-dashboard marketing pages.

---

## 11. AI panel layout

| Region | Content |
|---|---|
| Header | “AI” + scope (company/portfolio) + confidence/disclosure |
| Stream | User/AI messages; citations; source chips |
| Composer | Input + send; disabled when policy blocks |
| Footer | Research Mode / oversight reminder |

States: idle · streaming · awaiting oversight · error · unavailable.  
Motion: streaming cursor/opacity only; honor reduced-motion.

---

## 12. Report layout components

| Block | Spec |
|---|---|
| Cover / title | Fraunces title + meta |
| Section | h2 + prose ≤72ch |
| Figure | Chart/table + caption + interpretation |
| Disclaimer | Persistent Research Mode / legal footer |

---

## 13. Overlays

Modal · sheet · dropdown · command palette — elevation level 1 shadow only; focus trap; Esc closes.

---

## 14. Feedback states

| State | Pattern |
|---|---|
| Loading | Labeled spinner or layout-matched skeleton |
| Empty | Title + description + optional CTA |
| Partial | Show ready modules; skeleton remainder |
| Error | Danger alert + retry |

---

## 15. Variant matrix (summary)

| Component | Light | Dark | Compact | Mobile |
|---|---|---|---|---|
| All core | Token swap | Token swap | Spacing denser | Stack / sheet |
| Tables | — | — | Cell padding ↓ | Scroll/stack |
| AI panel | Dock | Dock | — | Full sheet |
