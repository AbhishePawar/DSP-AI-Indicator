# DSP AI Indicator — Cleanup Preservation Baseline

**Date:** 2026-09-03  
**Record type:** forensic preservation only  
**This document does not authorize deletion, refactor, stash, reset, commit, or push.**

No secrets, tokens, credentials, or private keys are recorded here.

Production path for this record:

```
GitHub → Google Cloud Build → Google Cloud Run
```

Frontend: Rocket / Next.js (`apps/web`). Application persistence: Supabase (optional). Financial authority: DSP backend + approved providers. AI: provider-neutral; production fail-closed.

---

## 1. Git branch / HEAD

| Ref | Value |
|---|---|
| Current branch | `fix/prod-upstox-secret-mount` |
| HEAD | `16c407e82b15db9ed6ee27488cfa9e483aad6ea3` |
| HEAD subject | `feat(web): persist user app data in Supabase without moving DSP intelligence` |
| Working-tree vs HEAD | Dirty (8 modified tracked, 23 untracked, 0 deleted, 0 staged) |

HEAD equals `origin/fix/prod-upstox-secret-mount`. The six commits on this branch that are not on `origin/main` **are** present on that remote branch.

## 2. Main HEAD

| Ref | Value |
|---|---|
| `origin/main` | `7460c176f2411eaedae30bc5177ee57b39cac468` |
| Subject | `feat(research): wire canonical six-moat dimensions into Research UI` |

Related remotes (not modified by this record):

| Ref | SHA | Subject |
|---|---|---|
| `origin/fix/prod-upstox-secret-mount` | `16c407e82b15db9ed6ee27488cfa9e483aad6ea3` | same as current HEAD |
| `origin/rocket/research-ui-refinement` | `762761c60408d023954be57702ca0a6c1ec10790` | recover Rocket institutional UI refinements |
| `origin/cursor/canonical-research-ai-port` | `9a68ca12ecaa38f8220fde47857d9996a21d58de` | provider-neutral canonical research AI port |

Commits on current HEAD that are **not** on `origin/main`:

| SHA | Subject |
|---|---|
| `16c407e` | persist user app data in Supabase without moving DSP intelligence |
| `163712a` | add validated external evidence and test-only AI seam (B1 + CanonicalResearchAiPort) |
| `d37b66e` | add ShareCountPort and fail closed without current outstanding |
| `eb95a0b` | honest DSP User-Agent on urllib requests |
| `a692b9b` | align Upstox instrument search with exchange |
| `857ccd3` | mount Upstox analytics token in production |

No tags matching `backup`, `audit`, `baseline`, `share`, or `evidence` exist.

## 3. Working-tree status

`git status --short` at capture time:

```
 M packages/api_platform/src/api_platform/api/dependencies.py
 M packages/api_platform/src/api_platform/api/routers/copilot.py
 M packages/api_platform/tests/test_architecture.py
 M packages/api_platform/tests/test_copilot_api.py
 M packages/api_platform/tests/test_copilot_v2_api.py
 M packages/data_engine/src/data_engine/__init__.py
 M packages/data_engine/src/data_engine/share_count/__init__.py
 M packages/llm_adapters/src/llm_adapters/activation_evidence.py
?? artifacts/
?? packages/api_platform/tests/test_copilot_activation_boundary.py
?? packages/data_engine/src/data_engine/share_count/acceptance.py
?? packages/data_engine/tests/test_share_count_acceptance.py
?? packages/dsp_platform/src/dsp_platform/external_evidence_discovery/
?? packages/dsp_platform/src/dsp_platform/primary_source_retrieval/
?? packages/dsp_platform/src/dsp_platform/share_count_evidence.py
?? packages/dsp_platform/tests/fixtures/
?? packages/dsp_platform/tests/test_external_evidence_discovery.py
?? packages/dsp_platform/tests/test_external_evidence_discovery_architecture.py
?? packages/dsp_platform/tests/test_primary_source_retrieval.py
?? packages/dsp_platform/tests/test_primary_source_retrieval_architecture.py
?? packages/dsp_platform/tests/test_share_count_evidence.py
?? packages/dsp_platform/tests/test_share_count_evidence_architecture.py
```

