"""Industry package public API — AIMF + Industry Evidence (C3.1–C3.5)."""

from __future__ import annotations

from industry.characteristics import (
    CharacteristicDefaults,
    IndustryProfile,
    InvestmentCharacteristics,
)
from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.enums import (
    ApplicabilityLevel,
    AssetIntensity,
    CapitalAllocationStyle,
    CapitalIntensity,
    CashFlowProfile,
    CharacteristicLifecycle,
    ComparisonDimension,
    ComparisonDimensionHint,
    CompetitiveCharacter,
    Cyclicality,
    EarningsStability,
    EvidenceAvailability,
    EvidenceBundleStatus,
    EvidenceCategory,
    EvidenceLifecycle,
    EvidenceObservationCategory,
    EvidenceObservationConfidence,
    EvidenceObservationSeverity,
    GroupEligibilityStatus,
    GrowthProfile,
    IdentityLifecycle,
    MappingStatus,
    MergeSource,
    MetricAvailability,
    MetricImportance,
    MetricUnit,
    MethodologyLifecycle,
    MissingEvidencePolicy,
    PeerEligibilityStatus,
    PeerUse,
    PricingPower,
    RegulatoryIntensity,
    TaxonomySource,
    ValuationPhilosophyHint,
)
from industry.evidence_applicability import (
    ApplicabilityGroup,
    EvidenceApplicabilityRule,
    IndustryEvidenceApplicability,
    RequiredEvidenceSet,
)
from industry.evidence_applicability_registry import (
    IndustryEvidenceApplicabilityRegistry,
)
from industry.evidence_applicability_seeds import (
    EXAMPLE_APPLICABILITY_IDS,
    build_example_evidence_applicability,
    register_example_evidence_applicability,
    seed_example_evidence_applicability_context,
)
from industry.evidence_bundle import (
    EvidenceBundle,
    EvidenceBundleAssemblyContext,
    EvidenceBundleEntry,
    EvidenceBundleMetadata,
    EvidenceBundleReference,
    EvidenceBundleSummary,
)
from industry.evidence_bundle_assembler import EvidenceBundleAssembler
from industry.evidence_bundle_seeds import (
    example_banking_assembly_context,
    seed_example_evidence_bundle_assembler,
    seed_example_evidence_bundle_context,
)
from industry.evidence_interpreter import (
    EvidenceInterpretation,
    EvidenceInterpretationContext,
    EvidenceInterpreter,
    EvidenceObservation,
    IndustryEvidenceInterpreter,
)
from industry.evidence_interpreter_registry import (
    IndustryEvidenceInterpreterRegistry,
)
from industry.evidence_interpreter_seeds import (
    EXAMPLE_INTERPRETER_IDS,
    PlaceholderEvidenceInterpreter,
    build_example_evidence_interpreters,
    register_example_evidence_interpreters,
    seed_example_evidence_interpreter_context,
)
from industry.evidence_models import (
    EvidenceProviderRef,
    EvidenceSnapshotRef,
    EvidenceVersion,
    IndustryEvidenceDefinition,
    IndustryMetricDefinition,
)
from industry.evidence_provider import (
    EvidenceProvider,
    EvidenceProviderCapability,
    EvidenceProviderResult,
    EvidenceResolutionContext,
    IndustryEvidenceProvider,
)
from industry.evidence_provider_registry import IndustryEvidenceProviderRegistry
from industry.evidence_provider_seeds import (
    EXAMPLE_PROVIDER_IDS,
    PlaceholderEvidenceProvider,
    build_example_evidence_providers,
    register_example_evidence_providers,
    seed_example_evidence_provider_context,
)
from industry.evidence_registry import IndustryEvidenceRegistry, IndustryMetricRegistry
from industry.evidence_seeds import (
    EXAMPLE_EVIDENCE_IDS,
    EXAMPLE_METRIC_IDS,
    build_example_evidence_definitions,
    build_example_metric_definitions,
    register_example_evidence_definitions,
    register_example_metric_definitions,
    seed_example_evidence_registries,
)
from industry.exceptions import IndustryError
from industry.instrument_resolution import resolve_methodology_for_instrument
from industry.mapping_registry import ClassificationMappingRegistry
from industry.methodology import (
    AssembledMethodology,
    IndustryMethodology,
    MetricApplicability,
    PeerEligibilityPolicyRef,
    SYSTEM_DEFAULT_DIMENSIONS,
    SYSTEM_DEFAULT_VALUATION,
    ValuationProfile,
    assemble_methodology,
)
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.methodology_seeds import (
    EXAMPLE_METHODOLOGY_IDS,
    build_example_methodologies,
    register_example_methodologies,
    seed_example_industry_context,
)
from industry.models import (
    ClassificationReference,
    IndustryIdentity,
    IndustryMapping,
)
from industry.peer_eligibility import (
    EligibilityOptions,
    GroupEligibilityResult,
    InstrumentIndustryAssignment,
    InstrumentMethodologyResolution,
    PeerEligibilityPolicy,
    PeerEligibilityReason,
    PeerEligibilityResult,
)
from industry.peer_evaluator import PeerEligibilityEvaluator
from industry.peer_registry import (
    InstrumentIndustryRegistry,
    PeerEligibilityPolicyRegistry,
)
from industry.peer_seeds import (
    EXAMPLE_PEER_POLICY_IDS,
    build_example_peer_policies,
    register_example_peer_policies,
    seed_peer_eligibility_context,
)
from industry.profile_registry import IndustryProfileRegistry
from industry.seeds import (
    EXAMPLE_ARCHETYPE_IDS,
    build_example_archetypes,
    register_example_archetypes,
)
from industry.semver import SemVer, compare_semver, parse_semver, require_semver
from industry.taxonomy import IndustryTaxonomy

