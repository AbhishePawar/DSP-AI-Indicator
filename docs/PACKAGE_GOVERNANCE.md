# Package Governance Standard

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | Active |
| **Last updated** | 2026-07-26 |
| **Authority** | ASI-004 · supplements Master Protocol |

## Rules

1. Every **registered** package under `packages/<name>/` MUST have a local `pyproject.toml` with:
   - `name`, `version`, `description`, `requires-python`, `license`
   - `dependencies` matching evidence-based first-party imports (empty list allowed)
   - `[tool.setuptools.packages.find] where = ["src"]`
2. `[project].version` MUST equal package `__version__`.
3. Public modules SHOULD define `__all__`; every `__all__` name MUST resolve on import.
4. Authors / README / URLs MAY live only on the root monorepo project unless a package is published independently.
5. Distribution names MAY use hyphens (`api-platform`) while import names use underscores — both MUST map clearly.
6. Soft / duck-typed dependencies require an ADR (see ADR-ASI-003-001).
7. Orphan directories MUST NOT be registered without an ADR.
8. Ownership & status → [PACKAGE_OWNERSHIP_MATRIX.md](PACKAGE_OWNERSHIP_MATRIX.md).
9. Version truth → [VERSION_MATRIX.md](VERSION_MATRIX.md) + [DSP_STATUS.md](DSP_STATUS.md).

## Out of scope

Changing public API behaviour, package layout, or business logic is **not** package governance.
