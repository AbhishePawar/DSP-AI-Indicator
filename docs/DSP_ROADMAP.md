# DSP Roadmap

| Field | Value |
|---|---|
| **Version** | `1.1.0` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-23 |
| **Audience** | Product · engineering leads · AI planning |
| **AI load** | **P4 — planning only** |

## Purpose

**Canonical** epic sequencing. Sprint detail stays in `docs/<EPIC>_SPRINT*.md`. Do not copy architecture, freezes, or coding standards into this file.

---

## 1. North star

Institutional-grade, explainable research: engines produce evidence-backed artifacts; clients present honestly; compliance modes stay enforceable.

---

## 2. Epic status board

| Epic | Focus | Status | Typical scope class |
|---|---|---|---|
| **K1.x** | Platform freeze | **Frozen** — RC `v1.0.0-rc1` | Infrastructure |
| **PR1.0–PR1.2** | Strategy, PXB, VLIS, trust | **Frozen** (docs) | Documentation / Presentation governance |
| **L1.0–L1.2** | Company Analysis web workspace | **Active / largely delivered** | Presentation |
| **V1.x** | Valuation intelligence (web) | In progress / partial | Presentation |
| **V2.x** | Advisor platform | In progress (demo-flagged) | Presentation / Decision |
| **M1.x** | Management Intelligence (web) | Delivered / validating → **protected** | Presentation (+ Domain if engine epic) |
| **M2.x** | Economic Moat Intelligence | In progress → treat certified parts as **protected** | Presentation / Domain |
| **EQ1.x** | Earnings Quality Intelligence | In progress / validating | Presentation / Domain |
| **E2+** | Quant risk / deeper providers | Future | Domain / Infrastructure |
| **Mobile** | Native / PWA | Future | Presentation |
| **Cloud persistence** | Accounts, sync, server exports | Future | Infrastructure |

Versions → [VERSION_MATRIX.md](VERSION_MATRIX.md) · Freezes → [DSP_STATUS.md](DSP_STATUS.md).

---

## 3. Sequencing principles

1. Freeze before extend.  
2. Presentation before providers (Unavailable > fabrication).  
3. Trust before polish ([PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md)).  
4. One epic + **one scope class** per change set when possible.  
5. This file flips status only; sprint notes hold delivery detail.

---

## 4. Near-term themes (non-binding)

1. Keep **GREEN** while validating M2 / EQ1.  
2. Harden Advisor (V2) behind flags.  
3. Maintain DSP_* suite as the only default AI load path.  
4. Cloud sync only as a dedicated Infrastructure epic.  
5. Optional LLM proxy — must not invent numbers.

---

## 5. Explicit non-goals (unless new epic)

Autonomous trading · Buy/Sell as default UX · Client-side valuation engines · Silent API breaks · Mid-sprint platform redesign · Editing **protected** modules without override

---

## 6. Related

[DSP_STATUS.md](DSP_STATUS.md) · [DSP_CHANGELOG.md](DSP_CHANGELOG.md) · [CHANGELOG.md](CHANGELOG.md) · [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md)
