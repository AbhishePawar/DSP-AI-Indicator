"""Industry Evidence Applicability tests (C3.2)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError

from industry import (
    ApplicabilityLevel,
    EvidenceApplicabilityRule,
    IndustryError,
    IndustryEvidenceApplicability,
    IndustryEvidenceApplicabilityRegistry,
    IndustryEvidenceRegistry,
    IndustryMethodologyRegistry,
    IndustryMetricRegistry,
    MissingEvidencePolicy,
    RequiredEvidenceSet,
    seed_example_evidence_applicability_context,
    seed_example_evidence_registries,
    seed_example_industry_context,
    InvestmentCharacteristicsRegistry,
    IndustryTaxonomy,
    register_example_methodologies,
)


def _ctx() -> tuple[
    IndustryMethodologyRegistry,
    IndustryEvidenceRegistry,
    IndustryEvidenceApplicabilityRegistry,
]:
    tax = IndustryTaxonomy()
    chars = InvestmentCharacteristicsRegistry()
    methods = IndustryMethodologyRegistry(tax, chars)
    seed_example_industry_context(tax, chars)
    register_example_methodologies(methods)
    metrics, evidence = seed_example_evidence_registries()
    apps = IndustryEvidenceApplicabilityRegistry(methods, evidence)
    return methods, evidence, apps


class TestApplicabilityModels:
    def test_conflict_in_constructor(self) -> None:
        with pytest.raises(ValidationError, match="conflicting"):
            IndustryEvidenceApplicability(
                id="dsp.evidence_applicability.x",
                methodology_id="dsp.methodology.commercial_banking",
                version="1.0.0",
                rules=(
                    EvidenceApplicabilityRule(
                        evidence_id="dsp.evidence.nim_stability",
                        level=ApplicabilityLevel.REQUIRED,
                    ),
                    EvidenceApplicabilityRule(
                        evidence_id="dsp.evidence.nim_stability",
                        level=ApplicabilityLevel.UNSUPPORTED,
                    ),
                ),
            )

    def test_conditional_requires_notes(self) -> None:
        with pytest.raises(ValidationError, match="condition_notes"):
            EvidenceApplicabilityRule(
                evidence_id="dsp.evidence.roe_persistence",
                level=ApplicabilityLevel.CONDITIONAL,
            )

    def test_required_set_rejects_unsupported(self) -> None:
        with pytest.raises(ValidationError, match="UNSUPPORTED"):
            IndustryEvidenceApplicability(
                id="dsp.evidence_applicability.x",
                methodology_id="dsp.methodology.commercial_banking",
                version="1.0.0",
                rules=(
                    EvidenceApplicabilityRule(
                        evidence_id="dsp.evidence.nim_stability",
                        level=ApplicabilityLevel.UNSUPPORTED,
                    ),
                ),
                required_sets=(
                    RequiredEvidenceSet(
                        id="dsp.required_set.x",
                        name="X",
                        evidence_ids=("dsp.evidence.nim_stability",),
                    ),
                ),
            )


class TestApplicabilityRegistry:
    def test_register_lookup_required_optional_unsupported(self) -> None:
        *_, apps = seed_example_evidence_applicability_context()
        banking = apps.lookup_active_for_methodology(
            "dsp.methodology.commercial_banking"
        )
        assert banking.required_evidence_ids() == (
            "dsp.evidence.nim_stability",
        )
        assert "dsp.evidence.regulated_cash_flow_visibility" in (
            banking.unsupported_evidence_ids()
        )
        recommended = banking.rules_by_level(ApplicabilityLevel.RECOMMENDED)
        assert any(
            r.evidence_id == "dsp.evidence.roe_persistence" for r in recommended
        )
        assert banking.missing_evidence_policy is MissingEvidencePolicy.DEGRADE
        apps.validate()

    def test_unknown_methodology_rejected(self) -> None:
        methods, evidence, apps = _ctx()
        with pytest.raises(IndustryError, match="unknown methodology"):
            apps.register(
                IndustryEvidenceApplicability(
                    id="dsp.evidence_applicability.missing",
                    methodology_id="dsp.methodology.does_not_exist",
                    version="1.0.0",
                    rules=(
                        EvidenceApplicabilityRule(
                            evidence_id="dsp.evidence.roe_persistence",
                            level=ApplicabilityLevel.OPTIONAL,
                        ),
                    ),
                )
            )

    def test_unknown_evidence_rejected(self) -> None:
        methods, evidence, apps = _ctx()
        with pytest.raises(IndustryError, match="unknown evidence"):
            apps.register(
                IndustryEvidenceApplicability(
                    id="dsp.evidence_applicability.banks",
                    methodology_id="dsp.methodology.commercial_banking",
                    version="1.0.0",
                    rules=(
                        EvidenceApplicabilityRule(
                            evidence_id="dsp.evidence.missing",
                            level=ApplicabilityLevel.REQUIRED,
                        ),
                    ),
                )
            )

    def test_duplicate_applicability_rejected(self) -> None:
        *_, apps = seed_example_evidence_applicability_context()
        banking = apps.lookup_active(
            "dsp.evidence_applicability.commercial_banking"
        )
        with pytest.raises(IndustryError, match="duplicate"):
            apps.register(
                IndustryEvidenceApplicability(
                    id=banking.id,
                    methodology_id=banking.methodology_id,
                    version=banking.version,
                    rules=(
                        EvidenceApplicabilityRule(
                            evidence_id="dsp.evidence.nim_stability",
                            level=ApplicabilityLevel.OPTIONAL,
                        ),
                    ),
                )
            )

    def test_one_lineage_per_methodology(self) -> None:
        methods, evidence, apps = _ctx()
        apps.register(
            IndustryEvidenceApplicability(
                id="dsp.evidence_applicability.banks_a",
                methodology_id="dsp.methodology.commercial_banking",
                version="1.0.0",
                rules=(
                    EvidenceApplicabilityRule(
                        evidence_id="dsp.evidence.nim_stability",
                        level=ApplicabilityLevel.REQUIRED,
                    ),
                ),
            )
        )
        with pytest.raises(IndustryError, match="already bound"):
            apps.register(
                IndustryEvidenceApplicability(
                    id="dsp.evidence_applicability.banks_b",
                    methodology_id="dsp.methodology.commercial_banking",
                    version="1.0.0",
                    rules=(
                        EvidenceApplicabilityRule(
                            evidence_id="dsp.evidence.roe_persistence",
                            level=ApplicabilityLevel.OPTIONAL,
                        ),
                    ),
                )
            )

    def test_example_methodologies_covered(self) -> None:
        *_, apps = seed_example_evidence_applicability_context()
        for mid in (
            "dsp.methodology.commercial_banking",
            "dsp.methodology.electric_utilities",
            "dsp.methodology.premium_consumer_franchise",
        ):
            app = apps.lookup_active_for_methodology(mid)
            assert app.rules
        utilities = apps.lookup_active_for_methodology(
            "dsp.methodology.electric_utilities"
        )
        assert utilities.required_evidence_ids() == (
            "dsp.evidence.regulated_cash_flow_visibility",
        )
