# Chart Standards

**Epic:** PR1.2 · VLIS  
**Rule:** Every chart ships with a plain-English **interpretation** beneath it.

---

## 1. Layout & spacing

| Spec | Value |
|---|---|
| Plot padding | ≥ 8px inside card; 16–24px card padding |
| Title | Above chart; Sora/Fraunces section rules |
| Interpretation | Directly below plot; body text ≤ 3 sentences |
| Gap title→plot | 8–12px |
| Gap plot→interpretation | 12–16px |
| Adjacent charts | 24px vertical rhythm |

---

## 2. Color semantics

| Series role | Color |
|---|---|
| Primary (subject) | `--accent` |
| Secondary (peer / benchmark) | Secondary blue `#3d5a80` / dark `#8bb4d9` |
| Tertiary | Tertiary brown-gray |
| Positive change | Accent / success — with text “up” |
| Negative change | Warning amber — with text “down” (not danger-red by default) |
| Risk highlight | Warning stroke |
| Forecast / model band | Accent at 30% fill |
| Street target (when present) | Dashed secondary — labeled “Street” |

Max **3** solid series before forcing small-multiples or toggle.

---

## 3. Tooltips

| Rule | Detail |
|---|---|
| Content | Label · value · unit · period |
| Extra | Optional one-line context |
| Focus | Keyboard users get same data via focusable points or data table |
| Mobile | Tap shows sticky tooltip; tap outside clears |
| Never | Tooltip-only critical conclusion |

---

## 4. Legend

| Viewport | Placement |
|---|---|
| Desktop | Top or right of plot; not overlapping series |
| Mobile | Above plot, wrap chips |
| Interactive legend | Click toggles series; announce state |

---

## 5. Axis rules

| Rule | Detail |
|---|---|
| Include zero | For bar/column magnitude comparisons **yes**; for index/zoom line charts document if truncated |
| No misleading zoom | Dual axes discouraged; if required, label both loudly |
| Units | Always on axis or title |
| Time | Consistent timezone/period labels |
| Density | Thin tick labels; rotate ≤ 45° on mobile if needed |
| Grid | Light `--border` at low opacity; horizontal preferred |

---

## 6. Empty & error

| State | UI |
|---|---|
| No data | Empty State in plot area + interpretation “Data not available from API.” |
| Partial | Plot available range + Alert info |
| Error | ErrorState; preserve last good frame only if clearly dated |

---

## 7. Scaling ethics

- Do not crop y-axis to exaggerate tiny differences without a caption disclosing crop.  
- Log scales must be labeled “log scale”.  
- Stacked 100% charts labeled as composition, not volume.  
- Pie/donut: ≤ 5 slices; otherwise bar.

---

## 8. Interpretation template

```text
What you see: …
Why it matters: …
Investor takeaway: …
```

Aligns with Metric Library voice; Research Mode vocabulary.

---

## 9. Accessibility

- Provide **data table** alternative (visually optional, SR available).  
- Don’t rely on color alone — pattern/dash for second series.  
- Contrast of lines vs background ≥ AA where feasible.  

---

## 10. Performance

- Lazy-mount charts when section enters viewport.  
- Avoid re-animating on every parent re-render.  
- Downsample points for long series (> 500) with note.  