Counts:

- Modified tracked: **8**
- Untracked files: **23**
- Deleted tracked: **0**
- Staged: **0**

`git diff --stat` vs HEAD: **8 files changed, 167 insertions, 29 deletions.**

## 4. Modified files

| Path | Status | Classification | Purpose |
|---|---|---|---|
| `packages/api_platform/src/api_platform/api/dependencies.py` | tracked modified | A / B | Copilot live-AI HTTP gate: `require_live_ai_activation` + `ApiState.activation_evidence` |
| `packages/api_platform/src/api_platform/api/routers/copilot.py` | tracked modified | A / B | `POST /copilot/complete` and `/copilot/stream` depend on that gate |
| `packages/llm_adapters/src/llm_adapters/activation_evidence.py` | tracked modified | A / B | `ActivationEvidence.missing()` fail-closed empty bundle |
| `packages/api_platform/tests/test_architecture.py` | tracked modified | D | Architecture assertion that copilot live routes require the gate |
| `packages/api_platform/tests/test_copilot_api.py` | tracked modified | D | Default complete/stream now 401/503 without activation |
| `packages/api_platform/tests/test_copilot_v2_api.py` | tracked modified | D | complete/stream unauthenticated → 401 |
| `packages/data_engine/src/data_engine/__init__.py` | tracked modified | A / B | Re-exports B4 acceptance symbols |
| `packages/data_engine/src/data_engine/share_count/__init__.py` | tracked modified | A / B | Exports `accept_current_outstanding_claims` and related B4 types |

All eight **must survive cleanup**.

## 5. Untracked files

### Source / tests (must survive)

| Path | Classification | Purpose |
|---|---|---|
| `packages/data_engine/src/data_engine/share_count/acceptance.py` | A / B | B4 CURRENT_OUTSTANDING claim acceptance |
| `packages/data_engine/tests/test_share_count_acceptance.py` | D | B4 tests |
| `packages/dsp_platform/src/dsp_platform/share_count_evidence.py` | A / B | B4 mapping: ValidatedExternalEvidencePackage → ShareCountSnapshot |
| `packages/dsp_platform/tests/test_share_count_evidence.py` | D | B4 mapping tests |
| `packages/dsp_platform/tests/test_share_count_evidence_architecture.py` | D | B4 architecture bans |
| `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/__init__.py` | B / C | B5 package |
| `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/models.py` | B / C | B5 models |
| `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/port.py` | B / C | B5 ExternalEvidenceDiscoveryPort |
| `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/testing.py` | D | B5 test-only discovery |
| `packages/dsp_platform/tests/test_external_evidence_discovery.py` | D | B5 tests |
| `packages/dsp_platform/tests/test_external_evidence_discovery_architecture.py` | D | B5 architecture bans |
| `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/__init__.py` | B / C | B6 package |
| `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/extraction.py` | B / C | B6 local fixture extraction |
| `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/models.py` | B / C | B6 models |
| `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/port.py` | B / C | B6 PrimarySourceDocumentRetrievalPort |
| `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/testing.py` | D | B6 local test retrieval |
| `packages/dsp_platform/tests/test_primary_source_retrieval.py` | D | B6 tests |
| `packages/dsp_platform/tests/test_primary_source_retrieval_architecture.py` | D | B6 architecture bans |
| `packages/dsp_platform/tests/fixtures/primary_sources/DSPX-FY24-note12-outstanding.txt` | D | B6 local fixture (not production retrieval) |
| `packages/api_platform/tests/test_copilot_activation_boundary.py` | D | Copilot activation-gate tests |

### Generated artifacts (do not delete in this phase)

| Path | Classification | Purpose |
|---|---|---|
| `artifacts/p109_critical_investment_evidence.json` | E | P109 evidence dump |
| `artifacts/p110_authenticity_hard_fail_evidence.json` | E | P110 evidence dump |
| `artifacts/rc1_hard_release_gate.json` | E | RC1 gate dump |

## 6. Classification of uncommitted work

Legend: **A** production-critical · **B** canonical architecture · **C** valuable feature · **D** test-only · **E** generated artifact · **F** unknown.

### Named workstreams

