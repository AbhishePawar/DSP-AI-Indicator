# Animation Guidelines

**Epic:** PR1.2 · VLIS  
**Philosophy:** Motion explains — it never decorates or celebrates.

---

## 1. Global rules

| Rule | Spec |
|---|---|
| Duration | 150–300ms typical; ≤ 400ms absolute |
| Easing | `ease` or `ease-out` — no bounce/spring by default |
| Property preference | `opacity`, `transform` — avoid layout thrash |
| Simultaneous | ≤ 2 motion channels at once in one region |
| Reduced motion | If `prefers-reduced-motion: reduce` → **no transform slides**; opacity 0→1 ≤ 100ms or instant |

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

(Implement equivalently in component transitions rather than blunt global if needed.)

---

## 2. Opening / closing

| Surface | Open | Close |
|---|---|---|
| Modal | Fade + slight scale 0.98→1 (200ms) | Reverse; unmount after |
| Drawer (nav) | TranslateX −100%→0 (250ms) | Reverse |
| Copilot sheet | TranslateY 100%→0 (250ms) | Reverse |
| Dropdown | Fade + 4px Y (150ms) | Fade out 100ms |
| Accordion | Height/grid auto with 200ms; or opacity if reduced | Same |

Focus moves **after** open animation starts (or immediately if reduced motion).

---

## 3. Loading

| Pattern | Motion |
|---|---|
| Skeleton | Gentle pulse opacity 0.5↔1 at 1.2s — **disabled** under reduced motion (static) |
| Spinner | CSS rotate; paused under reduced motion → swap to “Loading…” text only |
| Progressive reveal | Cards appear opacity 0→1 staggered ≤ 50ms apart; max 5 stagger |

---

## 4. Filtering & searching

| Action | Motion |
|---|---|
| Filter apply | List cross-fade 150ms or instant |
| Search results | Replace in place; no fly-in from offscreen |
| Clear filters | Instant reset preferred |

---

## 5. Navigation

| Action | Motion |
|---|---|
| Route change | Prefer instant; optional 150ms content fade |
| TOC scroll-spy | Instant highlight; smooth scroll only if user didn’t request reduced motion |
| Sidebar collapse | Width transition 200ms |

---

## 6. Card expansion

| Action | Motion |
|---|---|
| Learn more | Expand panel 200ms ease-out |
| Metric details | Same |
| Challenge lists | Accordion per group |

Avoid expanding cards that push primary CTA out of view without scroll compensation.

---

## 7. AI streaming

| Phase | Motion |
|---|---|
| Waiting | Skeleton line or subtle cursor — no fake long delay |
| Streaming tokens | Append text; optional fade on new block |
| Citations arrive | Fade-in chips 150ms |
| Complete | Stop cursor; enable actions |

Do not animate each character with delay beyond network stream.

---

## 8. Chart / graph

| Action | Motion |
|---|---|
| First paint | Draw series ≤ 400ms once; skip if reduced motion (static final frame) |
| Hover | Instant crosshair |
| Filter series | Cross-fade 150ms |
| KG layout | Prefer static settle; animate only if motion allowed and < 300ms |

---

## 9. Forbidden animations

- Infinite attention pulses on CTAs  
- Parallax scroll on research content  
- Confetti / success fireworks  
- Page-wide blur transitions  
- Auto-playing non-essential motion  

---

## 10. Checklist before shipping motion

- [ ] Meaningful state change?  
- [ ] ≤ 300ms?  
- [ ] Reduced-motion path tested?  
- [ ] No layout jump / CLS spike?  
- [ ] Keyboard user not trapped mid-animation?  
