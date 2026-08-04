# Release Checklist — v1.0.0-rc1

**Platform Release Candidate:** **v1.0.0-rc1**  
**Freeze:** [K1.4 Platform Freeze](K1_4_PLATFORM_FREEZE.md)

---

## Checklist

| # | Item | Status |
|---|---|---|
| 1 | Architecture frozen | **DONE** · [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) |
| 2 | Public APIs frozen | **DONE** · [PUBLIC_API_REFERENCE.md](PUBLIC_API_REFERENCE.md) |
| 3 | Security reviewed | **DONE** · K1.2; DSP Platform auth-independent |
| 4 | Production services reviewed | **DONE** · K1.3 provider-neutral ports |
| 5 | Regression suite green | **DONE** · **1538 / 1538** PASS |
| 6 | Documentation complete | **DONE** · K1.4 deliverable set |
| 7 | Semantic version assigned | **DONE** · **v1.0.0-rc1** · [VERSION_MATRIX.md](VERSION_MATRIX.md) |
| 8 | Known limitations recorded | **DONE** · K1.4 §4 |
| 9 | Future roadmap documented | **DONE** · L1.0 Web Application next |
| 10 | Dependency graph frozen | **DONE** · [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) |
| 11 | **Tier-0 CV-001…CV-010** enforced in gates | **MANDATORY** · [CORE_VALUES.md](CORE_VALUES.md) · [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md) |
| 12 | **Research Standards RS-001…RS-010** | **MANDATORY** · [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) |

---

## Tier-0 release gate (all future releases)

| ✓ | Requirement |
|---|---|
| | **CV-001** — no fabricated / placeholder production numbers |
| | **CV-002** — no scores on incomplete mandatory sources |
| | **CV-003** — explainability surface for scores/recommendations |
| | **CV-004** — deterministic / reproducible research outputs |
| | **CV-005** — uncertainty / Unable to calculate honest |
| | **CV-006** — traceability chain |
| | **CV-007** — audit envelope on research reports |
| | **CV-008** — research before recommendation |
| | **CV-009** — no governance bypass |
| | **CV-010** — quality over speed |

---

## Research Standards release gate

| ✓ | Requirement |
|---|---|
| | **RS-001…RS-010** minimum report sections enforced in validation |
| | Mandatory header first; MoS prominent (**RS-005**) |
| | Authenticated market data only (**RS-002**) |
| | Audit & provenance complete (**RS-010**) |

---

## Sign-off

| Role | Statement |
|---|---|
| Architecture | Backend stack certified for client integration |
| Quality | Regression gate green at freeze |
| Product | Approved to begin **Phase L1.0 — Web Application** subject to K1.4 conditions |

**Release candidate:** **v1.0.0-rc1**  
**Overall:** **PASS**

---

## Conditions carried into L1.0

1. Enable `SecurityBundle` on production `create_app`.  
2. Treat production / security in-memory stores as non-durable until adapters land.  
3. Prefer `/api/v1` and published OpenAPI for web clients.  
4. Do not bypass `dsp_platform` / `api_platform` with deep engine imports from the web app.