| Workstream | Location | In Git? | Classification | Must survive cleanup? |
|---|---|---|---|---|
| ShareCountPort (port, snapshot, Null adapter, fail-closed `/analyse`) | `packages/data_engine/src/data_engine/share_count/` (except `acceptance.py`) | **Yes** — commit `d37b66e` on this branch and `origin/fix/prod-upstox-secret-mount`. **Not** on `origin/main`. | A / B | YES |
| ShareCount `__init__` + `data_engine.__init__` B4 exports | modified tracked files above | **Working tree only** (diff vs HEAD) | A / B | YES |
| B1 ValidatedExternalEvidencePackage | `packages/dsp_platform/src/dsp_platform/external_evidence/` | **Yes** — `163712a`. Not on `origin/main`. | A / B | YES |
| B4 share-count evidence acceptance | `acceptance.py`, `share_count_evidence.py`, related tests | **Working tree only** | A / B | YES |
| B5 ExternalEvidenceDiscoveryPort | `external_evidence_discovery/` + tests | **Working tree only** | B / C | YES |
| B6 PrimarySourceDocumentRetrievalPort | `primary_source_retrieval/` + fixture + tests | **Working tree only** | B / C | YES |
| B7 source registry | — | **Not present** as implementation. Unrelated “B7” string in `docs/audit/COMMERCIAL_GA_CHECKLIST.md` is a commercial packaging row, not evidence-source registry. | F / absent | N/A |
| Canonical research AI | `canonical_research_ai/`, research_package, prompt, validation, assembly, `/research/company` stub | **Yes** on this branch (`163712a` + earlier research commits). CanonicalResearchAiPort **not** on `origin/main`. `/research/company` **is** on `origin/main`. | A / B | YES |
| Supabase app persistence | `supabase/`, `apps/web/src/lib/supabase/`, `/api/app/*` | **Yes** — `16c407e` on this branch and `origin/fix/prod-upstox-secret-mount`. **Not** on `origin/main`. | C (app infra, not financial authority) | YES |
| Copilot activation gate | dependencies, copilot router, activation_evidence.missing, tests | **Working tree only** | A / B | YES |
| Upstox production mount / UA / search | prior commits `857ccd3`, `a692b9b`, `eb95a0b` | **Yes** on this branch remote. **Not** on `origin/main`. | A | YES |
| `artifacts/*.json` | untracked | Working tree only | E | Preserve this phase; do not treat as source |

### Dependency relationships (uncommitted)

```
B1 ValidatedExternalEvidencePackage (committed 163712a)
  → B4 share_count_evidence.py (untracked)
      → data_engine.share_count.acceptance (untracked)
          → share_count/__init__.py + data_engine/__init__.py (modified tracked)

B5 discovery port (untracked) emits candidate records for B1
B6 retrieval port (untracked) supplies local documents for discovery/extraction
  B5 and B6 must not import ShareCountPort / valuation / CanonicalResearchAiPort
  (enforced by untracked architecture tests)

Copilot gate (modified tracked + untracked test):
  copilot.py → require_live_ai_activation → evaluate_activation
  → ActivationEvidence.missing() when ApiState.activation_evidence is None
```

## 7. Current architecture baseline

Intended invariant:

**DSP CALCULATES. AI RESEARCHES / INTERPRETS. DSP VALIDATES. CLIENT SEES ONLY VALIDATED REPORT.**

Runtime today:

```
Browser (apps/web, thin client)
  → DSP Auth
  → POST /api/v1/analyse          (compose_intelligence; ShareCount Null → fail closed)
  → POST /api/v1/research/company (503 AI_EXECUTION_BLOCKED; not executing AI)
  → POST /api/v1/copilot/complete|stream
        now: auth → evaluate_activation → BLOCKED by default (uncommitted gate)
```

Canonical research library path exists (ResearchPackage → prompt → CanonicalResearchAiPort → validate → assemble) and is **not** wired to production HTTP. Production adapter is blocked.

Duplicate historical systems remain in the repository (legacy `/analyze/company`, `ResearchOrchestrator`, `packages/research`, Helm/K8s, advisor demo). They are **cleanup candidates for a later phase**, not deletions in this record.

