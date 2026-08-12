# 07 — Iconography

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Upstream:** `docs/ICONOGRAPHY.md` (PR1.2)

---

## 1. Purpose

Icons support meaning; they never replace labels for risk, recommendation, or trust categories.

---

## 2. Principles

1. **Meaningful only** — every icon maps to a clear action or object.
2. **Text companion** — icon buttons require `aria-label`; status icons require visible text nearby.
3. **Optical calm** — 1.5–2px stroke feel; no neon duotone brand icons.
4. **Consistent set** — one library family per release (e.g. Lucide-compatible outline set).
5. **No emoji as system icons** in product chrome.

---

## 3. Sizes

| Size | px | Use |
|---|---|---|
| sm | 14–16 | Inline with meta text |
| md | 18–20 | Default toolbar / list |
| lg | 24 | Empty states, feature callouts |
| xl | 32+ | Rare; marketing only |

Hit area ≥ 44px for interactive icons.

---

## 4. Color

| Context | Treatment |
|---|---|
| Default | `--muted` or `--fg` |
| Active / selected | `--accent` |
| Warning | Warning semantic |
| Danger | Danger semantic |
| On accent buttons | `--accent-fg` |

Do not rainbow-color a toolbar of icons.

---

## 5. Domain mapping (examples)

| Domain | Example icons | Must not imply |
|---|---|---|
| Navigation | home, search, library | — |
| Research | file-text, book-open, link | Instant buy |
| Risk | alert-triangle + text | Automatic sell |
| AI | sparkles sparingly / message-square | Omniscience |
| Portfolio | briefcase, pie-chart | Guaranteed return |
| Admin | settings, users, shield | — |

---

## 6. Do / Don’t

| Do | Don’t |
|---|---|
| Pair icon + text for status | Color-only icon for HIGH risk |
| Keep metaphors stable | Cute mascots in research chrome |
| Use filled state for selection sparingly | Animated looping icon noise |
