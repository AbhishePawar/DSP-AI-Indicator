# Architecture Bible

| Field | Value |
|---|---|
| **Status** | **MANDATORY** |
| **Last updated** | 2026-07-28 |
| **Role** | Canonical index of non-negotiable architecture law |

This document is the **Architecture Bible** for DSP AI Indicator. It does not
replace freeze docs; it indexes permanent **Tier-0** rules that **fail**
architecture review when violated.

---

## 1. Permanent core values (Tier-0)

| ID | Name | Spec |
|---|---|---|
| **CV-001** | Data Authenticity First | [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) |
| **CV-002** | Source Before Score | [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md) |
| **CV-003** | Explainability Before Recommendation | same |
| **CV-004** | Determinism Before Intelligence | same |
| **CV-005** | Transparency Over Confidence | same |
| **CV-006** | Traceability By Design | same |
| **CV-007** | Auditability First | same |
| **CV-008** | Research Before Recommendation | same |
| **CV-009** | Governance Over Convenience | same |
| **CV-010** | Quality Over Speed | same |

Register → [CORE_VALUES.md](CORE_VALUES.md).  
**Any CV-001…CV-010 violation = Architecture Violation.**

---

## 1b. Research Standards (constitutional content)

| ID | Name | Spec |
|---|---|---|
| **RS-001…RS-010** | Minimum report content | [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) · [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md) |

**CV = how · RS = what.** Missing required RS section = Research Report Validation
**FAIL** (and Architecture Review FAIL when reports are in scope).

---

## 2. Authority stack (do not redesign mid-epic)

| Layer | Documents |
|---|---|
| Product | PR1.0 · PR1.1 · PR1.2 |
| Trust / Constitution | [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md) · [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md) · [CORE_VALUES.md](CORE_VALUES.md) |
| Governance | [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md) · this Bible |
| System | [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) · [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [DSP_AI_INDICATOR_ARCHITECTURE.md](DSP_AI_INDICATOR_ARCHITECTURE.md) |
| Research / Reports | [RESEARCH_ARCHITECTURE.md](RESEARCH_ARCHITECTURE.md) · [REPORT_ARCHITECTURE.md](REPORT_ARCHITECTURE.md) · [RESEARCH_REPORT_SPECIFICATION.md](RESEARCH_REPORT_SPECIFICATION.md) · [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) |
| Enterprise PEPs | [PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md](PEP_000_ENTERPRISE_ARCHITECTURE_FREEZE.md) · [PEP_ARCHITECTURE_DECISIONS.md](PEP_ARCHITECTURE_DECISIONS.md) |
| Quality | [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md) · [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md) |

---

## 3. Invariants (always)

1. **CV-001…CV-010** — Tier-0 core values  
2. **RS-001…RS-010** — minimum research report content  
3. **Thin client** — no valuation / recommendation / AI investment math in the browser  
4. **Frozen `/api/v1`** — no silent contract breaks  
5. **Hexagonal engines** — adapters at edges; engines stay auth-/infra-independent  
6. **Research Mode default** — SEBI-style advice UI only behind flags  
7. **Financial derivation** — never guess data; calculate only with a defined formula and verified compatible inputs; label **CALCULATED** vs **REPORTED**; else **UNAVAILABLE**. Spec → [FINANCIAL_DATA_DERIVATION_POLICY.md](FINANCIAL_DATA_DERIVATION_POLICY.md)  

---

## 4. When blocked

```text
STOP → document gap / ADR → do NOT redesign the platform mid-implementation
```

CV-009: never bypass architecture, compliance, governance, audit, security, or core values for convenience.

---

## 5. Related checklists

- [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md)  
- [CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md)  
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)  
- [CONTRIBUTING.md](CONTRIBUTING.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)  
