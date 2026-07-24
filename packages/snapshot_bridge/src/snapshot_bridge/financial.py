"""FinancialSnapshot construction from contracts statements."""

from __future__ import annotations

from collections.abc import Sequence

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from core.exceptions import ValidationError
from data_engine import DataEngineError, FundamentalStatementsBuilder
from fundamental import FinancialSnapshot
from snapshot_bridge.exceptions import SnapshotBridgeError

__all__ = ["FinancialSnapshotBuilder"]


class FinancialSnapshotBuilder:
    """Bridge ``FundamentalStatement`` tuples into ``FinancialSnapshot``.

    Ordering, instrument consistency, and uniqueness are enforced via
    ``data_engine.builders.FundamentalStatementsBuilder`` (contracts
    layer), then handed to ``fundamental.models.FinancialSnapshot``
    which applies the engine's own structural validation. No ratios or
    growth figures are computed here — the Fundamental Engine's
    analyzers derive margins, ROE, growth, etc. from the snapshot.
    """

    @staticmethod
    def build(
        instrument: Instrument,
        statements: Sequence[FundamentalStatement],
    ) -> FinancialSnapshot:
        """Assemble a validated ``FinancialSnapshot``.

        Args:
            instrument: Instrument every statement must belong to.
            statements: As-reported statements in any order.

        Returns:
            Engine-native ``FinancialSnapshot`` (most-recent-first).

        Raises:
            SnapshotBridgeError: If statements fail structural validation.
        """
        try:
            ordered = FundamentalStatementsBuilder.build(
                instrument, tuple(statements)
            )
            return FinancialSnapshot(instrument=instrument, statements=ordered)
        except (ValidationError, DataEngineError) as exc:
            msg = f"failed to build FinancialSnapshot: {exc}"
            raise SnapshotBridgeError(msg) from exc
