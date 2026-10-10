"""Application service for bounded AI research orchestration and report validation.

Decouples the HTTP composition router from LLM orchestrator internals,
safely bounding worker capacity, monotonic deadlines, cancellation propagation,
schema validation, and metric collection while preserving deterministic DSP authority.
"""

from __future__ import annotations

import concurrent.futures
import logging
import math
import os
import threading
from typing import Any

from api_platform.api.ops import metrics_registry
from api_platform.api.research_report_schema import validate_public_research_report
from llm_adapters.orchestrator.orchestrator import OrchestratorStatus
from llm_adapters.orchestrator.specification import UserResearchRequest

_LOG = logging.getLogger("dsp.api.research_orchestration")


def _parse_max_workers(default: int = 4, min_w: int = 1, max_w: int = 32) -> int:
    raw = os.environ.get("DSP_RESEARCH_MAX_WORKERS", "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
        if val < min_w:
            return min_w
        if val > max_w:
            return max_w
        return val
    except (ValueError, TypeError):
        return default


_MAX_ORCHESTRATION_WORKERS = _parse_max_workers()
_ORCHESTRATION_SEMAPHORE = threading.BoundedSemaphore(value=_MAX_ORCHESTRATION_WORKERS)
_RESEARCH_ORCHESTRATOR_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=_MAX_ORCHESTRATION_WORKERS, thread_name_prefix="dsp-research-orch"
)


def parse_orchestration_timeout(
    env_name: str = "DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS",
    fallback_name: str = "DSP_AI_REQUEST_TIMEOUT_SECONDS",
    default: float = 15.0,
    min_timeout: float = 0.01,
    max_timeout: float = 120.0,
) -> float:
    raw = os.environ.get(env_name, os.environ.get(fallback_name, "")).strip()
    if not raw:
        return default
    try:
        val = float(raw)
        if not math.isfinite(val) or val <= 0:
            return default
        if val < min_timeout:
            return min_timeout
        if val > max_timeout:
            return max_timeout
        return val
    except (ValueError, TypeError):
        return default


def _invoke_orchestrator(
    orchestrator: Any,
    request: UserResearchRequest,
    *,
    timeout_seconds: float,
    cancellation_event: threading.Event,
) -> Any:
    """Invoke orchestrator with strict bounded execution."""
    try:
        return orchestrator.run(
            request,
            timeout_seconds=timeout_seconds,
            cancellation_event=cancellation_event,
        )
    except TypeError as err:
        if (
            "unexpected keyword" in str(err)
            or "timeout_seconds" in str(err)
            or "cancellation_event" in str(err)
        ):
            _LOG.warning(
                "legacy_orchestrator_lacks_bounded_execution",
                extra={"error": str(err)},
            )
            raise RuntimeError(
                "Legacy orchestrator does not support bounded execution deadlines; failing closed."
            ) from err
        raise


def _worker_wrapper(
    orchestrator: Any,
    request: UserResearchRequest,
    *,
    timeout_seconds: float,
    cancellation_event: threading.Event,
    semaphore: threading.BoundedSemaphore,
) -> Any:
    try:
        return _invoke_orchestrator(
            orchestrator,
            request,
            timeout_seconds=timeout_seconds,
            cancellation_event=cancellation_event,
        )
    finally:
        semaphore.release()


class ResearchOrchestrationService:
    """Service layer coordinating bounded execution of AI research."""

    def __init__(
        self,
        executor: concurrent.futures.ThreadPoolExecutor | None = None,
        semaphore: threading.BoundedSemaphore | None = None,
    ) -> None:
        self._executor = executor or _RESEARCH_ORCHESTRATOR_EXECUTOR
        self._semaphore = semaphore or _ORCHESTRATION_SEMAPHORE

    def execute(
        self,
        orchestrator: Any,
        *,
        ticker: str,
        company: str,
        exchange: str,
        correlation_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        """Run bounded orchestration, validate public report, and record metrics."""
        limitations: list[str] = []
        if orchestrator is None:
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            return None, ["Research orchestrator not configured or unavailable."]

        metrics_registry.record_research_orchestration_event("attempted")
        effective_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else parse_orchestration_timeout()
        )

        if not self._semaphore.acquire(blocking=False):
            metrics_registry.record_research_orchestration_event("capacity_exhausted")
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            limitations.append("Research orchestrator capacity exhausted.")
            return None, limitations

        research_req = UserResearchRequest(
            symbol=ticker,
            question=f"Synthesize deterministic evidence and research findings for {company or ticker}.",
            exchange=exchange,
            request_id=correlation_id or f"req-{ticker}",
        )
        cancel_event = threading.Event()

        try:
            future = self._executor.submit(
                _worker_wrapper,
                orchestrator,
                research_req,
                timeout_seconds=effective_timeout,
                cancellation_event=cancel_event,
                semaphore=self._semaphore,
            )
        except Exception:
            self._semaphore.release()
            cancel_event.set()
            metrics_registry.record_research_orchestration_event("provider_failed")
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            limitations.append("Research orchestrator unavailable.")
            return None, limitations

        try:
            orchestrator_outcome = future.result(timeout=effective_timeout)
        except concurrent.futures.TimeoutError:
            cancel_event.set()
            metrics_registry.record_research_orchestration_event("timed_out")
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            limitations.append("Research orchestrator timed out.")
            return None, limitations
        except Exception:
            cancel_event.set()
            metrics_registry.record_research_orchestration_event("provider_failed")
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            limitations.append("Research orchestrator unavailable.")
            return None, limitations

        if getattr(orchestrator_outcome, "status", None) == OrchestratorStatus.FAILED_CLOSED:
            metrics_registry.record_research_orchestration_event("provider_failed")
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            limitations.append("Research orchestrator unavailable.")
            return None, limitations

        try:
            public_decision_pack = orchestrator_outcome.to_public()
            raw_dict = public_decision_pack.to_dict()
            valid_report, err = validate_public_research_report(raw_dict)
            if valid_report is not None:
                metrics_registry.record_research_orchestration_event("succeeded")
                return valid_report, []
            metrics_registry.record_research_orchestration_event("validation_failed")
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            limitations.append("Research report failed schema validation.")
            return None, limitations
        except Exception:
            metrics_registry.record_research_orchestration_event("validation_failed")
            metrics_registry.record_research_orchestration_event("deterministic_fallback")
            limitations.append("Research report failed schema validation.")
            return None, limitations


_DEFAULT_SERVICE = ResearchOrchestrationService()


def execute_research_orchestration(
    orchestrator: Any,
    *,
    ticker: str,
    company: str,
    exchange: str,
    correlation_id: str | None = None,
    timeout_seconds: float | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    return _DEFAULT_SERVICE.execute(
        orchestrator,
        ticker=ticker,
        company=company,
        exchange=exchange,
        correlation_id=correlation_id,
        timeout_seconds=timeout_seconds,
    )
