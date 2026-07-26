# DSP Master Protocol

| Field | Value |
|---|---|
| **Version** | `1.2.1` |
| **Status** | **Stable** |
| **Last updated** | 2026-07-23 |
| **Suite** | DSP Docs Suite |
| **Audience** | Humans · Cursor · ChatGPT · maintainers |

## Purpose

**Canonical entry document** for how DSP work is done. Every AI session starts here. Specialized topics live in sibling `DSP_*.md` files — this file indexes them; it does not restate them.

**Project integrity has higher priority than feature development.**

### PROJECT PROTECTION RULE (before any sprint)

1. Read **this file** (Master Protocol).  
2. Read [DSP_STATUS.md](DSP_STATUS.md).  
3. Verify sprint scope.  
4. Verify protected modules.  
5. Refuse to modify production-certified modules unless explicitly unlocked.  
6. Create or recommend a checkpoint before major architectural work.

Full framework → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) §0.

---

## 1. What DSP is

**DSP AI Indicator** = Explainable AI Investment Research Platform — **not** a stock-tip service.

- Tagline: *Complex Analysis. Simple Decisions.*
- Primary product feature: **User Trust** → [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md)
- Conflict order → [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md)
- Done criteria → [IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md)

---

## 2. AI documentation load order (mandatory)

| Priority | Document | Default? |
|---|---|---|
| **P1** | [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) (**this file**) | **Always** |
| **P2** | [DSP_STATUS.md](DSP_STATUS.md) | **Always** |
| **P3** | [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) | Structural / package / API work |
| **P4** | [DSP_ROADMAP.md](DSP_ROADMAP.md) | Planning / epic sequencing only |
| **P5** | Everything else | **Only when required** |

**P5 on demand**

| Need | Load |
|---|---|
| **Project protection / recovery / Git / backups** | [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) — **before any implementation** |
| Agent rules / safety checklist | [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md) |
| Coding rules / GREEN definition | [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) |
| ADR / conflict | [DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md) · ASI ADRs use [asi/ADR_TEMPLATE.md](asi/ADR_TEMPLATE.md) |
| Terms | [DSP_GLOSSARY.md](DSP_GLOSSARY.md) |
| Paths | [DSP_FOLDER_STRUCTURE.md](DSP_FOLDER_STRUCTURE.md) |
| Release pointers | [DSP_CHANGELOG.md](DSP_CHANGELOG.md) |
| One sprint/epic brief | `docs/<EPIC>_SPRINT*.md` |
| **Architecture Stabilization (ASI)** | [ASI_COMPLETION_SUMMARY.md](ASI_COMPLETION_SUMMARY.md) · [ASI_ARCHITECTURE_STABILIZATION_CERTIFICATE.md](ASI_ARCHITECTURE_STABILIZATION_CERTIFICATE.md) · [ASI_IMPLEMENTATION_FRAMEWORK.md](ASI_IMPLEMENTATION_FRAMEWORK.md) · [CI.md](CI.md) |
| UX freezes | PR1.0 / PR1.1 / PR1.2 — **search a section**, never paste whole files |
| Package versions | [VERSION_MATRIX.md](VERSION_MATRIX.md) |
| Historical specs | [archive/](archive/) — **never** unless user asks |

Product/UX freeze authority: [ARCHITECTURE_GOVERNANCE.md](ARCHITECTURE_GOVERNANCE.md).

---

## 3. AI context priority (classes)

| Class | Meaning | Examples |
|---|---|---|
| **Critical** | Always in default load | This file · STATUS |
| **High** | Load when implementing or recovering | [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) · ARCHITECTURE · CODING_STANDARDS · AI_COLLABORATION · active sprint brief |
| **Medium** | Load for planning / naming / navigation | ROADMAP · GLOSSARY · FOLDER_STRUCTURE · DECISION_RECORDS |
| **Low** | Rare; specific answers only | CHANGELOG index · VERSION_MATRIX · single PR1 section |
| **Historical** | Explicit request only | `docs/archive/**` · long superseded specs (e.g. full legacy architecture essay) |

---

## 4. Non-negotiable invariants

1. Evidence-first outputs (source · confidence · methodology · limitations).  
2. Clean Architecture — domain independent of UI / HTTP / vendors.  
3. Single ownership of durable artifacts.  
4. Thin client — `apps/web` has **no** investment math.  
5. Deterministic engines (labels may remap; numbers must not invent).  
6. Research Mode default (no Buy/Sell/Hold / Official Target Price unless flags).  
7. Freeze discipline — STOP → ADR → escalate ([DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md)).  
8. Regression **GREEN** — definition in [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) §Regression.  
9. **Project Protection** — production-certified work is recoverable and frozen unless unlocked ([DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md)).

Protected / frozen modules: **living list** → [DSP_STATUS.md](DSP_STATUS.md) §Protected.  
Protection policy / Git / backup / recovery / approval levels → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md).

---

## 5. Scope classification (every sprint = exactly one)

