"""Serialize compliance results (EPIC-A006)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.investment_policy.models import (
    POLICY_SCHEMA_VERSION,
    POLICY_SERVICE_VERSION,
    ComplianceResult,
    RuleResult,
    freeze_mapping,
)
from dsp_platform.investment_policy.validation import (
    InvestmentPolicyValidationError,
    validate_compliance_result,
)

__all__ = [
    "compliance_result_from_dict",
    "compliance_result_to_dict",
]


def compliance_result_to_dict(result: ComplianceResult) -> dict[str, Any]:
    validate_compliance_result(result)
    return result.to_dict()


def compliance_result_from_dict(data: Mapping[str, Any]) -> ComplianceResult:
    if not isinstance(data, Mapping):
        raise InvestmentPolicyValidationError("result must be a mapping")

    rule_results: list[RuleResult] = []
    for row in data.get("rule_results") or []:
        if not isinstance(row, Mapping):
            continue
        citations = tuple(
            freeze_mapping(dict(c)) or freeze_mapping({})
            for c in (row.get("citations") or [])
            if isinstance(c, Mapping)
        )
        rule_results.append(
            RuleResult(
                rule_id=str(row.get("rule_id") or ""),
                kind=str(row.get("kind") or ""),
                outcome=str(row.get("outcome") or ""),
                severity=str(row.get("severity") or ""),
                message=str(row.get("message") or ""),
                citations=citations,
                evidence=freeze_mapping(dict(row.get("evidence") or {}))
                or freeze_mapping({}),
            )
        )

    def _map_tuple(key: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            freeze_mapping(dict(m)) or freeze_mapping({})
            for m in (data.get(key) or [])
            if isinstance(m, Mapping)
        )

    limitations = data.get("limitations") or ()
    result = ComplianceResult(
        result_id=str(data.get("result_id") or ""),
        schema_version=str(data.get("schema_version") or POLICY_SCHEMA_VERSION),
        service_version=str(
            data.get("service_version") or POLICY_SERVICE_VERSION
        ),
        created_at=str(data.get("created_at") or ""),
        subject=str(data.get("subject") or ""),
        policy=freeze_mapping(dict(data.get("policy") or {})) or freeze_mapping({}),
        rule_results=tuple(rule_results),
        summary=freeze_mapping(dict(data.get("summary") or {})) or freeze_mapping({}),
        violations=_map_tuple("violations"),
        warnings=_map_tuple("warnings"),
        audit_trail=_map_tuple("audit_trail"),
        citations=_map_tuple("citations"),
        provenance=freeze_mapping(dict(data.get("provenance") or {}))
        or freeze_mapping({}),
        audit=freeze_mapping(dict(data.get("audit") or {})) or freeze_mapping({}),
        limitations=tuple(limitations)
        if isinstance(limitations, (list, tuple))
        else (),
    )
    validate_compliance_result(result)
    return result
