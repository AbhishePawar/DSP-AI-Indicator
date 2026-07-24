# Mobile UX

**Epic:** PR1.1 · PXB  
**Principle:** Mobile-first adaptations — **not** scaled-down desktop.

---

## 1. Breakpoints

| Name | Width | Shell |
|---|---|---|
| Mobile | < 768px | Drawer nav · single column |
| Tablet | 768–1023px | Collapsible sidebar · 1–2 col |
| Desktop | ≥ 1024px | Persistent sidebar · TOC + main |

---

## 2. Navigation

```text
┌ Menu │ Title           │ Account ┐
│ [drawer]                         │
│  Dashboard                       │
│  Analysis …                      │
└──────────────────────────────────┘
```

- One primary CTA in view at a time.  
- Breadcrumbs compress to Back + current.  
- Logout inside Account sheet.

---

## 3. Analysis mobile pattern

**Accordion sections** in PXB order; progress indicator `3 / 19`.

| Pattern | Detail |
|---|---|
| Snapshot | Always expanded first visit |
| Metric cards | Full width stack; rating badge top-right |
| Charts | Full bleed; interpretation below; swipe for series |
| Decision Dashboard | Sticky “Summary” chip → expands sheet |
| Copilot | Bottom bar “Ask AI” → sheet |
| Challenge | Full-screen step before Export on first visit (optional nudge) |
| Export | Share sheet / download action |

Avoid: multi-column score grids; tiny TOC; hover-only tooltips (use tap).

---

## 4. Dashboard mobile

- Vertical widget stack  
- Quick Actions as 2×2 button grid  
- Recent Reports as list rows  

---

## 5. Forms

- Large tap targets ≥ 44px  
- Date inputs native  
- Symbol search with clear affordance  

---

## 6. Performance UX

- Skeleton per section, not whole-page blank  
- Defer KG canvas until section opened  
- Prefetch next accordion on expand  

---

## 7. Accessibility (mobile)

- VoiceOver/TalkBack labels on icon actions  
- Focus order follows accordion  
- Reduced motion: instant expand  

---

## 8. Wireframes

### WF-M01 Drawer

```text
▓▓ overlay
┌────────────┐
│ DSP        │
│ Dashboard  │
│ Analysis   │
│ …          │
│ Settings   │
└────────────┘
```

### WF-M03 Copilot sheet

```text
======= handle =======
Context: AAPL · Risk
[prompts…]
conversation…
[ input ][ send ]
```

---

## 9. Offline / error

- Clear Error State if API unreachable  
- Do not cache invented research conclusions  
