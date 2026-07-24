# Architecture Governance

**Status:** MANDATORY · FROZEN  
**Applies to:** All DSP Platform implementation (L1.2+)

---

## 1. Authoritative source of truth

The following documents are **the** architecture and product authority.
Implementation must follow them **exactly**.

| Epic | Document set | Role |
|---|---|---|
| **PR1.0** | Product Strategy & Compliance | Modes, flags, terminology, compliance ports |
| **PR1.1** | Product Experience Blueprint | IA, journeys, analysis order, UX blueprints |
| **PR1.2** | Visual Language & Interaction System | Visual OS, interaction, a11y, performance UI |

Supporting constitution:

- [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md)  
- [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md)  
- [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md)  

---

## 2. Freeze rules

| Allowed | Forbidden |
|---|---|
| Implement screens/components per PXB + VLIS | Architectural redesign mid-implementation |
| Wire thin client to existing `/api/v1` | Changing API contracts without a new epic |
| Presentation / Research Mode terminology | Changing valuation / recommendation / workflow engines |
| Feature-flag gated UI | Inventing SEBI recommendation UI while flags off |
| Document gaps when blocked | “Fixing” architecture by redesigning the platform |

---

## 3. When an architectural issue is discovered

```text
STOP
Document the issue (ADR / gap note under docs/)
Do NOT redesign the platform
Escalate for a dedicated architecture epic if needed
```

Do not silently invent a new IA, mode model, or trust model.

---

## 4. Thin client invariant

- No investment calculations in the browser  
- No valuation / recommendation / AI reasoning client-side  
- Business intelligence exclusively from frozen backend APIs  

---

## 5. Regression

Backend / package regression suite must remain **GREEN** after every change.
No drive-by engine edits under a frontend epic.
