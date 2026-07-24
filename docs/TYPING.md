# Typing Policy — DSP AI Indicator

Phase A5 establishes **mypy** as the single supported static type checker.

The goal is confidence at architectural boundaries, not repository-wide
perfection in one sprint.

## Tool

| Item | Choice |
|------|--------|
| Checker | **mypy** (≥ 1.10) |
| Config | `[tool.mypy]` in root `pyproject.toml` |
| Parallel tools | **Not used** — do not add pyright CI unless mypy is retired |

Architecture docs allow “mypy or pyright”; this repo standardizes on mypy.

## Covered packages (strict-ish)

These packages are type-checked in CI and must stay clean:

| Package | Why |
|---------|-----|
| `contracts` | Shared kernel / public DTOs |
| `core` | Foundation utilities |
| `orchestration` | Application pipeline composition |
| `dsp_platform` | Public façade / app boundary |

Settings emphasize typed defs, no implicit `Optional`, strict equality,
and unused-ignore warnings. Full mypy `--strict` is **not** enabled yet
(avoids `disallow_any_generics` / `warn_unreachable` churn on gradual
adoption).

## How to run

```powershell
# from repo root, with the project venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\mypy.exe
```

Or after `pip install -e ".[dev]"`:

```powershell
mypy
```

Configuration is read from `pyproject.toml` automatically.

## Python version note

`[tool.mypy] python_version = "3.12"` because current **numpy** stubs use
`type` statements that mypy rejects under `--python-version 3.11`.

Runtime support remains `requires-python = ">=3.11"`. Mypy on a 3.11
interpreter is fine; only the *language level* for type analysis is 3.12.

## Untyped / deferred packages

Engines and supporting packages are **not** in the mypy `files` list yet:

- `data_engine`, `snapshot_bridge`
- `dsp`, `fundamental`, `economic`, `valuation`
- `ai_committee`, `recommendation`

`follow_imports = "silent"` means imports from those packages do not fail
the gate when their internals lack annotations.

## Adopting typing for a new package

1. Add the package path to `[tool.mypy] files`.
2. Ensure its `src` root is already on `mypy_path` (or add it).
3. Run `mypy` and fix **public** APIs first (constructors, returns,
   Protocols, DTOs).
4. Prefer fixing types over `# type: ignore`. Every ignore needs a
   short comment with an error code, e.g. `# type: ignore[attr-defined]`.
5. Do not enable a second checker.

## CI

GitHub Actions runs `mypy` after lint and before tests. A type error in a
covered package fails the build.

## Suppressions policy

- No blanket `ignore_errors = True` for covered packages.
- No mass `# type: ignore` to force green.
- Documented exceptions live in this file or next to the config comment
  in `pyproject.toml` (e.g. numpy / python_version).
