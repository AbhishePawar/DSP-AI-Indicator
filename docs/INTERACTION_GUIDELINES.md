# Interaction Guidelines

**Epic:** PR1.2 · VLIS  
**Pairs with:** [VISUAL_LANGUAGE.md](VISUAL_LANGUAGE.md) · [COMPONENT_BEHAVIOUR.md](COMPONENT_BEHAVIOUR.md)

---

## 1. Principles

1. **Predictable** — same control behaves the same everywhere.  
2. **Reversible** — expand/collapse and drawers are escapable.  
3. **Visible state** — hover, focus, selected, disabled never ambiguous.  
4. **Keyboard parity** — anything clickable is keyboard-reachable.  
5. **Touch honesty** — ≥ 44×44px targets; no hover-only affordances on mobile.  
6. **Quiet feedback** — confirm with state change, not noise.

---

## 2. Pointer states

| State | Visual | Notes |
|---|---|---|
| **Default** | Surface / text | |
| **Hover** | `surface-2` or border → accent soft | Desktop only; no layout shift |
| **Active / pressed** | Slightly darker / opacity 0.9 | 100ms |
| **Focus-visible** | Accent ring + offset | Keyboard & programmatic focus |
| **Selected** | Accent-soft fill + accent text or left bar | Lists, TOC, nav |
| **Disabled** | Opacity 0.5 + `not-allowed` | Still focusable only if needed for SR explanation |

---

## 3. Selection

| Pattern | Behaviour |
|---|---|
| Single select | Radio / segmented / nav `aria-current` |
| Multi select | Checkboxes; show count chip |
| Table row | Click selects; Ctrl/Cmd multi where useful |
| Graph node | Click selects; previous clears unless multi-mode |

Selected items must remain distinguishable in dark mode and without color alone (check, bar, or label).

---

## 4. Expansion & collapse

| Control | Open | Close |
|---|---|---|
| Accordion section | Expand panel; scroll into view if needed | Collapse; keep header focus |
| Metric “Learn more” | Reveal secondary copy inline | Hide; focus returns to trigger |
| Copilot sheet | Slide/fade from edge | Esc, backdrop, close button |
| Modal | Center + dimmer | Esc, backdrop, close |
| TOC nested | Reveal children | Collapse children only |

**Rule:** Only one *modal* at a time. Accordions may multi-open on desktop; mobile Analysis may prefer single-open for focus.

---

## 5. Loading

| Pattern | When |
|---|---|
| Skeleton matching layout | Section / card first paint |
| Spinner + label | Short inline waits (< skeleton worth) |
| Progressive | Show loaded cards; skeleton the rest |
| Disable primary submit | While mutation in flight |

Never blank the whole app shell for one widget.

---

## 6. Error & success

| Kind | UI |
|---|---|
| Field error | Inline text + `aria-invalid` + danger border |
| Section error | `ErrorState` / Alert danger |
| Toast (optional) | Rare; prefer inline for research |
| Success | Soft accent Alert or badge — not confetti |
| API envelope error | Show message from API; no invented research |

---

## 7. Transitions

| Transition | Duration | Easing |
|---|---|---|
| Color / background | 150ms | ease |
| Expand height | 200–250ms | ease-out |
| Drawer / sheet | 250–300ms | ease-out |
| Route content | Prefer instant or 150ms fade | — |
| Sidebar width | 200ms | ease |

No bounce, no elastic overshoot.

---

## 8. Micro-interactions

| Allowed | Forbidden |
|---|---|
| Button opacity press | Particle bursts |
| Chevron rotate 90° | Infinite attention-grabbing pulse |
| Streaming cursor / fade-in tokens | Fake “typing human” delays beyond stream |
| Badge count update | Aggressive shake on error |

---

## 9. Keyboard navigation

| Key | Behaviour |
|---|---|
| `Tab` / `Shift+Tab` | Focus cycle |
| `Enter` / `Space` | Activate buttons; toggle disclosures |
| `Esc` | Close modal, drawer, dropdown, sheet |
| `Arrow` keys | Menus, tabs, radio groups, TOC |
| `Home` / `End` | List extremes where applicable |

Skip link → `#main-content` required on app shell.

---

## 10. Touch interactions

| Gesture | Use |
|---|---|
| Tap | Primary activate |
| Swipe down | Dismiss bottom sheet (optional) |
| Long-press | Avoid as sole affordance |
| Pinch-zoom | Charts: optional; provide reset |
| Pull-to-refresh | Avoid on Analysis (accidental) |

Hover tooltips → **tap** to open / close on touch devices.

---

## 11. Research Mode interaction copy

Buttons and confirmations use research language (“Analyze via API”, “Open Challenge”) — never “Place Buy”.
