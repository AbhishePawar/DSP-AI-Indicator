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

- [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md)  
- [CORE_VALUES.md](CORE_VALUES.md) · [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) · [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md)  
- [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) · [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md)  
- [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md)  
- [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md)  
- [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md)  
- [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md)  

---

## 1b. Tier-0 Core Values (CV-001…CV-010)

[CORE_VALUES.md](CORE_VALUES.md) · [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md)

Any Tier-0 violation is an **Architecture Violation**. Architecture review
**MUST FAIL**. No feature may bypass Architecture · Compliance · Governance ·
Audit · Security · Core Values (**CV-009**).

### CV-001 (authenticity)

Fabricated / placeholder financial or market numbers in production research
output are forbidden. Show **Data unavailable.** when inputs are missing.

---

## 1c. Research Standards (RS-001…RS-010)

[RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md)

Minimum report content is constitutional. **Missing required section = Research
Report Validation FAIL.** CV governs behaviour; RS governs content.

---

## 2. Freeze rules

| Allowed | Forbidden |
|---|---|
| Implement screens/components per PXB + VLIS | Architectural redesign mid-implementation |
| Wire thin client to existing `/api/v1` | Changing API contracts without a new epic |
| Presentation / Research Mode terminology | Changing valuation / recommendation / workflow engines |
| Feature-flag gated UI | Inventing SEBI recommendation UI while flags off |
| Honest **Data unavailable.** / **Unable to calculate.** | Fabricating numbers or certainty (**CV-001**, **CV-005**) |
| Document gaps when blocked | Bypassing governance for convenience (**CV-009**) |

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
