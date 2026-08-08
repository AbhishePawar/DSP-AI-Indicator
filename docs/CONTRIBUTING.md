# Contributing

| Field | Value |
|---|---|
| **Status** | **Active** |
| **Last updated** | 2026-07-28 |

Thank you for contributing to DSP AI Indicator. All contributions must obey
**Tier-0 Core Values CV-001…CV-010**.

---

## Before you write code

1. Read [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md)  
2. Read [CORE_VALUES.md](CORE_VALUES.md) — **CV-001…CV-010 are non-negotiable**  
3. Read [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) if touching reports — **RS-001…RS-010**  
4. Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)  
5. Obey [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md) · thin client · frozen `/api/v1`  
6. Use [CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md) and [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md)  

---

## Absolute rules

| Rule | Detail |
|---|---|
| **CV-001…CV-010** | Tier-0 constitutional values — any violation fails review |
| **RS-001…RS-010** | Research report minimum content — missing section fails validation |
| Unavailable / uncertain | **Data unavailable.** / **Unable to calculate.** — never invent |
| Engines / scoring / APIs / models / boundaries | Do not change unless an epic explicitly unlocks |
| Thin client | No valuation / recommendation / AI investment math in `apps/web` |
| **CV-009** | Never bypass architecture, compliance, governance, audit, or security for convenience |

---

## Definition of Done (contributor)

| # | Criterion |
|---|---|
| 1 | GREEN tests for touched surfaces |
| 2 | [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md) including **CV-001…CV-010** and **RS-001…RS-010** (reports) |
| 3 | [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md) + [CORE_VALUES.md](CORE_VALUES.md) |
| 4 | Architecture / code-review checklists checked |
| 5 | Docs / ADR updated if governance or public contracts change |
| 6 | No unauthorized edits to protected modules |

---

## Pull requests

- Prefer small, scoped PRs  
- Call out user-visible numbers and their source category  
- Flag unavailable / unable-to-calculate paths  
- **CV-001…CV-010** and **RS-001…RS-010** violations are blocking — do not merge  

Coding rules → [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) · Local setup → [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
