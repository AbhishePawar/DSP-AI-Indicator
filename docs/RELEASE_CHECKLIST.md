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
