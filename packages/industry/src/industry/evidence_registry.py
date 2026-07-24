"""Industry Evidence + Metric definition registries (C3.1 — definitions only)."""

from __future__ import annotations

from industry.enums import EvidenceLifecycle
from industry.evidence_models import (
    IndustryEvidenceDefinition,
    IndustryMetricDefinition,
)
from industry.exceptions import IndustryError
from industry.semver import parse_semver

__all__ = ["IndustryEvidenceRegistry", "IndustryMetricRegistry"]

_LOOKUP_STATUSES = frozenset(
    {
        EvidenceLifecycle.DRAFT,
        EvidenceLifecycle.ACTIVE,
        EvidenceLifecycle.DEPRECATED,
        EvidenceLifecycle.RETIRED,
    }
)


class IndustryMetricRegistry:
    """Versioned registry of IndustryMetricDefinition metadata."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], IndustryMetricDefinition] = {}

    def register(self, metric: IndustryMetricDefinition) -> IndustryMetricDefinition:
        _assert_known_lifecycle(metric.status)
        key = metric.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == metric:
                return existing
            msg = (
                f"duplicate industry metric definition: {metric.id!r} "
                f"version {metric.version!r}"
            )
            raise IndustryError(msg)
        self._by_key[key] = metric
        return metric

    def get(self, metric_id: str, *, version: str) -> IndustryMetricDefinition:
        key = (metric_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown industry metric definition: {key!r}"
            raise IndustryError(msg) from exc

    def lookup(self, metric_id: str, *, version: str) -> IndustryMetricDefinition:
        return self.get(metric_id, version=version)

    def lookup_active(self, metric_id: str) -> IndustryMetricDefinition:
        mid = metric_id.strip().lower()
        active = [
            m
            for m in self._by_key.values()
            if m.id == mid and m.status is EvidenceLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active industry metric definition for {mid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda m: parse_semver(m.version))

    def contains(self, metric_id: str, *, version: str | None = None) -> bool:
        mid = metric_id.strip().lower()
        if version is not None:
            return (mid, parse_semver(version).raw) in self._by_key
        return any(m.id == mid for m in self._by_key.values())

    def list_all(
        self, *, status: EvidenceLifecycle | None = None
    ) -> tuple[IndustryMetricDefinition, ...]:
        items = list(self._by_key.values())
        if status is not None:
            items = [m for m in items if m.status is status]
        return tuple(
            sorted(items, key=lambda m: (m.id, parse_semver(m.version).as_tuple()))
        )

    def deprecate(self, metric_id: str, *, version: str) -> IndustryMetricDefinition:
        current = self.get(metric_id, version=version)
        if current.status is EvidenceLifecycle.DEPRECATED:
            return current
        if current.status is EvidenceLifecycle.RETIRED:
            msg = f"cannot deprecate retired metric {metric_id!r}@{version}"
            raise IndustryError(msg)
        deprecated = IndustryMetricDefinition(
            id=current.id,
            name=current.name,
            version=current.version,
            category=current.category,
            unit=current.unit,
            status=EvidenceLifecycle.DEPRECATED,
            description=current.description,
            availability=current.availability,
            provider=current.provider,
            notes=current.notes,
        )
        self._by_key[deprecated.registry_key] = deprecated
        return deprecated

    def validate(self) -> None:
        for key, item in self._by_key.items():
            if item.registry_key != key:
                msg = f"metric registry corruption: key {key!r} stores {item.registry_key!r}"
                raise IndustryError(msg)
            _assert_known_lifecycle(item.status)


class IndustryEvidenceRegistry:
    """Versioned registry of IndustryEvidenceDefinition metadata.

    Optionally validates related_metric_ids against an IndustryMetricRegistry.
    Does not evaluate, interpret, or produce evidence.
    """

    def __init__(
        self, metrics: IndustryMetricRegistry | None = None
    ) -> None:
        self._metrics = metrics
        self._by_key: dict[tuple[str, str], IndustryEvidenceDefinition] = {}

    def register(
        self, evidence: IndustryEvidenceDefinition
    ) -> IndustryEvidenceDefinition:
        _assert_known_lifecycle(evidence.status)
        self._validate_metric_refs(evidence)
        key = evidence.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == evidence:
                return existing
            msg = (
                f"duplicate industry evidence definition: {evidence.id!r} "
                f"version {evidence.version!r}"
            )
            raise IndustryError(msg)
        self._by_key[key] = evidence
        return evidence

    def get(self, evidence_id: str, *, version: str) -> IndustryEvidenceDefinition:
        key = (evidence_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown industry evidence definition: {key!r}"
            raise IndustryError(msg) from exc

    def lookup(
        self, evidence_id: str, *, version: str
    ) -> IndustryEvidenceDefinition:
        return self.get(evidence_id, version=version)

    def lookup_active(self, evidence_id: str) -> IndustryEvidenceDefinition:
        eid = evidence_id.strip().lower()
        active = [
            e
            for e in self._by_key.values()
            if e.id == eid and e.status is EvidenceLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active industry evidence definition for {eid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda e: parse_semver(e.version))

    def contains(self, evidence_id: str, *, version: str | None = None) -> bool:
        eid = evidence_id.strip().lower()
        if version is not None:
            return (eid, parse_semver(version).raw) in self._by_key
        return any(e.id == eid for e in self._by_key.values())

    def list_all(
        self, *, status: EvidenceLifecycle | None = None
    ) -> tuple[IndustryEvidenceDefinition, ...]:
        items = list(self._by_key.values())
        if status is not None:
            items = [e for e in items if e.status is status]
        return tuple(
            sorted(items, key=lambda e: (e.id, parse_semver(e.version).as_tuple()))
        )

    def deprecate(
        self, evidence_id: str, *, version: str
    ) -> IndustryEvidenceDefinition:
        current = self.get(evidence_id, version=version)
        if current.status is EvidenceLifecycle.DEPRECATED:
            return current
        if current.status is EvidenceLifecycle.RETIRED:
            msg = f"cannot deprecate retired evidence {evidence_id!r}@{version}"
            raise IndustryError(msg)
        deprecated = IndustryEvidenceDefinition(
            id=current.id,
            name=current.name,
            version=current.version,
            category=current.category,
            purpose=current.purpose,
            status=EvidenceLifecycle.DEPRECATED,
            description=current.description,
            related_metric_ids=current.related_metric_ids,
            supported_industry_ids=current.supported_industry_ids,
            interpretation_guidance=current.interpretation_guidance,
            provider_requirements=current.provider_requirements,
            dimension_hints=current.dimension_hints,
            snapshot_compatible=current.snapshot_compatible,
            notes=current.notes,
        )
        self._by_key[deprecated.registry_key] = deprecated
        return deprecated

    def validate(self) -> None:
        for key, item in self._by_key.items():
            if item.registry_key != key:
                msg = (
                    f"evidence registry corruption: key {key!r} "
                    f"stores {item.registry_key!r}"
                )
                raise IndustryError(msg)
            _assert_known_lifecycle(item.status)
            self._validate_metric_refs(item)

    def _validate_metric_refs(self, evidence: IndustryEvidenceDefinition) -> None:
        if not evidence.related_metric_ids:
            return
        if self._metrics is None:
            msg = (
                f"metric registry required to validate related_metric_ids on "
                f"evidence {evidence.id!r}"
            )
            raise IndustryError(msg)
        for mid in evidence.related_metric_ids:
            if not self._metrics.contains(mid):
                msg = (
                    f"unknown related metric {mid!r} on evidence "
                    f"{evidence.id!r}"
                )
                raise IndustryError(msg)


def _assert_known_lifecycle(status: EvidenceLifecycle) -> None:
    if status not in _LOOKUP_STATUSES:
        msg = f"invalid evidence lifecycle: {status!r}"
        raise IndustryError(msg)
