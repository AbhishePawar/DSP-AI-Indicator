"""Email delivery port — Console adapter for local; SMTP/SendGrid plug-in later."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "ConsoleEmailAdapter",
    "EmailDeliveryResult",
    "EmailProviderPort",
    "NullEmailAdapter",
    "build_email_provider",
]


@dataclass(frozen=True, slots=True)
class EmailDeliveryResult:
    ok: bool
    provider: str
    detail: str | None = None
    debug_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "provider": self.provider,
            "detail": self.detail,
        }
        if self.debug_token is not None:
            out["debug_token"] = self.debug_token
        return out


@runtime_checkable
class EmailProviderPort(Protocol):
    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        purpose: str = "transactional",
    ) -> EmailDeliveryResult: ...


class NullEmailAdapter:
    def provider_name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        purpose: str = "transactional",
    ) -> EmailDeliveryResult:
        _ = (to, subject, body, purpose)
        return EmailDeliveryResult(
            ok=False,
            provider=self.provider_name(),
            detail="Email provider unavailable.",
        )


class ConsoleEmailAdapter:
    """Dev/console mailer — logs intent; returns debug token when provided in body marker."""

    def __init__(self) -> None:
        self._sent: list[dict[str, str]] = []

    def provider_name(self) -> str:
        return "console"

    def is_available(self) -> bool:
        return True

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        purpose: str = "transactional",
    ) -> EmailDeliveryResult:
        self._sent.append({"to": to, "subject": subject, "purpose": purpose})
        # Optional: TOKEN=... line for local flows
        debug = None
        for line in body.splitlines():
            if line.startswith("TOKEN="):
                debug = line.split("=", 1)[1].strip()
                break
        return EmailDeliveryResult(
            ok=True,
            provider=self.provider_name(),
            detail=f"Console email to {to}: {subject}",
            debug_token=debug,
        )


def build_email_provider(name: str | None = None) -> EmailProviderPort:
    preferred = (name or os.environ.get("DSP_EMAIL_PROVIDER") or "console").strip().lower()
    if preferred == "null":
        return NullEmailAdapter()
    return ConsoleEmailAdapter()
