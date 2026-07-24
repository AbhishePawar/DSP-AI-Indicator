"""Illustrative Industry Metric + Evidence definitions (C3.1 fixtures).

Banking + Utilities acceptance fixtures — definitions only, no providers.
"""

from __future__ import annotations

from industry.enums import (
    ComparisonDimension,
    EvidenceCategory,
    MetricAvailability,
    MetricUnit,
)
from industry.evidence_models import (
    EvidenceProviderRef,
    IndustryEvidenceDefinition,
    IndustryMetricDefinition,
)
from industry.evidence_registry import IndustryEvidenceRegistry, IndustryMetricRegistry

__all__ = [
    "EXAMPLE_EVIDENCE_IDS",
    "EXAMPLE_METRIC_IDS",
    "build_example_evidence_definitions",
    "build_example_metric_definitions",
    "register_example_evidence_definitions",
    "register_example_metric_definitions",
    "seed_example_evidence_registries",
]

EXAMPLE_METRIC_IDS: tuple[str, ...] = (
    "dsp.metric.roe",
    "dsp.metric.nim",
    "dsp.metric.regulated_return",
)

EXAMPLE_EVIDENCE_IDS: tuple[str, ...] = (
    "dsp.evidence.roe_persistence",
    "dsp.evidence.nim_stability",
    "dsp.evidence.regulated_cash_flow_visibility",
)


def build_example_metric_definitions() -> tuple[IndustryMetricDefinition, ...]:
    return (
        IndustryMetricDefinition(
            id="dsp.metric.roe",
            name="Return on Equity",
            version="1.0.0",
            category=EvidenceCategory.FINANCIAL,
            unit=MetricUnit.RATIO,
            description="Net income divided by average equity (metadata only).",
            availability=MetricAvailability.DERIVABLE,
            provider=EvidenceProviderRef(
                provider_id="dsp.provider.fundamental_statements",
                notes=("Future provider — not implemented in C3.1.",),
            ),
            notes=("No formula executed by the registry.",),
        ),
        IndustryMetricDefinition(
            id="dsp.metric.nim",
            name="Net Interest Margin",
            version="1.0.0",
            category=EvidenceCategory.INDUSTRY_KPI,
            unit=MetricUnit.PERCENT,
            description="Banking net interest margin (metadata only).",
            availability=MetricAvailability.REQUIRES_NEW_DATA,
            provider=EvidenceProviderRef(
                provider_id="dsp.provider.banking_kpi",
            ),
        ),
        IndustryMetricDefinition(
            id="dsp.metric.regulated_return",
            name="Allowed / Regulated Return",
            version="1.0.0",
            category=EvidenceCategory.REGULATORY,
            unit=MetricUnit.PERCENT,
            description="Regulatory return parameter for utilities (metadata only).",
            availability=MetricAvailability.REQUIRES_NEW_DATA,
            provider=EvidenceProviderRef(
                provider_id="dsp.provider.utilities_regulatory",
            ),
        ),
    )


def build_example_evidence_definitions() -> tuple[IndustryEvidenceDefinition, ...]:
    return (
        IndustryEvidenceDefinition(
            id="dsp.evidence.roe_persistence",
            name="ROE Persistence",
            version="1.0.0",
            category=EvidenceCategory.FINANCIAL,
            purpose=(
                "Describe whether reported ROE has remained elevated across "
                "multiple periods without declaring investment preference."
            ),
            description="Cross-industry financial persistence evidence type.",
            related_metric_ids=("dsp.metric.roe",),
            supported_industry_ids=(
                "dsp.industry.commercial_banking",
                "dsp.industry.premium_consumer_franchise",
            ),
            interpretation_guidance=(
                "Cite multi-period ROE readings when available; otherwise record a gap.",
                "Do not treat elevated ROE alone as a buy signal.",
            ),
            provider_requirements=(
                EvidenceProviderRef(provider_id="dsp.provider.fundamental_statements"),
            ),
            dimension_hints=(
                ComparisonDimension.QUALITY,
                ComparisonDimension.FINANCIAL_STRENGTH,
            ),
            snapshot_compatible=True,
            notes=(
                "supported_industry_ids are hints only; methodology applicability is C3.2+.",
            ),
        ),
        IndustryEvidenceDefinition(
            id="dsp.evidence.nim_stability",
            name="NIM Stability",
            version="1.0.0",
            category=EvidenceCategory.INDUSTRY_KPI,
            purpose=(
                "Describe stability or pressure in net interest margin for "
                "deposit-franchise banks."
            ),
            related_metric_ids=("dsp.metric.nim",),
            supported_industry_ids=("dsp.industry.commercial_banking",),
            interpretation_guidance=(
                "Require banking KPI inputs; absent NIM data must surface as a gap.",
            ),
            provider_requirements=(
                EvidenceProviderRef(provider_id="dsp.provider.banking_kpi"),
            ),
            dimension_hints=(
                ComparisonDimension.QUALITY,
                ComparisonDimension.RISK,
            ),
            snapshot_compatible=True,
        ),
        IndustryEvidenceDefinition(
            id="dsp.evidence.regulated_cash_flow_visibility",
            name="Regulated Cash Flow Visibility",
            version="1.0.0",
            category=EvidenceCategory.REGULATORY,
            purpose=(
                "Describe visibility of regulated or contracted utility cash flows "
                "without ordering operators by preference."
            ),
            related_metric_ids=("dsp.metric.regulated_return",),
            supported_industry_ids=("dsp.industry.electric_utilities",),
            interpretation_guidance=(
                "Anchor claims to regulatory return and contract structure metadata.",
            ),
            provider_requirements=(
                EvidenceProviderRef(provider_id="dsp.provider.utilities_regulatory"),
            ),
            dimension_hints=(
                ComparisonDimension.PREDICTABILITY,
                ComparisonDimension.VALUATION,
            ),
            snapshot_compatible=True,
        ),
    )


def register_example_metric_definitions(
    registry: IndustryMetricRegistry,
) -> IndustryMetricRegistry:
    for metric in build_example_metric_definitions():
        registry.register(metric)
    return registry


def register_example_evidence_definitions(
    registry: IndustryEvidenceRegistry,
) -> IndustryEvidenceRegistry:
    for evidence in build_example_evidence_definitions():
        registry.register(evidence)
    return registry


def seed_example_evidence_registries(
    metrics: IndustryMetricRegistry | None = None,
    evidence: IndustryEvidenceRegistry | None = None,
) -> tuple[IndustryMetricRegistry, IndustryEvidenceRegistry]:
    """Seed banking + utilities definition fixtures (idempotent)."""
    metric_reg = metrics or IndustryMetricRegistry()
    register_example_metric_definitions(metric_reg)
    evidence_reg = evidence or IndustryEvidenceRegistry(metric_reg)
    register_example_evidence_definitions(evidence_reg)
    return metric_reg, evidence_reg