__all__ = [
    "EXAMPLE_APPLICABILITY_IDS",
    "EXAMPLE_ARCHETYPE_IDS",
    "EXAMPLE_EVIDENCE_IDS",
    "EXAMPLE_INTERPRETER_IDS",
    "EXAMPLE_METRIC_IDS",
    "EXAMPLE_METHODOLOGY_IDS",
    "EXAMPLE_PEER_POLICY_IDS",
    "EXAMPLE_PROVIDER_IDS",
    "ApplicabilityGroup",
    "ApplicabilityLevel",
    "AssembledMethodology",
    "AssetIntensity",
    "CapitalAllocationStyle",
    "CapitalIntensity",
    "CashFlowProfile",
    "CharacteristicDefaults",
    "CharacteristicLifecycle",
    "ClassificationMappingRegistry",
    "ClassificationReference",
    "ComparisonDimension",
    "ComparisonDimensionHint",
    "CompetitiveCharacter",
    "Cyclicality",
    "EarningsStability",
    "EligibilityOptions",
    "EvidenceApplicabilityRule",
    "EvidenceAvailability",
    "EvidenceBundle",
    "EvidenceBundleAssembler",
    "EvidenceBundleAssemblyContext",
    "EvidenceBundleEntry",
    "EvidenceBundleMetadata",
    "EvidenceBundleReference",
    "EvidenceBundleStatus",
    "EvidenceBundleSummary",
    "EvidenceCategory",
    "EvidenceInterpretation",
    "EvidenceInterpretationContext",
    "EvidenceInterpreter",
    "EvidenceLifecycle",
    "EvidenceObservation",
    "EvidenceObservationCategory",
    "EvidenceObservationConfidence",
    "EvidenceObservationSeverity",
    "EvidenceProvider",
    "EvidenceProviderCapability",
    "EvidenceProviderRef",
    "EvidenceProviderResult",
    "EvidenceResolutionContext",
    "EvidenceSnapshotRef",
    "EvidenceVersion",
    "GroupEligibilityResult",
    "GroupEligibilityStatus",
    "GrowthProfile",
    "IdentityLifecycle",
    "IndustryError",
    "IndustryEvidenceApplicability",
    "IndustryEvidenceApplicabilityRegistry",
    "IndustryEvidenceDefinition",
    "IndustryEvidenceInterpreter",
    "IndustryEvidenceInterpreterRegistry",
    "IndustryEvidenceProvider",
    "IndustryEvidenceProviderRegistry",
    "IndustryEvidenceRegistry",
    "IndustryIdentity",
    "IndustryMapping",
    "IndustryMethodology",
    "IndustryMethodologyRegistry",
    "IndustryMetricDefinition",
    "IndustryMetricRegistry",
    "IndustryProfile",
    "IndustryProfileRegistry",
    "IndustryTaxonomy",
    "InstrumentIndustryAssignment",
    "InstrumentIndustryRegistry",
    "InstrumentMethodologyResolution",
    "InvestmentCharacteristics",
    "InvestmentCharacteristicsRegistry",
    "MappingStatus",
    "MergeSource",
    "MetricApplicability",
    "MetricAvailability",
    "MetricImportance",
    "MetricUnit",
    "MethodologyLifecycle",
    "MissingEvidencePolicy",
    "PeerEligibilityEvaluator",
    "PeerEligibilityPolicy",
    "PeerEligibilityPolicyRef",
    "PeerEligibilityPolicyRegistry",
    "PeerEligibilityReason",
    "PeerEligibilityResult",
    "PeerEligibilityStatus",
    "PeerUse",
    "PlaceholderEvidenceInterpreter",
    "PlaceholderEvidenceProvider",
    "PricingPower",
    "RegulatoryIntensity",
    "RequiredEvidenceSet",
    "SYSTEM_DEFAULT_DIMENSIONS",
    "SYSTEM_DEFAULT_VALUATION",
    "SemVer",
    "TaxonomySource",
    "ValuationPhilosophyHint",
    "ValuationProfile",
    "assemble_methodology",
    "build_example_archetypes",
    "build_example_evidence_applicability",
    "build_example_evidence_definitions",
    "build_example_evidence_interpreters",
    "build_example_evidence_providers",
    "build_example_metric_definitions",
    "build_example_methodologies",
    "build_example_peer_policies",
    "compare_semver",
    "example_banking_assembly_context",
    "parse_semver",
    "register_example_archetypes",
    "register_example_evidence_applicability",
    "register_example_evidence_definitions",
    "register_example_evidence_interpreters",
    "register_example_evidence_providers",
    "register_example_metric_definitions",
    "register_example_methodologies",
    "register_example_peer_policies",
    "require_semver",
    "resolve_methodology_for_instrument",
    "seed_example_evidence_applicability_context",
    "seed_example_evidence_bundle_assembler",
    "seed_example_evidence_bundle_context",
    "seed_example_evidence_interpreter_context",
    "seed_example_evidence_provider_context",
    "seed_example_evidence_registries",
    "seed_example_industry_context",
    "seed_peer_eligibility_context",
]

__version__ = "0.9.0"
