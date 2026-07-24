# Phase C3.6 — DecisionPack Evidence Integration

**Status:** Implemented · References only · No Comparison / Portfolio wiring

## DecisionPack ownership

DecisionPack remains the **canonical single-security** investor artifact:

- Recommendation
- Decision Brief
- Assurance Assessment
- Optional `evidence_bundle_ref` (`EvidenceBundleReference`)

DecisionPack **never owns** Evidence Bundle payloads.

## Reference philosophy

```text
EvidenceBundle.reference()  →  EvidenceBundleReference  →  DecisionPack
```

Consumers that need observations resolve the cited bundle from IEF registries /
stores. The pack only carries identity + digest + status.

## Why references instead of embedding

| Embed bundles | Reference bundles |
|---|---|
| Duplicates large payloads | Keeps DecisionPack lightweight |
| Couples DI to IEF internals | Preserves package boundaries |
| Risks divergent copies | Digest pins a specific assembly |
| Encourages re-interpretation | Forces cite-don't-reinterpret |

Frozen architecture: DecisionPack cites evidence; Comparison / Portfolio consume
citations or separately supplied bundles.

## Summary surface

`DecisionPack.evidence_summary()` / presentation `EvidenceSection` expose:

- Evidence status
- Bundle / methodology version
- Availability (`not_attached` or status value)
- Reference citation string

Never observations, scores, or rankings.

## Migration path

1. Existing `build_pack(report, recommendation)` — unchanged, `ref=None`
2. Optional: `build_pack(..., evidence_bundle_ref=bundle.reference())`
3. Or: `attach_evidence_bundle_ref(pack, ref, expected_methodology_id=...)`
4. Platform: `analyze_decision_pack(request, evidence_bundle_ref=...)`

## Non-goals

Comparison EvidenceBundle consume, Portfolio, ranking, scoring, bundle/provider
/interpreter changes.
