"""Assemble the canonical research chain without executing AI.

Orchestrates existing components only. Does not calculate valuation,
scores, X/10, entry/exit, scenarios, or expected returns. Does not call
providers, HTTP, or DSP engines.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dsp_platform.research_assembly.models import (
    AI_EXECUTION_BLOCKED,
    AI_OUTPUT_FIXTURE,
    ASSEMBLY_SCHEMA_VERSION,
    AssemblyOutcome,
    CanonicalResearchAssembly,
)
from dsp_platform.research_package.models import (
    SOURCE_PIPELINE_COMPOSE_INTELLIGENCE,
    ResearchPackage,
)
from dsp_platform.research_prompt import (
    PRIVATE_METHODOLOGY_CANARY,
    PrivateResearchPromptError,
    build_private_research_prompt,
)
from dsp_platform.research_report.models import (
    PRIVATE_REPORT_FIELD_NAMES,
    assert_public_report_privacy,
)
from dsp_platform.research_validation import (
    CanonicalAIResearchOutput,
    CanonicalValidationIssue,
    CanonicalValidationKind,
    CanonicalValidationResult,
    CanonicalValidationStatus,
    validate_canonical_research,
)

__all__ = ["assemble_canonical_research"]


def assemble_canonical_research(
    research_package: object,
    ai_output: CanonicalAIResearchOutput | Mapping[str, Any] | None = None,
) -> CanonicalResearchAssembly:
    """Run the private in-process research chain with AI execution blocked.

    ``ai_output=None`` keeps the AI stage at ``AI_EXECUTION_BLOCKED``.
    A supplied draft is treated as ``AI_OUTPUT_FIXTURE`` (not a provider
    response) and passed to ``validate_canonical_research``.
    """
    package = _require_package(research_package)
    if isinstance(package, CanonicalResearchAssembly):
        return package
    try:
        prompt = build_private_research_prompt(package)
    except PrivateResearchPromptError as exc:
        return _invalid_assembly(
            source_pipeline=package.source_pipeline,
            message=str(exc),
            ai_output=ai_output,
        )
    if ai_output is None:
        return _finalize(
            CanonicalResearchAssembly(
                schema_version=ASSEMBLY_SCHEMA_VERSION,
                source_pipeline=package.source_pipeline,
                ai_execution_state=AI_EXECUTION_BLOCKED,
                outcome=AssemblyOutcome.AI_EXECUTION_BLOCKED.value,
                private_prompt=prompt,
                validation=None,
                report=None,
            )
        )
    validation = validate_canonical_research(package, ai_output)
    if validation.status is CanonicalValidationStatus.VALID and validation.ok:
        outcome = AssemblyOutcome.VALID.value
        report = validation.report
    elif validation.status is CanonicalValidationStatus.INVALID:
        outcome = AssemblyOutcome.INVALID.value
        report = None
    else:
        outcome = AssemblyOutcome.FAILED_CLOSED.value
        report = None
    return _finalize(
        CanonicalResearchAssembly(
            schema_version=ASSEMBLY_SCHEMA_VERSION,
            source_pipeline=package.source_pipeline,
            ai_execution_state=AI_OUTPUT_FIXTURE,
            outcome=outcome,
            private_prompt=prompt,
            validation=validation,
            report=report,
        )
    )


def _require_package(
    research_package: object,
) -> ResearchPackage | CanonicalResearchAssembly:
    if isinstance(research_package, ResearchPackage):
        if research_package.source_pipeline != SOURCE_PIPELINE_COMPOSE_INTELLIGENCE:
            return _invalid_assembly(
                source_pipeline=str(research_package.source_pipeline),
                message=(
                    "assemble_canonical_research requires source_pipeline="
                    f"{SOURCE_PIPELINE_COMPOSE_INTELLIGENCE!r}"
                ),
                ai_output=None,
            )
        return research_package
    name = type(research_package).__name__
    return _invalid_assembly(
        source_pipeline="",
        message=(
            "assemble_canonical_research requires a compose_intelligence "
            f"ResearchPackage, not {name}."
        ),
        ai_output=None,
    )


def _invalid_assembly(
    *,
    source_pipeline: str,
    message: str,
    ai_output: object,
) -> CanonicalResearchAssembly:
    state = AI_OUTPUT_FIXTURE if ai_output is not None else AI_EXECUTION_BLOCKED
    return _finalize(
        CanonicalResearchAssembly(
            schema_version=ASSEMBLY_SCHEMA_VERSION,
            source_pipeline=source_pipeline,
            ai_execution_state=state,
            outcome=AssemblyOutcome.INVALID.value,
            private_prompt=None,
            validation=CanonicalValidationResult(
                status=CanonicalValidationStatus.INVALID,
                report=None,
                issues=(
                    CanonicalValidationIssue(
                        kind=CanonicalValidationKind.INVALID_INPUT,
                        message=message,
                    ),
                ),
            ),
            report=None,
        )
    )


def _finalize(assembly: CanonicalResearchAssembly) -> CanonicalResearchAssembly:
    dumped = assembly.to_public_dict()
    leaked = sorted(set(dumped) & PRIVATE_REPORT_FIELD_NAMES)
    if leaked:
        return _privacy_failure(assembly, "assembly public view leaked private keys")
    blob = str(dumped)
    if PRIVATE_METHODOLOGY_CANARY in blob:
        return _privacy_failure(assembly, "methodology canary leaked into public view")
    if assembly.private_prompt is not None and assembly.private_prompt.text in blob:
        return _privacy_failure(assembly, "private prompt leaked into public view")
    report_dict = dumped.get("report")
    if isinstance(report_dict, dict):
        try:
            assert_public_report_privacy(report_dict)
        except ValueError:
            return _privacy_failure(assembly, "public report failed privacy validation")
    return assembly


def _privacy_failure(
    assembly: CanonicalResearchAssembly, message: str
) -> CanonicalResearchAssembly:
    return CanonicalResearchAssembly(
        schema_version=assembly.schema_version,
        source_pipeline=assembly.source_pipeline,
        ai_execution_state=assembly.ai_execution_state,
        outcome=AssemblyOutcome.FAILED_CLOSED.value,
        private_prompt=assembly.private_prompt,
        validation=CanonicalValidationResult(
            status=CanonicalValidationStatus.FAILED_CLOSED,
            report=None,
            issues=(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.PRIVACY,
                    message=message,
                ),
            ),
        ),
        report=None,
    )
