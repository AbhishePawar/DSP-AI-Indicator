"""Classification mapping registry tests."""

from __future__ import annotations

import pytest

from industry import (
    ClassificationMappingRegistry,
    ClassificationReference,
    IndustryError,
    IndustryIdentity,
    IndustryMapping,
    IndustryTaxonomy,
    MappingStatus,
    TaxonomySource,
)


def _tax_with(*ids: tuple[str, str]) -> IndustryTaxonomy:
    tax = IndustryTaxonomy()
    for identity_id, name in ids:
        tax.register(IndustryIdentity(id=identity_id, name=name))
    return tax


def _mapping(
    *,
    source: TaxonomySource,
    code: str,
    industry_id: str,
    mapping_version: str,
    status: MappingStatus = MappingStatus.ACTIVE,
    taxonomy_version: str | None = None,
) -> IndustryMapping:
    return IndustryMapping(
        classification=ClassificationReference(
            source=source,
            code=code,
            taxonomy_version=taxonomy_version,
            label=code,
        ),
        industry_id=industry_id,
        mapping_version=mapping_version,
        status=status,
    )


class TestClassificationMappingRegistry:
    def test_register_and_lookup_active(self) -> None:
        tax = _tax_with(("dsp.industry.utilities", "Utilities"))
        registry = ClassificationMappingRegistry(tax)
        registry.register(
            _mapping(
                source=TaxonomySource.GICS,
                code="5510",
                industry_id="dsp.industry.utilities",
                mapping_version="1.0.0",
            )
        )
        found = registry.lookup_active(TaxonomySource.GICS, "5510")
        assert found.industry_id == "dsp.industry.utilities"

    def test_unknown_mapping(self) -> None:
        tax = _tax_with(("dsp.industry.utilities", "Utilities"))
        registry = ClassificationMappingRegistry(tax)
        with pytest.raises(IndustryError, match="no active mapping"):
            registry.lookup_active(TaxonomySource.NSE, "BANK")

    def test_unknown_industry_rejected(self) -> None:
        tax = IndustryTaxonomy()
        registry = ClassificationMappingRegistry(tax)
        with pytest.raises(IndustryError, match="unknown industry"):
            registry.register(
                _mapping(
                    source=TaxonomySource.NSE,
                    code="BANK",
                    industry_id="dsp.industry.banks",
                    mapping_version="1.0.0",
                )
            )

    def test_active_collision_rejected(self) -> None:
        tax = _tax_with(
            ("dsp.industry.banks", "Banks"),
            ("dsp.industry.nbfc", "NBFC"),
        )
        registry = ClassificationMappingRegistry(tax)
        registry.register(
            _mapping(
                source=TaxonomySource.NSE,
                code="FINANCIAL",
                industry_id="dsp.industry.banks",
                mapping_version="1.0.0",
            )
        )
        with pytest.raises(IndustryError, match="collision"):
            registry.register(
                _mapping(
                    source=TaxonomySource.NSE,
                    code="FINANCIAL",
                    industry_id="dsp.industry.nbfc",
                    mapping_version="1.0.1",
                )
            )

    def test_versioning_and_deprecate(self) -> None:
        tax = _tax_with(("dsp.industry.software", "Software"))
        registry = ClassificationMappingRegistry(tax)
        registry.register(
            _mapping(
                source=TaxonomySource.ICB,
                code="10101010",
                industry_id="dsp.industry.software",
                mapping_version="1.0.0",
            )
        )
        registry.deprecate(
            TaxonomySource.ICB, "10101010", mapping_version="1.0.0"
        )
        registry.register(
            _mapping(
                source=TaxonomySource.ICB,
                code="10101010",
                industry_id="dsp.industry.software",
                mapping_version="2.0.0",
            )
        )
        active = registry.lookup_active(TaxonomySource.ICB, "10101010")
        assert active.mapping_version == "2.0.0"
        old = registry.get(
            TaxonomySource.ICB, "10101010", mapping_version="1.0.0"
        )
        assert old.status is MappingStatus.DEPRECATED

    def test_list_for_industry(self) -> None:
        tax = _tax_with(("dsp.industry.cement", "Cement"))
        registry = ClassificationMappingRegistry(tax)
        registry.register(
            _mapping(
                source=TaxonomySource.BSE,
                code="CEMENT",
                industry_id="dsp.industry.cement",
                mapping_version="1.0.0",
            )
        )
        registry.register(
            _mapping(
                source=TaxonomySource.GICS,
                code="15102010",
                industry_id="dsp.industry.cement",
                mapping_version="1.0.0",
            )
        )
        listed = registry.list_mappings(industry_id="dsp.industry.cement")
        assert len(listed) == 2

    def test_validate_integrity(self) -> None:
        tax = _tax_with(("dsp.industry.pharma", "Pharma"))
        registry = ClassificationMappingRegistry(tax)
        registry.register(
            _mapping(
                source=TaxonomySource.CUSTOM,
                code="PHARMA",
                industry_id="dsp.industry.pharma",
                mapping_version="1.0.0",
            )
        )
        registry.validate()