## 8. Current production path

**GitHub → Google Cloud Build → Google Cloud Run.**

Canonical files: `cloudbuild.yaml`, `cloudbuild-frontend.yaml`, `docker/backend/Dockerfile`, `docker/frontend/Dockerfile`.

Not production: Vercel (no `vercel.json`), Helm/K8s, docker-compose “production” stacks.

## 9. Current known AI activation state

| Item | State |
|---|---|
| Canonical `/api/v1/research/company` | 503 `AI_EXECUTION_BLOCKED` (committed) |
| `evaluate_activation` | Existing fail-closed guard in `llm_adapters` |
| Copilot `/complete` and `/stream` | **Uncommitted** HTTP gate: unauthenticated 401; missing evidence 503; no provider `invoke` until READY |
| Production evidence bundle | **Not wired** at `create_app`; default is `ActivationEvidence.missing()` → BLOCKED |
| Live LLM adapters | Exist (OpenAI, Anthropic, Gemini, DeepSeek); must not run on those two routes unless READY |
| Perplexity | No adapter |
| Frontend `lib/ai` factory | Present; out of scope for this record |

## 10. Current ShareCount state

| Item | State |
|---|---|
| ShareCountPort / Snapshot / Null adapter | Committed on this branch (`d37b66e`); production Null |
| `/analyse` without CURRENT_OUTSTANDING | Fail closed (committed) |
| CURRENT_OUTSTANDING ≠ WEIGHTED_AVERAGE_SHARES | Enforced in committed B1 models and uncommitted B4 |
| B4 acceptance | **Uncommitted only** |
| Quote `shares_outstanding` | Must not be ShareCount authority |

## 11. Current Upstox state

Committed on this branch, not on `origin/main`: analytics-token mount (`857ccd3`), instrument search alignment (`a692b9b`), honest User-Agent (`eb95a0b`). Production selector `DSP_INVESTMENT_DATA_PROVIDER=upstox` uses Upstox for quote + statements. ShareCount is **not** Upstox.

No Upstox source files are dirty in this working tree.

## 12. Current Supabase state

Committed on this branch (`16c407e`): schema/RLS migration, Next.js BFF `/api/app/*`, PersistenceProvider sync, localStorage fallback. DSP Auth is **not** replaced. Financial calculation does not live in Supabase. Live project apply / env is outside this record (no secrets recorded).

No Supabase files are dirty in this working tree.

## 13. Current frontend / Rocket state

`apps/web` is the Rocket / Next.js client. `origin/rocket/research-ui-refinement` at `762761c` is a related remote; it is **not** the current branch. No frontend files are dirty in this working tree. Thin-client rule remains: no valuation/recommendation/AI reasoning in the browser.

## 14. Known cleanup candidates

**Inventory only. Do not delete in this phase.**

- README-only `packages/data-ingestion/`
- Nested `tools/audit-package/` duplicate tree
- Untracked `artifacts/*.json` (after workflows can regenerate)
- Twelve identical `origin/cloud-run-*` remotes at `e39fc8e` (2026-07-28)
- Helm/K8s and compose-as-production docs/files vs Cloud Run
- Legacy `/analyze/company`, `packages/research` synthesizer, `ResearchOrchestrator` as research HTTP
- Large historical `docs/` EPIC freeze set; advisor demo routes
- `.bytecode_backup` gitignore exception (directory absent)

## 15. Explicit DO-NOT-DELETE list

Do **not** delete or `git clean` any of the following:

1. Entire uncommitted B4/B5/B6 tree listed in sections 4–5 (except that artifacts may be regenerated later — still keep this phase).
2. Copilot activation-gate modifications and `test_copilot_activation_boundary.py`.
3. Committed ShareCountPort, Null adapter, fail-closed analyse path (`d37b66e`).
4. Committed B1 `external_evidence/` (`163712a`).
5. Committed CanonicalResearchAiPort, research_package, prompt, validation, assembly, `/research/company` stub.
6. Committed Supabase persistence (`16c407e`).
7. Committed Upstox mount / UA / search commits on this branch.
8. `packages/data_engine`, `dsp_platform` compose, `api_platform` `/analyse`, `auth`, `security_platform`, valuation and quality engines used by compose.
9. `llm_adapters.activation_guard` and provider adapters (path may change later; adapters stay).
10. Architecture tests (`*_architecture.py`), P109/P110 authenticity tests.
11. `cloudbuild.yaml`, Cloud Run Dockerfiles.
12. Distinction CURRENT_OUTSTANDING vs WEIGHTED_AVERAGE_SHARES.
13. DSP Auth (do not replace with Supabase Auth).
14. Historical git branches (cloud-run, cursor, rocket, backup, fix). Branch deletion is a later task.
15. This file: `docs/audits/2026-09-03-cleanup-baseline.md`.

