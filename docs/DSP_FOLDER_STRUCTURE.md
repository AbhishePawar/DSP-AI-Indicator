# DSP Folder Structure

| Field | Value |
|---|---|
| **Version** | `1.1.0` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-23 |
| **Audience** | Engineers · AI agents |

## Purpose

**Canonical** path map + **archive policy**. Package semantics → [DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md). Lifecycle states → [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) §9.

---

## 1. Top level

```text
DSP-AI-Indicator/
├── apps/
│   └── web/                 # Next.js thin client
├── packages/                # Python domain + platform packages
├── docs/                    # Active + Stable docs + DSP_* suite
│   └── archive/             # Historical / Archived specs (AI opt-in only)
├── .cursor/rules/
├── README.md
└── …
```

---

## 2. `packages/` (one-line roles)

| Package | Role |
|---|---|
| `contracts` | Shared vocabulary |
| `core` | Domain-agnostic utilities |
| `data_engine` | Acquisition / normalization ports |
| `dsp` | Indicator / DSP signals |
| `fundamental` / `economic` / `valuation` | Analysis engines |
| `decision_intelligence` | Decision Pack / assurance |
| `industry` / `comparison` | Industry + peers |
| `portfolio` / `risk` / `quantitative_risk` | Portfolio & risk |
| `research` / `recommendation` / `workflow` | Research & recs |
| `knowledge_graph` / `copilot` | KG + copilot domain |
| `compliance` | Flags & terminology ports |
| `dsp_platform` | Composition façade |
| `api_platform` / `security_platform` / `production_platform` | Edge & ops |

Versions → [VERSION_MATRIX.md](VERSION_MATRIX.md).

---

## 3. `apps/web/`

```text
apps/web/src/
├── app/           # routes
├── components/    # UI
└── lib/           # view-models / mappers / epic modules (no domain math)
```

---

## 4. `docs/` navigation

| Area | Use | AI default? |
|---|---|---|
| `DSP_*.md` | Master suite — start here | Per load order (P1–P4) |
| `ARCHITECTURE_*` / `PRODUCT_*` | Governance | On demand |
| Epic prefixes `PR1_` `L1_` `V*` `M*` `EQ1_` | Sprint notes | One brief only |
| `VERSION_MATRIX.md` / `CHANGELOG.md` | Versions / detail | On demand |
| **`docs/archive/`** | Superseded specs | **Never** unless asked |

---

## 5. Historical Archive Policy (canonical)

1. **Do not delete** obsolete specifications.  
2. Move them to `docs/archive/` (preserve relative links via redirect stubs if needed).  
3. Mark front-matter: `Status: Archived` · `Superseded-by: <path>`.  
4. AI agents **must not** load `docs/archive/**` unless the user explicitly requests Historical context.  
5. Active suite (`DSP_*`) remains the only default navigation layer.  
6. Prefer stub at old path → “Moved to archive/…” over silent breakage.

See [archive/README.md](archive/README.md).

---

## 6. Related

[DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md) · [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_STATUS.md](DSP_STATUS.md)
