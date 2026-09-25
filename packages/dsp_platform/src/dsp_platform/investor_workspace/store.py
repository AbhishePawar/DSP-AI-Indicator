"""Per-user investor workspace store (Figma Dashboard / Portfolio / Profile).

Holds user-authored records only:

- watchlist symbols
- portfolio holdings (quantity + average cost — user input, never inferred)
- saved research (Research Hub cards)
- research canvases (Research Canvas blocks)
- client financial profile (Client Profile form)

Market prices, ratings and scores are *not* stored here; they are joined at
read time by ``InvestorWorkspaceService`` from authenticated services.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from threading import Lock, RLock
from typing import Any

from dsp_platform.durable_snapshot import (
    ensure_snapshot_table,
    load_snapshot,
    save_snapshot,
)

__all__ = [
    "WORKSPACE_SNAPSHOT_KEY",
    "WORKSPACE_SNAPSHOT_TABLE",
    "DatabaseInvestorWorkspaceStore",
    "InvestorWorkspaceStore",
    "WorkspaceValidationError",
    "get_investor_workspace_store",
    "reset_investor_workspace_store_for_tests",
]

WORKSPACE_SNAPSHOT_TABLE = "investor_workspace_snapshots"
WORKSPACE_SNAPSHOT_KEY = "investor_workspace_v1"


class WorkspaceValidationError(ValueError):
    """Client-supplied record failed validation (HTTP 422)."""


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text or len(text) > 32:
        raise WorkspaceValidationError("symbol must be 1–32 characters")
    return text


def _positive(value: Any, name: str, *, allow_zero: bool = False) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise WorkspaceValidationError(f"{name} must be numeric") from None
    if out != out or out < 0 or (out == 0 and not allow_zero):
        raise WorkspaceValidationError(f"{name} must be {'≥' if allow_zero else '>'} 0")
    return out


def _optional_nonneg(value: Any, name: str) -> float | None:
    if value is None or value == "":
        return None
    return _positive(value, name, allow_zero=True)


class InvestorWorkspaceStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._watchlists: dict[str, list[dict[str, Any]]] = {}
        self._holdings: dict[str, dict[str, dict[str, Any]]] = {}
        self._saved_research: dict[str, dict[str, dict[str, Any]]] = {}
        self._canvases: dict[str, dict[str, dict[str, Any]]] = {}
        self._profiles: dict[str, dict[str, Any]] = {}

    # -- watchlist ---------------------------------------------------------
    def list_watchlist(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._watchlists.get(user_id, [])]

    def add_watchlist(self, user_id: str, symbol: str, *, exchange: str | None = None) -> dict[str, Any]:
        sym = _symbol(symbol)
        with self._lock:
            items = self._watchlists.setdefault(user_id, [])
            for item in items:
                if item["symbol"] == sym:
                    return dict(item)
            record = {
                "symbol": sym,
                "exchange": (str(exchange).strip().upper() or None) if exchange else None,
                "added_at": _now(),
            }
            items.append(record)
            return dict(record)

    def remove_watchlist(self, user_id: str, symbol: str) -> bool:
        sym = _symbol(symbol)
        with self._lock:
            items = self._watchlists.get(user_id, [])
            before = len(items)
            self._watchlists[user_id] = [i for i in items if i["symbol"] != sym]
            return len(self._watchlists[user_id]) != before

    # -- holdings ----------------------------------------------------------
    def list_holdings(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(h) for h in self._holdings.get(user_id, {}).values()]

    def upsert_holding(
        self,
        user_id: str,
        *,
        symbol: str,
        quantity: Any,
        average_cost: Any,
        exchange: str | None = None,
        sector: str | None = None,
    ) -> dict[str, Any]:
        sym = _symbol(symbol)
        qty = _positive(quantity, "quantity")
        avg = _positive(average_cost, "average_cost")
        with self._lock:
            book = self._holdings.setdefault(user_id, {})
            existing = book.get(sym)
            record = {
                "holding_id": existing["holding_id"] if existing else str(uuid.uuid4()),
                "symbol": sym,
                "exchange": (str(exchange).strip().upper() or None) if exchange else (existing or {}).get("exchange"),
                "quantity": qty,
                "average_cost": avg,
                "sector_override": (str(sector).strip() or None) if sector else (existing or {}).get("sector_override"),
                "created_at": existing["created_at"] if existing else _now(),
                "updated_at": _now(),
            }
            book[sym] = record
            return dict(record)

    def remove_holding(self, user_id: str, symbol: str) -> bool:
        sym = _symbol(symbol)
        with self._lock:
            return self._holdings.get(user_id, {}).pop(sym, None) is not None

    def clear_holdings(self, user_id: str) -> int:
        with self._lock:
            count = len(self._holdings.get(user_id, {}))
            self._holdings[user_id] = {}
            return count

    # -- saved research ----------------------------------------------------
    def list_saved_research(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._saved_research.get(user_id, {}).values())
        rows.sort(key=lambda r: r["updated_at"], reverse=True)
        return [dict(r) for r in rows]

    def save_research(
        self,
        user_id: str,
        *,
        symbol: str,
        title: str,
        tags: list[str] | None = None,
        turns: int | None = None,
        research_id: str | None = None,
        saved_id: str | None = None,
    ) -> dict[str, Any]:
        sym = _symbol(symbol)
        clean_title = str(title or "").strip()
        if not clean_title or len(clean_title) > 200:
            raise WorkspaceValidationError("title must be 1–200 characters")
        clean_tags = [str(t).strip() for t in (tags or []) if str(t).strip()][:12]
        if turns is not None:
            try:
                turns = int(turns)
            except (TypeError, ValueError):
                raise WorkspaceValidationError("turns must be an integer") from None
            if turns < 0:
                raise WorkspaceValidationError("turns must be ≥ 0")
        with self._lock:
            book = self._saved_research.setdefault(user_id, {})
            existing = book.get(saved_id) if saved_id else None
            record = {
                "saved_id": existing["saved_id"] if existing else (saved_id or str(uuid.uuid4())),
                "symbol": sym,
                "title": clean_title,
                "tags": clean_tags,
                "turns": turns if turns is not None else (existing or {}).get("turns"),
                "research_id": research_id or (existing or {}).get("research_id"),
                "created_at": existing["created_at"] if existing else _now(),
                "updated_at": _now(),
            }
            book[record["saved_id"]] = record
            return dict(record)

    def delete_saved_research(self, user_id: str, saved_id: str) -> bool:
        with self._lock:
            return self._saved_research.get(user_id, {}).pop(str(saved_id), None) is not None

    # -- canvases ----------------------------------------------------------
    def list_canvases(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._canvases.get(user_id, {}).values())
        rows.sort(key=lambda r: r["updated_at"], reverse=True)
        return [dict(r) for r in rows]

    def get_canvas(self, user_id: str, canvas_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._canvases.get(user_id, {}).get(str(canvas_id))
            return dict(row) if row else None

    def save_canvas(
        self,
        user_id: str,
        *,
        title: str,
        blocks: list[dict[str, Any]],
        canvas_id: str | None = None,
    ) -> dict[str, Any]:
        clean_title = str(title or "").strip() or "Untitled canvas"
        if len(clean_title) > 200:
            raise WorkspaceValidationError("title must be ≤ 200 characters")
        if not isinstance(blocks, list) or len(blocks) > 500:
            raise WorkspaceValidationError("blocks must be a list of ≤ 500 items")
        allowed = {"heading", "text", "metric", "table", "chart-ref", "divider"}
        clean_blocks: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                raise WorkspaceValidationError("each block must be an object")
            kind = str(block.get("type") or "")
            if kind not in allowed:
                raise WorkspaceValidationError(f"unsupported block type {kind!r}")
            clean_blocks.append(
                {
                    "id": str(block.get("id") or uuid.uuid4()),
                    "type": kind,
                    "content": str(block.get("content") or "")[:20_000],
                    "meta": dict(block.get("meta") or {}),
                }
            )
        with self._lock:
            book = self._canvases.setdefault(user_id, {})
            existing = book.get(canvas_id) if canvas_id else None
            record = {
                "canvas_id": existing["canvas_id"] if existing else (canvas_id or str(uuid.uuid4())),
                "title": clean_title,
                "blocks": clean_blocks,
                "version": (existing["version"] + 1) if existing else 1,
                "created_at": existing["created_at"] if existing else _now(),
                "updated_at": _now(),
            }
            book[record["canvas_id"]] = record
            return dict(record)

    def delete_canvas(self, user_id: str, canvas_id: str) -> bool:
        with self._lock:
            return self._canvases.get(user_id, {}).pop(str(canvas_id), None) is not None

    # -- client financial profile ------------------------------------------
    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._profiles.get(user_id)
            return dict(row) if row else None

    def put_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        clean = validate_financial_profile(profile)
        with self._lock:
            existing = self._profiles.get(user_id)
            record = {
                **clean,
                "created_at": existing["created_at"] if existing else _now(),
                "updated_at": _now(),
            }
            self._profiles[user_id] = record
            return dict(record)

    # -- state -------------------------------------------------------------
    def export_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "watchlists": {k: [dict(i) for i in v] for k, v in self._watchlists.items()},
                "holdings": {k: {s: dict(h) for s, h in v.items()} for k, v in self._holdings.items()},
                "saved_research": {k: {s: dict(h) for s, h in v.items()} for k, v in self._saved_research.items()},
                "canvases": {k: {s: dict(h) for s, h in v.items()} for k, v in self._canvases.items()},
                "profiles": {k: dict(v) for k, v in self._profiles.items()},
            }

    def import_state(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._watchlists = {
                str(k): [dict(i) for i in (v or [])]
                for k, v in (payload.get("watchlists") or {}).items()
            }
            self._holdings = {
                str(k): {str(s): dict(h) for s, h in (v or {}).items()}
                for k, v in (payload.get("holdings") or {}).items()
            }
            self._saved_research = {
                str(k): {str(s): dict(h) for s, h in (v or {}).items()}
                for k, v in (payload.get("saved_research") or {}).items()
            }
            self._canvases = {
                str(k): {str(s): dict(h) for s, h in (v or {}).items()}
                for k, v in (payload.get("canvases") or {}).items()
            }
            self._profiles = {
                str(k): dict(v) for k, v in (payload.get("profiles") or {}).items()
            }


# Figma Client Profile form fields — exact set; nothing else is accepted.
PROFILE_TEXT_FIELDS = ("full_name", "email", "mobile", "city", "occupation")
PROFILE_INT_FIELDS = ("age", "dependents", "target_year")
PROFILE_MONEY_FIELDS = (
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
    "other_monthly_income",
    "total_savings",
    "total_investments",
    "emergency_fund",
    "outstanding_loans",
    "credit_card_outstanding",
    # Figma "Health Insurance" / "Life / Term Insurance" are ₹ cover amounts.
    "health_insurance",
    "life_insurance",
    "target_amount",
)
PROFILE_BOOL_FIELDS = ("no_outstanding_debt",)
PROFILE_GOALS = (
    "wealth_creation",
    "retirement",
    "regular_income",
    "childrens_education",
    "home_purchase",
    "marriage",
    "emergency_fund",
    "other",
)


def validate_financial_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise WorkspaceValidationError("profile must be an object")
    out: dict[str, Any] = {}
    for key in PROFILE_TEXT_FIELDS:
        raw = profile.get(key)
        out[key] = (str(raw).strip()[:200] or None) if raw is not None else None
    for key in PROFILE_INT_FIELDS:
        raw = profile.get(key)
        if raw is None or raw == "":
            out[key] = None
            continue
        try:
            val = int(raw)
        except (TypeError, ValueError):
            raise WorkspaceValidationError(f"{key} must be an integer") from None
        if val < 0 or val > 3000:
            raise WorkspaceValidationError(f"{key} out of range")
        out[key] = val
    for key in PROFILE_MONEY_FIELDS:
        out[key] = _optional_nonneg(profile.get(key), key)
    for key in PROFILE_BOOL_FIELDS:
        raw = profile.get(key)
        out[key] = None if raw is None else bool(raw)
    goal = profile.get("primary_goal")
    if goal is not None and goal != "":
        goal_key = str(goal).strip().lower()
        if goal_key not in PROFILE_GOALS:
            raise WorkspaceValidationError("primary_goal is not a recognised goal")
        out["primary_goal"] = goal_key
    else:
        out["primary_goal"] = None
    investments = profile.get("investments")
    clean_inv: list[dict[str, Any]] = []
    if investments is not None:
        if not isinstance(investments, list) or len(investments) > 100:
            raise WorkspaceValidationError("investments must be a list of ≤ 100 items")
        for item in investments:
            if not isinstance(item, dict):
                raise WorkspaceValidationError("each investment must be an object")
            clean_inv.append(
                {
                    "label": str(item.get("label") or "").strip()[:120],
                    "kind": str(item.get("kind") or "").strip()[:60] or None,
                    "amount": _optional_nonneg(item.get("amount"), "investment.amount"),
                }
            )
    out["investments"] = clean_inv
    return out


_META = frozenset(
    {"ensure_schema", "ensure_fresh", "hydrate", "flush", "export_state", "import_state"}
)
_READ_ONLY = frozenset(
    {
        "list_watchlist",
        "list_holdings",
        "list_saved_research",
        "list_canvases",
        "get_canvas",
        "get_profile",
    }
)


class DatabaseInvestorWorkspaceStore(InvestorWorkspaceStore):
    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self.ensure_schema()
        self.hydrate()

    def ensure_schema(self) -> None:
        ensure_snapshot_table(self._db, WORKSPACE_SNAPSHOT_TABLE)

    def ensure_fresh(self) -> None:
        with self._persist_lock:
            self.hydrate()

    def hydrate(self) -> None:
        payload = load_snapshot(
            self._db, table=WORKSPACE_SNAPSHOT_TABLE, snapshot_key=WORKSPACE_SNAPSHOT_KEY
        )
        if payload:
            self.import_state(payload)

    def flush(self) -> None:
        with self._persist_lock:
            save_snapshot(
                self._db,
                table=WORKSPACE_SNAPSHOT_TABLE,
                snapshot_key=WORKSPACE_SNAPSHOT_KEY,
                payload=self.export_state(),
                updated_at=_now(),
            )

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_") or name in _META:
            return object.__getattribute__(self, name)
        attr = object.__getattribute__(self, name)
        if not callable(attr):
            return attr

        def bound(*args: Any, **kwargs: Any) -> Any:
            object.__getattribute__(self, "ensure_fresh")()
            result = attr(*args, **kwargs)
            if name not in _READ_ONLY:
                object.__getattribute__(self, "flush")()
            return result

        return bound


_STORE_LOCK = Lock()
_STORE: InvestorWorkspaceStore | None = None


def get_investor_workspace_store(database: Any | None = None) -> InvestorWorkspaceStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = (
                DatabaseInvestorWorkspaceStore(database)
                if database is not None
                else InvestorWorkspaceStore()
            )
        return _STORE


def reset_investor_workspace_store_for_tests(
    store: InvestorWorkspaceStore | None = None,
) -> None:
    global _STORE
    with _STORE_LOCK:
        _STORE = store