---

## SHA-256 of valuable uncommitted source files

Hashes are SHA-256 of file bytes as they existed on disk at capture (Windows `Get-FileHash`). Line endings were not altered.

### Modified tracked

| SHA-256 | Path |
|---|---|
| `ef78275abcdc7fd5cc027ac170c200a55d27a7b44d3c4e72b06d0d9f3b7e1489` | `packages/api_platform/src/api_platform/api/dependencies.py` |
| `52ffef66c4e976a958c62720b70e58e371af733e10206f529d40782e132b01ad` | `packages/api_platform/src/api_platform/api/routers/copilot.py` |
| `63a72ec0ead19fcb1be25424badc393d9a941e2cdeccf971f3d19d7a4db977f4` | `packages/api_platform/tests/test_architecture.py` |
| `4d8a5081a69a0273c7e88d4021b98f8d286111e2826775091b3b429bb3e19755` | `packages/api_platform/tests/test_copilot_api.py` |
| `67612ec42234d75868e9ad3cf4848b40e2e9c2da65aba401473eb22871e93716` | `packages/api_platform/tests/test_copilot_v2_api.py` |
| `d6876e5239564d3bfb1f89042e03f16e9ed41df8bf78628356966e8acbe0d2b2` | `packages/llm_adapters/src/llm_adapters/activation_evidence.py` |
| `6949aa560af7c5a1212bb4acd64a056e6fea25acaaaa9ad30c2e5018771a9816` | `packages/data_engine/src/data_engine/__init__.py` |
| `3dd36d424669070c460559ea6984d745c17a3d67763c3218339b0513a66a9a96` | `packages/data_engine/src/data_engine/share_count/__init__.py` |

### Untracked source and tests

| SHA-256 | Path |
|---|---|
| `15c870be1a04c69fecc0eecacfb4aa546e3db4bc2cdf4fb91d880cfffe84fa5d` | `packages/api_platform/tests/test_copilot_activation_boundary.py` |
| `4761d256423aed1bdd5227e21586e1955081fd28c04a61fcd59b7eb67fe06af1` | `packages/data_engine/src/data_engine/share_count/acceptance.py` |
| `ff429509363ef80b181031b668aff70cd018758f0560ca423b1ce74e9e7aadaa` | `packages/data_engine/tests/test_share_count_acceptance.py` |
| `5d58b92ea8327adb8655f8f0a6b6ac6f3ac2f9f401abb24f2d41b9cf611613e3` | `packages/dsp_platform/src/dsp_platform/share_count_evidence.py` |
| `4141ccd70f1771622aeffa7de706b1e1697eb719407f362efae50eff8dc46588` | `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/__init__.py` |
| `28ac99585f1f0c84dc3eaabdfe07d7b3f8c30a37537f11994ffb67471b75cf56` | `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/models.py` |
| `65bd3a87709aed18507b8927d3e4b9e5a25ec45f035cc0327dcf54461f329280` | `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/port.py` |
| `a408b1fbfb51263f708f429fc5d2e109ee01f30ea8f1c76a45e31f9b4a9e3655` | `packages/dsp_platform/src/dsp_platform/external_evidence_discovery/testing.py` |
| `2adfeb49c0815034b0a077dd52c5d5c268347fb192da53e91c759210e9fe1b59` | `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/__init__.py` |
| `d8517ea842dce2a968f38b1bc64082175d1e9f8703387fcd77d16106285bf53f` | `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/extraction.py` |
| `4b4a7d1d4ec8279fbe65854a3960a858cc0107ffd88bef17120e9caef16ff9ed` | `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/models.py` |
| `e1c6c89234fdfa57305631e5f0493aa9a58539b6ad77f813852d3c6a8ed4d060` | `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/port.py` |
| `f916e4f1f40a7b78886cec89a244f6226b214e5dc376c366d3141a9d364cbf27` | `packages/dsp_platform/src/dsp_platform/primary_source_retrieval/testing.py` |
| `b0aa7b9447f259874424e65d23d9b233de286e3a7593f578a3b62387ed4c2a4f` | `packages/dsp_platform/tests/fixtures/primary_sources/DSPX-FY24-note12-outstanding.txt` |
| `04fde3ff42b5a321c0d418130f72ec5dfb77d5302f087bac11812ed3593c5a00` | `packages/dsp_platform/tests/test_external_evidence_discovery.py` |
| `b2f5246b5d4edcc8ff224a11901e346e1f8a94d9555fb3563765f42696f6342f` | `packages/dsp_platform/tests/test_external_evidence_discovery_architecture.py` |
| `f745f5f4886fe19d5d3bde5b141b3ee02f997b2fc01fea925addbf60838b31f1` | `packages/dsp_platform/tests/test_primary_source_retrieval.py` |
| `1566008942cb58242955c197b36b84f3756b143cb48db912846c39174e4e43d4` | `packages/dsp_platform/tests/test_primary_source_retrieval_architecture.py` |
| `42ca70eced7af5b009ad319bfa02bd0c1233eea1df0ded1ed586238963581ad5` | `packages/dsp_platform/tests/test_share_count_evidence.py` |
| `ab6f0d1d356768243ccb68fa68a1ac19fb62c32763282523fa4d8e05d6aa5571` | `packages/dsp_platform/tests/test_share_count_evidence_architecture.py` |

