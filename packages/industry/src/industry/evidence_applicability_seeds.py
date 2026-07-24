"""Illustrative Evidence Applicability for example methodologies (C3.2)."""

from __future__ import annotations

from industry.enums import ApplicabilityLevel, MissingEvidencePolicy
from industry.evidence_applicability import (
    ApplicabilityGroup,
    EvidenceApplicabilityRule,
    IndustryEvidenceApplicability,
    RequiredEvidenceSet,
)
from industry.evidence_applicability_registry import (
    IndustryEvidenceApplicabilityRegistry,
)
from industry.evidence_registry import IndustryEvidenceRegistry, IndustryMetricRegistry
from industry.evidence_seeds import seed_example_evidence_registries
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.methodology_seeds import (
    register_example_methodologies,
    seed_example_industry_context,
)
from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.taxonomy import IndustryTaxonomy

__all__ = [
    "EXAMPLE_APPLICABILITY_IDS",
    "build_example_evidence_applicability",
    "register_example_evidence_applicability",
    "seed_example_evidence_applicability_context",
]

EXAMPLE_APPLICABILITY_IDS: tuple[str, ...] = (
    "dsp.evidence_applicability.commercial_banking",
    "dsp.evidence_applicability.electric_utilities",
    "dsp.evidence_applicability.premium_consumer_franchise",
)


def build_example_evidence_applicability() -> tuple[
    IndustryEvidenceApplicability, ...
]:
    return (
        IndustryEvidenceApplicability(
            id="dsp.evidence_applicability.commercial_banking",
            methodology_id="dsp.methodology.commercial_banking",
            version="1.0.0",
            methodology_version_pin="1.0.0",
            groups=(
                ApplicabilityGroup(
                    id="dsp.applicability_group.banking_core",
                    name="Banking Core KPIs",
                    description="Deposit-franchise operating evidence.",
                ),
            ),
            rules=(
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.nim_stability",
                    level=ApplicabilityLevel.REQUIRED,
                    group_id="dsp.applicability_group.banking_core",
                ),
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.roe_persistence",
                    level=ApplicabilityLevel.RECOMMENDED,
                ),
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.regulated_cash_flow_visibility",
                    level=ApplicabilityLevel.UNSUPPORTED,
                    notes=("Utility regulatory evidence does not apply to banks.",),
                ),
            ),
            required_sets=(
                RequiredEvidenceSet(
                    id="dsp.required_set.banking_minimum",
                    name="Banking Minimum Evidence",
                    evidence_ids=("dsp.evidence.nim_stability",),
                ),
            ),
            missing_evidence_policy=MissingEvidencePolicy.DEGRADE,
            notes=("Illustrative banking applicability — no providers in C3.2.",),
        ),
        IndustryEvidenceApplicability(
            id="dsp.evidence_applicability.electric_utilities",
            methodology_id="dsp.methodology.electric_utilities",
            version="1.0.0",
            methodology_version_pin="1.0.0",
            rules=(
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.regulated_cash_flow_visibility",
                    level=ApplicabilityLevel.REQUIRED,
                ),
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.roe_persistence",
                    level=ApplicabilityLevel.OPTIONAL,
                ),
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.nim_stability",
                    level=ApplicabilityLevel.UNSUPPORTED,
                ),
            ),
            required_sets=(
                RequiredEvidenceSet(
                    id="dsp.required_set.utilities_minimum",
                    name="Utilities Minimum Evidence",
                    evidence_ids=(
                        "dsp.evidence.regulated_cash_flow_visibility",
                    ),
                ),
            ),
            missing_evidence_policy=MissingEvidencePolicy.RECORD_GAP,
        ),
        IndustryEvidenceApplicability(
            id="dsp.evidence_applicability.premium_consumer_franchise",
            methodology_id="dsp.methodology.premium_consumer_franchise",
            version="1.0.0",
            methodology_version_pin="1.0.0",
            rules=(
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.roe_persistence",
                    level=ApplicabilityLevel.RECOMMENDED,
                ),
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.nim_stability",
                    level=ApplicabilityLevel.UNSUPPORTED,
                ),
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.regulated_cash_flow_visibility",
                    level=ApplicabilityLevel.UNSUPPORTED,
                ),
            ),
            required_sets=(),
            missing_evidence_policy=MissingEvidencePolicy.RECORD_GAP,
            notes=("Franchise starts OPTIONAL/RECOMMENDED-heavy per IEF freeze.",),
        ),
    )


def register_example_evidence_applicability(
    registry: IndustryEvidenceApplicabilityRegistry,
) -> IndustryEvidenceApplicabilityRegistry:
    for item in build_example_evidence_applicability():
        registry.register(item)
    return registry


def seed_example_evidence_applicability_context(
    taxonomy: IndustryTaxonomy | None = None,
    characteristics: InvestmentCharacteristicsRegistry | None = None,
    methodologies: IndustryMethodologyRegistry | None = None,
    metrics: IndustryMetricRegistry | None = None,
    evidence: IndustryEvidenceRegistry | None = None,
    applicability: IndustryEvidenceApplicabilityRegistry | None = None,
) -> tuple[
    IndustryTaxonomy,
    InvestmentCharacteristicsRegistry,
    IndustryMethodologyRegistry,
    IndustryMetricRegistry,
    IndustryEvidenceRegistry,
    IndustryEvidenceApplicabilityRegistry,
]:
    """Seed identities, methodologies, evidence defs, and applicability."""
    tax = taxonomy or IndustryTaxonomy()
    chars = characteristics or InvestmentCharacteristicsRegistry()
    methods = methodologies or IndustryMethodologyRegistry(tax, chars)
    seed_example_industry_context(tax, chars)
    register_example_methodologies(methods)
    metric_reg, evidence_reg = seed_example_evidence_registries(metrics, evidence)
    app_reg = applicability or IndustryEvidenceApplicabilityRegistry(
        methods, evidence_reg
    )
    register_example_evidence_applicability(app_reg)
    return tax, chars, methods, metric_reg, evidence_reg, app_reg
