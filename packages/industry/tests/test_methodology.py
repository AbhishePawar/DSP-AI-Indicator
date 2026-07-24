"""Industry Methodology registry and merge tests."""

from __future__ import annotations

import pytest

from core.exceptions import ValidationError
from industry import (
    AssembledMethodology,
    ComparisonDimension,
    IndustryError,
    IndustryIdentity,
    IndustryMethodology,
    IndustryMethodologyRegistry,
    IndustryTaxonomy,
    InvestmentCharacteristics,
    InvestmentCharacteristicsRegistry,
    MergeSource,
    MethodologyLifecycle,
    PeerEligibilityPolicyRef,
    ValuationProfile,
    assemble_methodology,
    build_example_methodologies,
    compare_semver,
    parse_semver,
    register_example_archetypes,
    register_example_methodologies,
    seed_example_industry_context,
)


def _tax_with(*ids: str) -> IndustryTaxonomy:
    tax = IndustryTaxonomy()
    for iid in ids:
        tax.register(IndustryIdentity(id=iid, name=iid))
    return tax


class TestSemVer:
    def test_ordering_not_lexicographic(self) -> None:
        assert compare_semver("1.10.0", "1.9.0") == 1
        assert parse_semver("1.10.0") > parse_semver("1.9.0")

    def test_invalid_rejected(self) -> None:
        with pytest.raises(ValidationError, match="semantic version"):
            parse_semver("1.0")
        with pytest.raises(ValidationError, match="semantic version"):
            IndustryMethodology(
                id="dsp.methodology.x",
                industry_id="dsp.industry.x",
                version="v1",
            )


class TestMethodologyRegistry:
    def test_register_lookup_list_deprecate(self) -> None:
        tax = _tax_with("dsp.industry.banks")
        chars = InvestmentCharacteristicsRegistry()
        reg = IndustryMethodologyRegistry(tax, chars)
        m1 = IndustryMethodology(
            id="dsp.methodology.banks",
            industry_id="dsp.industry.banks",
            version="1.0.0",
            name="Banks",
        )
        m2 = IndustryMethodology(
            id="dsp.methodology.banks",
            industry_id="dsp.industry.banks",
            version="1.10.0",
            name="Banks",
        )
        m_mid = IndustryMethodology(
            id="dsp.methodology.banks",
            industry_id="dsp.industry.banks",
            version="1.9.0",
            name="Banks",
        )
        reg.register(m1)
        reg.register(m_mid)
        reg.register(m2)
        assert reg.lookup_active("dsp.methodology.banks").version == "1.10.0"
        assert reg.lookup("dsp.methodology.banks", version="1.0.0") == m1
        assert len(reg.list_all(industry_id="dsp.industry.banks")) == 3
        reg.deprecate("dsp.methodology.banks", version="1.10.0")
        assert reg.lookup_active("dsp.methodology.banks").version == "1.9.0"

    def test_duplicate_rejected(self) -> None:
        tax = _tax_with("dsp.industry.x")
        reg = IndustryMethodologyRegistry(tax)
        reg.register(
            IndustryMethodology(
                id="dsp.methodology.x",
                industry_id="dsp.industry.x",
                version="1.0.0",
            )
        )
        with pytest.raises(IndustryError, match="duplicate"):
            reg.register(
                IndustryMethodology(
                    id="dsp.methodology.x",
                    industry_id="dsp.industry.x",
                    version="1.0.0",
                    name="Different",
                )
            )

    def test_unknown_industry_rejected(self) -> None:
        tax = IndustryTaxonomy()
        reg = IndustryMethodologyRegistry(tax)
        with pytest.raises(IndustryError, match="unknown industry"):
            reg.register(
                IndustryMethodology(
                    id="dsp.methodology.x",
                    industry_id="dsp.industry.missing",
                    version="1.0.0",
                )
            )

    def test_unknown_characteristic_rejected(self) -> None:
        tax = _tax_with("dsp.industry.x")
        chars = InvestmentCharacteristicsRegistry()
        reg = IndustryMethodologyRegistry(tax, chars)
        with pytest.raises(IndustryError, match="unknown investment"):
            reg.register(
                IndustryMethodology(
                    id="dsp.methodology.x",
                    industry_id="dsp.industry.x",
                    version="1.0.0",
                    characteristic_ids=("dsp.characteristics.missing",),
                )
            )

    def test_one_lineage_per_industry(self) -> None:
        tax = _tax_with("dsp.industry.x")
        reg = IndustryMethodologyRegistry(tax)
        reg.register(
            IndustryMethodology(
                id="dsp.methodology.a",
                industry_id="dsp.industry.x",
                version="1.0.0",
            )
        )
        with pytest.raises(IndustryError, match="already bound"):
            reg.register(
                IndustryMethodology(
                    id="dsp.methodology.b",
                    industry_id="dsp.industry.x",
                    version="1.0.0",
                )
            )

    def test_invalid_valuation_overlap(self) -> None:
        with pytest.raises(ValidationError, match="preferred and unsupported"):
            ValuationProfile(preferred=("dcf",), unsupported=("dcf",))


