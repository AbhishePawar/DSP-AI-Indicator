# 11 — Accessibility

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Target:** WCAG 2.2 Level AA (minimum)  
**Upstream:** `docs/ACCESSIBILITY_GUIDELINES.md` (PR1.2)

---

## 1. Purpose

Accessibility is a Constitution priority above visual polish. Trust requires that meaning is available without relying on color, motion, or mouse-only paths.

---

## 2. Non-negotiables

1. Text contrast ≥ AA for body and UI text on surfaces.  
2. Focus-visible rings on all interactive controls (`--accent` ring + `--bg` offset).  
3. Do not convey rating/risk by color alone — text label required.  
4. Icon-only controls need accessible names.  
5. Honor `prefers-reduced-motion`.  
6. Keyboard operability for nav, dialogs, tables (where interactive), AI composer.  
7. Forms: labels, errors, `aria-invalid`, describedby helpers.  
8. Dialogs: focus trap, Escape, restore focus.  
9. Live regions for streaming AI and async errors (polite/assertive as appropriate).  
10. Hit targets ≥ 44×44px on touch.

---

## 3. Trust-preserving a11y

| Concern | Requirement |
|---|---|
| Source chips | Readable text, not icon-only |
| Epistemic category | Announced / visible text |
| Chart interpretation | Text caption available to AT |
| Recommendation state | Text category; never color-only |
| Unavailable data | Explicit “Unavailable”, not empty cell silence |

---

## 4. Structure

- Landmark regions: header, nav, main, complementary (AI), contentinfo  
- Heading order without skips  
- Skip link to main content  
- Language attribute correct  

---

## 5. Theming

Light and dark themes must independently meet contrast. Test both.  
High-contrast system settings: do not fight OS forced-colors when present.

---

## 6. Mobile & assistive tech

- Zoom to 200% without loss of essential content  
- Screen reader labels match visible intent  
- No horizontal page trap (tables may scroll locally)  

---

## 7. Testing expectations

| Layer | Method |
|---|---|
| Automated | axe / eslint-plugin-jsx-a11y where applicable |
| Manual | Keyboard-only pass; SR spot-check critical flows |
| Visual | Contrast check light + dark |
| Motion | Toggle reduced-motion |

---

## 8. Do / Don’t

| Do | Don’t |
|---|---|
| Visible focus | `outline: none` without replacement |
| Text + color | Red/green only encodings |
| Named controls | “Click here” icon soup |
| Honest unavailable states | Decorative empty charts |
