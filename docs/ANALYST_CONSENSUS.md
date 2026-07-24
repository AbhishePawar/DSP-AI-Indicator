# Analyst Consensus

**Status:** Architecture only — **no provider integrations in PR1.0**.

---

## Purpose

Surface **Market Analyst Consensus** beside DSP research so users can compare
Street views with DSP View — without implying DSP is a tip service.

---

## Planned fields

| Field | Description |
|---|---|
| Average Target Price | Street mean target (provider later) |
| Consensus Rating | Aggregated rating label |
| Coverage Count | Number of covering analysts |
| Rating Distribution | Counts by rating bucket |
| Individual Analysts | Row-level estimates |
| Target Distribution | Histogram buckets |
| Bull Case | Narrative high case |
| Bear Case | Narrative low case |
| Market Agreement | Agreement / dispersion note |
| DSP vs Street | Comparison presentation |
| AI Consensus Analysis | Cite-backed commentary (backend) |

---

## Ports

`compliance.analyst_consensus`:

- `ConsensusSnapshot`  
- `AnalystEstimate`  
- `DspVsStreetComparison`  
- `ConsensusProviderPort.fetch_consensus(symbol)`  

**Do not** add Bloomberg / FactSet / broker SDKs in this epic.

---

## UI placement

Analysis page section: **Market Analyst Consensus** (after Executive Summary).

Research Mode labels Street “target” carefully; DSP intrinsic range remains
separate from Official Target Price (SEBI-only).
