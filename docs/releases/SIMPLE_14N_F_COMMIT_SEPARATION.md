# SIMPLE-14N-F — Commit Separation Forensic

## STATUS

**COMBINED COMMIT**

Safe two-commit history in the preferred order was **not** possible. A single logically correct commit is used instead of two misleading commits.

**NO PRODUCTION DEPLOYMENT**

## BASELINE SHA

`bdf4f1ed6ea4bd72b11224a026694e14f6efe6f8` (`fix/asi003-dsp-platform-boundaries`)

Safety refs (not pushed; do not discard work):

- `backup/pre-simple14nf-nse-mcp-commit` → baseline HEAD
- `refs/backup/simple14nf-nse-mcp-wip` → `git stash create` of the tracked working tree immediately before this commit

The previously staged NSE-MCP index was **not** committed. It was not a clean historical snapshot.

## COMBINED COMMIT

Message:

`SIMPLE-14N-F: universal acquisition and NSE research integration`

Preferred history was:

1. SIMPLE-14N-F planned-field acquisition
2. NSE-MCP-OPENAI adapter

That order cannot stand alone. Reverse order also cannot be a *clean* NSE-MCP commit because the already-staged shared files contained 14N-E/F hunks.

## WHY THE CHANGES COULD NOT BE SAFELY SEPARATED

### 1. Import graph (14N-F depends on NSE MCP)

`field_acquisition.py` and `test_simple14nf.py` import `NSE_MCP_COMMERCIAL_STATUS` from `nse_mcp.py`.

A SIMPLE-14N-F-first commit would fail to import. Rewriting that import solely to manufacture a commit boundary was forbidden.

### 2. Mixed files already in the staged NSE-MCP snapshot

These files were staged as NSE-MCP but their diffs vs HEAD also contain SIMPLE-14N-E/F work. They were not hunk-split because `git add -p` is interactive and unsafe here, and the hunks are interleaved with shared types:

| File | NSE-MCP hunks | SIMPLE-14N-E/F hunks |
|---|---|---|
| `models.py` | `official_nse_mcp` / `openai_nse_mcp` agent roles | `document_hash`, CA types (`acquisition`, `new_issue`, …), `ResearchRequest`/`ResearchResult` planner fields |
| `judge.py` | `openai_nse_mcp` never verifies; production MCP commercial block | `ShareCountSnapshot.source_url` / `corporate_actions_checked`; `_copy(document_hash)` |
| `source_policy.py` | `mcp.nseindia.in`, `nseindia.in` | Screener `approved_research`, `field_authority_chain`, `record_source_clash` |
| `verified_dataset.py` | none (provenance fields only) | `source_url`, `document_hash`, `semantic_type` on shares |
| `research_failures.py` | staged: MCP failure codes + `ResearchFailure` | unstaged: TRANSPORT vs DOMAIN split, `NETWORK`/`HTTP`/…, 14N-F domain codes |

`research_failures.py` *could* be split (staged = NSE-MCP, unstaged = 14N-F). The other shared files could not be split without rewriting or interactive patching. Splitting only that one file would still leave 14N-F unable to import `nse_mcp` if it were committed first, and would leave NSE-MCP tests depending on judge/model hunks that belong in the other commit.

### 3. NSE-MCP tests need the mixed judge/model/source_policy edits

`test_nse_mcp_openai.py` asserts commercial blocking on `EvidenceJudge` and MCP failure codes. Putting adapters in commit B without those shared hunks would make that commit red. Putting the shared hunks into NSE-MCP would smuggle 14N-E/F planner contracts into an “NSE-MCP only” commit.

A logically correct combined commit is better than two misleading commits.

## FILES IN EACH COMMIT

There is one commit. Classification of every included path:

### NSE_MCP_OPENAI (pure adapter)

- `packages/llm_adapters/src/llm_adapters/openai_responses.py`
- `packages/llm_adapters/tests/test_openai_responses.py`
- `packages/data_engine/src/data_engine/official_research/nse_mcp.py`
- `packages/data_engine/src/data_engine/official_research/nse_mcp_evidence.py`
- `packages/data_engine/src/data_engine/official_research/openai_nse_agent.py`
- `packages/data_engine/tests/test_nse_mcp_openai.py`
- `packages/data_engine/tests/test_nse_mcp_live.py`
- `docs/releases/NSE_MCP_OPENAI_FORENSIC_1.md`
- `docs/releases/NSE_MCP_OPENAI_2_LIVE_QUALIFICATION.md`

