# DSP Decision Records

| Field | Value |
|---|---|
| **Version** | `1.2.2` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-26 |
| **Audience** | Architects · leads · AI resolving conflicts |

## Purpose

**Canonical ADR index**. Narrative freezes stay in baseline/epic docs. Do not re-litigate accepted rows mid-sprint.

---

## 1. How to add an ADR

1. **STOP** — no mid-sprint redesign ([ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md)).  
2. Add a row below **or** create `docs/adr/ADR-XXXX-title.md` (prefer folder for long ADRs).  
3. Link from this index.  
4. Escalate if a new epic is required.  
5. Superseded ADRs → mark **Deprecated**; full obsolete files → [archive/](archive/) per lifecycle (Master Protocol §9).

Template (short):

```markdown
# ADR-XXXX Title
Status: Proposed | Accepted | Superseded
Context: …
Decision: …
Consequences: …
```

**ASI / enterprise ADRs:** use the full template → [asi/ADR_TEMPLATE.md](asi/ADR_TEMPLATE.md) (Context, Evidence, Options, Migration, Risks, Rollback, …).

---

## 2. Standing decisions (accepted)

| ID | Decision | See |
|---|---|---|
| **ADR-0001** | Thin web client — no investment math in browser | Governance |
| **ADR-0002** | Research Mode is default product mode | PR1.0 · `compliance` |
| **ADR-0003** | `dsp_platform` is composition façade; domains must not import it | Baseline |
| **ADR-0004** | Security wraps API, not domain façade | Architecture Overview |
| **ADR-0005** | Single ownership; cite don’t embed | Baseline §2 |
| **ADR-0006** | Unavailable > fabricated consensus / prices | Trust Standard · elevated by **ADR-CV-001** |
| **ADR-0007** | Feature flags gate recommendation / SEBI-style labels | PR1.0 |
| **ADR-0008** | Copilot is explainability assistant, not autonomous recommender | L1.2 Sprint 6 |
| **ADR-0009** | Presentation KG / reports / workspace may use localStorage; must disclose | L1.2 Sprint 7–8 |
| **ADR-0010** | Mid-implementation redesign forbidden; ADR + epic | Governance |
| **ADR-0011** | Product Constitution priority order is mandatory | Constitution |
| **ADR-0012** | Backend RC `v1.0.0-rc1` is client contract until next RC | VERSION_MATRIX |
| **ADR-0013** | DSP Docs Suite is the default AI load path; archive is opt-in | Master Protocol v1.1 |
| **ADR-0014** | Every sprint declares exactly one scope class | Master Protocol §5 |
| **ADR-0015** | Protected production modules require explicit user override to edit | STATUS §Protected · [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) |
| **ADR-0016** | GREEN = Build + Tests + Architecture + Public APIs + Determinism + Docs | Coding Standards §Regression |
| **ADR-0017** | Project Protection Framework is permanent; recoverability > rewrite | [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) |
| **ADR-0018** | Change approval levels: Documentation · Presentation · Domain · Architecture · Breaking | Protection §9 |
| **ADR-0019** | STATUS must always track Project Health dashboard (version · sprint · modules · regression · health · checkpoint) | STATUS §0 · Protection §10 |
| **ADR-0020** | PROJECT PROTECTION RULE is mandatory before any sprint; integrity > features | Protection §0 · Master Protocol · AI Collaboration |
| **ADR-ASI-002-001** | Living version truth: API RC `v1.0.0-rc1` ≠ domain milestone tags | [adr/ADR-ASI-002-001-living-version-truth.md](adr/ADR-ASI-002-001-living-version-truth.md) |
| **ADR-ASI-002-002** | Defer registration of empty `data-ingestion` orphan | [adr/ADR-ASI-002-002-orphan-data-ingestion.md](adr/ADR-ASI-002-002-orphan-data-ingestion.md) |
| **ADR-ASI-002-003** | Register `economic_moat` scaffold; no F4 analytics | [adr/ADR-ASI-002-003-register-economic-moat.md](adr/ADR-ASI-002-003-register-economic-moat.md) |
| **ADR-ASI-003-001** | Keep BQ↔FA duck typing; do not force `financial` import | [adr/ADR-ASI-003-001-business-quality-financial-duck-typing.md](adr/ADR-ASI-003-001-business-quality-financial-duck-typing.md) |
| **ADR-ASI-003-002** | Evidence-based architecture allowlists + cycle guard | [adr/ADR-ASI-003-002-architecture-allowlists.md](adr/ADR-ASI-003-002-architecture-allowlists.md) |
| **ADR-ASI-004-001** | Thin local pyprojects for former root-owned packages | [adr/ADR-ASI-004-001-thin-package-pyprojects.md](adr/ADR-ASI-004-001-thin-package-pyprojects.md) |
| **ADR-ASI-004-002** | Remove unused `core` dep from `compliance` | [adr/ADR-ASI-004-002-compliance-empty-deps.md](adr/ADR-ASI-004-002-compliance-empty-deps.md) |
| **ADR-ASI-005-001** | Standard 12-section README card (+ appendix for long docs) | [adr/ADR-ASI-005-001-readme-standard-card.md](adr/ADR-ASI-005-001-readme-standard-card.md) |
| **ADR-ASI-006-001** | Monorepo façade smoke over duplicate public_api files | [adr/ADR-ASI-006-001-monorepo-smoke-over-duplicate-api-tests.md](adr/ADR-ASI-006-001-monorepo-smoke-over-duplicate-api-tests.md) |
| **ADR-ASI-007-001** | Blocking monorepo CI gates (integrity/arch/smoke/full) | [adr/ADR-ASI-007-001-monorepo-ci-quality-gates.md](adr/ADR-ASI-007-001-monorepo-ci-quality-gates.md) |
| **ADR-REP-001-001** | Release packaging excludes caches/VMs/IDE/temp; remove empty compose; no invented infra | [REP_001_REPOSITORY_CLEANUP.md](REP_001_REPOSITORY_CLEANUP.md) · [RELEASE_ENGINEERING.md](RELEASE_ENGINEERING.md) |
| **ADR-FEATURE-001-001** | Unlock `economic_moat` Phase 1 analytics in-package; do not wire `dsp_platform` yet | [adr/ADR-FEATURE-001-001-economic-moat-core.md](adr/ADR-FEATURE-001-001-economic-moat-core.md) |
| **ADR-FEATURE-002-001** | Introduce `management_quality` Phase 1; package-only; defer platform composition | [adr/ADR-FEATURE-002-001-management-quality-core.md](adr/ADR-FEATURE-002-001-management-quality-core.md) |
| **ADR-FEATURE-003-001** | Introduce `financial_strength` Phase 1; package-only; defer platform composition | [adr/ADR-FEATURE-003-001-financial-strength-core.md](adr/ADR-FEATURE-003-001-financial-strength-core.md) |
| **ADR-FEATURE-004-001** | Introduce `earnings_quality` Phase 1; distinct from BQ F3.2; defer platform composition | [adr/ADR-FEATURE-004-001-earnings-quality-core.md](adr/ADR-FEATURE-004-001-earnings-quality-core.md) |
| **ADR-FEATURE-005-001** | Introduce `growth_quality` Phase 1; Buffett-aligned reinvestment; defer platform composition | [adr/ADR-FEATURE-005-001-growth-quality-core.md](adr/ADR-FEATURE-005-001-growth-quality-core.md) |
| **ADR-FEATURE-006-001** | Introduce `business_quality_aggregator` Phase 1; distinct from F3.7; defer platform composition | [adr/ADR-FEATURE-006-001-business-quality-aggregator.md](adr/ADR-FEATURE-006-001-business-quality-aggregator.md) |
| **ADR-FEATURE-007-001** | Introduce `investment_recommendation` Phase 1; MoS-gated; distinct from G1.3; defer platform composition | [adr/ADR-FEATURE-007-001-investment-recommendation.md](adr/ADR-FEATURE-007-001-investment-recommendation.md) |
| **ADR-FEATURE-008-001** | Introduce `investment_committee` Phase 1; deterministic reviewers; distinct from frozen ai_committee; defer platform composition | [adr/ADR-FEATURE-008-001-investment-committee.md](adr/ADR-FEATURE-008-001-investment-committee.md) |
| **ADR-EPIC-001-001** | Compose FEATURE packages into `dsp_platform` orchestration pipeline; no `/api/v1` / scoring changes | [adr/ADR-EPIC-001-001-platform-composition.md](adr/ADR-EPIC-001-001-platform-composition.md) |
| **ADR-EPIC-002-001** | Expose composition via `/api/v1` DTOs over `dsp_platform` only; no engine changes | [adr/ADR-EPIC-002-001-api-composition.md](adr/ADR-EPIC-002-001-api-composition.md) |
| **ADR-EPIC-003-001** | Intelligence Workspace over `/api/v1` only; no backend package imports | [adr/ADR-EPIC-003-001-intelligence-workspace.md](adr/ADR-EPIC-003-001-intelligence-workspace.md) |
| **ADR-CV-001** | **Data Authenticity First** — permanent core value; fabricated numbers fail architecture review | [adr/ADR-CV-001-data-authenticity-first.md](adr/ADR-CV-001-data-authenticity-first.md) · [CORE_VALUES.md](CORE_VALUES.md) |
| **ADR-CV-002-010** | Tier-0 Core Values CV-002…CV-010 — constitutional; violation fails all gates | [adr/ADR-CV-002-010-tier0-core-values.md](adr/ADR-CV-002-010-tier0-core-values.md) · [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md) |
| **ADR-RS-001** | Research Standards RS-001…RS-010 — minimum report content; missing section = FAIL | [adr/ADR-RS-001-research-standards.md](adr/ADR-RS-001-research-standards.md) · [RESEARCH_STANDARDS.md](RESEARCH_STANDARDS.md) |

---

## 3. Supersessions

| Old | New | Notes |
|---|---|---|
| Ad-hoc “indicator library only” | Institutional research platform | Historical essay |
| Client-side “engines” | Presentation builders only | ADR-0001 |
| Docs Suite v1.0 load order (Architecture before Status) | v1.1: P1 Protocol → P2 Status → P3 Architecture → P4 Roadmap | ADR-0013 |

---

## 4. Open questions (do not invent in sprints)

| Topic | Status |
|---|---|
| Cloud sync / accounts | Deferred — Infrastructure epic |
| Server-side PDF/DOCX | Deferred — placeholders OK |
| Live LLM proxy for Copilot | Deferred — no invented numbers |
| Mobile client | Future |

---

## 5. Related

[DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_STATUS.md](DSP_STATUS.md) · [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md)
