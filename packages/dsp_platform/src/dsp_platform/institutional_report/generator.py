"""Generate Institutional Research Report from Research Object only (EPIC-R002).

Read-only projection. No calculations, scoring, valuation, or AI.
"""

from __future__ import annotations

import uuid
from types import MappingProxyType
from typing import Any, Mapping

from dsp_platform.institutional_report.mapper import (
    field_or_unavailable,
    map_display_fields,
    section_payload_dict,
)
from dsp_platform.institutional_report.models import (
    GENERATOR_VERSION,
    REPORT_SCHEMA_VERSION,
    InstitutionalResearchReport,
    ReportMetadata,
    ReportSection,
    ReportVersion,
    UNAVAILABLE_MESSAGE,
    freeze_mapping,
    utc_now,
)
from dsp_platform.institutional_report.validation import validate_institutional_report
from dsp_platform.research_object.models import (
    RESEARCH_OBJECT_SCHEMA_VERSION,
    ResearchObject,
    ResearchSection,
)
from dsp_platform.research_object.serde import research_object_from_dict

__all__ = [
    "GENERATOR_VERSION",
    "InstitutionalReportGenerator",
    "generate_institutional_report",
]

# Display field key candidates — first present wins; else Data unavailable.
_HEADER_FIELDS: dict[str, tuple[str, ...]] = {
    "current_market_price": (
        "current_price",
        "current_market_price",
        "price",
        "last",
    ),
    "intrinsic_value": (
        "intrinsic_value",
        "intrinsic_value_per_share",
        "fair_value",
    ),
    "margin_of_safety": ("margin_of_safety",),
    "fair_value_range": ("fair_value_range", "valuation_range", "range"),
    "expected_cagr": ("expected_cagr", "cagr"),
    "confidence": ("confidence",),
    "overall_score": ("overall_score", "score"),
    "research_status": ("research_status", "status", "label"),
    "recommendation": ("recommendation", "label", "recommendation_status"),
}

_EXECUTIVE_FIELDS: dict[str, tuple[str, ...]] = {
    "company_name": ("company_name", "company", "name"),
    "ticker": ("symbol", "ticker"),
    "exchange": ("exchange",),
    "sector": ("sector",),
    "industry": ("industry",),
    "research_date": ("research_date", "created_at"),
    "report_version": ("report_version",),
    "research_mode": ("research_mode",),
    "confidence": ("confidence",),
    "overall_score": ("overall_score", "score"),
    "recommendation_status": (
        "recommendation_status",
        "label",
        "recommendation",
        "status",
    ),
}

_MARKET_FIELDS: dict[str, tuple[str, ...]] = {
    "current_price": ("current_price", "price", "last"),
    "market_capitalisation": (
        "market_capitalisation",
        "market_cap",
        "marketCapitalization",
    ),
    "enterprise_value": ("enterprise_value", "ev"),
    "fifty_two_week_high": ("fifty_two_week_high", "week_52_high", "high_52w"),
    "fifty_two_week_low": ("fifty_two_week_low", "week_52_low", "low_52w"),
    "volume": ("volume",),
    "shares_outstanding": ("shares_outstanding", "sharesOutstanding"),
    "dividend_yield": ("dividend_yield", "dividendYield"),
    "market_data_timestamp": ("retrieved_at", "as_of", "timestamp"),
    "data_source": ("provider_id", "provider_name", "source_type", "data_source"),
}


def _ro_section_to_report(
    name: str,
    *,
    rs_id: str | None,
    source_section: str,
    ro_section: ResearchSection,
    display_fields: Mapping[str, tuple[str, ...]] | None = None,
    include_raw: bool = True,
) -> ReportSection:
    """Project a Research Object section into a report section."""
    if not ro_section.available or ro_section.payload is None:
        return ReportSection.unavailable(
            name, rs_id=rs_id, source_section=source_section
        )

    payload_src = section_payload_dict(ro_section) or {}
    display = (
        map_display_fields(payload_src, display_fields) if display_fields else {}
    )
    out: dict[str, Any] = {}
    if display:
        out["fields"] = display
    if include_raw:
        out["source_payload"] = payload_src
    out["source_status"] = ro_section.status
    out["source_name"] = ro_section.name

    return ReportSection.from_payload(
        name,
        rs_id=rs_id,
        source_section=source_section,
        payload=out,
        provenance=dict(ro_section.provenance)
        if isinstance(ro_section.provenance, Mapping)
        else {"source_type": "research_object", "section": source_section},
        retrieved_at=ro_section.retrieved_at,
        status=ro_section.status if ro_section.status in {"ok", "partial"} else "ok",
    )


