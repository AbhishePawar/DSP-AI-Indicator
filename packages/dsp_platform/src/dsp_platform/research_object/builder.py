"""Build ResearchObject from existing outputs only (EPIC-R001).

Aggregates Unified Data Bundle (D005) + analysis public dict + optional
request signals. Never calculates, scores, values, or invents fields.
"""

from __future__ import annotations

import uuid
from types import MappingProxyType
from typing import Any, Mapping

from dsp_platform.research_object.models import (
    RESEARCH_OBJECT_SCHEMA_VERSION,
    ResearchMetadata,
    ResearchObject,
    ResearchSection,
    ResearchVersion,
    UNAVAILABLE_MESSAGE,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_object.validation import validate_research_object

__all__ = [
    "BUILDER_VERSION",
    "ResearchObjectBuilder",
    "build_research_object",
]

BUILDER_VERSION = "1.0.0"


def _stage_summary(
    analysis: Mapping[str, Any] | None, stage_name: str
) -> dict[str, Any] | None:
    if not analysis:
        return None
    summaries = analysis.get("stage_summaries")
    if isinstance(summaries, list):
        for row in summaries:
            if isinstance(row, Mapping) and row.get("stage") == stage_name:
                return dict(row)
    stages = analysis.get("stages")
    if isinstance(stages, list):
        for row in stages:
            if isinstance(row, Mapping) and row.get("stage") == stage_name:
                return dict(row)
    return None


def _section_from_data_bundle(
    name: str,
    bundle: Mapping[str, Any] | None,
    bundle_key: str,
) -> ResearchSection:
    if not isinstance(bundle, Mapping):
        return ResearchSection.unavailable(name, source="data_bundle")
    section = bundle.get(bundle_key)
    if not isinstance(section, Mapping):
        return ResearchSection.unavailable(name, source="data_bundle")
    status = section.get("status") if isinstance(section.get("status"), Mapping) else {}
    available = bool(status.get("available"))
    payload = section.get("payload")
    provenance = section.get("provenance")
    if not available or not isinstance(payload, Mapping):
        return ResearchSection(
            name=name,
            available=False,
            status=str(status.get("status") or "unavailable"),
            source="data_bundle",
            payload=None,
            provenance=freeze_mapping(dict(provenance))
            if isinstance(provenance, Mapping)
            else None,
            message=status.get("message") or UNAVAILABLE_MESSAGE,
            retrieved_at=status.get("retrieved_at"),
        )
    return ResearchSection.from_payload(
        name,
        source="data_bundle",
        payload=payload,
        provenance=provenance if isinstance(provenance, Mapping) else None,
        retrieved_at=status.get("retrieved_at"),
    )


def _section_from_analysis_summary(
    name: str,
    analysis: Mapping[str, Any] | None,
    stage_name: str,
) -> ResearchSection:
    summary = _stage_summary(analysis, stage_name)
    if summary is None or not summary.get("has_result"):
        return ResearchSection.unavailable(name, source="analysis")
    return ResearchSection.from_payload(
        name,
        source="analysis",
        payload=summary,
        provenance={
            "source_type": "analysis_pipeline",
            "stage": stage_name,
        },
    )


class ResearchObjectBuilder:
    """Fluent builder — aggregates existing dicts only."""

    def __init__(self) -> None:
        self._symbol: str = ""
        self._company: str | None = None
        self._exchange: str | None = None
        self._data_bundle: Mapping[str, Any] | None = None
        self._analysis: Mapping[str, Any] | None = None
        self._valuation_signals: Mapping[str, Any] | None = None
        self._correlation_id: str | None = None
        self._api_version: str | None = "v1"
        self._platform_version: str | None = None
        self._research_mode: str = "Research Mode"
        self._object_id: str | None = None
        self._created_at: str | None = None

    def with_identity(
        self,
        symbol: str,
        *,
        company: str | None = None,
        exchange: str | None = None,
    ) -> ResearchObjectBuilder:
        self._symbol = symbol.strip().upper()
        self._company = company
        self._exchange = exchange
        return self

    def with_data_bundle(
        self, bundle: Mapping[str, Any] | None
    ) -> ResearchObjectBuilder:
        self._data_bundle = bundle
        return self

    def with_analysis_payload(
        self, analysis: Mapping[str, Any] | None
    ) -> ResearchObjectBuilder:
        """Pass ``pipeline_result_public_dict`` / AnalyseResponse.payload."""
        self._analysis = analysis
        return self

    def with_valuation_signals(
        self, signals: Mapping[str, Any] | None
    ) -> ResearchObjectBuilder:
        """Pass-through request valuation_signals (user/engine inputs already produced)."""
        self._valuation_signals = signals
        return self

    def with_correlation_id(self, correlation_id: str | None) -> ResearchObjectBuilder:
        self._correlation_id = correlation_id
        return self

    def with_versions(
        self,
        *,
        api_version: str | None = "v1",
        platform_version: str | None = None,
    ) -> ResearchObjectBuilder:
        self._api_version = api_version
        self._platform_version = platform_version
        return self

    def with_research_mode(self, mode: str) -> ResearchObjectBuilder:
        self._research_mode = mode
        return self

    def with_object_id(self, object_id: str) -> ResearchObjectBuilder:
        self._object_id = object_id
        return self

    def with_created_at(self, created_at: str) -> ResearchObjectBuilder:
        """Fixed timestamp for deterministic builds/tests."""
        self._created_at = created_at
        return self

    def build(self) -> ResearchObject:
        if not self._symbol:
            # Prefer identity from data bundle when symbol omitted
            if isinstance(self._data_bundle, Mapping):
                identity = self._data_bundle.get("identity")
                if isinstance(identity, Mapping) and identity.get("symbol"):
                    self._symbol = str(identity["symbol"]).strip().upper()
            if not self._symbol and isinstance(self._analysis, Mapping):
                # analysis may not carry ticker; leave empty → validation may fail identity
                pass
        if not self._symbol:
            raise ValueError("research object requires symbol")

        created_at = self._created_at or utc_now().isoformat()
        object_id = self._object_id or str(uuid.uuid4())

        # Identity: prefer D005 identity, else request fields
        identity_payload: dict[str, Any] | None = None
        identity_prov: dict[str, Any] | None = None
        if isinstance(self._data_bundle, Mapping):
            raw_id = self._data_bundle.get("identity")
            if isinstance(raw_id, Mapping) and raw_id.get("symbol"):
                identity_payload = dict(raw_id)
                identity_prov = {"source_type": "data_bundle", "resolved_by": raw_id.get("resolved_by")}
        if identity_payload is None:
            identity_payload = {
                "symbol": self._symbol,
                "ticker": self._symbol,
                "company": self._company,
                "exchange": self._exchange,
            }
            identity_prov = {"source_type": "request"}

        identity = ResearchSection.from_payload(
            "identity",
            source="data_bundle" if identity_prov and identity_prov.get("source_type") == "data_bundle" else "request",
            payload=identity_payload,
            provenance=identity_prov,
            retrieved_at=created_at,
        )

        market_data = _section_from_data_bundle(
            "market_data", self._data_bundle, "market_quote"
        )
        financial_statements = _section_from_data_bundle(
            "financial_statements", self._data_bundle, "financial_statements"
        )
        corporate_actions = _section_from_data_bundle(
            "corporate_actions", self._data_bundle, "corporate_actions"
        )
        historical_series = _section_from_data_bundle(
            "historical_series", self._data_bundle, "historical_series"
        )

        valuation = _section_from_analysis_summary(
            "valuation", self._analysis, "valuation"
        )
        # Overlay valuation_signals when analysis stage missing but signals present
        if not valuation.available and isinstance(self._valuation_signals, Mapping):
            valuation = ResearchSection.from_payload(
                "valuation",
                source="request",
                payload=dict(self._valuation_signals),
                provenance={"source_type": "valuation_signals"},
            )

        mos_payload: dict[str, Any] | None = None
        mos_source = "analysis"
        if isinstance(self._analysis, Mapping):
            rec = self._analysis.get("recommendation_summary")
            if isinstance(rec, Mapping) and rec.get("margin_of_safety") is not None:
                mos_payload = {
                    "margin_of_safety": rec.get("margin_of_safety"),
                    "source": "recommendation_summary",
                }
        if mos_payload is None and isinstance(self._valuation_signals, Mapping):
            if self._valuation_signals.get("margin_of_safety") is not None:
                mos_payload = {
                    "margin_of_safety": self._valuation_signals.get("margin_of_safety"),
                    "intrinsic_value_per_share": self._valuation_signals.get(
                        "intrinsic_value_per_share"
                    ),
                    "current_market_price": self._valuation_signals.get(
                        "current_market_price"
                    ),
                    "source": "valuation_signals",
                }
                mos_source = "request"
        margin_of_safety = (
            ResearchSection.from_payload(
                "margin_of_safety",
                source=mos_source,
                payload=mos_payload,
                provenance={"source_type": mos_source},
            )
            if mos_payload is not None
            else ResearchSection.unavailable("margin_of_safety", source=mos_source)
        )

        business_quality = _section_from_analysis_summary(
            "business_quality", self._analysis, "business_quality_aggregator"
        )
        # Risk: composition has no dedicated risk stage in public summaries —
        # leave unavailable unless analysis carries an explicit risk key
        risk = ResearchSection.unavailable("risk", source="analysis")
        if isinstance(self._analysis, Mapping) and isinstance(
            self._analysis.get("risk"), Mapping
        ):
            risk = ResearchSection.from_payload(
                "risk",
                source="analysis",
                payload=self._analysis["risk"],  # type: ignore[arg-type]
                provenance={"source_type": "analysis_pipeline"},
            )

        scenarios = ResearchSection.unavailable("scenarios", source="analysis")
        if isinstance(self._analysis, Mapping) and isinstance(
            self._analysis.get("scenarios"), Mapping
        ):
            scenarios = ResearchSection.from_payload(
                "scenarios",
                source="analysis",
                payload=self._analysis["scenarios"],  # type: ignore[arg-type]
                provenance={"source_type": "analysis_pipeline"},
            )

        recommendation = ResearchSection.unavailable("recommendation", source="analysis")
        if isinstance(self._analysis, Mapping):
            rec = self._analysis.get("recommendation_summary")
            if isinstance(rec, Mapping) and rec:
                recommendation = ResearchSection.from_payload(
                    "recommendation",
                    source="analysis",
                    payload=dict(rec),
                    provenance={"source_type": "analysis_pipeline"},
                )

        # Explainability: stage_summaries pass-through (already produced)
        explainability = ResearchSection.unavailable("explainability", source="analysis")
        if isinstance(self._analysis, Mapping):
            summaries = self._analysis.get("stage_summaries")
            if isinstance(summaries, list) and summaries:
                explainability = ResearchSection.from_payload(
                    "explainability",
                    source="analysis",
                    payload={"stage_summaries": list(summaries)},
                    provenance={"source_type": "analysis_pipeline"},
                )

        meta_block: dict[str, Any] = {}
        package_versions: dict[str, str] = {}
        pipeline_version = None
        platform_version = self._platform_version
        if isinstance(self._analysis, Mapping):
            meta_block = (
                dict(self._analysis["metadata"])
                if isinstance(self._analysis.get("metadata"), Mapping)
                else {}
            )
            pkg = meta_block.get("package_versions") or {}
            if isinstance(pkg, Mapping):
                package_versions = {str(k): str(v) for k, v in pkg.items()}
            pipeline_version = meta_block.get("pipeline_version")
            platform_version = platform_version or meta_block.get("platform_version")

        analysis_id = None
        result_fingerprint = None
        trust_chain = None
        if isinstance(self._analysis, Mapping):
            raw_aid = self._analysis.get("analysis_id") or self._analysis.get(
                "audit_reference"
            )
            if raw_aid is not None and str(raw_aid).strip():
                analysis_id = str(raw_aid).strip()
            if self._analysis.get("result_fingerprint") is not None:
                result_fingerprint = self._analysis.get("result_fingerprint")
            if isinstance(self._analysis.get("trust_chain"), Mapping):
                trust_chain = dict(self._analysis["trust_chain"])  # type: ignore[index]

        audit_payload = {
            "research_object_id": object_id,
            "correlation_id": self._correlation_id or meta_block.get("correlation_id"),
            "created_at": created_at,
            "pipeline_version": pipeline_version,
            "platform_version": platform_version,
            "package_versions": package_versions,
            "analysis_id": analysis_id,
            "audit_reference": analysis_id,
            "result_fingerprint": result_fingerprint,
            "trust_chain": trust_chain,
            "analysis_ok": (
                self._analysis.get("ok")
                if isinstance(self._analysis, Mapping)
                else None
            ),
            "data_retrieval": (
                dict(self._data_bundle["retrieval"])
                if isinstance(self._data_bundle, Mapping)
                and isinstance(self._data_bundle.get("retrieval"), Mapping)
                else None
            ),
        }
        audit = ResearchSection.from_payload(
            "audit",
            source="aggregated",
            payload=audit_payload,
            provenance={"source_type": "research_object_builder"},
            retrieved_at=created_at,
        )

        provenance: dict[str, Any] = {
            "market_data": market_data.provenance,
            "financial_statements": financial_statements.provenance,
            "corporate_actions": corporate_actions.provenance,
            "historical_series": historical_series.provenance,
            "valuation": valuation.provenance,
            "margin_of_safety": margin_of_safety.provenance,
            "business_quality": business_quality.provenance,
            "risk": risk.provenance,
            "scenarios": scenarios.provenance,
            "recommendation": recommendation.provenance,
            "explainability": explainability.provenance,
            "audit": audit.provenance,
            "identity": identity.provenance,
        }

        metadata = ResearchMetadata(
            research_object_id=object_id,
            schema_version=RESEARCH_OBJECT_SCHEMA_VERSION,
            created_at=created_at,
            research_mode=self._research_mode,
            correlation_id=self._correlation_id or meta_block.get("correlation_id"),
            ticker=self._symbol,
            company=self._company
            or (
                identity_payload.get("company_name")
                if identity_payload
                else None
            ),
            exchange=self._exchange
            or (identity_payload.get("exchange") if identity_payload else None),
            report_version=pipeline_version,
            pipeline_version=pipeline_version,
            platform_version=platform_version,
            api_version=self._api_version,
            package_versions=MappingProxyType(package_versions),
        )

        version = ResearchVersion(
            schema_version=RESEARCH_OBJECT_SCHEMA_VERSION,
            object_version="1",
            builder_version=BUILDER_VERSION,
        )

        data_retrieval = (
            freeze_mapping(dict(self._data_bundle["retrieval"]))
            if isinstance(self._data_bundle, Mapping)
            and isinstance(self._data_bundle.get("retrieval"), Mapping)
            else None
        )
        data_health = (
            freeze_mapping(dict(self._data_bundle["health"]))
            if isinstance(self._data_bundle, Mapping)
            and isinstance(self._data_bundle.get("health"), Mapping)
            else None
        )

        obj = ResearchObject(
            metadata=metadata,
            identity=identity,
            market_data=market_data,
            financial_statements=financial_statements,
            corporate_actions=corporate_actions,
            historical_series=historical_series,
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
            data_retrieval=data_retrieval,
            data_health=data_health,
        )
        validate_research_object(obj)
        return obj


def build_research_object(
    *,
    symbol: str,
    data_bundle: Mapping[str, Any] | None = None,
    analysis_payload: Mapping[str, Any] | None = None,
    valuation_signals: Mapping[str, Any] | None = None,
    company: str | None = None,
    exchange: str | None = None,
    correlation_id: str | None = None,
    platform_version: str | None = None,
    api_version: str | None = "v1",
    research_mode: str = "Research Mode",
    object_id: str | None = None,
    created_at: str | None = None,
) -> ResearchObject:
    """Convenience builder entry point."""
    builder = (
        ResearchObjectBuilder()
        .with_identity(symbol, company=company, exchange=exchange)
        .with_data_bundle(data_bundle)
        .with_analysis_payload(analysis_payload)
        .with_valuation_signals(valuation_signals)
        .with_correlation_id(correlation_id)
        .with_versions(api_version=api_version, platform_version=platform_version)
        .with_research_mode(research_mode)
    )
    if object_id:
        builder = builder.with_object_id(object_id)
    if created_at:
        builder = builder.with_created_at(created_at)
    return builder.build()