| Scope | Meaning |
|---|---|
| **Presentation** | UI / view-models / thin-client mapping only |
| **Domain** | Package engine / aggregate / scoring ownership |
| **Research** | Research intelligence artifacts / research UX |
| **Decision** | Decision Pack / DI / recommendation presentation contracts |
| **Portfolio** | Portfolio intelligence / holdings / allocation UX |
| **Infrastructure** | API, security, production ports, CI, tooling |
| **Documentation** | Docs-only (this suite, ADRs, sprint notes) |

A sprint must declare **one** primary scope. Cross-cutting work still names a primary; secondary touches require explicit approval and must not violate freezes.

---

## 6. Stack at a glance

```text
apps/web (Next.js presentation)
        ↓ HTTPS /api/v1
api_platform + security_platform
        ↓
dsp_platform (composition façade)
        ↓ cite / orchestrate
Domain engines (contracts → … → research / recommendation / KG / copilot)
```

Dependencies (allowed / forbidden / circular): **canonical** → [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) §Dependency rules.

---

## 7. Work protocol

```text
0. PROJECT PROTECTION RULE → DSP_PROJECT_PROTECTION.md §0 (integrity > features)
1. Classify scope (Presentation | Domain | … | Documentation)
2. Confirm change approval level → DSP_PROJECT_PROTECTION.md §9
3. Run Sprint Safety Rules + AI Safety Checklist
4. Load only P1–P2 (+ Protection / P3–P5 if needed)
5. Respect protected modules (DSP_STATUS); unlock only if explicit
6. Note Last Safe Checkpoint; recommend/create checkpoint before Architecture/Breaking work
7. Implement improve-in-place; no drive-by refactors
8. Satisfy GREEN before complete (DSP_CODING_STANDARDS)
9. Update STATUS Project Health / CHANGELOG if release-facing
10. If blocked → ADR; do not invent a new stack
```

---

## 8. Versioning policy (canonical)

| Kind | When | Example |
|---|---|---|
| **Major** | Breaking public API / RC contract / incompatible domain ownership | Backend `v2.0.0` |
| **Minor** | Additive compatible capability | Web epic `2.1.0` |
| **Patch** | Bugfix / docs typo / non-breaking hardening | `2.1.1` |
| **Documentation** | This suite only (`DSP_*` SemVer) | Suite `1.1.0` |
| **Sprint** | Epic delivery label (not SemVer substitute) | `L1.2 Sprint 8` |

Rules: do not equate `apps/web/package.json` with backend RC. Package freeze versions → [VERSION_MATRIX.md](VERSION_MATRIX.md).

---

## 9. Documentation lifecycle (canonical)

| State | Meaning | AI load? |
|---|---|---|
| **Draft** | In progress; may be wrong | Only if task is authoring it |
| **Active** | Current living guidance | Per priority class |
| **Stable** | Normative; change via deliberate bump | Yes when relevant |
| **Deprecated** | Superseded; keep for links | Prefer successor |
| **Historical** | Context only | Explicit request |
| **Archived** | Moved under `docs/archive/` | **Never** unless asked |

Transitions: Draft → Active → Stable; Stable → Deprecated → Historical → Archived. **Do not delete** — archive ([DSP_FOLDER_STRUCTURE.md](DSP_FOLDER_STRUCTURE.md) §Archive).

---

## 10. Token optimization (canonical rules)

1. **One canonical source per topic** (see §11).  
2. Cross-link; never copy architecture / roadmap / coding standards into sprint notes.  
3. Cite paths; do not paste encyclopedias into chat.  
4. One epic sprint brief per task.  
5. Historical/archived docs stay out of default context.

Detail → [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md).

---

## 11. Canonical source map

| Topic | Canonical file |
|---|---|
| Entry + load order + lifecycle + versioning | **This file** |
| What’s frozen / Project Health / current truth | [DSP_STATUS.md](DSP_STATUS.md) |
| Protection policy · Git · backup · recovery · approvals | [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) |
| Structure + dependency rules | [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) |
| Epic sequencing | [DSP_ROADMAP.md](DSP_ROADMAP.md) |
| Coding + GREEN | [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) |
| AI safety / prompts | [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md) |
| ADRs | [DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md) |
| Terms | [DSP_GLOSSARY.md](DSP_GLOSSARY.md) |
| Paths + archive policy | [DSP_FOLDER_STRUCTURE.md](DSP_FOLDER_STRUCTURE.md) |
| Change index | [DSP_CHANGELOG.md](DSP_CHANGELOG.md) |

---

## 12. Language reality

| Layer | Language |
|---|---|
| Domain / API | **Python** (`packages/`) — RC `v1.0.0-rc1` |
| Web presentation | **TypeScript** (`apps/web`) — thin client |
| Shared vocabulary | Python `contracts` |

---

## 13. Related

[DSP_STATUS.md](DSP_STATUS.md) · [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) · [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md) · [DSP_CHANGELOG.md](DSP_CHANGELOG.md)
