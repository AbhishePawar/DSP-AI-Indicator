# Product Strategy

**Epic:** PR1.0

---

## Strategic intent

Transform DSP from an engineering-complete research stack into a
**two-mode product**:

1. **Research Mode (default)** — educational / decision-support language; no
   Buy / Sell / Hold / Target Price UI.  
2. **SEBI Mode (future)** — official recommendation surfaces after registration.

Investment engines (**valuation, recommendation, workflow, KG, APIs**) stay
frozen. Strategy changes **presentation, flags, docs, and compliance ports**.

---

## Roadmap (product → delivery)

### PR1.0 (this epic)

- Product Research  
- UX Research  
- Competitor Analysis (documented intent)  
- Design System standards (V2)  
- Information Architecture  
- Wireframes / User Journey (documented)  
- Compliance bounded context + feature flags  

### PR1.1 — Product Experience Blueprint (**FROZEN**)

Complete UX blueprint for L1.2–L1.7: IA, journeys, wireframes, design system,
metric & terminology libraries, analysis / decision / consensus / copilot / KG /
mobile specs. See [PRODUCT_EXPERIENCE_BLUEPRINT.md](PRODUCT_EXPERIENCE_BLUEPRINT.md).

### PR1.2 — Visual Language & Interaction System (**FROZEN**)

Definitive visual/interaction OS: tokens, motion, component behaviour, charts,
a11y, responsive, performance UI.
See [PR1_2_VISUAL_LANGUAGE_AND_INTERACTION_SYSTEM.md](PR1_2_VISUAL_LANGUAGE_AND_INTERACTION_SYSTEM.md).

### Governance (MANDATORY)

- [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md)  
- [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md)  
- [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md)  
- [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md)  

### Then (engineering L-series)

| Phase | Focus |
|---|---|
| L1.2 | Company Analysis Workspace |
| L1.3 | AI Copilot Workspace |
| L1.4 | Portfolio |
| L1.5 | Reports |

---

## Competitive posture

| DSP is | DSP is not |
|---|---|
| Explainable research | Tip blasting |
| Evidence-cited conclusions | Opaque black-box scores only |
| Dual-sided AI Challenge Mode | One-sided cheerleading |
| Mode-gated recommendations | Always-on Buy/Sell |

---

## Operating modes

See [FEATURE_FLAG_STRATEGY.md](FEATURE_FLAG_STRATEGY.md),
[RESEARCH_MODE.md](RESEARCH_MODE.md), [SEBI_MODE.md](SEBI_MODE.md).

## Non-goals (PR1.0)

- No engine redesign  
- No API contract breaks  
- No SEBI functionality implementation  
- No provider integrations for Street consensus  
