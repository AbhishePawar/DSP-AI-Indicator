"""Enterprise → equity bridge and intrinsic value per share."""

from __future__ import annotations

from dataclasses import dataclass

from valuation.dcf_intelligence.assumptions import DcfBridgeInputs
from valuation.dcf_intelligence.explain import ExplainedValue

__all__ = ["EquityBridgeResult", "compute_equity_bridge"]


@dataclass(frozen=True, slots=True)
class EquityBridgeResult:
    """Equity value and optional per-share intrinsic value."""

    equity_value: ExplainedValue
    intrinsic_value_per_share: ExplainedValue


def compute_equity_bridge(
    *,
    enterprise_value: float,
    bridge: DcfBridgeInputs,
) -> EquityBridgeResult:
    """Bridge EV to equity value.

    ``Equity = EV − Debt − Minority + Cash + Investments``
    """
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
