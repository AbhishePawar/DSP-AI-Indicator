"""Validate compliance results (EPIC-A006)."""

from __future__ import annotations

from dsp_platform.investment_policy.models import (
    POLICY_SCHEMA_VERSION,
    RULE_OUTCOMES,
    ComplianceResult,
)

__all__ = [
    "InvestmentPolicyValidationError",
    "validate_compliance_result",
]


class InvestmentPolicyValidationError(ValueError):
    """Compliance result failed validation."""


def validate_compliance_result(result: ComplianceResult) -> None:
    if result.schema_version != POLICY_SCHEMA_VERSION:
        raise InvestmentPolicyValidationError(
            f"unsupported schema_version {result.schema_version!r}"
        )
    if not result.result_id.strip():
        raise InvestmentPolicyValidationError("missing result_id")
    if not result.subject.strip():
        raise InvestmentPolicyValidationError("missing subject")
    if not result.created_at:
        raise InvestmentPolicyValidationError("missing created_at")
    for rule in result.rule_results:
        if rule.outcome not in RULE_OUTCOMES:
            raise InvestmentPolicyValidationError(
                f"invalid outcome {rule.outcome!r}"
            )
        if not rule.citations:
            raise InvestmentPolicyValidationError(
                f"rule {rule.rule_id} missing citations"
            )
        for c in rule.citations:
            if not c.get("path") or not c.get("section"):
                raise InvestmentPolicyValidationError(
                    f"rule {rule.rule_id} citation missing path/section"
                )
    if not result.citations:
        raise InvestmentPolicyValidationError("citations required")
    if result.provenance is None or result.audit is None:
        raise InvestmentPolicyValidationError("missing provenance/audit")
    if "status" not in result.summary:
        raise InvestmentPolicyValidationError("summary missing status")
