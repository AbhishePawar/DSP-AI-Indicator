"""Evidence Bundle consumption for qualitative comparison (C3.7).

Comparison cites Industry Evidence observations and limitations.
It never calculates, interprets, or owns evidence.
"""

from __future__ import annotations

from decision_intelligence import DecisionPack
from industry import (
    EvidenceAvailability,
    EvidenceBundle,
    EvidenceBundleStatus,
)

from comparison.exceptions import ComparisonError
from comparison.models import (
    ComparisonEvidenceSummary,
    ComparisonLimitation,
    ComparisonObservation,
)

__all__ = [
    "build_comparison_evidence_summary",
    "build_evidence_backed_observations",
    "build_evidence_limitations",
    "validate_evidence_bundles_for_comparison",
]


def validate_evidence_bundles_for_comparison(
    bundles: tuple[EvidenceBundle, ...],
    *,
    packs: tuple[DecisionPack, ...],
    methodology_id: str,
    methodology_version: str,
    included_symbols: tuple[str, ...],
) -> None:
    """Reject invalid / mismatched Evidence Bundles before citation."""
    pack_by_symbol = {
        p.recommendation.instrument.symbol: p for p in packs
    }
    pack_symbols = set(pack_by_symbol)
    included = set(included_symbols)
    seen: set[str] = set()

    for bundle in bundles:
        meta = bundle.metadata
        key = meta.instrument_key
        if key in seen:
            msg = f"duplicate evidence bundle for instrument {key!r}"
            raise ComparisonError(msg)
        seen.add(key)
        if key not in pack_symbols:
            msg = (
                f"evidence bundle instrument {key!r} is not present in "
                f"comparison DecisionPacks"
            )
            raise ComparisonError(msg)
        if key not in included:
            msg = (
                f"evidence bundle instrument {key!r} is not among included "
                f"comparison peers {sorted(included)!r}"
            )
            raise ComparisonError(msg)
        if meta.methodology_id != methodology_id:
            msg = (
                f"evidence methodology mismatch for {key}: "
                f"bundle {meta.methodology_id!r} vs comparison "
                f"{methodology_id!r}"
            )
            raise ComparisonError(msg)
        if meta.methodology_version != methodology_version:
            msg = (
                f"evidence methodology version mismatch for {key}: "
                f"bundle {meta.methodology_version!r} vs comparison "
                f"{methodology_version!r}"
            )
            raise ComparisonError(msg)
        if not isinstance(bundle.status, EvidenceBundleStatus):
            msg = f"invalid evidence bundle status for {key}"
            raise ComparisonError(msg)
        if not bundle.digest:
            msg = f"broken evidence bundle reference: empty digest for {key}"
            raise ComparisonError(msg)

        pack = pack_by_symbol[key]
        ref = pack.evidence_bundle_ref
        if ref is not None:
            if ref.instrument_key != key:
                msg = (
                    f"DecisionPack evidence_bundle_ref instrument mismatch "
                    f"for {key}"
                )
                raise ComparisonError(msg)
            if ref.digest != bundle.digest:
                msg = (
                    f"evidence bundle digest mismatch for {key}: "
                    f"pack cites {ref.digest!r}, bundle digest is "
                    f"{bundle.digest!r}"
                )
                raise ComparisonError(msg)
            if ref.methodology_id != meta.methodology_id:
                msg = (
                    f"evidence_bundle_ref methodology mismatch for {key}"
                )
                raise ComparisonError(msg)


def build_comparison_evidence_summary(
    bundles: tuple[EvidenceBundle, ...],
    *,
    included_symbols: tuple[str, ...],
    methodology_id: str,
) -> ComparisonEvidenceSummary:
    if not bundles:
        return ComparisonEvidenceSummary.not_supplied()

    by_symbol = {b.metadata.instrument_key: b for b in bundles}
    covered = tuple(s for s in included_symbols if s in by_symbol)
    missing = tuple(s for s in included_symbols if s not in by_symbol)
    statuses = tuple(by_symbol[s].status.value for s in covered)
    versions = tuple(
        by_symbol[s].metadata.methodology_version for s in covered
    )
    digests = tuple(by_symbol[s].digest for s in covered)

    if missing:
        availability = "partial_coverage"
    elif all(s == EvidenceBundleStatus.COMPLETE.value for s in statuses):
        availability = "complete"
    elif all(s == EvidenceBundleStatus.EMPTY.value for s in statuses):
        availability = "empty"
    elif any(
        s
        in {
            EvidenceBundleStatus.INCOMPLETE.value,
            EvidenceBundleStatus.PARTIAL.value,
            EvidenceBundleStatus.EMPTY.value,
        }
        for s in statuses
    ):
        availability = "mixed"
    else:
        availability = "attached"

    return ComparisonEvidenceSummary(
        attached=True,
        availability=availability,
        bundle_count=len(covered),
        covered_symbols=covered,
        missing_symbols=missing,
        methodology_id=methodology_id,
        bundle_versions=tuple(dict.fromkeys(versions)),
        bundle_statuses=statuses,
        digests=digests,
    )


