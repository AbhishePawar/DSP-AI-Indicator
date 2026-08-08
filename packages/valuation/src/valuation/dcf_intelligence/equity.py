"""Enterprise → equity bridge and intrinsic value per share."""

from __future__ import annotations

from dataclasses import dataclass

from valuation.dcf_intelligence.assumptions import DcfBridgeInputs
from valuation.dcf_intelligence.explain import ExplainedValue
from valuation.exceptions import ValuationError

__all__ = ["EquityBridgeResult", "compute_equity_bridge", "validate_equity_bridge"]


@dataclass(frozen=True, slots=True)
class EquityBridgeResult:
    """Equity value and optional per-share intrinsic value."""

    equity_value: ExplainedValue
    intrinsic_value_per_share: ExplainedValue


def validate_equity_bridge(
    *,
    enterprise_value: float,
    bridge: DcfBridgeInputs,
) -> None:
    """P1-04 — fail closed on invalid EV→equity bridge inputs.

    Detects structural abuses (not accounting restatement):
    * negative enterprise value
    * cash / debt / MI / investments already validated non-negative on bridge
    * cash + investments exceeding EV by an absurd margin (likely double-count)
    * shares missing when caller later needs IV/share (soft — returns None IVPS)
    """
    if enterprise_value < 0:
        raise ValuationError(
            f"enterprise_value must be non-negative, got {enterprise_value}"
        )
    add_backs = bridge.cash + bridge.non_operating_investments
    # Absurd add-backs vs EV strongly suggest cash/investments double counting.
    if enterprise_value > 0 and add_backs > enterprise_value * 2.0 + 1.0:
        raise ValuationError(
            "equity bridge unavailable: cash + investments exceed 2× enterprise "
            "value (possible double counting)"
        )
    claims = bridge.total_debt + bridge.minority_interest
    if enterprise_value > 0 and claims > enterprise_value * 5.0 + 1.0:
        raise ValuationError(
            "equity bridge unavailable: debt + minority interest exceed 5× "
            "enterprise value (possible double counting)"
        )


def compute_equity_bridge(
    *,
    enterprise_value: float,
    bridge: DcfBridgeInputs,
) -> EquityBridgeResult:
    """Bridge EV to equity value.

    ``Equity = EV − Debt − Minority + Cash + Investments``

    Each adjustment is applied exactly once.
    """
    validate_equity_bridge(enterprise_value=enterprise_value, bridge=bridge)
    equity = (
        enterprise_value
        - bridge.total_debt
        - bridge.minority_interest
        + bridge.cash
        + bridge.non_operating_investments
    )
    equity_explained = ExplainedValue(
        name="equity_value",
        value=equity,
        formula="Equity = EV − Debt − Minority + Cash + Investments",
        inputs={
            "enterprise_value": enterprise_value,
            "total_debt": bridge.total_debt,
            "minority_interest": bridge.minority_interest,
            "cash": bridge.cash,
            "non_operating_investments": bridge.non_operating_investments,
        },
        intermediates={
            "net_debt_like": bridge.total_debt + bridge.minority_interest,
            "add_backs": bridge.cash + bridge.non_operating_investments,
        },
        confidence="high",
    )

    if bridge.shares_outstanding is None:
        ivps = ExplainedValue(
            name="intrinsic_value_per_share",
            value=None,
            formula="IV/share = Equity / Shares",
            inputs={
                "equity_value": equity,
                "shares_outstanding": None,
            },
            intermediates={},
            confidence="insufficient",
            notes="shares_outstanding not provided",
        )
    else:
        per_share = equity / bridge.shares_outstanding
        ivps = ExplainedValue(
            name="intrinsic_value_per_share",
            value=per_share,
            formula="IV/share = Equity / Shares",
            inputs={
                "equity_value": equity,
                "shares_outstanding": bridge.shares_outstanding,
            },
            intermediates={},
            confidence="high",
        )

    return EquityBridgeResult(
        equity_value=equity_explained,
        intrinsic_value_per_share=ivps,
    )
