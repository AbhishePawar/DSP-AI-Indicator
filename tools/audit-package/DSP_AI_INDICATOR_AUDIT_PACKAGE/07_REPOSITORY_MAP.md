# 07 — Repository Map

Maps the live monorepo into this audit package. Generator refreshes copies; this document explains the intended layout.

---

## Repository root (selected)

```text
DSP-AI-Indicator/
├── VERSION
├── README.md · CONTRIBUTING.md · LICENSE
├── pyproject.toml
├── apps/
│   └── web/                 # Next.js thin client
├── packages/                # Python research + platform packages
├── docs/                    # Architecture, CV/RS, releases, design, research
├── .github/workflows/       # CI
├── docker/ · scripts/ · tests/ · tools/
└── tools/audit-package/     # THIS generator + package
```

---

## Audit package mirror

```text
DSP_AI_INDICATOR_AUDIT_PACKAGE/
├── 00_START_HERE.md … 09_AUDIT_GUIDE.md
├── AUDIT_MANIFEST.md
├── docs/
│   ├── root/                # README, CONTRIBUTING, LICENSE, CHANGELOG (if present)
│   ├── project/             # Selected top-level docs/*.md (governance-critical set + releases index)
│   ├── design/
│   ├── governance/
│   ├── research/
│   ├── releases/
│   └── reviews/
├── source/
│   ├── web/                 # apps/web/src (+ public, selected tests)
│   └── packages/            # packages/*/src, tests, pyproject, README
├── configs/
│   ├── root/
│   └── web/
├── workflows/
├── manifests/
├── archives/
└── reports/
```

---

## Copy policy

| Include | Exclude |
|---|---|
| Source trees listed above | `node_modules`, `.next`, `.git`, `dist`, `build`, `out`, `coverage` |
| Docs design/governance/research/releases/reviews | `.cache`, `.turbo`, `playwright-report`, `test-results` |
| Config manifests & lockfiles | `__pycache__`, `*.egg-info`, `.venv`, logs, `*.tsbuildinfo` |
| GitHub workflows | IDE folders (`.idea`, `.vscode`), tmp |

---

## Size strategy

If total package exceeds **350 MB**, the generator splits ZIPs:

- `archives/audit-docs.zip`
- `archives/audit-source.zip`
- `archives/audit-tests.zip`
- `archives/audit-config.zip`

Otherwise it still produces convenient ZIP archives (docs/source/config/workflows) for AI-tool upload. Current expected size is well under 350 MB when exclusions are honored.
