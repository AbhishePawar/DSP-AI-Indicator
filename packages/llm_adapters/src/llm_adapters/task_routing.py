"""Dynamic Task Routing and Fallback Policy Engine.

Enforces task-to-provider mappings, validated fallback rules, bounded timeouts,
and strict dual-model independence checks for authoritative statement corroboration.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_ROUTING_STORE_PATH = os.environ.get(
    "DSP_TASK_ROUTING_PATH", "/tmp/dsp_task_routing.json"
)


@dataclass
class TaskPolicy:
    """Routing policy configuration for a specific platform task."""

    task_id: str
    display_name: str
    description: str
    primary_provider: str
    primary_model: str
    fallback_provider: str | None = None
    fallback_model: str | None = None
    require_corroboration: bool = False
    secondary_provider: str | None = None
    secondary_model: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 1
    deterministic_fallback_allowed: bool = True
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_TASK_POLICIES: list[TaskPolicy] = [
    TaskPolicy(
        task_id="statement_extraction",
        display_name="Financial Statement Extraction",
        description="Extracts line items from regulatory SEC/BSE/NSE filings into structured metrics.",
        primary_provider="gemini",
        primary_model="gemini-2.0-flash",
        fallback_provider="openai",
        fallback_model="gpt-4.1-mini",
        require_corroboration=True,
        secondary_provider="openai",
        secondary_model="gpt-4.1-mini",
        timeout_seconds=25.0,
        max_retries=1,
    ),
    TaskPolicy(
        task_id="statement_corroboration",
        display_name="Independent Statement Corroboration",
        description="Secondary independent extraction used to verify figures within 5% tolerance.",
        primary_provider="openai",
        primary_model="gpt-4.1-mini",
        fallback_provider="deepseek",
        fallback_model="deepseek-chat",
        timeout_seconds=25.0,
        max_retries=1,
    ),
    TaskPolicy(
        task_id="qualitative_research",
        display_name="Qualitative Company Research",
        description="Analyzes business model, industry tailwinds, competitive moat, and management.",
        primary_provider="gemini",
        primary_model="gemini-2.0-flash",
        fallback_provider="openai",
        fallback_model="gpt-4.1-mini",
        timeout_seconds=30.0,
        max_retries=1,
    ),
    TaskPolicy(
        task_id="evidence_summarization",
        display_name="Evidence Summarization",
        description="Summarizes filing notes, auditor remarks, and regulatory announcements.",
        primary_provider="gemini",
        primary_model="gemini-2.0-flash",
        fallback_provider="openai",
        fallback_model="gpt-4.1-mini",
        timeout_seconds=20.0,
        max_retries=1,
    ),
    TaskPolicy(
        task_id="citation_verification",
        display_name="Citation & Evidence Verification",
        description="Cross-references claims against source document paragraph anchors.",
        primary_provider="openai",
        primary_model="gpt-4.1-mini",
        fallback_provider="gemini",
        fallback_model="gemini-2.0-flash",
        timeout_seconds=20.0,
        max_retries=1,
    ),
    TaskPolicy(
        task_id="general_ai",
        display_name="General AI Explanations",
        description="Provides conversational context, metric definitions, and user Q&A.",
        primary_provider="gemini",
        primary_model="gemini-2.0-flash",
        fallback_provider="openai",
        fallback_model="gpt-4.1-mini",
        timeout_seconds=20.0,
        max_retries=1,
    ),
]


class TaskRoutingManager:
    """Thread-safe task routing and fallback coordinator."""

    def __init__(self, store_path: str = DEFAULT_ROUTING_STORE_PATH):
        self._lock = threading.RLock()
        self._store_path = store_path
        self._policies: dict[str, TaskPolicy] = {}

        for p in DEFAULT_TASK_POLICIES:
            self._policies[p.task_id] = copy.deepcopy(p)

        self._load_from_disk_if_present()

    def _load_from_disk_if_present(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                for tid, pdata in data.items():
                    if tid in self._policies:
                        curr = self._policies[tid]
                        curr.primary_provider = pdata.get("primary_provider", curr.primary_provider)
                        curr.primary_model = pdata.get("primary_model", curr.primary_model)
                        curr.fallback_provider = pdata.get("fallback_provider", curr.fallback_provider)
                        curr.fallback_model = pdata.get("fallback_model", curr.fallback_model)
                        curr.require_corroboration = pdata.get("require_corroboration", curr.require_corroboration)
                        curr.secondary_provider = pdata.get("secondary_provider", curr.secondary_provider)
                        curr.secondary_model = pdata.get("secondary_model", curr.secondary_model)
                        curr.timeout_seconds = pdata.get("timeout_seconds", curr.timeout_seconds)
                        curr.max_retries = pdata.get("max_retries", curr.max_retries)
                        curr.version = pdata.get("version", curr.version)
        except Exception as e:
            logger.error("Failed to load task routing policies from disk: %s", e)

    def _save_to_disk(self) -> None:
        try:
            data = {tid: pol.to_dict() for tid, pol in self._policies.items()}
            temp_path = f"{self._store_path}.tmp.{os.getpid()}"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, self._store_path)
        except Exception as e:
            logger.error("Failed to save task routing policies to disk: %s", e)

    def get_policy(self, task_id: str) -> TaskPolicy | None:
        with self._lock:
            p = self._policies.get(task_id)
            return copy.deepcopy(p) if p else None

    def list_policies(self) -> list[TaskPolicy]:
        with self._lock:
            return [copy.deepcopy(p) for p in self._policies.values()]

    def update_policy(
        self,
        task_id: str,
        *,
        primary_provider: str | None = None,
        primary_model: str | None = None,
        fallback_provider: str | None = None,
        fallback_model: str | None = None,
        require_corroboration: bool | None = None,
        secondary_provider: str | None = None,
        secondary_model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> TaskPolicy:
        with self._lock:
            policy = self._policies.get(task_id)
            if not policy:
                raise KeyError(f"Task policy '{task_id}' not found.")

            # Validate independence for corroboration tasks
            eff_prim_prov = primary_provider or policy.primary_provider
            eff_prim_mod = primary_model or policy.primary_model
            eff_sec_prov = secondary_provider or policy.secondary_provider
            eff_sec_mod = secondary_model or policy.secondary_model
            eff_require_corr = (
                require_corroboration
                if require_corroboration is not None
                else policy.require_corroboration
            )

            if eff_require_corr and task_id == "statement_extraction":
                if eff_prim_prov == eff_sec_prov and eff_prim_mod == eff_sec_mod:
                    raise ValueError(
                        "Dual verification requires two distinct providers or models. "
                        f"Primary and secondary cannot both be {eff_prim_prov}:{eff_prim_mod}."
                    )

            if primary_provider is not None:
                policy.primary_provider = primary_provider.lower()
            if primary_model is not None:
                policy.primary_model = primary_model
            if fallback_provider is not None:
                policy.fallback_provider = fallback_provider.lower() if fallback_provider else None
            if fallback_model is not None:
                policy.fallback_model = fallback_model
            if require_corroboration is not None:
                policy.require_corroboration = require_corroboration
            if secondary_provider is not None:
                policy.secondary_provider = secondary_provider.lower() if secondary_provider else None
            if secondary_model is not None:
                policy.secondary_model = secondary_model
            if timeout_seconds is not None:
                policy.timeout_seconds = max(1.0, min(120.0, float(timeout_seconds)))
            if max_retries is not None:
                policy.max_retries = max(0, min(5, int(max_retries)))

            policy.version += 1
            self._save_to_disk()
            return copy.deepcopy(policy)


_GLOBAL_ROUTING: TaskRoutingManager | None = None
_ROUTING_LOCK = threading.Lock()


def get_task_routing_manager() -> TaskRoutingManager:
    global _GLOBAL_ROUTING
    if _GLOBAL_ROUTING is None:
        with _ROUTING_LOCK:
            if _GLOBAL_ROUTING is None:
                _GLOBAL_ROUTING = TaskRoutingManager()
    return _GLOBAL_ROUTING