### Untracked generated artifacts (preserved this phase)

| SHA-256 | Path |
|---|---|
| `8498d9e15827fdbb3a26c1022e5a4bc6314860f49316709f36f71c746b21f82f` | `artifacts/p109_critical_investment_evidence.json` |
| `4c3960c6dcae62a7983adb899c3bd28ff44f520470d0fa15aba24d2e5eeba37d` | `artifacts/p110_authenticity_hard_fail_evidence.json` |
| `f74f5bc8bd4ff737ea1e298d0d1212998366799e91586099592afd7b3e9e7487` | `artifacts/rc1_hard_release_gate.json` |

---

## Recoverable Git vs working-tree-only (no merge performed)

| Work | Already in Git | Working tree only | Other branch |
|---|---|---|---|
| ShareCountPort + fail-closed analyse | `d37b66e` on this branch / `origin/fix/prod-upstox-secret-mount` | `__init__` export edits only | Not on `origin/main` |
| B1 external evidence package | `163712a` same remotes | — | Not on `origin/main` |
| CanonicalResearchAiPort | `163712a` (this branch). Earlier related work on `origin/cursor/canonical-research-ai-port` (`9a68ca1`) | — | Cursor branch is an older related snapshot; not a substitute for HEAD + B1 |
| `/research/company` blocked stub | On `origin/main` and this branch | — | — |
| Supabase persistence | `16c407e` this branch remote | — | Not on `origin/main` |
| Upstox mount / UA / search | `857ccd3` `a692b9b` `eb95a0b` this branch remote | — | Not on `origin/main` |
| B4 / B5 / B6 | **No committed ancestor** | Entire trees | Not found on `origin/main`, rocket, or cursor remotes checked |
| Copilot activation HTTP gate | **No** (`require_live_ai_activation` absent from HEAD) | All of it | — |
| `artifacts/*.json` | No | Yes | — |
| Rocket UI refinements | `origin/rocket/research-ui-refinement` | Not dirty here | Separate branch |

**Preservation risk:** B4/B5/B6 and the copilot activation gate exist **only in the working tree**. A `git clean`, `git reset --hard`, stash drop, or branch checkout would destroy them. They are not on `origin/main`. Committed-but-not-on-main work is recoverable from `origin/fix/prod-upstox-secret-mount` at `16c407e`.

No stash, reset, checkout, commit, or push was performed to create this record.
