"""Provider-neutral tool-call dispatcher.

Receives already-normalized ``ToolCall`` values, authorizes them against
``ToolRegistry.public_manifest()``, and forwards only approved names to
``ToolRegistry.dispatch``. Unknown, unauthorized, and malformed calls
fail closed. DSP engines are never imported here — the injected backend
is the ``DSPPlatformToolAdapter`` (or a test stub).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from llm_adapters.tools.contract import DSPToolBackend, ToolResult, assert_no_tool_leakage
from llm_adapters.tools.protocol.models import (
    ToolCall,
    ToolCallError,
    ToolCallOutcome,
    ToolCallStatus,
    ToolDeclaration,
    tool_status_to_call_status,
)
from llm_adapters.tools.protocol.names import allowed_names_from_manifest
from llm_adapters.tools.protocol.privacy import (
    ProtocolPrivacyError,
    assert_provider_envelope_private_free,
    failed_privacy_envelope,
)
from llm_adapters.tools.registry import ToolRegistry


def _sanitize_error_message(raw: str) -> str:
    """Drop exception internals / secret-shaped text from fail-closed reasons."""
    text = " ".join(raw.split())
    lowered = text.lower()
    if any(token in lowered for token in ("api_key", "bearer ", "sk-", "authorization")):
        return "tool call failed"
    if len(text) > 240:
        text = text[:240]
    return text or "tool call failed"


def _audit_record(
    *,
    call_id: str,
    tool_name: str,
    status: ToolCallStatus,
    argument_keys: tuple[str, ...],
) -> dict[str, Any]:
    """Internal audit row — keys only, no argument values, no secrets."""
    return {
        "call_id": call_id,
        "tool_name": tool_name,
        "status": status.value,
        "argument_keys": argument_keys,
    }


def _reject(
    *,
    call_id: str,
    tool_name: str,
    status: ToolCallStatus,
    message: str,
    argument_keys: tuple[str, ...] = (),
) -> ToolCallOutcome:
    return ToolCallOutcome(
        call_id=call_id or "malformed",
        tool_name=tool_name or "unknown",
        status=status,
        result=None,
        error=ToolCallError(kind=status, message=_sanitize_error_message(message)),
        audit=_audit_record(
            call_id=call_id or "malformed",
            tool_name=tool_name or "unknown",
            status=status,
            argument_keys=argument_keys,
        ),
    )


class ToolCallBoundary:
    """Authorize and execute provider-neutral tool calls.

    The AI may only invoke names published by ``public_manifest()``.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        backend: DSPToolBackend,
    ) -> None:
        self._registry = registry
        self._backend = backend
        manifest = registry.public_manifest()
        self._manifest = tuple(dict(entry) for entry in manifest)
        self._allowed = allowed_names_from_manifest(self._manifest)
        self._registered = frozenset(registry.names())

    def declarations(self) -> tuple[ToolDeclaration, ...]:
        return tuple(ToolDeclaration.from_manifest_entry(entry) for entry in self._manifest)

    def allowed_names(self) -> frozenset[str]:
        return self._allowed

    def public_manifest(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in self._manifest]

    def execute(self, call: ToolCall) -> ToolCallOutcome:
        if not isinstance(call, ToolCall):
            return _reject(
                call_id="malformed",
                tool_name="unknown",
                status=ToolCallStatus.MALFORMED,
                message="tool call is not a ToolCall",
            )
        call_id = call.call_id if isinstance(call.call_id, str) and call.call_id else ""
        name = call.name if isinstance(call.name, str) else ""
        arguments = call.arguments
        if not call_id:
            return _reject(
                call_id="malformed",
                tool_name=name or "unknown",
                status=ToolCallStatus.MALFORMED,
                message="tool call missing call_id",
            )
        if not name:
            return _reject(
                call_id=call_id,
                tool_name="unknown",
                status=ToolCallStatus.MALFORMED,
                message="tool call missing name",
            )
        if not isinstance(arguments, Mapping):
            return _reject(
                call_id=call_id,
                tool_name=name,
                status=ToolCallStatus.MALFORMED,
                message="tool call arguments must be an object",
            )
        argument_keys = tuple(str(k) for k in arguments.keys())
        if name not in self._allowed:
            if name in self._registered:
                return _reject(
                    call_id=call_id,
                    tool_name=name,
                    status=ToolCallStatus.UNAUTHORIZED,
                    message="tool is not in the public manifest",
                    argument_keys=argument_keys,
                )
            return _reject(
                call_id=call_id,
                tool_name=name,
                status=ToolCallStatus.UNKNOWN_TOOL,
                message="unknown or unapproved tool",
                argument_keys=argument_keys,
            )
        try:
            result = self._registry.dispatch(name, dict(arguments), self._backend)
        except Exception as exc:  # noqa: BLE001 — fail-closed
            return _reject(
                call_id=call_id,
                tool_name=name,
                status=ToolCallStatus.TOOL_FAILED,
                message=f"{exc.__class__.__name__}",
                argument_keys=argument_keys,
            )
        return self._from_result(call_id, name, argument_keys, result)

    def execute_many(
        self, calls: Sequence[ToolCall | ToolCallOutcome]
    ) -> tuple[ToolCallOutcome, ...]:
        outcomes: list[ToolCallOutcome] = []
        for item in calls:
            if isinstance(item, ToolCallOutcome):
                outcomes.append(item)
            elif isinstance(item, ToolCall):
                outcomes.append(self.execute(item))
            else:
                outcomes.append(
                    _reject(
                        call_id="malformed",
                        tool_name="unknown",
                        status=ToolCallStatus.MALFORMED,
                        message="unrecognized tool-call item",
                    )
                )
        return tuple(outcomes)

    def _from_result(
        self,
        call_id: str,
        name: str,
        argument_keys: tuple[str, ...],
        result: ToolResult,
    ) -> ToolCallOutcome:
        try:
            assert_no_tool_leakage(result.result)
            assert_no_tool_leakage(result.calculation_metadata)
        except ValueError:
            return _reject(
                call_id=call_id,
                tool_name=name,
                status=ToolCallStatus.TOOL_FAILED,
                message="tool result failed privacy validation",
                argument_keys=argument_keys,
            )
        status = tool_status_to_call_status(result.status)
        error = None
        if status is not ToolCallStatus.OK:
            reason = ""
            if isinstance(result.result, Mapping):
                raw_reason = result.result.get("reason")
                if isinstance(raw_reason, str):
                    reason = raw_reason
            if not reason and result.limitations:
                reason = result.limitations[0]
            error = ToolCallError(kind=status, message=_sanitize_error_message(reason or "tool call failed"))
        outcome = ToolCallOutcome(
            call_id=call_id,
            tool_name=name,
            status=status,
            result=result,
            error=error,
            audit=_audit_record(
                call_id=call_id,
                tool_name=name,
                status=status,
                argument_keys=argument_keys,
            ),
        )
        try:
            assert_provider_envelope_private_free(outcome.provider_payload())
        except (ProtocolPrivacyError, ValueError):
            return ToolCallOutcome(
                call_id=call_id,
                tool_name=name,
                status=ToolCallStatus.TOOL_FAILED,
                result=None,
                error=ToolCallError(
                    kind=ToolCallStatus.TOOL_FAILED,
                    message="tool result failed privacy validation",
                ),
                audit=_audit_record(
                    call_id=call_id,
                    tool_name=name,
                    status=ToolCallStatus.TOOL_FAILED,
                    argument_keys=argument_keys,
                ),
            )
        return outcome


def safe_provider_payload(outcome: ToolCallOutcome) -> dict[str, Any]:
    """Export a privacy-checked envelope; fail closed on leakage."""
    try:
        payload = outcome.provider_payload()
        assert_provider_envelope_private_free(payload)
        return payload
    except (ProtocolPrivacyError, ValueError):
        return failed_privacy_envelope(outcome.tool_name)


__all__ = [
    "ToolCallBoundary",
    "safe_provider_payload",
]
