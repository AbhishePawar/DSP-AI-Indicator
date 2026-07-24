# Iconography

**Epic:** PR1.2 · VLIS

---

## 1. Rules

1. **No decorative icons.** If removing the icon loses no meaning, remove it.  
2. Icons **communicate** state, type, or action — they do not ornament.  
3. Every icon control needs a **text alternative** (`aria-label` or visible label).  
4. Prefer **outline** 1.5–2px stroke icons at 16/20/24px.  
5. **One metaphor per concept** across the product (same “risk” icon everywhere).  
6. Do not use currency/rocket/fire emoji in product chrome.  
7. Rating meaning must never rely on icon alone — pair with text.

---

## 2. Size scale

| Size | px | Use |
|---|---|---|
| sm | 16 | Inline with body / table |
| md | 20 | Buttons, inputs |
| lg | 24 | Section utility, empty illustration *only if meaningful* |

Touch targets remain ≥ 44px even when glyph is 20px.

---

## 3. Color

| Context | Color |
|---|---|
| Default | `--muted` |
| Active / selected | `--accent` |
| On accent button | `--accent-fg` |
| Danger action | `--danger-fg` |
| Warning | Amber warn token |

Icons inherit `currentColor` wherever possible.

---

## 4. Semantic catalog (v1)

| Concept | Metaphor | Where |
|---|---|---|
| Navigate / menu | Soft hamburger / list | Mobile topbar |
| Close | X | Dialogs |
| Expand / collapse | Chevron | Accordion, TOC |
| Search | Magnifier | SearchBox |
| Info / terminology | Info circle | Tooltips trigger |
| Warning / caution | Triangle alert | Alerts |
| Error | Octagon / X circle | ErrorState |
| Success / healthy | Check | Success alerts only |
| Copilot / AI | Simple spark *or* chat — pick one | Copilot entry |
| Evidence / doc | Document | Evidence chips |
| External / export | Download / share | Export |
| Risk | Shield or alert — pick one | Risk section |
| Chart | Small sparkline glyph rare | Only if needed |
| Graph / KG | Nodes link | KG entry |
| Settings | Gear | Settings nav |
| Account | User | Account menu |

**Avoid:** skull, money bag, trending rocket, crystal ball.

---

## 5. Empty states

Prefer short **text** empty states.  
If an illustration is used, it must be monochrome, flat, and explain emptiness (e.g. hollow folder) — not mascot entertainment.

---

## 6. Accessibility

- Decorative SVG: `aria-hidden="true"`  
- Meaningful SVG: `<title>` or parent `aria-label`  
- Do not animate icons continuously  

---

## 7. Implementation note (L1.2+)

Use one icon set (e.g. Lucide or Heroicons outline) — **do not** mix skeuomorphic and duotone styles.
