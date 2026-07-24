"""Registry for IndustryEvidenceApplicability (methodology policy)."""

from __future__ import annotations

from industry.enums import EvidenceLifecycle
from industry.evidence_applicability import IndustryEvidenceApplicability
from industry.evidence_registry import IndustryEvidenceRegistry
from industry.exceptions import IndustryError
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.semver import parse_semver

__all__ = ["IndustryEvidenceApplicabilityRegistry"]


class IndustryEvidenceApplicabilityRegistry:
    """Versioned applicability policies bound to IndustryMethodology.

    Evidence Registry stays definition-only; this registry owns policy links.
    """

    def __init__(
        self,
        methodologies: IndustryMethodologyRegistry,
        evidence: IndustryEvidenceRegistry,
    ) -> None:
        self._methodologies = methodologies
        self._evidence = evidence
        self._by_key: dict[tuple[str, str], IndustryEvidenceApplicability] = {}
        # methodology_id → applicability id (one lineage per methodology)
        self._methodology_lineage: dict[str, str] = {}

    def register(
        self, applicability: IndustryEvidenceApplicability
    ) -> IndustryEvidenceApplicability:
        self._validate_refs(applicability)
        existing_lineage = self._methodology_lineage.get(
            applicability.methodology_id
        )
        if (
            existing_lineage is not None
            and existing_lineage != applicability.id
        ):
            msg = (
                f"methodology {applicability.methodology_id!r} already bound to "
                f"applicability {existing_lineage!r}; cannot register "
                f"{applicability.id!r}"
            )
            raise IndustryError(msg)
        key = applicability.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == applicability:
                return existing
            msg = (
                f"duplicate industry evidence applicability: "
                f"{applicability.id!r} version {applicability.version!r}"
            )
            raise IndustryError(msg)
        self._by_key[key] = applicability
        self._methodology_lineage[applicability.methodology_id] = applicability.id
        return applicability

    def get(
        self, applicability_id: str, *, version: str
    ) -> IndustryEvidenceApplicability:
        key = (applicability_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown industry evidence applicability: {key!r}"
            raise IndustryError(msg) from exc

    def lookup(
        self, applicability_id: str, *, version: str
    ) -> IndustryEvidenceApplicability:
        return self.get(applicability_id, version=version)

    def lookup_active(self, applicability_id: str) -> IndustryEvidenceApplicability:
        aid = applicability_id.strip().lower()
        active = [
            a
            for a in self._by_key.values()
            if a.id == aid and a.status is EvidenceLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active industry evidence applicability for {aid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda a: parse_semver(a.version))

    def lookup_active_for_methodology(
        self, methodology_id: str
    ) -> IndustryEvidenceApplicability:
        mid = methodology_id.strip().lower()
        aid = self._methodology_lineage.get(mid)
        if aid is None:
            msg = f"no evidence applicability registered for methodology {mid!r}"
            raise IndustryError(msg)
        return self.lookup_active(aid)

    def contains(
        self, applicability_id: str, *, version: str | None = None
    ) -> bool:
        aid = applicability_id.strip().lower()
        if version is not None:
            return (aid, parse_semver(version).raw) in self._by_key
        return any(a.id == aid for a in self._by_key.values())

    def list_all(
        self,
        *,
        methodology_id: str | None = None,
        status: EvidenceLifecycle | None = None,
    ) -> tuple[IndustryEvidenceApplicability, ...]:
        items = list(self._by_key.values())
        if methodology_id is not None:
            mid = methodology_id.strip().lower()
            items = [a for a in items if a.methodology_id == mid]
        if status is not None:
            items = [a for a in items if a.status is status]
        return tuple(
            sorted(
                items,
                key=lambda a: (a.id, parse_semver(a.version).as_tuple()),
            )
        )

    def deprecate(
        self, applicability_id: str, *, version: str
    ) -> IndustryEvidenceApplicability:
        current = self.get(applicability_id, version=version)
        if current.status is EvidenceLifecycle.DEPRECATED:
            return current
        if current.status is EvidenceLifecycle.RETIRED:
            msg = (
                f"cannot deprecate retired applicability "
                f"{applicability_id!r}@{version}"
            )
            raise IndustryError(msg)
        deprecated = IndustryEvidenceApplicability(
            id=current.id,
            methodology_id=current.methodology_id,
            version=current.version,
            rules=current.rules,
            status=EvidenceLifecycle.DEPRECATED,
            groups=current.groups,
            required_sets=current.required_sets,
            missing_evidence_policy=current.missing_evidence_policy,
            methodology_version_pin=current.methodology_version_pin,
            notes=current.notes,
        )
        self._by_key[deprecated.registry_key] = deprecated
        return deprecated

    def validate(self) -> None:
        for key, item in self._by_key.items():
            if item.registry_key != key:
                msg = (
                    f"applicability registry corruption: key {key!r} "
                    f"stores {item.registry_key!r}"
                )
                raise IndustryError(msg)
            expected = self._methodology_lineage.get(item.methodology_id)
            if expected != item.id:
                msg = (
                    f"applicability registry corruption: methodology "
                    f"{item.methodology_id!r} maps to {expected!r} but "
                    f"stores {item.id!r}"
                )
                raise IndustryError(msg)
            self._validate_refs(item)

    def _validate_refs(self, applicability: IndustryEvidenceApplicability) -> None:
        if not self._methodologies.contains(applicability.methodology_id):
            msg = (
                f"unknown methodology for applicability {applicability.id!r}: "
                f"{applicability.methodology_id!r}"
            )
            raise IndustryError(msg)
        if applicability.methodology_version_pin is not None:
            if not self._methodologies.contains(
                applicability.methodology_id,
                version=applicability.methodology_version_pin,
            ):
                msg = (
                    f"unknown methodology pin "
                    f"{applicability.methodology_id!r}@"
                    f"{applicability.methodology_version_pin} on "
                    f"applicability {applicability.id!r}"
                )
                raise IndustryError(msg)
        for rule in applicability.rules:
            if not self._evidence.contains(rule.evidence_id):
                msg = (
                    f"unknown evidence definition {rule.evidence_id!r} on "
                    f"applicability {applicability.id!r}"
                )
                raise IndustryError(msg)
        for req in applicability.required_sets:
            for eid in req.evidence_ids:
                if not self._evidence.contains(eid):
                    msg = (
                        f"unknown evidence {eid!r} in required set {req.id!r} "
                        f"on applicability {applicability.id!r}"
                    )
                    raise IndustryError(msg)
