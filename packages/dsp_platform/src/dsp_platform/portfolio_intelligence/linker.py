"""Research linker (EPIC-A002) — map symbols to provided Research Objects only."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.portfolio_intelligence.models import UNAVAILABLE_MESSAGE
from dsp_platform.research_archive.hashing import to_plain_jsonable

__all__ = [
    "ResearchBundle",
    "extract_field",
    "link_research_map",
    "section_available",
    "section_payload",
]


class ResearchBundle:
    """Read-only research artifacts for one symbol."""

    __slots__ = (
        "symbol",
        "research_object",
        "report",
        "snapshot",
        "research_object_id",
        "report_id",
        "snapshot_id",
    )

    def __init__(
        self,
        symbol: str,
        *,
        research_object: Mapping[str, Any] | None = None,
        report: Mapping[str, Any] | None = None,
        snapshot: Mapping[str, Any] | None = None,
    ) -> None:
        self.symbol = symbol
        self.research_object = (
            to_plain_jsonable(research_object)
            if isinstance(research_object, Mapping)
            else None
        )
        self.report = to_plain_jsonable(report) if isinstance(report, Mapping) else None
        self.snapshot = (
            to_plain_jsonable(snapshot) if isinstance(snapshot, Mapping) else None
        )
        self.research_object_id = _id_from(self.research_object, "research_object_id")
        self.report_id = _id_from(self.report, "report_id")
        self.snapshot_id = (
            str(self.snapshot.get("snapshot_id"))
            if isinstance(self.snapshot, dict) and self.snapshot.get("snapshot_id")
            else None
        )


def _id_from(doc: Any, key: str) -> str | None:
    if not isinstance(doc, dict):
        return None
    meta = doc.get("metadata")
    if isinstance(meta, dict) and meta.get(key):
        return str(meta[key])
    return None


def link_research_map(
    *,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    snapshot_ids: Mapping[str, str] | None = None,
) -> dict[str, ResearchBundle]:
    """Build symbol → ResearchBundle from caller-supplied artifacts only."""
    ro_map = _index_by_symbol(research_objects, prefer_keys=("ticker", "symbol"))
    report_map = _index_by_symbol(reports, prefer_keys=("ticker", "symbol"))
    snap_map = _index_snapshots(snapshots)

    if snapshot_ids:
        from dsp_platform.research_archive import get_research_archive

        archive = get_research_archive()
        for symbol, snap_id in snapshot_ids.items():
            sym = str(symbol).strip().upper()
            if not sym:
                continue
            try:
                snap_map[sym] = archive.get_dict(str(snap_id))
            except Exception:  # noqa: BLE001 — missing stays unlinked
                continue

    symbols = sorted(set(ro_map) | set(report_map) | set(snap_map))
    out: dict[str, ResearchBundle] = {}
    for sym in symbols:
        snap = snap_map.get(sym)
        # If snapshot holds research_object payload and RO missing, expose payload
        ro = ro_map.get(sym)
        if ro is None and isinstance(snap, dict) and snap.get("kind") == "research_object":
            payload = snap.get("payload")
            if isinstance(payload, dict):
                ro = payload
        report = report_map.get(sym)
        if (
            report is None
            and isinstance(snap, dict)
            and snap.get("kind") == "institutional_report"
        ):
            payload = snap.get("payload")
            if isinstance(payload, dict):
                report = payload
        out[sym] = ResearchBundle(
            sym, research_object=ro, report=report, snapshot=snap
        )
    return out


def _index_by_symbol(
    items: Mapping[str, Any] | list[Any] | None,
    *,
    prefer_keys: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if items is None:
        return out
    if isinstance(items, Mapping):
        # Either symbol→doc or a single doc
        for key, value in items.items():
            if isinstance(value, Mapping) and (
                "metadata" in value or "identity" in value or "version" in value
            ):
                sym = str(key).strip().upper()
                out[sym] = to_plain_jsonable(value)  # type: ignore[assignment]
            elif key in prefer_keys:
                # single document keyed oddly — ignore
                continue
        # If mapping looks like a single research object
        if not out and ("metadata" in items or "identity" in items):
            sym = _symbol_from_doc(items)
            if sym:
                out[sym] = to_plain_jsonable(items)  # type: ignore[assignment]
        return out
    if isinstance(items, list):
        for value in items:
            if not isinstance(value, Mapping):
                continue
            sym = _symbol_from_doc(value)
            if sym:
                out[sym] = to_plain_jsonable(value)  # type: ignore[assignment]
    return out


def _index_snapshots(
    items: Mapping[str, Any] | list[Any] | None,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if items is None:
        return out
    if isinstance(items, Mapping):
        for key, value in items.items():
            if isinstance(value, Mapping) and "snapshot_id" in value:
                sym = str(value.get("ticker") or key).strip().upper()
                out[sym] = to_plain_jsonable(value)  # type: ignore[assignment]
            elif isinstance(value, Mapping):
                # symbol → snapshot
                out[str(key).strip().upper()] = to_plain_jsonable(value)  # type: ignore[assignment]
        return out
    if isinstance(items, list):
        for value in items:
            if not isinstance(value, Mapping):
                continue
            sym = str(value.get("ticker") or "").strip().upper()
            if not sym:
                payload = value.get("payload")
                if isinstance(payload, dict):
                    sym = _symbol_from_doc(payload) or ""
            if sym:
                out[sym] = to_plain_jsonable(value)  # type: ignore[assignment]
    return out


def _symbol_from_doc(doc: Mapping[str, Any]) -> str | None:
    meta = doc.get("metadata")
    if isinstance(meta, dict):
        if meta.get("ticker"):
            return str(meta["ticker"]).strip().upper()
    identity = doc.get("identity")
    if isinstance(identity, dict):
        payload = identity.get("payload")
        if isinstance(payload, dict):
            if payload.get("symbol"):
                return str(payload["symbol"]).strip().upper()
            if payload.get("ticker"):
                return str(payload["ticker"]).strip().upper()
        if identity.get("symbol"):
            return str(identity["symbol"]).strip().upper()
    return None


def section_payload(doc: Mapping[str, Any] | None, section: str) -> Any:
    if not isinstance(doc, dict):
        return None
    block = doc.get(section)
    if not isinstance(block, dict):
        return None
    if block.get("available") is False:
        return None
    return block.get("payload")


def section_available(doc: Mapping[str, Any] | None, section: str) -> bool:
    if not isinstance(doc, dict):
        return False
    block = doc.get(section)
    if not isinstance(block, dict):
        return False
    return bool(block.get("available"))


def extract_field(doc: Mapping[str, Any] | None, section: str, *keys: str) -> Any:
    """Pass-through field lookup from RO/report section payload."""
    payload = section_payload(doc, section)
    if not isinstance(payload, dict):
        return UNAVAILABLE_MESSAGE
    # Prefer nested fields map (report display)
    fields = payload.get("fields")
    if isinstance(fields, dict):
        for key in keys:
            if key in fields and fields[key] is not None:
                return fields[key]
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    identity = section_payload(doc, "identity") if section != "identity" else payload
    if section == "identity" and isinstance(payload, dict):
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
    if isinstance(identity, dict):
        for key in keys:
            if key in identity and identity[key] is not None:
                return identity[key]
    return UNAVAILABLE_MESSAGE
