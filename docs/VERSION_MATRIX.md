# Version Matrix

**Platform Release Candidate:** **`v1.0.0-rc1`**  
**Freeze date:** 2026-07-21  
**Regression gate:** **1538 / 1538** PASS

Semantic versioning: package versions below are **frozen baselines** for this
RC. Additive patch/minor increments within a package require review against
K1.4 freeze rules; breaking public API changes require a new RC or major bump.

---

## 1. Platform release

| Artifact | Version |
|---|---|
| **DSP AI Indicator Backend RC** | **v1.0.0-rc1** |
| Root project (`dsp-ai-indicator`) | 0.1.0 (monorepo meta) |

---

## 2. Epic K packages

| Package | Version | Phase |
|---|---|---|
| `dsp_platform` | **0.6.0** | K1.0 |
| `api_platform` | **0.1.0** | K1.1 |
| `security_platform` | **0.1.0** | K1.2 |
| `production_platform` | **0.1.0** | K1.3 |

---

## 3. Frozen business / foundation packages

| Package | Version |
|---|---|
| `copilot` | 0.5.0 |
| `knowledge_graph` | 0.4.0 |
| `workflow` | 0.4.0 |
| `recommendation` | 0.4.0 |
| `quantitative_risk` | 0.3.0 |
| `research` | 0.4.0 |
| `risk` | 0.5.0 |
| `portfolio` | 0.5.0 |
| `comparison` | 0.2.0 |
| `decision_intelligence` | 0.2.0 |
| `industry` | 0.9.0 |
| `universe` | 0.1.0 |
| `orchestration` | 0.2.0 |
| `contracts` | 0.3.0 |
| `core` | 0.2.0 |
| `data_engine` | 0.6.0 |
| `dsp` | 0.2.0 |
| `fundamental` | 0.1.0 |
| `economic` | 0.1.1 |
| `valuation` | 0.12.0 |
| `ai_committee` | 0.3.0 |
| `snapshot_bridge` | 0.1.0 |
| `compliance` | **0.1.0** (PR1.0 — flags / terminology / ports) |

---

## 4. HTTP / API versioning

| Surface | Version |
|---|---|
| HTTP API | **v1** (`/api/v1`, `X-API-Version`) |
| OpenAPI `info.version` | 0.1.0 (`api_platform`) |

---

## 5. Compatibility policy

- **RC → GA (`v1.0.0`):** documentation / adapter / bugfix only unless
  freeze amendment.  
- **Clients:** pin against RC tag; treat public façades in
  [PUBLIC_API_REFERENCE.md](PUBLIC_API_REFERENCE.md) as the contract.  
- **Providers:** swap via ports without bumping domain package majors.
