# DSP Glossary

| Field | Value |
|---|---|
| **Version** | `1.1.0` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-23 |
| **Audience** | Contributors · AI agents |

## Purpose

**Canonical** engineering vocabulary. UX copy rules → PR1.0 / `packages/compliance`. Do not redefine architecture here.

---

## A–D

| Term | Meaning |
|---|---|
| **ADR** | Architecture Decision Record |
| **Archived** | Doc lifecycle state: under `docs/archive/`; AI must not default-load |
| **API Platform** | `api_platform` — FastAPI HTTP edge |
| **Baseline** | [DSP_ARCHITECTURE_BASELINE_v1_0.md](DSP_ARCHITECTURE_BASELINE_v1_0.md) |
| **Bounded context** | Package-owned domain with clear aggregates |
| **Citation / cite** | Reference without owning the artifact |
| **Clean Architecture** | Domain independent of frameworks/vendors |
| **Compliance package** | Flags, Research/SEBI terminology, disclosure ports |
| **Contracts** | Shared domain types; no business I/O |
| **Copilot** | Explainability assistant (not autonomous trader) |
| **Critical (context)** | AI priority class — always load (Protocol + Status) |
| **Decision Pack** | Investor-facing decision artifact from DI |
| **Deterministic** | Same inputs → same outputs |
| **Documentation (scope)** | Sprint scope class for docs-only work |
| **DSP (product)** | Decision Support / DSP AI Indicator platform |
| **DSP (package)** | `packages/dsp` — indicator engine (not whole product) |
| **Domain (scope)** | Sprint scope class for engine/aggregate work |

---

## E–M

| Term | Meaning |
|---|---|
| **EMI / M2** | Economic Moat Intelligence Engine |
| **EQI / EQ1** | Earnings Quality Intelligence Engine |
| **Evidence-first** | Source, confidence, methodology, limits |
| **Façade** | Public entry (`dsp_platform`) composing engines |
| **Feature flag** | Gates recommendation / SEBI-style surfaces |
| **Frozen / Protected** | No edit without explicit override ([DSP_STATUS.md](DSP_STATUS.md)) |
| **GREEN** | Official regression pass — Coding Standards §Regression |
| **Historical (context)** | AI priority — load only on explicit request |
| **IEF** | Industry Evidence Framework |
| **Infrastructure (scope)** | API, security, CI, production ports |
| **KG** | Knowledge Graph (engine and/or presentation) |
| **L1.2** | Company Analysis Workspace epic (web) |
| **MIE / M1** | Management Intelligence Engine |
| **Moat / M2** | See EMI |

---

## N–Z

| Term | Meaning |
|---|---|
| **Port / Adapter** | Interface vs vendor implementation |
| **Portfolio (scope)** | Holdings / allocation intelligence work |
| **PR1.0 / PR1.1 / PR1.2** | Strategy & compliance / PXB / VLIS freezes |
| **Presentation (scope)** | UI / view-models / thin-client mapping only |
| **Presentation builder** | Envelope → view-model (no math) |
| **PXB** | Product Experience Blueprint |
| **RC** | Release Candidate (backend `v1.0.0-rc1`) |
| **Research (scope)** | Research intelligence / research UX |
| **Research Mode** | Default UX: research language, not Buy/Sell advice |
| **Scope class** | Exactly one of seven sprint classifications (Master Protocol §5) |
| **Thin client** | UI does not recalculate finance |
| **Trust Standard** | [USER_TRUST_STANDARD.md](USER_TRUST_STANDARD.md) |
| **Unavailable** | Honest empty state; preferred over invention |
| **VLIS** | Visual Language & Interaction System |
| **View-model** | UI-ready structure from API envelope |

---

## Related

[FINANCIAL_TERMINOLOGY.md](FINANCIAL_TERMINOLOGY.md) · [METRIC_LIBRARY.md](METRIC_LIBRARY.md) · [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md)
