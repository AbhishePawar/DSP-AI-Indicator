# Start Here — DSP AI Indicator Enterprise Audit Package

| Field | Value |
|---|---|
| Package | `DSP_AI_INDICATOR_AUDIT_PACKAGE` |
| Generator | `tools/audit-package/generate-audit-package.ps1` / `.sh` |
| Product version | **1.0.0** (`VERSION` → `v1.0.0`) |
| Branch (evaluated tip) | `cursor/p6-1-commercial-readiness` |
| Package purpose | Independent enterprise / institutional audit — **not** a product redesign |
| Authorized posture | **Closed-beta / institutional pilot GO** |
| Commercial GA | **REJECTED** (see `docs/releases/GA_CERTIFICATION_REPORT.md`) |

---

## 1. What this package is

A **reproducible** snapshot for auditors (engineering, trust, architecture, research, ops) covering:

- Narrative audit guides (`00`–`09` + `AUDIT_MANIFEST.md`)
- Project documentation (governance, research ontology, release certs, design)
- Frontend and backend/research **source** (thin-client web + Python packages)
- Build / test / lint **configs**
- CI **workflows**
- Manifests and ZIP archives for upload to review tools

It does **not** replace the live repository. Regenerate with the scripts under `tools/audit-package/`.

---

## 2. Read order (recommended)

| Step | Document | Why |
|---|---|---|
| 1 | This file | Orientation + decision posture |
| 2 | [`01_PROJECT_OVERVIEW.md`](./01_PROJECT_OVERVIEW.md) | Product intent & Research Mode |
| 3 | [`05_RELEASE_STATUS.md`](./05_RELEASE_STATUS.md) | Pilot GO vs Commercial GA REJECTED |
| 4 | [`06_KNOWN_LIMITATIONS.md`](./06_KNOWN_LIMITATIONS.md) | Honest limitations packet |
| 5 | [`02_ARCHITECTURE.md`](./02_ARCHITECTURE.md) | Thin client + backend analytics ownership |
| 6 | [`03_MODULE_INDEX.md`](./03_MODULE_INDEX.md) · [`07_REPOSITORY_MAP.md`](./07_REPOSITORY_MAP.md) | Where code lives |
| 7 | [`04_FEATURE_MATRIX.md`](./04_FEATURE_MATRIX.md) | Scope vs out-of-scope |
| 8 | [`08_DEPENDENCY_REPORT.md`](./08_DEPENDENCY_REPORT.md) | Dependency posture |
| 9 | [`09_AUDIT_GUIDE.md`](./09_AUDIT_GUIDE.md) | How to audit without redesign |
| 10 | [`AUDIT_MANIFEST.md`](./AUDIT_MANIFEST.md) | Inventory & regeneration |

Authoritative release artefacts (copied under `docs/releases/` when regenerated):

- `GA_CERTIFICATION_REPORT.md` — **COMMERCIAL GA REJECTED**
- `RELEASE_BOARD.md` — pilot APPROVED; unrestricted Commercial GA NOT APPROVED
- `KNOWN_LIMITATIONS.md` — pilot vs GA-condition split
- `RC3_FINAL_CERTIFICATION_REPORT.md` — PASS WITH CONDITIONS (pilot)

---

## 3. Non-negotiable audit truths

1. **No fabricated numbers** — prefer **Data unavailable.** (CV-001).
2. **Thin client** — no valuation, recommendation, or AI reasoning in the browser; frozen `/api/v1` only.
3. **Commercial GA is not authorized** for Version 1.0.0.
4. **Closed-beta / institutional pilot** under Research Mode is the authorized production path.
5. Do not redesign engines, API boundaries, scoring, or research ontology during audit review.

---

## 4. Folder map

```text
DSP_AI_INDICATOR_AUDIT_PACKAGE/
├── 00_START_HERE.md … 09_AUDIT_GUIDE.md
├── AUDIT_MANIFEST.md
├── docs/          # project docs + design/governance/research/releases/reviews
├── source/        # web/ + packages/ (research engines, API, platform)
├── configs/       # package manifests, tsconfig, next, eslint, prettier, vitest, …
├── workflows/     # .github/workflows
├── manifests/     # VERSION, package summary
├── archives/      # ZIP outputs for upload
└── reports/       # AUDIT_PACKAGE_REPORT + validation
```

---

## 5. Regenerate

From repository root:

```powershell
pwsh -File tools/audit-package/generate-audit-package.ps1
```

```bash
bash tools/audit-package/generate-audit-package.sh
```

See also `tools/audit-package/AUDIT_PACKAGE_REPORT.md`.
