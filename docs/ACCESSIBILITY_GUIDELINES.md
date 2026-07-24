# Accessibility Guidelines

**Epic:** PR1.2 · VLIS  
**Target:** **WCAG 2.2 Level AA** for product UI.

---

## 1. Scope

Applies to `apps/web` and future mobile webviews.  
Research content must remain operable without mouse and without color vision.

---

## 2. Contrast

| Element | Minimum |
|---|---|
| Body text | 4.5:1 vs background |
| Large text (≥ 18px / 14px bold) | 3:1 |
| UI borders / icons meaning | 3:1 against adjacent colors |
| Focus ring | Visible on light and dark themes |

Verify both `light` and `dark` token sets.

---

## 3. Keyboard support

| Requirement | Standard |
|---|---|
| All actions | Reachable via Tab |
| Focus order | Matches reading order |
| Focus visible | Accent ring always on `:focus-visible` |
| Esc | Closes overlays |
| No keyboard trap | Except intentional modal focus trap with return |
| Skip link | “Skip to main content” |

See [INTERACTION_GUIDELINES.md](INTERACTION_GUIDELINES.md).

---

## 4. Screen reader guidance

| Pattern | Implementation |
|---|---|
| Landmarks | `header` / `nav` / `main` / `complementary` |
| Page title | Unique per route |
| Live regions | `aria-live="polite"` for conclusion refresh / streaming complete |
| Buttons | Name from text or `aria-label` |
| Icon-only | Required accessible name |
| Decorative | `aria-hidden` |
| Dialogs | `role="dialog"` `aria-modal` labelledby title |
| Accordion | `aria-expanded` `aria-controls` |
| Tabs | `tablist` / `tab` / `tabpanel` |
| Tables | `<th scope>` · caption when dense |
| Charts | Text summary + data table alternative |
| Ratings | Text label (“HIGH”) not color alone |

---

## 5. Forms

- Visible labels (not placeholder-only)  
- `aria-invalid` + error text linked via `aria-describedby`  
- Required fields indicated in text  

---

## 6. Motion

Honor `prefers-reduced-motion` ([ANIMATION_GUIDELINES.md](ANIMATION_GUIDELINES.md)).

---

## 7. Research Mode language

Assistive tech must hear **Research Conclusion / DSP View** labels — not hard-coded Buy/Sell when flags disallow.

---

## 8. Accessibility checklist (ship gate)

- [ ] AA contrast checked (light + dark)  
- [ ] Keyboard-only path for primary journey (login → analyze)  
- [ ] Focus visible on all interactive elements  
- [ ] Modals trap focus and restore  
- [ ] Images/icons have correct SR treatment  
- [ ] Charts have text alternative  
- [ ] Errors announced / associated  
- [ ] Reduced motion verified  
- [ ] Zoom 200% usable without loss of action  
- [ ] No seizure-risk flashing  

---

## 9. Testing methods

1. Keyboard-only walkthrough  
2. axe / Lighthouse a11y (advisory)  
3. One screen reader smoke (NVDA or VoiceOver) on Analysis  
4. Forced colors / Windows contrast mode spot check when feasible  
