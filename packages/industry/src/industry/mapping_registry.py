"""Classification mapping registry — external taxonomy → DSP identity."""

from __future__ import annotations

from industry.enums import MappingStatus, TaxonomySource
from industry.exceptions import IndustryError
from industry.models import ClassificationReference, IndustryMapping
from industry.taxonomy import IndustryTaxonomy

__all__ = ["ClassificationMappingRegistry"]


class ClassificationMappingRegistry:
    """Versioned mappings from external classifications to DSP identities.

    Never mutates IndustryIdentity. Active collision: same external key
    (source, code, taxonomy_version) cannot map to two different
    industry ids while both mappings are ACTIVE.
    """

    def __init__(self, taxonomy: IndustryTaxonomy) -> None:
        self._taxonomy = taxonomy
        self._by_key: dict[tuple[str, str, str, str], IndustryMapping] = {}

    def register(self, mapping: IndustryMapping) -> IndustryMapping:
        """Register a mapping. Rejects unknown industries and collisions."""
        if not self._taxonomy.contains(mapping.industry_id):
            msg = (
                f"cannot map to unknown industry identity: "
                f"{mapping.industry_id!r}"
            )
            raise IndustryError(msg)

        key = mapping.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == mapping:
                return existing
            msg = (
                f"duplicate mapping registration for key {key!r}: "
                f"existing={existing!r}"
            )
            raise IndustryError(msg)

        if mapping.status is MappingStatus.ACTIVE:
            self._assert_no_active_collision(mapping)

        self._by_key[key] = mapping
        return mapping

    def get(
        self,
        source: TaxonomySource,
        code: str,
        *,
        mapping_version: str,
        taxonomy_version: str | None = None,
    ) -> IndustryMapping:
        """Lookup an exact mapping version."""
        ref = ClassificationReference(
            source=source,
            code=code,
            taxonomy_version=taxonomy_version,
        )
        key = (*ref.key, mapping_version.strip().lower())
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown mapping: {key!r}"
            raise IndustryError(msg) from exc

    def lookup_active(
        self,
        source: TaxonomySource,
        code: str,
        *,
        taxonomy_version: str | None = None,
    ) -> IndustryMapping:
        """Return the single ACTIVE mapping for an external classification.

        If multiple ACTIVE versions exist for the same classification key,
        the lexicographically greatest ``mapping_version`` wins
        (deterministic tie-break for version strings).
        """
        ref = ClassificationReference(
            source=source,
            code=code,
            taxonomy_version=taxonomy_version,
        )
        class_key = ref.key
        active = [
            m
            for m in self._by_key.values()
            if m.classification.key == class_key
            and m.status is MappingStatus.ACTIVE
        ]
        if not active:
            msg = (
                f"no active mapping for {source.value}:{code}"
                f"{'' if not taxonomy_version else f'@{taxonomy_version}'}"
            )
            raise IndustryError(msg)
        return max(active, key=lambda m: m.mapping_version.lower())

    def list_mappings(
        self,
        *,
        industry_id: str | None = None,
        status: MappingStatus | None = None,
    ) -> tuple[IndustryMapping, ...]:
        items = list(self._by_key.values())
        if industry_id is not None:
            key = industry_id.strip().lower()
            items = [m for m in items if m.industry_id == key]
        if status is not None:
            items = [m for m in items if m.status is status]
        return tuple(sorted(items, key=lambda m: m.registry_key))

    def deprecate(
        self,
        source: TaxonomySource,
        code: str,
        *,
        mapping_version: str,
        taxonomy_version: str | None = None,
    ) -> IndustryMapping:
        """Mark an existing mapping DEPRECATED (identity unchanged)."""
        current = self.get(
            source,
            code,
            mapping_version=mapping_version,
            taxonomy_version=taxonomy_version,
        )
        if current.status is MappingStatus.DEPRECATED:
            return current
        deprecated = IndustryMapping(
            classification=current.classification,
            industry_id=current.industry_id,
            mapping_version=current.mapping_version,
            status=MappingStatus.DEPRECATED,
            notes=current.notes,
        )
        self._by_key[deprecated.registry_key] = deprecated
        return deprecated

    def validate(self) -> None:
        """Ensure all mappings reference known identities; no active collisions."""
        for mapping in self._by_key.values():
            if not self._taxonomy.contains(mapping.industry_id):
                msg = (
                    f"broken mapping reference to unknown industry "
                    f"{mapping.industry_id!r}"
                )
                raise IndustryError(msg)
        # Group ACTIVE by classification key
        active_by_class: dict[tuple[str, str, str], list[IndustryMapping]] = {}
        for mapping in self._by_key.values():
            if mapping.status is not MappingStatus.ACTIVE:
                continue
            active_by_class.setdefault(mapping.classification.key, []).append(
                mapping
            )
        for class_key, group in active_by_class.items():
            industry_ids = {m.industry_id for m in group}
            if len(industry_ids) > 1:
                msg = (
                    f"active mapping collision for {class_key!r}: "
                    f"maps to {sorted(industry_ids)}"
                )
                raise IndustryError(msg)

    def _assert_no_active_collision(self, mapping: IndustryMapping) -> None:
        class_key = mapping.classification.key
        for existing in self._by_key.values():
            if existing.status is not MappingStatus.ACTIVE:
                continue
            if existing.classification.key != class_key:
                continue
            if existing.industry_id != mapping.industry_id:
                msg = (
                    f"active mapping collision: {class_key!r} already maps to "
                    f"{existing.industry_id!r}, cannot also map to "
                    f"{mapping.industry_id!r}"
                )
                raise IndustryError(msg)
