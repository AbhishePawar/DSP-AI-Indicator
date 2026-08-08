# Product Constitution

**Status:** MANDATORY  
**Use:** Resolve conflicts during implementation decisions.

When priorities conflict, always rank in this order:

| Priority | Principle | Meaning |
|---|---|---|
| **0** | **Tier-0 Core Values (CV-001…CV-010)** | Constitutional behaviour — [CORE_VALUES.md](CORE_VALUES.md) |
| **0b** | **Research Standards (RS-001…RS-010)** | Constitutional report content — [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) |
| **1** | User Trust | Traceable, honest, research-first (implements Tier-0) |
| **2** | Correctness | Accurate reflection of API / engine outputs |
| **3** | Explainability | Four questions answered (**CV-003**) |
| **4** | Consistency | PXB / VLIS / terminology / flags |
| **5** | Accessibility | WCAG AA, keyboard, SR |
| **6** | Performance | Budgets without sacrificing 0–5 (**CV-010**: quality > speed) |
| **7** | Visual Polish | VLIS aesthetics |
| **8** | Feature Completeness | Scope fullness last |

---

## Decision rules

- Tier-0 Core Values **override** convenience, demo pressure, and speed (**CV-009**, **CV-010**).  
- A visually attractive feature that **reduces trust** must **never** ship.  
- A simpler feature that **increases trust** should **always** ship.  
- If polish conflicts with honesty (e.g. hiding “Unavailable”), honesty wins.  
- If polish tempts fabricated / placeholder numbers, **CV-001** wins — show **Data unavailable.**  
- If mandatory inputs are incomplete, **CV-002** wins — do not calculate; show **Data unavailable.**  
- If uncertainty exists, **CV-005** wins — prefer **Unable to calculate.** over fake certainty.  
- Research before recommendation (**CV-008**); SEBI-looking labels stay flag-gated.  
- If a new widget needs client-side “smart” scoring, **stop** — thin client + Trust Standard + **CV-004**.  
- Research reports must satisfy **RS-001…RS-010** minimum content
  ([RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md)); missing section fails validation.  
- No feature may bypass Architecture · Compliance · Governance · Audit · Security · Core Values (**CV-009**).

---

## Related

- [CORE_VALUES.md](CORE_VALUES.md) · [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md)  
- [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md)  
- [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md)  
- [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) · [RS_001_TO_RS_010.md](RS_001_TO_RS_010.md)  
- [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md)  
- [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md)  
- [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md)  
