# Component Behaviour

**Epic:** PR1.2 · VLIS  
**Implements behaviours for PXB components** — no business logic here.

---

## 1. Metric Card

| Aspect | Behaviour |
|---|---|
| Structure | Title · Rating badge · Actual value · Meaning · Why · Takeaway |
| Default | All six fields visible on desktop; Meaning+ collapsed behind “Details” on narrow mobile optional |
| Hover | Border → accent soft (desktop) |
| Focus | Whole card not focusable; interactive children are |
| Learn more | Button/link opens terminology drawer or inline expand |
| Ask AI | Fires Copilot with metric `ai_prompts[0]` + context chip |
| Loading | Skeleton equal height |
| Empty | Empty State — never fabricate rating |
| Error | ErrorState inside card body |

---

## 2. Decision Card (score chip / score tile)

| Aspect | Behaviour |
|---|---|
| Shows | Label + score 0–100 + band |
| Click | Scrolls/expands to related Analysis section |
| Keyboard | Enter activates same as click |
| Tooltip | One-line definition from terminology |
| Missing | “—” + Unavailable badge |

---

## 3. Research Conclusion Card

| Aspect | Behaviour |
|---|---|
| Content | DSP View label (Attractive / Fairly Valued / Caution…) + short rationale |
| Badge | Semantic color by band — not Buy/Sell chrome |
| Actions | Open Challenge · Ask Copilot · Jump to Decision Dashboard |
| Disclaimer | Research Mode strip when flags research-only |
| Update | When API refreshes, announce via `aria-live="polite"` |

---

## 4. Section Header

| Aspect | Behaviour |
|---|---|
| Elements | `h2` title · one-line purpose · optional Copilot chip row · anchor id |
| Sticky (optional) | Desktop only under topbar when scrolling section |
| Collapse (mobile) | Header is accordion button; `aria-expanded` |
| In-page nav | TOC highlights on IntersectionObserver |

---

## 5. Knowledge Graph

| Aspect | Behaviour |
|---|---|
| Select node | Detail drawer; `aria` list alternative updated |
| Filter | Instant client filter of visible types; no layout jump of chrome |
| Density | Low/Med/High rebuilds layout with skeleton flash |
| Empty / error | EmptyState / ErrorState over canvas |
| Mobile | List-first; “Open graph” secondary full-screen |
| Reduced motion | Instant reposition; no animated force layout |

---

## 6. Charts

See [CHART_STANDARDS.md](CHART_STANDARDS.md).  
Behaviour summary: hover/focus crosshair · tooltip · keyboard focusable points where feasible · interpretation text always below.

---

## 7. Tables

| Aspect | Behaviour |
|---|---|
| Sort | Optional; announce sort state |
| Scroll | Horizontal on overflow; sticky header |
| Row click | Navigate or select per context |
| Virtualize | > 100 rows ([PERFORMANCE_UI_GUIDELINES.md](PERFORMANCE_UI_GUIDELINES.md)) |
| Empty | Empty State in body |

---

## 8. Tooltips

| Aspect | Behaviour |
|---|---|
| Desktop | Hover + focus-within show |
| Mobile | Tap toggle; tap outside closes |
| Delay | 300ms show / 100ms hide |
| Content | Definition ≤ 2 sentences; link Learn more |
| Never | Truncate critical ratings into tooltip-only |

---

## 9. AI Copilot Panel

| Aspect | Behaviour |
|---|---|
| Open | Rail (desktop) / sheet (mobile) |
| Context chip | Section + symbol; editable |
| Prompt chips | Insert into composer; editable before send |
| Streaming | Token append; citations appear when complete |
| Stop | Cancels in-flight request |
| Error | Inline ErrorState; preserve composer text |
| Esc | Closes panel; focus returns to opener |

---

## 10. Decision Dashboard

| Aspect | Behaviour |
|---|---|
| Load | Skeleton score row then content |
| Score click | Deep-link to section |
| CTAs | Challenge · Copilot · Evidence |
| Partial data | Show available fields; Unavailable for rest |
| Sticky summary (mobile) | Chip opens bottom sheet with full dashboard |

---

## 11. Consensus Cards

| Aspect | Behaviour |
|---|---|
| Provider missing | Dedicated empty copy (Street not connected) |
| Distribution | Chart + data table alternative |
| Timeline | Range control updates series |
| DSP vs Street | Side-by-side cards; gap badge |
| AI Summary | Expandable; Ask AI refine |

---

## 12. Challenge Cards

| Aspect | Behaviour |
|---|---|
| Structure | Supporting · Against · Risks · Assumptions · Unknowns |
| Mandatory UX | Visible path from Research Conclusion |
| Expand | Each list collapsible |
| Cite | Evidence chips navigate to Evidence section |
| Loading | Skeleton five blocks |
| Reduced motion | Instant expand |

---

## 13. Shared state matrix

| Component | Loading | Empty | Error | Success |
|---|---|---|---|---|
| Metric Card | Skeleton | EmptyState | ErrorState | Data |
| Tables | Skeleton rows | EmptyState | Alert | Rows |
| Copilot | Streaming / spinner | Prompt idle | ErrorState | Answer |
| Charts | Skeleton plot | EmptyState | ErrorState | Plot + interpretation |
| KG | Skeleton canvas | EmptyState | ErrorState | Graph |
