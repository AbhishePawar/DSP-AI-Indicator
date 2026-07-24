"""Snapshot Bridge — contracts → engine-native snapshots.

Sprint 6.4 completes the data plane by translating canonical
``contracts`` outputs from the Data Engine into the snapshot types
analytical engines already consume:

* ``tuple[FundamentalStatement, ...]`` → ``FinancialSnapshot``
* ``Mapping[str, EconomicSeries]`` → ``EconomicSnapshot``

This package may depend on ``contracts``, ``core``, ``data_engine``,
``fundamental``, and ``economic``. Engines must never depend back on
it. ``data_engine`` never imports this package (or the engines).
"""

from __future__ import annotations

from snapshot_bridge.economic import EconomicSnapshotBuilder
from snapshot_bridge.exceptions import SnapshotBridgeError
from snapshot_bridge.financial import FinancialSnapshotBuilder
from snapshot_bridge.services import EconomicBridgeService, FinancialBridgeService

__all__ = [
    "EconomicBridgeService",
    "EconomicSnapshotBuilder",
    "FinancialBridgeService",
    "FinancialSnapshotBuilder",
    "SnapshotBridgeError",
]

__version__ = "0.1.0"
