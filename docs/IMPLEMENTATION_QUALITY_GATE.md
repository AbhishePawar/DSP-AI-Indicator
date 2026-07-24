# Implementation Quality Gate

**Status:** MANDATORY  
**When:** Before marking any feature **COMPLETE**

---

## 1. Epic & governance gate

Every completed feature must satisfy:

| Check | Reference |
|---|---|
| ✓ PR1.0 | Strategy, Research Mode, feature flags, compliance posture |
| ✓ PR1.1 | PXB IA, analysis order, metric/term standards |
| ✓ PR1.2 | VLIS visual & interaction OS |
| ✓ Architecture Governance | No redesign; thin client |
| ✓ User Trust Standard | Traceable → Research First |
| ✓ Product Constitution | Priority order honored |
| ✓ Four Question Rule | What / Why / Why care / What next |
| ✓ Research Mode Terminology | No Buy/Sell/Hold/Official Target unless flags |
| ✓ Feature Flag Compliance | Recommendation UI gated |
| ✓ Accessibility | AA + keyboard + SR |
| ✓ Performance Budget | Lazy/split/skeleton targets |
| ✓ Responsive Behaviour | Intentional breakpoints |
| ✓ Mobile Experience | Mobile-first adaptations |
| ✓ Thin Client Architecture | No browser investment math |

---

## 2. Final implementation checklist

Before COMPLETE:

| ✓ | Criterion |
|---|---|
| | Correct |
| | Traceable |
| | Explainable |
| | Honest |
| | Consistent |
| | Accessible |
| | Responsive |
| | Performant |
| | Actionable |
| | Production Ready |

**Regression must remain GREEN.**

---

## 3. Required return format (implementation epics)

```text
Architecture Impact
Components Added
Pages Updated
Feature Flags Used
Accessibility Validation
Performance Validation
Responsive Validation
Known Limitations
Future Enhancements
Regression Summary
```

If an architectural conflict appears: **STOP**, document, do not redesign
([ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md)).

---

## 4. Suggested per-PR evidence

- Screenshots or notes for Research Mode labels  
- Source/category labels on new insights  
- Flag matrix for any recommendation-like UI  
- a11y keyboard path smoke  
- Bundle/lazy note for heavy widgets  
- pytest / CI green summary  
