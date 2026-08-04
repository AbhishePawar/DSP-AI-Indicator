# Core Values

| Field | Value |
|---|---|
| **Status** | **MANDATORY · Tier-0** |
| **Last updated** | 2026-07-28 |
| **Authority** | [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) · [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md) · [PROJECT_CHARTER.md](PROJECT_CHARTER.md) §4 |

Core values are permanent **Constitutional** law. Convenience, polish, demo
pressure, or speed **do not** waive them.

**Violation of any CV-001…CV-010 = Architecture Violation** (review **MUST FAIL**).

---

## Tier-0 register

| ID | Name | Spec |
|---|---|---|
| **CV-001** | Data Authenticity First | [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) |
| **CV-002** | Source Before Score | [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md)#cv-002 |
| **CV-003** | Explainability Before Recommendation | same catalog |
| **CV-004** | Determinism Before Intelligence | same catalog |
| **CV-005** | Transparency Over Confidence | same catalog |
| **CV-006** | Traceability By Design | same catalog |
| **CV-007** | Auditability First | same catalog |
| **CV-008** | Research Before Recommendation | same catalog |
| **CV-009** | Governance Over Convenience | same catalog |
| **CV-010** | Quality Over Speed | same catalog |

Full CV-002…CV-010 text → [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md).  
ADRs → [ADR-CV-001](adr/ADR-CV-001-data-authenticity-first.md) · [ADR-CV-002-010](adr/ADR-CV-002-010-tier0-core-values.md).

---

## Summaries

### CV-001 — Data Authenticity First

Never display fabricated / placeholder / dummy financial or market numbers.
Allowed sources only. Missing → **Data unavailable.**

### CV-002 — Source Before Score

No score / valuation / recommendation / AI research output until mandatory
sources are validated. Incomplete mandatory inputs → **Data unavailable.** —
never calculate on incomplete mandatory inputs.

### CV-003 — Explainability Before Recommendation

Expose Source Data · Formula · Inputs · Weights · Engine · Confidence ·
Reasoning · Contribution. No black boxes.

### CV-004 — Determinism Before Intelligence

Identical inputs → identical outputs. No randomness or hidden AI re-scoring.
Reports must be reproducible.

### CV-005 — Transparency Over Confidence

State uncertainty. Prefer **Unable to calculate.** over fabricated certainty
or soft guesses.

### CV-006 — Traceability By Design

Output → Engine → Formula → Input → Source → Timestamp → Version.

### CV-007 — Auditability First

Reports carry Configuration · Engine/Rule/Calculation versions · Input
reference · Timestamp · Audit Reference.

### CV-008 — Research Before Recommendation

Research first; recommendations are downstream. Research Mode / flags honored.

### CV-009 — Governance Over Convenience

No bypass of Architecture · Compliance · Governance · Audit · Security · Core Values.

### CV-010 — Quality Over Speed

Correctness > Speed · Authenticity > Convenience · Explainability > Complexity ·
Reproducibility > Novelty · Verified Data > Fast Data.

---

## Charter values (continue to apply)

| Value | Maps to |
|---|---|
| Truth over convenience | CV-001 · CV-005 · CV-010 |
| Evidence over opinion | CV-002 · CV-006 |
| Clarity over complexity | CV-003 · CV-010 |
| Humility over certainty | CV-005 |
| Ownership over duplication | Package governance |
| Protection over velocity | CV-009 · CV-010 |
| Accessibility over exclusivity | Product charter |

---

## Constitution priority (conflict resolution)

**Trust (CV-001…CV-010)** → Correctness → Explainability → Consistency →
Accessibility → Performance → Visual Polish → Feature Completeness

CV-009/CV-010: governance and quality always beat convenience and speed.

Research Standards (**RS-001…RS-010**) define mandatory report *content*
alongside these behavioural values → [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md).

---

## Related

- [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md)  
- [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md)  
- [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md)  
- [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md)  
- [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) · [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md)  
