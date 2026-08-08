# 03 — Color System

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Upstream:** `docs/VISUAL_LANGUAGE.md` (PR1.2 VLIS)

---

## 1. Purpose

Define light theme, dark theme, semantic, financial, and status color roles so meaning is consistent across all surfaces.

---

## 2. Themes

Both themes share structure. Tokens swap via `data-theme` (`light` | `dark` | `system`).  
Do not invert images ad hoc. Charts must define series colors per theme.

### 2.1 Light theme — core

| Token | Value | Role |
|---|---|---|
| `--bg` | `#f3efe6` | Page canvas (warm paper) |
| `--fg` | `#1c2421` | Primary text |
| `--muted` | `#5c6b66` | Secondary text |
| `--surface` | `#fffdf8` | Cards / panels |
| `--surface-2` | `#ebe4d6` | Hover / inset |
| `--border` | `#d5ccbc` | Hairline structure |
| `--accent` | `#0f6e56` | Brand / primary CTA |
| `--accent-fg` | `#f4fff9` | Text on accent |
| `--accent-soft` | `#d8f0e6` | Selected / soft fill |

### 2.2 Dark theme — core

| Token | Value | Role |
|---|---|---|
| `--bg` | `#101614` | Page canvas |
| `--fg` | `#e8f0ec` | Primary text |
| `--muted` | `#9bb0a7` | Secondary text |
| `--surface` | `#18211e` | Cards / panels |
| `--surface-2` | `#24302c` | Hover / inset |
| `--border` | `#31433d` | Hairline structure |
| `--accent` | `#3dba8f` | Brand / primary CTA |
| `--accent-fg` | `#06241a` | Text on accent |
| `--accent-soft` | `#1d3b32` | Selected / soft fill |

---

## 3. Semantic colors

| Semantic | Meaning | Light | Dark |
|---|---|---|---|
| Success | Healthy / attractive / low concern | Accent + `--accent-soft` | Same roles |
| Warning | Caution / watch / medium | Text `#7a5a12` · bg `#f7ecd2` | Text `#e6d29a` · bg `#3a3218` |
| Information | Neutral guidance / Research Mode banner | Border + `--surface-2` | Same roles |
| Neutral | Default chrome | `--surface` / `--muted` | Same roles |
| Danger | System error / destructive only | `--danger-*` | `--danger-*` |

**Critical rule:** High financial risk ≠ red “Sell” chrome. Prefer warning + text rating (`Caution`, `HIGH`). Danger is reserved for errors and destructive confirms.

---

## 4. Financial colors

Financial meaning must remain honest and Research Mode–safe.

| Use | Treatment |
|---|---|
| Positive change (factual Δ) | Accent / success soft + numeric sign |
| Negative change (factual Δ) | Warning or muted danger-adjacent **with text**; never color-only |
| Valuation attractive band | Accent soft + categorical label |
| Valuation fair band | Neutral surface-2 + label |
| Valuation caution band | Amber warning + label |
| Unavailable / unknown | Muted + explicit “Unavailable” / “Unknown” |

Never encode BUY/SELL as green/red buttons in Research Mode.

---

## 5. Status colors

| Status | Color role | Always include |
|---|---|---|
| Success / complete | Success | Text or icon + text |
| In progress | Information / accent soft | Label |
| Warning / needs review | Warning | Label |
| Error / failed | Danger | Label + recovery action |
| Disabled | Muted + reduced opacity | Not color-only |

Source / epistemic chips (Verified, Calculated, Estimated, AI, Consensus, User, Unknown, Unavailable) use neutral borders + text; accent only for emphasis, not as a second rating system.

---

## 6. Chart series colors

| Series | Light | Dark |
|---|---|---|
| Primary | `--accent` | `--accent` |
| Peer / secondary | `#3d5a80` | `#8bb4d9` |
| Tertiary (max third) | `#6b5b4a` | `#c4b5a5` |

Max three hue series before using pattern/dash. Provide non-color cues for accessibility.

---

## 7. Forbidden

- Purple / magenta brand accents
- Neon glow stacks as status
- Color-only risk encoding
- Rainbow dashboards
