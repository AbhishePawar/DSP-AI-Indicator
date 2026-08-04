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
| ✓ **Tier-0 CV-001…CV-010** | [CORE_VALUES.md](CORE_VALUES.md) — authenticity through quality-over-speed |
| ✓ **Research Standards RS-001…RS-010** | [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) — minimum report content |
| ✓ User Trust Standard | Traceable → Research First |
| ✓ Product Constitution | Priority order honored (Tier-0 first) |
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
| | **Authentic (CV-001)** — no fabricated / placeholder production numbers |
| | **Source-gated (CV-002)** — no score on incomplete mandatory inputs |
| | **Explainable (CV-003)** |
| | **Deterministic / reproducible (CV-004 · CV-007)** |
| | **Transparent uncertainty (CV-005)** |
| | **Traceable (CV-006)** |
| | **Research-first (CV-008)** |
| | **Governance-compliant (CV-009)** |
| | **Quality over speed (CV-010)** |
| | **RS-001…RS-010** — research report minimum content (when reports in scope) |
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

- **CV-001…CV-010** — Tier-0 checklist evidence ([ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md))  
- **RS-001…RS-010** — Research Standards evidence when reports/emitters touched  
- Screenshots or notes for Research Mode labels  
- Source/category labels on new insights  
- Unavailable / Unable to calculate paths documented  
- Flag matrix for any recommendation-like UI  
- a11y keyboard path smoke  
- Bundle/lazy note for heavy widgets  
- pytest / CI green summary  
- [CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md)  
- [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md)  
