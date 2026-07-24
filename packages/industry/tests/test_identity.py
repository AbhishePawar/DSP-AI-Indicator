"""Industry identity and hierarchy tests."""

from __future__ import annotations

import pytest

from core.exceptions import ValidationError
from industry import (
    IdentityLifecycle,
    IndustryError,
    IndustryIdentity,
    IndustryTaxonomy,
)


def _id(
    identity_id: str,
    name: str,
    *,
    parent_id: str | None = None,
    status: IdentityLifecycle = IdentityLifecycle.ACTIVE,
) -> IndustryIdentity:
    return IndustryIdentity(
        id=identity_id,
        name=name,
        parent_id=parent_id,
        status=status,
    )


class TestIndustryIdentity:
    def test_normalizes_id(self) -> None:
        identity = _id("DSP.Industry.Utilities", "Utilities")
        assert identity.id == "dsp.industry.utilities"

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            IndustryIdentity(id="dsp.industry.x", name="  ")

    def test_rejects_self_parent(self) -> None:
        with pytest.raises(ValidationError):
            IndustryIdentity(
                id="dsp.industry.x",
                name="X",
                parent_id="dsp.industry.x",
            )


class TestIndustryTaxonomy:
    def test_register_and_get(self) -> None:
        tax = IndustryTaxonomy()
        root = tax.register(_id("dsp.industry.energy", "Energy"))
        child = tax.register(
            _id("dsp.industry.utilities", "Utilities", parent_id=root.id)
        )
        assert tax.get(child.id).name == "Utilities"
        assert tax.parent(child.id) == root
        assert tax.children(root.id) == (child,)

    def test_duplicate_rejected(self) -> None:
        tax = IndustryTaxonomy()
        tax.register(_id("dsp.industry.banks", "Banks"))
        with pytest.raises(IndustryError, match="duplicate"):
            tax.register(_id("dsp.industry.banks", "Banks Again"))

    def test_unknown_parent_rejected(self) -> None:
        tax = IndustryTaxonomy()
        with pytest.raises(IndustryError, match="unknown parent"):
            tax.register(
                _id(
                    "dsp.industry.utilities",
                    "Utilities",
                    parent_id="dsp.industry.missing",
                )
            )

    def test_circular_hierarchy_detected_on_validate(self) -> None:
        tax = IndustryTaxonomy()
        tax.register(_id("a", "A"))
        tax.register(_id("b", "B", parent_id="a"))
        # Simulate corruption / illegal back-edge A → B.
        tax._identities["a"] = IndustryIdentity(id="a", name="A", parent_id="b")
        with pytest.raises(IndustryError, match="circular"):
            tax.validate()

    def test_ancestors_and_descendants(self) -> None:
        tax = IndustryTaxonomy()
        energy = tax.register(_id("dsp.industry.energy", "Energy"))
        util = tax.register(
            _id("dsp.industry.utilities", "Utilities", parent_id=energy.id)
        )
        power = tax.register(
            _id("dsp.industry.power", "Power", parent_id=util.id)
        )
        assert tax.ancestors(power.id) == (util, energy)
        assert tax.descendants(energy.id) == (power, util)

    def test_list_and_roots(self) -> None:
        tax = IndustryTaxonomy()
        tax.register(_id("dsp.industry.a", "A"))
        tax.register(
            _id(
                "dsp.industry.b",
                "B",
                status=IdentityLifecycle.DEPRECATED,
            )
        )
        assert len(tax.roots()) == 2
        assert len(tax.list_identities(status=IdentityLifecycle.ACTIVE)) == 1

    def test_unknown_get(self) -> None:
        tax = IndustryTaxonomy()
        with pytest.raises(IndustryError, match="unknown"):
            tax.get("missing")
