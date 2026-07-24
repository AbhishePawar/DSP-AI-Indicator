# Phase C4.4 — Portfolio Citation Enrichment

**Status:** Implemented · Aggregation only

## Citation philosophy

Portfolio Intelligence **aggregates citations**. It does not own evidence,
interpret observations, or execute comparison.

Citations are references to existing DSP contracts:

- `DecisionPackReference`
- `EvidenceBundleReference`
- `ComparisonReportReference`

## Aggregation rules

1. Collect DecisionPack citations from holdings (+ optional overlays).
2. Collect EvidenceBundle citations from holdings (+ optional overlays).
3. Collect ComparisonReport citations from holdings, snapshots, and overlays.
4. Record methodology bundle versions from EvidenceBundle references.
5. Emit coverage counts and citation gaps.
6. Enrich `PortfolioReport` with citation summary fields.

Duplicates and foreign symbols are rejected. Identical re-attachments of the
same citation are allowed.

## Consumer-only behavior

`PortfolioCitationAssembler` may aggregate, summarize, and reference.

It must **not**:

- resolve providers
- interpret evidence
- run comparison
- generate observations
- score, rank, or recommend

## PortfolioReport extensions (additive)

| Field | Role |
|---|---|
| `citation_summary` | Aggregated citation counts / bundle versions |
| `coverage_summary` | Holding-level citation coverage |
| `citation_gaps` | Human-readable missing citation notes |
| `decision_pack_refs` | Decision references (existing) |
| `evidence_bundle_refs` | Evidence references (existing) |
| `comparison_report_refs` | Comparison references (existing) |

## Status

| Status | Meaning |
|---|---|
| `EMPTY` | No holdings |
| `ABSENT` | Holdings present; optional evidence/comparison citations absent |
| `PARTIAL` | Some optional citations present; gaps remain |
| `COMPLETE` | Decision + evidence + comparison coverage for all holdings |

## Non-goals

Risk, optimization, monitoring, scoring, ranking, trading, provider
resolution, evidence interpretation, comparison execution.
