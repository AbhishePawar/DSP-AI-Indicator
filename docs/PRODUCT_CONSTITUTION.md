# Product Constitution

**Status:** MANDATORY  
**Use:** Resolve conflicts during implementation decisions.

When priorities conflict, always rank in this order:

| Priority | Principle | Meaning |
|---|---|---|
| **1** | User Trust | Traceable, honest, research-first |
| **2** | Correctness | Accurate reflection of API / engine outputs |
| **3** | Explainability | Four questions answered |
| **4** | Consistency | PXB / VLIS / terminology / flags |
| **5** | Accessibility | WCAG AA, keyboard, SR |
| **6** | Performance | Budgets without sacrificing 1–5 |
| **7** | Visual Polish | VLIS aesthetics |
| **8** | Feature Completeness | Scope fullness last |

---

## Decision rules

- A visually attractive feature that **reduces trust** must **never** ship.  
- A simpler feature that **increases trust** should **always** ship.  
- If polish conflicts with honesty (e.g. hiding “Unavailable”), honesty wins.  
- If a new widget needs client-side “smart” scoring, **stop** — thin client + Trust Standard forbid it.  
- If SEBI-looking labels are easier but flags are off, Research Mode wins.

---

## Related

- [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md)  
- [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md)  
- [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md)  
