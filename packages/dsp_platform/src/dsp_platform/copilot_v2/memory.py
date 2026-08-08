"""Conversation memory for Copilot 2.0 — context + turns (no research payloads)."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any
from uuid import uuid4

__all__ = [
    "CopilotMemoryStore",
    "get_copilot_memory_store",
    "reset_copilot_memory_store_for_tests",
]


def _empty_context() -> dict[str, Any]:
    return {
        "current_company": None,
        "current_portfolio_id": None,
        "previous_questions": [],
        "previous_comparisons": [],
        "selected_valuation": None,
        "current_workspace": None,
        "symbols": [],
        "mode": None,
    }


class CopilotMemoryStore:
    """Process-local conversation memory for Copilot 2.0.

    Stores turn metadata and session context pointers only — never mutable
    research engine payloads (architecture freeze).
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._turns: dict[str, list[dict[str, Any]]] = {}
        self._context: dict[str, dict[str, Any]] = {}
        self._meta: dict[str, dict[str, Any]] = {}

    def ensure(self, conversation_id: str | None = None) -> str:
        cid = (conversation_id or "").strip() or str(uuid4())
        with self._lock:
            self._turns.setdefault(cid, [])
            self._context.setdefault(cid, _empty_context())
            self._meta.setdefault(
                cid,
                {"conversation_id": cid, "title": "Research Copilot", "updated_at": None},
            )
        return cid

    def append(self, conversation_id: str, turn: dict[str, Any]) -> None:
        cid = self.ensure(conversation_id)
        with self._lock:
            self._turns[cid].append(dict(turn))
            self._meta[cid]["updated_at"] = turn.get("created_at")

    def history(self, conversation_id: str) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(self._turns.get(conversation_id, []))

    def get_context(self, conversation_id: str) -> dict[str, Any]:
        cid = self.ensure(conversation_id)
        with self._lock:
            return deepcopy(self._context[cid])

    def update_context(self, conversation_id: str, patch: dict[str, Any] | None) -> dict[str, Any]:
        cid = self.ensure(conversation_id)
        if not patch:
            return self.get_context(cid)
        with self._lock:
            ctx = self._context[cid]
            for key, value in patch.items():
                if key == "previous_questions" and isinstance(value, list):
                    prior = list(ctx.get("previous_questions") or [])
                    for item in value:
                        if item and item not in prior:
                            prior.append(item)
                    ctx["previous_questions"] = prior[-50:]
                elif key == "previous_comparisons" and isinstance(value, list):
                    prior = list(ctx.get("previous_comparisons") or [])
                    for item in value:
                        if item and item not in prior:
                            prior.append(item)
                    ctx["previous_comparisons"] = prior[-20:]
                elif key == "symbols" and isinstance(value, list):
                    symbols = []
                    for raw in value:
                        sym = str(raw or "").strip().upper()
                        if sym and sym not in symbols:
                            symbols.append(sym)
                    ctx["symbols"] = symbols[:20]
                else:
                    ctx[key] = value
            return deepcopy(ctx)

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = []
            for cid, meta in self._meta.items():
                rows.append(
                    {
                        **meta,
                        "turn_count": len(self._turns.get(cid, [])),
                        "context": {
                            "current_company": (self._context.get(cid) or {}).get(
                                "current_company"
                            ),
                            "current_portfolio_id": (self._context.get(cid) or {}).get(
                                "current_portfolio_id"
                            ),
                            "mode": (self._context.get(cid) or {}).get("mode"),
                        },
                    }
                )
            rows.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
            return rows

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            existed = conversation_id in self._turns or conversation_id in self._context
            self._turns.pop(conversation_id, None)
            self._context.pop(conversation_id, None)
            self._meta.pop(conversation_id, None)
            return existed


_STORE: CopilotMemoryStore | None = None


def get_copilot_memory_store() -> CopilotMemoryStore:
    global _STORE
    if _STORE is None:
        _STORE = CopilotMemoryStore()
    return _STORE


def reset_copilot_memory_store_for_tests(store: CopilotMemoryStore | None = None) -> None:
    global _STORE
    _STORE = store