### SIMPLE_14N_F (planner + planned-field loop + reports)

- `packages/data_engine/src/data_engine/official_research/field_acquisition.py`
- `packages/data_engine/src/data_engine/official_research/research_plan.py`
- `packages/data_engine/src/data_engine/official_research/research_loop.py`
- `packages/data_engine/src/data_engine/official_research/provider_router.py`
- `packages/data_engine/src/data_engine/official_research/forensic_artifacts.py`
- `packages/data_engine/tests/test_simple14ne.py`
- `packages/data_engine/tests/test_simple14nf.py`
- `docs/releases/SIMPLE_14N_F_UNIVERSAL_PLANNED_FIELD_ACQUISITION.md`
- `docs/releases/SIMPLE_14N_F_COMMIT_SEPARATION.md`

### PRE-EXISTING (uncommitted 14N-D/E foundation required by the loop)

- `packages/data_engine/src/data_engine/official_research/documents.py`
- `packages/data_engine/src/data_engine/official_research/extraction.py`
- `packages/data_engine/src/data_engine/official_research/currentness.py`
- `packages/data_engine/src/data_engine/official_research/statement_tables.py`
- `packages/data_engine/src/data_engine/official_research/annual_report.py`
- `packages/data_engine/src/data_engine/official_research/orchestrator.py`
- `packages/data_engine/src/data_engine/official_research/agents.py`
- `packages/data_engine/tests/test_simple14nd.py`
- `packages/data_engine/tests/test_simple14nd_local_pdfs.py`
- `packages/data_engine/tests/test_simple14n_acquisition.py`
- `packages/data_engine/tests/test_official_research_engine.py`

### SHARED / MIXED (final working-tree versions)

- `packages/data_engine/src/data_engine/official_research/research_failures.py`
- `packages/data_engine/src/data_engine/official_research/judge.py`
- `packages/data_engine/src/data_engine/official_research/models.py`
- `packages/data_engine/src/data_engine/official_research/source_policy.py`
- `packages/data_engine/src/data_engine/official_research/verified_dataset.py`
- `packages/data_engine/src/data_engine/official_research/__init__.py`

## MIXED FILES

See table in “Why the changes could not be safely separated.”

`research_failures.py` was the only mixed file with a clean staged/unstaged split. That split was **not used**, because the remaining mixed files and the `nse_mcp` import still blocked a truthful two-commit history.

## TEST RESULTS

Run before commit (working tree):

| Suite | Result |
|---|---|
| `test_simple14ne.py` | 16 passed |
| `test_simple14nf.py` | 17 passed |
| `test_nse_mcp_openai.py` | 22 passed (mocked; no live OpenAI) |
| `test_openai_responses.py` | 5 passed |
| `test_official_research_engine.py` (EvidenceJudge) | 29 passed |
| **Total** | **89 passed** |

No live OpenAI. No live NSE MCP in this run. `test_nse_mcp_live.py` remains opt-in.

## WORKING TREE STATUS

After this combined commit, the following remain **untracked and excluded on purpose**:

- `.bytecode_backup/`
- nested `DSP-AI-Indicator/`
- `apps/web/src/components/auth/DemoModeBanner.tsx`
- `apps/web/src/lib/auth/demoAuth.ts`
- `apps/web/src/lib/auth/demoAuth.test.ts`
- `artifacts/`
- `body.txt`

No production config files are included. Test OpenAI key material is the fixture `sk-test-secret-key` used only to prove redaction.

## PRODUCTION IMPACT

**NONE. NO PRODUCTION DEPLOYMENT.**

Not changed:

- `/api/v1/analyse`
- production environment / Cloud Run
- production OpenAI activation
- production NSE MCP activation (`COMMERCIAL_USE_PENDING` remains)
- frontend production

Excluded from this commit (parking / unrelated):

- `.bytecode_backup/`
- nested `DSP-AI-Indicator/`
- `apps/web/.../demoAuth*`
- `artifacts/`
- `body.txt`
