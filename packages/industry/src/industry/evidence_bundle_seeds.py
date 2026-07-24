"""Seed helpers for EvidenceBundle assembly demos (C3.5)."""

from __future__ import annotations

from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.evidence_applicability_registry import (
    IndustryEvidenceApplicabilityRegistry,
)
from industry.evidence_applicability_seeds import (
    seed_example_evidence_applicability_context,
)
from industry.evidence_bundle import EvidenceBundleAssemblyContext
from industry.evidence_bundle_assembler import EvidenceBundleAssembler
from industry.evidence_interpreter_registry import IndustryEvidenceInterpreterRegistry
from industry.evidence_interpreter_seeds import register_example_evidence_interpreters
from industry.evidence_provider_registry import IndustryEvidenceProviderRegistry
from industry.evidence_provider_seeds import register_example_evidence_providers
from industry.evidence_registry import IndustryEvidenceRegistry, IndustryMetricRegistry
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.taxonomy import IndustryTaxonomy

__all__ = [
    "example_banking_assembly_context",
    "seed_example_evidence_bundle_assembler",
    "seed_example_evidence_bundle_context",
]


def seed_example_evidence_bundle_context() -> tuple[
    IndustryTaxonomy,
    InvestmentCharacteristicsRegistry,
    IndustryMethodologyRegistry,
    IndustryMetricRegistry,
    IndustryEvidenceRegistry,
    IndustryEvidenceApplicabilityRegistry,
    IndustryEvidenceProviderRegistry,
    IndustryEvidenceInterpreterRegistry,
]:
    """Seed full IEF stack through interpreters for bundle assembly demos."""
    tax, chars, methods, metrics, evidence, applicability = (
        seed_example_evidence_applicability_context()
    )
    providers = IndustryEvidenceProviderRegistry(evidence)
    register_example_evidence_providers(providers)
    interpreters = IndustryEvidenceInterpreterRegistry(evidence)
    register_example_evidence_interpreters(interpreters)
    return (
        tax,
        chars,
        methods,
        metrics,
        evidence,
        applicability,
        providers,
        interpreters,
    )


def seed_example_evidence_bundle_assembler() -> EvidenceBundleAssembler:
    *_, evidence, applicability, providers, interpreters = (
        seed_example_evidence_bundle_context()
    )
    return EvidenceBundleAssembler(
        evidence=evidence,
        applicability=applicability,
        providers=providers,
        interpreters=interpreters,
    )


def example_banking_assembly_context(
    *,
    instrument_key: str = "HDFCBANK",
    emit_placeholder: bool = False,
) -> EvidenceBundleAssemblyContext:
    extras: tuple[tuple[str, str], ...] = ()
    if emit_placeholder:
        extras = (("emit_placeholder", "true"),)
    return EvidenceBundleAssemblyContext(
        instrument_key=instrument_key,
        methodology_id="dsp.methodology.commercial_banking",
        methodology_version="1.0.0",
        as_of="2026-07-21",
        extras=extras,
    )
