# Git Recovery Manager

Internal DSP tooling that turns a **dirty working tree** into **logical, reviewable commits**.

**Scope:** tooling only. Does not modify business/product source as part of its operation beyond optional, explicitly confirmed `git add` / `commit` / `push` of classified paths.

## Safety rails

| Never | Always |
|---|---|
| `git add -A` / `git add .` / `git add -u` | Stage **only** files in the current group |
| One mega-commit of everything | One group → one commit |
| `git push --force` / `--force-with-lease` | Plain `git push origin HEAD:refs/heads/<branch>` |
| History rewrite (`rebase`, `filter-branch`, hard reset) | Verify staged set is empty after commit |

Ignored automatically (never staged): `node_modules/`, `.next/`, `__pycache__/`, real `.env*`, key/pem material, caches, build outputs.

## Install / run

From the repository root (Python 3.11+):

```bash
python -m tools.git_recovery plan
python -m tools.git_recovery status
python -m tools.git_recovery recover
python -m tools.git_recovery recover --dry-run
python -m tools.git_recovery recover --no-push
```

## Commands

### `plan`

Reads:

```bash
git status --porcelain=v1 -uall
```

Classifies every path and writes `git_recovery_plan.md` (override with `--output`).

### `status`

Prints classified groups and counts without writing a plan file (still uses porcelain `-uall`).

### `recover` (interactive)

1. Writes the recovery plan.
2. For **each** group, prints purpose / files / risk / message.
3. Asks: `Commit this group? [Y/N]`
4. On **Y**:
   - `git add -- <group files only>`
   - `git commit -m "<suggested message>"`
   - `git push origin HEAD:refs/heads/<current_branch>` (unless `--no-push`)
   - prints `git status -sb`
5. On **N**: skips the group.
6. Continues until all groups are processed.
7. Reports whether the tree is clean.

## Classification groups

Configuration · CI/CD · Documentation · Legal · DevOps · Security · Authentication · Persistence · Workspace · Data Engine · Platform · API · Frontend Foundation · Frontend Authentication · Frontend Legal · Frontend Dashboard · Frontend Research · Frontend Portfolio · Frontend Admin · Frontend Other · Tests · Other · Ignored

Order is dependency-aware (e.g. Platform before API; Frontend Foundation before feature UIs).

## Tests

```bash
python -m pytest tools/git_recovery/tests -q
```

## Example plan

See [`examples/git_recovery_plan.example.md`](examples/git_recovery_plan.example.md).

## Layout

```text
tools/git_recovery/
  __init__.py
  __main__.py
  cli.py
  parser.py
  classifier.py
  planner.py
  git_ops.py
  models.py
  README.md
  examples/
  tests/
```
