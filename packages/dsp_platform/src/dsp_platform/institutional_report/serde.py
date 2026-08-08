"""Serialize / deserialize Institutional Research Report (EPIC-R002)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from dsp_platform.institutional_report.models import (
    GENERATOR_VERSION,
    REPORT_SCHEMA_VERSION,
    InstitutionalResearchReport,
    ReportMetadata,
    ReportSection,
    ReportVersion,
    freeze_mapping,
)
from dsp_platform.institutional_report.validation import (
    InstitutionalReportValidationError,
    validate_institutional_report,
)
from dsp_platform.research_object.models import RESEARCH_OBJECT_SCHEMA_VERSION

__all__ = [
    "institutional_report_from_dict",
    "institutional_report_to_dict",
]


def institutional_report_to_dict(report: InstitutionalResearchReport) -> dict[str, Any]:
    validate_institutional_report(report)
    return report.to_dict()


def _section_from_dict(
    data: Mapping[str, Any], expected_name: str, *, rs_id: str | None = None
) -> ReportSection:
    name = str(data.get("name") or expected_name)
    available = bool(data.get("available", False))
    status = str(data.get("status") or ("ok" if available else "unavailable"))
    source_section = str(data.get("source_section") or "research_object")
    payload = data.get("payload")
    provenance = data.get("provenance")
    return ReportSection(
        name=name,
        rs_id=data.get("rs_id", rs_id),
        available=available,
        status=status,
        source_section=source_section,
        payload=freeze_mapping(dict(payload)) if isinstance(payload, Mapping) else None,
        provenance=freeze_mapping(dict(provenance))
        if isinstance(provenance, Mapping)
        else None,
        message=data.get("message"),
        retrieved_at=data.get("retrieved_at"),
    )


def institutional_report_from_dict(
    data: Mapping[str, Any],
) -> InstitutionalResearchReport:
    if not isinstance(data, Mapping):
        raise InstitutionalReportValidationError("report must be a mapping")

    meta_raw = data.get("metadata")
    if not isinstance(meta_raw, Mapping):
        raise InstitutionalReportValidationError("missing metadata")

    version_raw = data.get("version")
    if isinstance(version_raw, Mapping):
        version = ReportVersion(
            schema_version=str(
                version_raw.get("schema_version")
                or data.get("schema_version")
                or REPORT_SCHEMA_VERSION
            ),
            report_version=str(version_raw.get("report_version") or "1"),
            generator_version=str(
                version_raw.get("generator_version") or GENERATOR_VERSION
            ),
            research_object_schema_version=str(
                version_raw.get("research_object_schema_version")
                or RESEARCH_OBJECT_SCHEMA_VERSION
            ),
        )
    else:
        version = ReportVersion(
            schema_version=str(data.get("schema_version") or REPORT_SCHEMA_VERSION),
            report_version="1",
            generator_version=GENERATOR_VERSION,
            research_object_schema_version=RESEARCH_OBJECT_SCHEMA_VERSION,
        )

    pkg = meta_raw.get("package_versions") or {}
    package_versions = MappingProxyType(
        {str(k): str(v) for k, v in dict(pkg).items()}
    )

    metadata = ReportMetadata(
        report_id=str(meta_raw.get("report_id") or ""),
        schema_version=str(meta_raw.get("schema_version") or version.schema_version),
        generated_at=str(meta_raw.get("generated_at") or ""),
        research_object_id=str(meta_raw.get("research_object_id") or ""),
        research_object_schema_version=str(
            meta_raw.get("research_object_schema_version")
            or version.research_object_schema_version
        ),
        research_mode=str(meta_raw.get("research_mode") or "Research Mode"),
        correlation_id=meta_raw.get("correlation_id"),
        ticker=meta_raw.get("ticker"),
        company=meta_raw.get("company"),
        exchange=meta_raw.get("exchange"),
        generator_version=str(
            meta_raw.get("generator_version") or GENERATOR_VERSION
        ),
        api_version=meta_raw.get("api_version"),
        package_versions=package_versions,
    )

    provenance = data.get("provenance") or {}
    if not isinstance(provenance, Mapping):
        raise InstitutionalReportValidationError("provenance must be a mapping")

    ref = data.get("research_object_ref") or {}
    if not isinstance(ref, Mapping):
        raise InstitutionalReportValidationError(
            "research_object_ref must be a mapping"
        )

    report = InstitutionalResearchReport(
        metadata=metadata,
        header=_section_from_dict(data.get("header") or {}, "header"),
        executive_summary=_section_from_dict(
            data.get("executive_summary") or {}, "executive_summary", rs_id="RS-001"
        ),
        market_data=_section_from_dict(
            data.get("market_data") or {}, "market_data", rs_id="RS-002"
        ),
        financial_statements=_section_from_dict(
            data.get("financial_statements") or {},
            "financial_statements",
            rs_id="RS-003",
        ),
        corporate_actions=_section_from_dict(
            data.get("corporate_actions") or {}, "corporate_actions"
        ),
        historical_summary=_section_from_dict(
            data.get("historical_summary") or {}, "historical_summary"
        ),
        valuation=_section_from_dict(
            data.get("valuation") or {}, "valuation", rs_id="RS-004"
        ),
        margin_of_safety=_section_from_dict(
            data.get("margin_of_safety") or {}, "margin_of_safety", rs_id="RS-005"
        ),
        business_quality=_section_from_dict(
            data.get("business_quality") or {}, "business_quality", rs_id="RS-006"
        ),
        risk=_section_from_dict(data.get("risk") or {}, "risk", rs_id="RS-007"),
        scenarios=_section_from_dict(
            data.get("scenarios") or {}, "scenarios", rs_id="RS-008"
        ),
        recommendation=_section_from_dict(
            data.get("recommendation") or {}, "recommendation"
        ),
        explainability=_section_from_dict(
            data.get("explainability") or {}, "explainability", rs_id="RS-009"
        ),
        audit=_section_from_dict(data.get("audit") or {}, "audit", rs_id="RS-010"),
        provenance=freeze_mapping(dict(provenance)) or MappingProxyType({}),
        version=version,
        research_object_ref=freeze_mapping(dict(ref)) or MappingProxyType({}),
    )
    validate_institutional_report(report)
    return report
