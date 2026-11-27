"""Evidence canonicalization, duplicate detection, and conflicting-claim resolution."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dsp_platform.research_retrieval.models import (
    ConflictingClaim,
    ResearchEvidenceRecord,
    SourceTier,
)

__all__ = [
    "DeduplicationEngine",
    "DeduplicationResult",
    "canonicalize_url",
]

# Tracking parameters to strip from URLs
TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "source",
        "campaign",
        "trk",
    }
)


def canonicalize_url(url: str) -> str:
    """Normalize a URL to its canonical form, stripping tracking query parameters."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return url.strip()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    # Strip standard port
    if netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    # Filter query parameters
    query_dict = parse_qs(parsed.query, keep_blank_values=False)
    filtered_params = {
        k: v for k, v in query_dict.items() if k.lower() not in TRACKING_PARAMS
    }
    # Deterministically sort parameters
    sorted_query = urlencode(filtered_params, doseq=True)

    return urlunparse((scheme, netloc, path, "", sorted_query, ""))


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    unique_evidence: tuple[ResearchEvidenceRecord, ...]
    conflicts: tuple[ConflictingClaim, ...]
    duplicate_count: int


def _fact_key(record: ResearchEvidenceRecord) -> str:
    """Identity of a fact: same document and claim *and* same metric/value/units/period/revision.

    Two different numbers in one document are distinct facts, so they must survive
    deduplication and reach conflict detection.
    """
    prov = record.provenance
    value = "" if record.metric_value is None else repr(float(record.metric_value))
    return "|".join(
        (
            record.ticker.strip().upper(),
            prov.canonical_url,
            record.claim,
            (record.metric_name or "").strip().upper(),
            value,
            (record.units or "").strip().upper(),
            (prov.effective_period or "").strip().upper(),
            prov.content_hash or "",
        )
    )


class DeduplicationEngine:
    """Detects duplicates, links corroborations, and preserves conflicting claims."""

    def __init__(self, conflict_tolerance: float = 0.02) -> None:
        self.conflict_tolerance = conflict_tolerance

    def process_evidence(
        self,
        records: Iterable[ResearchEvidenceRecord],
    ) -> DeduplicationResult:
        items = list(records)
        unique_map: dict[str, ResearchEvidenceRecord] = {}
        conflicts: list[ConflictingClaim] = []
        duplicates = 0

        # Group by metric and period for conflict analysis
        metric_groups: dict[tuple[str, str, str], list[ResearchEvidenceRecord]] = {}

        for record in items:
            key = _fact_key(record)
            if key in unique_map:
                duplicates += 1
                continue
            unique_map[key] = record

            if record.metric_name and record.metric_value is not None:
                group_key = (
                    record.ticker.strip().upper(),
                    record.metric_name.strip().upper(),
                    (record.provenance.effective_period or "current").strip().upper(),
                )
                metric_groups.setdefault(group_key, []).append(record)

        # Detect conflicts and corroborations across metric groups
        for (ticker, metric, period), group in metric_groups.items():
            if len(group) < 2:
                continue

            # Separate into primary and secondary
            primaries = [
                r for r in group if r.provenance.source_tier is SourceTier.PRIMARY
            ]
            secondaries = [
                r for r in group if r.provenance.source_tier is SourceTier.SECONDARY
            ]

            base = primaries[0] if primaries else group[0]
            for other in group:
                if other is base:
                    continue

                diff = abs((other.metric_value or 0.0) - (base.metric_value or 0.0))
                denom = max(abs(base.metric_value or 1.0), 1.0)
                rel_diff = diff / denom

                if rel_diff > self.conflict_tolerance:
                    # Material discrepancy detected -> record conflict
                    conflicts.append(
                        ConflictingClaim(
                            ticker=ticker,
                            metric_name=metric,
                            period=period,
                            primary_claim=base,
                            conflicting_claim=other,
                            discrepancy_pct=round(rel_diff * 100.0, 2),
                            description=(
                                f"Metric '{metric}' for {ticker} ({period}) has conflicting reports: "
                                f"{base.provenance.source} reports {base.metric_value} vs "
                                f"{other.provenance.source} reports {other.metric_value} "
                                f"({round(rel_diff * 100.0, 1)}% discrepancy)"
                            ),
                        )
                    )
                else:
                    # Corroboration: link evidence IDs
                    base_key = _fact_key(base)
                    current = unique_map[base_key]
                    if other.evidence_id not in current.corroborated_by:
                        # Accumulate links on the latest copy so earlier corroborations
                        # are kept; preserve first-seen order for stable output.
                        updated_base = ResearchEvidenceRecord(
                            evidence_id=base.evidence_id,
                            ticker=base.ticker,
                            claim=base.claim,
                            status=base.status,
                            provenance=base.provenance,
                            freshness=base.freshness,
                            metric_name=base.metric_name,
                            metric_value=base.metric_value,
                            units=base.units,
                            raw_excerpt=base.raw_excerpt,
                            document_location=base.document_location,
                            rejection_reason=base.rejection_reason,
                            corroborated_by=(
                                *current.corroborated_by,
                                other.evidence_id,
                            ),
                            conflicts_with=base.conflicts_with,
                        )
                        unique_map[base_key] = updated_base

        return DeduplicationResult(
            unique_evidence=tuple(unique_map.values()),
            conflicts=tuple(conflicts),
            duplicate_count=duplicates,
        )
