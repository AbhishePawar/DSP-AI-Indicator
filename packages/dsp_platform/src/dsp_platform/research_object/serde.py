"""Serialize / deserialize ResearchObject (EPIC-R001)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from dsp_platform.research_object.models import (
    RESEARCH_OBJECT_SCHEMA_VERSION,
    ResearchMetadata,
    ResearchObject,
    ResearchSection,
    ResearchVersion,
    freeze_mapping,
)
from dsp_platform.research_object.validation import (
    ResearchObjectValidationError,
    validate_research_object,
)

__all__ = [
    "research_object_from_dict",
    "research_object_to_dict",
]

_BUILDER_VERSION = "1.0.0"


def research_object_to_dict(obj: ResearchObject) -> dict[str, Any]:
    """Deterministic public dict — deep-copies frozen proxies to plain dicts."""
    validate_research_object(obj)
    return obj.to_dict()


def _section_from_dict(data: Mapping[str, Any], expected_name: str) -> ResearchSection:
    name = str(data.get("name") or expected_name)
    available = bool(data.get("available", False))
    status = str(data.get("status") or ("ok" if available else "unavailable"))
    source = str(data.get("source") or "none")
    payload = data.get("payload")
    provenance = data.get("provenance")
    return ResearchSection(
        name=name,
        available=available,
        status=status,
        source=source,
        payload=freeze_mapping(dict(payload)) if isinstance(payload, Mapping) else None,
        provenance=freeze_mapping(dict(provenance))
        if isinstance(provenance, Mapping)
        else None,
        message=data.get("message"),
        retrieved_at=data.get("retrieved_at"),
    )


def research_object_from_dict(data: Mapping[str, Any]) -> ResearchObject:
    """Rebuild an immutable ResearchObject from a public dict."""
    if not isinstance(data, Mapping):
        raise ResearchObjectValidationError("research object must be a mapping")

    meta_raw = data.get("metadata")
    if not isinstance(meta_raw, Mapping):
        raise ResearchObjectValidationError("missing metadata")

    version_raw = data.get("version")
    if isinstance(version_raw, Mapping):
        version = ResearchVersion(
            schema_version=str(
                version_raw.get("schema_version")
                or data.get("schema_version")
                or RESEARCH_OBJECT_SCHEMA_VERSION
            ),
            object_version=str(version_raw.get("object_version") or "1"),
            builder_version=str(
                version_raw.get("builder_version") or _BUILDER_VERSION
            ),
        )
    else:
        version = ResearchVersion(
            schema_version=str(
                data.get("schema_version") or RESEARCH_OBJECT_SCHEMA_VERSION
            ),
            object_version="1",
            builder_version=_BUILDER_VERSION,
        )

    pkg = meta_raw.get("package_versions") or {}
    package_versions = MappingProxyType(
        {str(k): str(v) for k, v in dict(pkg).items()}
    )

    metadata = ResearchMetadata(
        research_object_id=str(meta_raw.get("research_object_id") or ""),
        schema_version=str(meta_raw.get("schema_version") or version.schema_version),
        created_at=str(meta_raw.get("created_at") or ""),
        research_mode=str(meta_raw.get("research_mode") or "Research Mode"),
        correlation_id=meta_raw.get("correlation_id"),
        ticker=meta_raw.get("ticker"),
        company=meta_raw.get("company"),
        exchange=meta_raw.get("exchange"),
        report_version=meta_raw.get("report_version"),
        pipeline_version=meta_raw.get("pipeline_version"),
        platform_version=meta_raw.get("platform_version"),
        api_version=meta_raw.get("api_version"),
        package_versions=package_versions,
    )

    provenance = data.get("provenance") or {}
    if not isinstance(provenance, Mapping):
        raise ResearchObjectValidationError("provenance must be a mapping")

    obj = ResearchObject(
        metadata=metadata,
        identity=_section_from_dict(data.get("identity") or {}, "identity"),
        market_data=_section_from_dict(data.get("market_data") or {}, "market_data"),
        financial_statements=_section_from_dict(
            data.get("financial_statements") or {}, "financial_statements"
        ),
        corporate_actions=_section_from_dict(
            data.get("corporate_actions") or {}, "corporate_actions"
        ),
        historical_series=_section_from_dict(
            data.get("historical_series") or {}, "historical_series"
        ),
        valuation=_section_from_dict(data.get("valuation") or {}, "valuation"),
        margin_of_safety=_section_from_dict(
            data.get("margin_of_safety") or {}, "margin_of_safety"
        ),
        business_quality=_section_from_dict(
            data.get("business_quality") or {}, "business_quality"
        ),
        risk=_section_from_dict(data.get("risk") or {}, "risk"),
        scenarios=_section_from_dict(data.get("scenarios") or {}, "scenarios"),
        recommendation=_section_from_dict(
            data.get("recommendation") or {}, "recommendation"
        ),
        explainability=_section_from_dict(
            data.get("explainability") or {}, "explainability"
        ),
        audit=_section_from_dict(data.get("audit") or {}, "audit"),
        provenance=freeze_mapping(dict(provenance)) or MappingProxyType({}),
        version=version,
        data_retrieval=freeze_mapping(dict(data["data_retrieval"]))
        if isinstance(data.get("data_retrieval"), Mapping)
        else None,
        data_health=freeze_mapping(dict(data["data_health"]))
        if isinstance(data.get("data_health"), Mapping)
        else None,
    )
    validate_research_object(obj)
    return obj
