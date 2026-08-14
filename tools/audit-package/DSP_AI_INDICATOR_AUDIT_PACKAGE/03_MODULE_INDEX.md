# 03 — Module Index

Index of major modules as mirrored in this audit package. Paths are relative to package root unless noted as repository paths.

---

## A. Narrative & manifests

| Module | Path |
|---|---|
| Start / guides | `00_START_HERE.md` … `09_AUDIT_GUIDE.md` |
| Manifest | `AUDIT_MANIFEST.md` |
| Reports | `reports/` |
| Version / inventory | `manifests/` |

---

## B. Frontend (`source/web/`)

| Module | Repo path | Audit notes |
|---|---|---|
| App Router | `apps/web/src/app` | Primary IA + auth honesty surfaces |
| Components | `apps/web/src/components` | Analysis, reports, DS, advisor (AUX) |
| Lib / API clients | `apps/web/src/lib` | Thin `/api/v1` clients, flags, a11y |
| Foundation | `apps/web/src/foundation` | Tokens, routes, layout, UX |
| Hooks / providers | `apps/web/src/hooks`, `providers` | Client wiring |
| Tests / e2e | `apps/web/src/e2e`, `**/*.test.*` | Vitest certification set |
| Public assets | `apps/web/public` | If present |

---

## C. Backend & research (`source/packages/`)

| Module | Package dir | Audit focus |
|---|---|---|
| Platform façade | `dsp_platform` | Composition, research façades |
| HTTP API | `api_platform` | Routers, middleware, schemas |
| Auth / security | `auth`, `security_platform` | Institutional auth, middleware |
| Admin / beta | `admin` (+ API beta routers) | Provisioning, beta programme |
| Data engine | `data_engine` | Authenticated market/fundamentals/series |
| Contracts | `contracts` | Shared domain types |
| Research / reports | `research`, report/archive/diff façades | RS / ontology alignment |
| Engines (BQ family) | `economic_moat`, `management_quality`, `earnings_quality`, `financial_strength`, `business_quality*`, `growth_quality` | Server-side scoring |
| Valuation / decision | `valuation`, `recommendation`, `decision_intelligence`, `ai_committee`, `investment_*` | Must remain server-side |
| Portfolio / workflow | `portfolio`, `workflow`, `workspace`, `persistence` | Institutional pilot workflows |
| Other | `core`, `orchestration`, `compliance`, `llm_adapters`, … | Supporting layers |

---

## D. Documentation (`docs/`)

| Cluster | Path |
|---|---|
| Design system | `docs/design/` |
| Governance | `docs/governance/` |
| Research ontology (REP-002) | `docs/research/` |
| Release / certification | `docs/releases/` |
| Reviews / UX certs | `docs/reviews/` |
| Root project docs copy | `docs/project/` + `docs/root/` |

Priority reads for auditors:

- `ARCHITECTURE_BIBLE.md`, `CORE_VALUES.md`, `CV_001_*`, `CV_002_TO_010_*`
- `RESEARCH_STANDARDS.md`, `RS_001_TO_RS_010.md`
- `USER_TRUST_STANDARD.md`, `PRODUCT_CONSTITUTION.md`
- `docs/releases/GA_CERTIFICATION_REPORT.md`

---

## E. Configs & workflows

| Cluster | Path |
|---|---|
| Root Python / repo | `configs/root/` (`pyproject.toml`, `VERSION`, …) |
| Web | `configs/web/` |
| CI | `workflows/` |

---

## F. How to extend this index

Regenerate the package; `manifests/PACKAGE_INVENTORY.md` and `manifests/SOURCE_TREE.txt` are refreshed by the generator with the live repository layout.