def build_evidence_backed_observations(
    bundles: tuple[EvidenceBundle, ...],
    *,
    included_symbols: tuple[str, ...],
) -> tuple[ComparisonObservation, ...]:
    """Cite Industry observations without reinterpretation."""
    by_symbol = {b.metadata.instrument_key: b for b in bundles}
    notes: list[ComparisonObservation] = []

    for symbol in included_symbols:
        bundle = by_symbol.get(symbol)
        if bundle is None:
            continue
        notes.append(
            ComparisonObservation(
                code="industry_evidence_bundle_cited",
                text=(
                    f"{symbol}: Industry Evidence Bundle "
                    f"{bundle.metadata.bundle_id} "
                    f"(status={bundle.status.value}) is cited for this "
                    f"comparison under methodology "
                    f"{bundle.metadata.methodology_id}@"
                    f"{bundle.metadata.methodology_version}."
                ),
                subjects=(symbol,),
                evidence_refs=(bundle.metadata.bundle_id, bundle.digest),
            )
        )
        for entry in bundle.entries:
            obs = entry.observation
            if obs is None:
                continue
            notes.append(
                ComparisonObservation(
                    code="industry_evidence_observation",
                    text=(
                        f"{symbol} [{entry.evidence_id}]: {obs.title}. "
                        f"{obs.summary}"
                    ),
                    subjects=(symbol,),
                    evidence_refs=(entry.evidence_id, obs.id),
                )
            )
            if entry.is_gap or (
                entry.provider_result is not None
                and entry.provider_result.availability
                is not EvidenceAvailability.AVAILABLE
            ):
                avail = (
                    "gap"
                    if entry.provider_result is None
                    else entry.provider_result.availability.value
                )
                notes.append(
                    ComparisonObservation(
                        code="industry_evidence_availability",
                        text=(
                            f"{symbol} evidence {entry.evidence_id} "
                            f"availability is recorded as {avail} in the "
                            f"cited Industry Evidence Bundle."
                        ),
                        subjects=(symbol,),
                        evidence_refs=(entry.evidence_id,),
                    )
                )

    evidence_ids: set[str] = set()
    for bundle in bundles:
        if bundle.metadata.instrument_key in included_symbols:
            for entry in bundle.entries:
                evidence_ids.add(entry.evidence_id)

    for eid in sorted(evidence_ids):
        parts: list[str] = []
        subjects: list[str] = []
        for symbol in included_symbols:
            bundle = by_symbol.get(symbol)
            if bundle is None:
                continue
            entry = bundle.entry_for(eid)
            if entry is None:
                continue
            subjects.append(symbol)
            if entry.provider_result is None:
                parts.append(f"{symbol}=unresolved")
            else:
                parts.append(
                    f"{symbol}={entry.provider_result.availability.value}"
                )
        if len(subjects) >= 2 and len(set(parts)) > 1:
            notes.append(
                ComparisonObservation(
                    code="industry_evidence_availability_contrast",
                    text=(
                        f"Evidence {eid} availability differs across peers: "
                        + "; ".join(parts)
                        + ". This records coverage differences only."
                    ),
                    subjects=tuple(subjects),
                    evidence_refs=(eid,),
                )
            )

    return tuple(notes)


def build_evidence_limitations(
    bundles: tuple[EvidenceBundle, ...],
    *,
    included_symbols: tuple[str, ...],
) -> tuple[ComparisonLimitation, ...]:
    if not bundles:
        return (
            ComparisonLimitation(
                code="industry_evidence_not_supplied",
                message=(
                    "No Industry Evidence Bundle was supplied for this "
                    "comparison. C2.5 DecisionPack-only qualitative notes "
                    "apply; industry evidence citations are absent."
                ),
            ),
        )

    by_symbol = {b.metadata.instrument_key: b for b in bundles}
    limits: list[ComparisonLimitation] = []
    missing = [s for s in included_symbols if s not in by_symbol]
    for symbol in missing:
        limits.append(
            ComparisonLimitation(
                code="industry_evidence_missing_for_peer",
                message=(
                    f"{symbol} was included in comparison without a matching "
                    f"Industry Evidence Bundle."
                ),
                subjects=(symbol,),
            )
        )

    for symbol in included_symbols:
        bundle = by_symbol.get(symbol)
        if bundle is None:
            continue
        for note in bundle.limitations:
            limits.append(
                ComparisonLimitation(
                    code="industry_evidence_bundle_limitation",
                    message=f"{symbol}: {note}",
                    subjects=(symbol,),
                )
            )
        for entry in bundle.entries:
            for note in entry.limitations:
                limits.append(
                    ComparisonLimitation(
                        code="industry_evidence_entry_limitation",
                        message=f"{symbol} [{entry.evidence_id}]: {note}",
                        subjects=(symbol,),
                    )
                )
            if entry.is_gap:
                limits.append(
                    ComparisonLimitation(
                        code="industry_evidence_gap",
                        message=(
                            f"{symbol} records a gap for evidence "
                            f"{entry.evidence_id} under the cited bundle."
                        ),
                        subjects=(symbol,),
                    )
                )
        if bundle.status is EvidenceBundleStatus.INCOMPLETE:
            limits.append(
                ComparisonLimitation(
                    code="industry_evidence_incomplete",
                    message=(
                        f"{symbol} Industry Evidence Bundle status is "
                        f"incomplete."
                    ),
                    subjects=(symbol,),
                )
            )
        elif bundle.status is EvidenceBundleStatus.PARTIAL:
            limits.append(
                ComparisonLimitation(
                    code="industry_evidence_partial",
                    message=(
                        f"{symbol} Industry Evidence Bundle status is partial."
                    ),
                    subjects=(symbol,),
                )
            )
        elif bundle.status is EvidenceBundleStatus.EMPTY:
            limits.append(
                ComparisonLimitation(
                    code="industry_evidence_empty",
                    message=(
                        f"{symbol} Industry Evidence Bundle is empty."
                    ),
                    subjects=(symbol,),
                )
            )

    return tuple(limits)