class TestMergePrecedence:
    def test_methodology_wins(self) -> None:
        chars = InvestmentCharacteristicsRegistry()
        register_example_archetypes(chars)
        stable = chars.lookup_active(
            "dsp.characteristics.stable_regulated_cash_flow"
        )
        methodology = IndustryMethodology(
            id="dsp.methodology.utilities",
            industry_id="dsp.industry.utilities",
            version="1.0.0",
            characteristic_ids=(stable.id,),
            valuation=ValuationProfile(
                preferred=("nav",),
                unsupported=("earnings_multiple",),
            ),
            dimensions=(ComparisonDimension.RISK,),
        )
        assembled = assemble_methodology(methodology, (stable,))
        assert isinstance(assembled, AssembledMethodology)
        assert assembled.valuation_source is MergeSource.METHODOLOGY
        assert assembled.valuation.preferred == ("nav",)
        assert assembled.dimensions_source is MergeSource.METHODOLOGY
        assert assembled.dimensions == (ComparisonDimension.RISK,)
        assert "valuation: methodology override" in assembled.merge_trace

    def test_characteristics_then_system(self) -> None:
        chars = InvestmentCharacteristicsRegistry()
        register_example_archetypes(chars)
        franchise = chars.lookup_active(
            "dsp.characteristics.pricing_power_franchise"
        )
        with_chars = IndustryMethodology(
            id="dsp.methodology.luxury",
            industry_id="dsp.industry.luxury",
            version="1.0.0",
            characteristic_ids=(franchise.id,),
            valuation=None,
            dimensions=None,
        )
        assembled = assemble_methodology(with_chars, (franchise,))
        assert assembled.valuation_source is MergeSource.CHARACTERISTICS
        assert assembled.dimensions_source is MergeSource.CHARACTERISTICS
        assert ComparisonDimension.QUALITY in assembled.dimensions

        bare = IndustryMethodology(
            id="dsp.methodology.bare",
            industry_id="dsp.industry.bare",
            version="1.0.0",
        )
        system = assemble_methodology(bare, ())
        assert system.valuation_source is MergeSource.SYSTEM
        assert system.dimensions_source is MergeSource.SYSTEM

    def test_metrics_and_peers_never_from_characteristics(self) -> None:
        methodology = IndustryMethodology(
            id="dsp.methodology.x",
            industry_id="dsp.industry.x",
            version="1.0.0",
            peer_policy=PeerEligibilityPolicyRef(
                policy_id="dsp.peer_policy.x"
            ),
        )
        assembled = assemble_methodology(methodology, ())
        assert assembled.metrics == ()
        assert assembled.peer_policy is not None
        assert assembled.peer_policy.policy_id == "dsp.peer_policy.x"


class TestExampleMethodologies:
    def test_examples_register_and_assemble(self) -> None:
        tax = IndustryTaxonomy()
        chars = InvestmentCharacteristicsRegistry()
        seed_example_industry_context(tax, chars)
        reg = IndustryMethodologyRegistry(tax, chars)
        register_example_methodologies(reg)
        assert len(build_example_methodologies()) == 3
        reg.validate()
        utilities = reg.lookup_active("dsp.methodology.electric_utilities")
        assembled = reg.assemble(utilities)
        assert assembled.valuation_source is MergeSource.METHODOLOGY
        assert assembled.dimensions_source is MergeSource.CHARACTERISTICS
        franchise = reg.lookup_active(
            "dsp.methodology.premium_consumer_franchise"
        )
        fran_assembled = reg.assemble(franchise)
        assert fran_assembled.valuation_source is MergeSource.CHARACTERISTICS
        assert fran_assembled.dimensions_source is MergeSource.METHODOLOGY

    def test_characteristics_semver_active(self) -> None:
        chars = InvestmentCharacteristicsRegistry()
        chars.register(
            InvestmentCharacteristics(
                id="dsp.characteristics.demo",
                name="Demo",
                version="1.9.0",
            )
        )
        chars.register(
            InvestmentCharacteristics(
                id="dsp.characteristics.demo",
                name="Demo",
                version="1.10.0",
            )
        )
        assert chars.lookup_active("dsp.characteristics.demo").version == "1.10.0"