class InstitutionalReportGenerator:
    """Fluent generator — Research Object is the sole source."""

    def __init__(self) -> None:
        self._research_object: ResearchObject | None = None
        self._report_id: str | None = None
        self._generated_at: str | None = None

    def with_research_object(
        self, research_object: ResearchObject | Mapping[str, Any]
    ) -> InstitutionalReportGenerator:
        if isinstance(research_object, ResearchObject):
            self._research_object = research_object
        elif isinstance(research_object, Mapping):
            self._research_object = research_object_from_dict(research_object)
        else:
            raise TypeError("research_object must be ResearchObject or mapping")
        return self

    def with_report_id(self, report_id: str) -> InstitutionalReportGenerator:
        self._report_id = report_id
        return self

    def with_generated_at(self, generated_at: str) -> InstitutionalReportGenerator:
        self._generated_at = generated_at
        return self

    def generate(self) -> InstitutionalResearchReport:
        if self._research_object is None:
            raise ValueError("research object is required")

        ro = self._research_object
        if ro.version.schema_version != RESEARCH_OBJECT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported research object schema_version "
                f"{ro.version.schema_version!r}; expected "
                f"{RESEARCH_OBJECT_SCHEMA_VERSION!r}"
            )

        generated_at = self._generated_at or utc_now().isoformat()
        report_id = self._report_id or str(uuid.uuid4())

        identity_payload = section_payload_dict(ro.identity) or {}
        rec_payload = section_payload_dict(ro.recommendation) or {}
        mos_payload = section_payload_dict(ro.margin_of_safety) or {}
        valuation_payload = section_payload_dict(ro.valuation) or {}
        market_payload = section_payload_dict(ro.market_data) or {}
        meta = ro.metadata

        # --- Mandatory header (display first) — field extract only ---
        header_source: dict[str, Any] = {
            **market_payload,
            **valuation_payload,
            **mos_payload,
            **rec_payload,
        }
        # Prefer provenance timestamp for market data stamp without inventing
        if (
            isinstance(ro.market_data.provenance, Mapping)
            and ro.market_data.provenance.get("retrieved_at")
            and "retrieved_at" not in header_source
        ):
            header_source = {
                **header_source,
                "retrieved_at": ro.market_data.provenance.get("retrieved_at"),
            }
        header_fields = map_display_fields(header_source, _HEADER_FIELDS)
        header = ReportSection.from_payload(
            "header",
            rs_id=None,
            source_section="market_data+valuation+margin_of_safety+recommendation",
            payload={"fields": header_fields},
            provenance={"source_type": "research_object", "projection": "header"},
            retrieved_at=generated_at,
        )

        # --- RS-001 Executive Summary ---
        exec_source: dict[str, Any] = {
            **identity_payload,
            **rec_payload,
            "research_date": meta.created_at,
            "report_version": REPORT_SCHEMA_VERSION,
            "research_mode": meta.research_mode,
            "company": meta.company or identity_payload.get("company"),
            "company_name": identity_payload.get("company_name")
            or meta.company
            or identity_payload.get("company"),
            "exchange": meta.exchange or identity_payload.get("exchange"),
            "symbol": meta.ticker or identity_payload.get("symbol"),
            "ticker": meta.ticker or identity_payload.get("ticker"),
        }
        exec_fields = map_display_fields(exec_source, _EXECUTIVE_FIELDS)
        executive_summary = ReportSection.from_payload(
            "executive_summary",
            rs_id="RS-001",
            source_section="identity+recommendation+metadata",
            payload={"fields": exec_fields},
            provenance={
                "source_type": "research_object",
                "projection": "executive_summary",
            },
            retrieved_at=meta.created_at,
        )

        market_data = _ro_section_to_report(
            "market_data",
            rs_id="RS-002",
            source_section="market_data",
            ro_section=ro.market_data,
            display_fields=_MARKET_FIELDS,
        )
        # Attach data_source from provenance when fields missing — still pass-through
        if market_data.available and market_data.payload is not None:
            fields = dict(market_data.payload.get("fields") or {})
            if fields.get("data_source") == UNAVAILABLE_MESSAGE and isinstance(
                ro.market_data.provenance, Mapping
            ):
                fields["data_source"] = field_or_unavailable(
                    dict(ro.market_data.provenance),
                    "provider_id",
                    "provider_name",
                    "source_type",
                )
            if fields.get("market_data_timestamp") == UNAVAILABLE_MESSAGE:
                fields["market_data_timestamp"] = (
                    ro.market_data.retrieved_at
                    or field_or_unavailable(
                        dict(ro.market_data.provenance or {}),
                        "retrieved_at",
                    )
                )
            market_data = ReportSection.from_payload(
                "market_data",
                rs_id="RS-002",
                source_section="market_data",
                payload={
                    **dict(market_data.payload),
                    "fields": fields,
                },
                provenance=dict(ro.market_data.provenance)
                if isinstance(ro.market_data.provenance, Mapping)
                else market_data.provenance,
                retrieved_at=ro.market_data.retrieved_at,
                status=market_data.status,
            )

        financial_statements = _ro_section_to_report(
            "financial_statements",
            rs_id="RS-003",
            source_section="financial_statements",
            ro_section=ro.financial_statements,
        )
        corporate_actions = _ro_section_to_report(
            "corporate_actions",
            rs_id=None,
            source_section="corporate_actions",
            ro_section=ro.corporate_actions,
        )
        historical_summary = _ro_section_to_report(
            "historical_summary",
            rs_id=None,
            source_section="historical_series",
            ro_section=ro.historical_series,
        )
        valuation = _ro_section_to_report(
            "valuation",
            rs_id="RS-004",
            source_section="valuation",
            ro_section=ro.valuation,
        )
        margin_of_safety = _ro_section_to_report(
            "margin_of_safety",
            rs_id="RS-005",
            source_section="margin_of_safety",
            ro_section=ro.margin_of_safety,
        )
        business_quality = _ro_section_to_report(
            "business_quality",
            rs_id="RS-006",
            source_section="business_quality",
            ro_section=ro.business_quality,
        )
        risk = _ro_section_to_report(
            "risk",
            rs_id="RS-007",
            source_section="risk",
            ro_section=ro.risk,
        )
        scenarios = _ro_section_to_report(
            "scenarios",
            rs_id="RS-008",
            source_section="scenarios",
            ro_section=ro.scenarios,
        )
        recommendation = _ro_section_to_report(
            "recommendation",
            rs_id=None,
            source_section="recommendation",
            ro_section=ro.recommendation,
        )
        explainability = _ro_section_to_report(
            "explainability",
            rs_id="RS-009",
            source_section="explainability",
            ro_section=ro.explainability,
        )

        ro_audit = section_payload_dict(ro.audit)
        audit_payload: dict[str, Any] = {
            "report_id": report_id,
            "audit_reference": field_or_unavailable(
                ro_audit,
                "analysis_id",
                "audit_reference",
                "research_object_id",
                "correlation_id",
            ),
            "analysis_id": field_or_unavailable(
                ro_audit,
                "analysis_id",
                "audit_reference",
            ),
            "generation_timestamp": generated_at,
            "engine_version": field_or_unavailable(
                ro_audit,
                "pipeline_version",
                "platform_version",
                "engine_version",
            ),
            "rules_version": REPORT_SCHEMA_VERSION,
            "data_timestamp": field_or_unavailable(
                ro_audit,
                "created_at",
                "data_timestamp",
            ),
            "financial_statement_period": field_or_unavailable(
                section_payload_dict(ro.financial_statements),
                "period",
                "reporting_period",
                "as_of",
            ),
            "source_metadata": ro_audit,
            "trust_chain": (
                dict(ro_audit["trust_chain"])
                if isinstance(ro_audit.get("trust_chain"), dict)
                else UNAVAILABLE_MESSAGE
            ),
            "result_fingerprint": field_or_unavailable(
                ro_audit,
                "result_fingerprint",
            ),
            "calculation_metadata": UNAVAILABLE_MESSAGE,  # R002 never calculates
            "research_version": ro.version.schema_version,
            "research_object_id": meta.research_object_id,
            "generator_version": GENERATOR_VERSION,
        }
        if not ro.audit.available:
            # Still emit RS-010 with report-level audit + honest unavailable slots
            audit_payload["source_metadata"] = UNAVAILABLE_MESSAGE

        audit = ReportSection.from_payload(
            "audit",
            rs_id="RS-010",
            source_section="audit",
            payload=audit_payload,
            provenance={
                "source_type": "research_object",
                "projection": "audit",
                "research_object_audit_available": ro.audit.available,
            },
            retrieved_at=generated_at,
        )

        provenance = {
            "header": header.provenance,
            "executive_summary": executive_summary.provenance,
            "market_data": market_data.provenance,
            "financial_statements": financial_statements.provenance,
            "corporate_actions": corporate_actions.provenance,
            "historical_summary": historical_summary.provenance,
            "valuation": valuation.provenance,
            "margin_of_safety": margin_of_safety.provenance,
            "business_quality": business_quality.provenance,
            "risk": risk.provenance,
            "scenarios": scenarios.provenance,
            "recommendation": recommendation.provenance,
            "explainability": explainability.provenance,
            "audit": audit.provenance,
            "research_object_provenance": dict(ro.provenance)
            if isinstance(ro.provenance, Mapping)
            else None,
        }

        metadata = ReportMetadata(
            report_id=report_id,
            schema_version=REPORT_SCHEMA_VERSION,
            generated_at=generated_at,
            research_object_id=meta.research_object_id,
            research_object_schema_version=ro.version.schema_version,
            research_mode=meta.research_mode,
            correlation_id=meta.correlation_id,
            ticker=meta.ticker,
            company=meta.company,
            exchange=meta.exchange,
            generator_version=GENERATOR_VERSION,
            api_version=meta.api_version or "v1",
            package_versions=MappingProxyType(dict(meta.package_versions)),
        )

        version = ReportVersion(
            schema_version=REPORT_SCHEMA_VERSION,
            report_version="1",
            generator_version=GENERATOR_VERSION,
            research_object_schema_version=ro.version.schema_version,
        )

        research_object_ref = {
            "research_object_id": meta.research_object_id,
            "schema_version": ro.version.schema_version,
            "object_version": ro.version.object_version,
            "builder_version": ro.version.builder_version,
            "created_at": meta.created_at,
        }

        report = InstitutionalResearchReport(
            metadata=metadata,
            header=header,
            executive_summary=executive_summary,
            market_data=market_data,
            financial_statements=financial_statements,
            corporate_actions=corporate_actions,
            historical_summary=historical_summary,
            valuation=valuation,
            margin_of_safety=margin_of_safety,
            business_quality=business_quality,
            risk=risk,
            scenarios=scenarios,
            recommendation=recommendation,
            explainability=explainability,
            audit=audit,
            provenance=freeze_mapping(provenance) or MappingProxyType({}),
            version=version,
            research_object_ref=freeze_mapping(research_object_ref)
            or MappingProxyType({}),
        )
        validate_institutional_report(report)
        return report


def generate_institutional_report(
    research_object: ResearchObject | Mapping[str, Any],
    *,
    report_id: str | None = None,
    generated_at: str | None = None,
) -> InstitutionalResearchReport:
    """Convenience entry — Research Object is the only input source."""
    gen = InstitutionalReportGenerator().with_research_object(research_object)
    if report_id:
        gen = gen.with_report_id(report_id)
    if generated_at:
        gen = gen.with_generated_at(generated_at)
    return gen.generate()
