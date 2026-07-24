# DSP Decision Records

| Field | Value |
|---|---|
| **Version** | `1.2.1` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-23 |
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

Template:

```markdown
# ADR-XXXX Title
Status: Proposed | Accepted | Superseded
Context: …
Decision: …
Consequences: …
```

---

## 2. Standing decisions (accepted)

| ID | Decision | See |
|---|---|---|
| **ADR-0001** | Thin web client — no investment math in browser | Governance |
| **ADR-0002** | Research Mode is default product mode | PR1.0 · `compliance` |
| **ADR-0003** | `dsp_platform` is composition façade; domains must not import it | Baseline |
| **ADR-0004** | Security wraps API, not domain façade | Architecture Overview |
| **ADR-0005** | Single ownership; cite don’t embed | Baseline §2 |
| **ADR-0006** | Unavailable > fabricated consensus / prices | Trust Standard |
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
