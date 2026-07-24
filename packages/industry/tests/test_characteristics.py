"""Investment Characteristics registry tests."""

from __future__ import annotations

import pytest

from core.exceptions import ValidationError
from industry import (
    CharacteristicDefaults,
    CharacteristicLifecycle,
    ComparisonDimensionHint,
    IndustryError,
    IndustryIdentity,
    IndustryProfile,
    IndustryProfileRegistry,
    IndustryTaxonomy,
    InvestmentCharacteristics,
    InvestmentCharacteristicsRegistry,
    ValuationPhilosophyHint,
    build_example_archetypes,
    register_example_archetypes,
)


def _char(
    cid: str,
    *,
    version: str = "1.0.0",
    status: CharacteristicLifecycle = CharacteristicLifecycle.ACTIVE,
) -> InvestmentCharacteristics:
    return InvestmentCharacteristics(
        id=cid,
        name=cid,
        version=version,
        status=status,
        defaults=CharacteristicDefaults(
            valuation_philosophy=ValuationPhilosophyHint.INCOME,
            dimension_emphasis=(ComparisonDimensionHint.VALUATION,),
        ),
    )


class TestInvestmentCharacteristics:
    def test_immutable_and_normalized(self) -> None:
        c = _char("DSP.Characteristics.Demo")
        assert c.id == "dsp.characteristics.demo"
        with pytest.raises(ValidationError):
            InvestmentCharacteristics(id="x", name="X", version="  ")

    def test_registry_register_lookup_list(self) -> None:
        reg = InvestmentCharacteristicsRegistry()
        reg.register(_char("dsp.characteristics.a", version="1.0.0"))
        reg.register(_char("dsp.characteristics.a", version="2.0.0"))
        assert reg.lookup_active("dsp.characteristics.a").version == "2.0.0"
        assert len(reg.list_all()) == 2

    def test_duplicate_rejected(self) -> None:
        reg = InvestmentCharacteristicsRegistry()
        reg.register(_char("dsp.characteristics.a"))
        with pytest.raises(IndustryError, match="duplicate"):
            reg.register(
                InvestmentCharacteristics(
                    id="dsp.characteristics.a",
                    name="Different Name",
                    version="1.0.0",
                )
            )

    def test_deprecate(self) -> None:
        reg = InvestmentCharacteristicsRegistry()
        reg.register(_char("dsp.characteristics.a", version="1.0.0"))
        reg.deprecate("dsp.characteristics.a", version="1.0.0")
        with pytest.raises(IndustryError, match="no active"):
            reg.lookup_active("dsp.characteristics.a")
        assert (
            reg.get("dsp.characteristics.a", version="1.0.0").status
            is CharacteristicLifecycle.DEPRECATED
        )

    def test_validate(self) -> None:
        reg = InvestmentCharacteristicsRegistry()
        reg.register(_char("dsp.characteristics.a"))
        reg.validate()

    def test_example_archetypes(self) -> None:
        reg = InvestmentCharacteristicsRegistry()
        register_example_archetypes(reg)
        assert len(build_example_archetypes()) == 5
        assert len(reg.list_all(status=CharacteristicLifecycle.ACTIVE)) == 5
        stable = reg.lookup_active(
            "dsp.characteristics.stable_regulated_cash_flow"
        )
        assert stable.defaults.valuation_philosophy is ValuationPhilosophyHint.INCOME


class TestIndustryProfileReferences:
    def test_profile_references_characteristics(self) -> None:
        tax = IndustryTaxonomy()
        tax.register(
            IndustryIdentity(id="dsp.industry.utilities", name="Utilities")
        )
        chars = InvestmentCharacteristicsRegistry()
        chars.register(
            _char("dsp.characteristics.stable_regulated_cash_flow")
        )
        profiles = IndustryProfileRegistry(tax, chars)
        profile = profiles.register(
            IndustryProfile(
                industry_id="dsp.industry.utilities",
                version="1.0.0",
                characteristic_ids=(
                    "dsp.characteristics.stable_regulated_cash_flow",
                ),
            )
        )
        assert profile.characteristic_ids == (
            "dsp.characteristics.stable_regulated_cash_flow",
        )
        assert profiles.lookup_active("dsp.industry.utilities") == profile

    def test_unknown_characteristic_rejected(self) -> None:
        tax = IndustryTaxonomy()
        tax.register(IndustryIdentity(id="dsp.industry.x", name="X"))
        chars = InvestmentCharacteristicsRegistry()
        profiles = IndustryProfileRegistry(tax, chars)
        with pytest.raises(IndustryError, match="unknown investment"):
            profiles.register(
                IndustryProfile(
                    industry_id="dsp.industry.x",
                    version="1.0.0",
                    characteristic_ids=("dsp.characteristics.missing",),
                )
            )

    def test_unknown_industry_rejected(self) -> None:
        tax = IndustryTaxonomy()
        chars = InvestmentCharacteristicsRegistry()
        chars.register(_char("dsp.characteristics.a"))
        profiles = IndustryProfileRegistry(tax, chars)
        with pytest.raises(IndustryError, match="unknown industry"):
            profiles.register(
                IndustryProfile(
                    industry_id="dsp.industry.missing",
                    version="1.0.0",
                    characteristic_ids=("dsp.characteristics.a",),
                )
            )

    def test_zero_characteristics_allowed(self) -> None:
        tax = IndustryTaxonomy()
        tax.register(IndustryIdentity(id="dsp.industry.x", name="X"))
        chars = InvestmentCharacteristicsRegistry()
        profiles = IndustryProfileRegistry(tax, chars)
        profile = profiles.register(
            IndustryProfile(industry_id="dsp.industry.x", version="1.0.0")
        )
        assert profile.characteristic_ids == ()
