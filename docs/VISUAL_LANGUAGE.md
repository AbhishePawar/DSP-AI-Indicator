# Visual Language

**Epic:** PR1.2 — Visual Language & Interaction System (VLIS)  
**Status:** FROZEN for L1.2+ UI implementation  
**Inputs:** PR1.0 · PR1.1 PXB · Design Standard V2 · Research Mode  

**Identity:** Calm institutional research — teal/slate, Fraunces + Sora.  
**Not:** Tip-app neon, purple AI glow, stock-ticker noise.

---

## 1. Visual identity statement

DSP should feel like a **quiet research desk**: warm paper surfaces, clear hierarchy, evidence before ornament. Motion is purposeful. Color carries meaning (risk, success, info) — never decoration alone.

**Taglines (brand, not chrome clutter):**  
Complex Analysis. Simple Decisions. · Professional Investment Research for Everyone.

---

## 2. Primary palette

| Token | Light | Dark | Role |
|---|---|---|---|
| `--bg` | `#f3efe6` | `#101614` | Page canvas |
| `--fg` | `#1c2421` | `#e8f0ec` | Primary text |
| `--surface` | `#fffdf8` | `#18211e` | Cards / panels |
| `--surface-2` | `#ebe4d6` | `#24302c` | Hover / inset |
| `--border` | `#d5ccbc` | `#31433d` | Hairline structure |
| `--accent` | `#0f6e56` | `#3dba8f` | Brand / primary CTA |
| `--accent-fg` | `#f4fff9` | `#06241a` | Text on accent |
| `--accent-soft` | `#d8f0e6` | `#1d3b32` | Selected / soft fill |
| `--glow` | teal 18% | teal 16% | Ambient hero wash only |

---

## 3. Secondary palette

| Name | Light | Dark | Use |
|---|---|---|---|
| Ink muted | `#5c6b66` (`--muted`) | `#9bb0a7` | Meta, captions |
| Amber warn | `#7a5a12` / bg `#f7ecd2` | `#e6d29a` / bg `#3a3218` | Caution bands |
| Chart peer | `#3d5a80` | `#8bb4d9` | Secondary series |
| Chart tertiary | `#6b5b4a` | `#c4b5a5` | Third series max |

Never introduce purple/magenta as brand accent.

---

## 4. Semantic colors

| Semantic | Meaning | Light treatment | Dark treatment |
|---|---|---|---|
| **Success** | Attractive / healthy / low concern | Accent + `--accent-soft` | Same tokens |
| **Warning** | Caution / medium / watch | Amber warn pair | Amber dark pair |
| **Risk** | High risk / adverse | Prefer warning first; escalate to danger only for **system** failure | Same |
| **Information** | Neutral guidance / Research Mode banner | Border + surface-2 | Same |
| **Neutral** | Default chrome | surface / muted | Same |
| **Danger** | Errors / destructive only — **not** “Sell” | `--danger-*` | `--danger-*` |

**Research Mode rule:** High financial risk ≠ red “Sell” chrome. Use warning + text rating (“Caution”, “HIGH”).

---

## 5. Typography hierarchy

| Level | Font | Size | Weight | Tracking | Use |
|---|---|---|---|---|---|
| Brand | Fraunces | 1.25–1.5rem | 500 | tight | Shell wordmark |
| Page title | Fraunces | 1.875–2.25rem | 500 | tight | `h1` |
| Section | Fraunces | 1.25–1.5rem | 500 | tight | `h2` |
| Card title | Fraunces | 1.125rem | 500 | tight | Card headers |
| Body | Sora | 0.875–1rem | 400 | normal | Copy |
| Label | Sora | 0.75rem | 500 | wide optional | Field labels / “Why it matters” |
| Meta | Sora | 0.75rem | 400 | normal | Timestamps, breadcrumbs |
| Mono | ui-monospace | 0.75rem | 400 | | API / evidence ids |

**Measure:** explanatory prose ≤ 72ch.  
**Pairing rule:** Fraunces for titles only; never body in display serif.

---

## 6. Spacing scale

| Step | px | Rem (base 16) | Common use |
|---|---|---|---|
| 1 | 4 | 0.25 | Icon gaps |
| 2 | 8 | 0.5 | Compact stacks |
| 3 | 12 | 0.75 | Chip padding |
| 4 | 16 | 1 | Default inset |
| 5 | 24 | 1.5 | Card padding / section gap |
| 6 | 32 | 2 | Section separation |
| 7 | 48 | 3 | Page rhythm |
| 8 | 64 | 4 | Hero / login breathing |

**Grid gutters:** 16 mobile · 24 desktop. **Content max:** 72rem.

---

## 7. Corner radius

| Element | Radius |
|---|---|
| Buttons, inputs, badges | `6px` (`rounded-md`) |
| Cards, panels, tables wrap | `8px` (`rounded-lg`) |
| Modals / sheets | `8–12px` |
| Pills / full round | **Avoid** by default |
| Graphs / avatars | Intentional exception only |

---

## 8. Elevation & surfaces

| Level | Treatment |
|---|---|
| 0 Flat | Default — border + surface fill |
| 1 Raise | Optional soft shadow on modal/dropdown only |
| 2 Overlay | Dimmer `rgba(0,0,0,0.4)` behind dialogs |

**Philosophy:** Prefer **flat + border** over stacked shadows. Research UI should not float like a consumer fintech dashboard.

---

## 9. Glass / flat usage

| Pattern | Allowed? | Where |
|---|---|---|
| Flat surface | **Default** | Cards, sections, tables |
| Light blur topbar | **Yes** | `backdrop-blur` on sticky chrome only |
| Heavy glassmorphism | **No** | — |
| Ambient radial glow | **Yes, subtle** | Login / shell background wash (`--glow`) |

---

## 10. Borders & shadows

| Token | Spec |
|---|---|
| Border | 1px solid `--border` |
| Focus ring | 2px `--accent` + 2px offset `--bg` |
| Shadow sm | `0 8px 24px rgba(16,22,20,0.08)` — dropdown/modal only |
| Shadow lg | Login card only |

No multi-layer neon shadows.

---

## 11. Animation philosophy (summary)

Motion **explains state** (open/close, load, stream). It never celebrates.  
Duration short (150–300ms). Easing standard ease-out.  
**Always** honor `prefers-reduced-motion: reduce` → instant or opacity-only.  

Full rules: [ANIMATION_GUIDELINES.md](ANIMATION_GUIDELINES.md).

---

## 12. Dark mode

Same structure; tokens swap via `data-theme`.  
Do not invert images ad hoc. Charts must define dark series colors explicitly.  
Semantic meaning preserved across themes.

---

## 13. Do / Don’t

| Do | Don’t |
|---|---|
| Calm teal accent | Purple gradients |
| Text ratings + color | Color-only risk |
| Flat cards | Card-in-card nesting |
| One primary CTA | Competing accent buttons |
| Research vocabulary | BUY/SELL chrome in Research Mode |
