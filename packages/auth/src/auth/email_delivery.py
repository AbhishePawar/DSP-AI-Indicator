"""Email delivery port — Console adapter for local; production SMTP adapter."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "ConsoleEmailAdapter",
    "EmailDeliveryResult",
    "EmailProviderPort",
    "NullEmailAdapter",
    "SmtpEmailAdapter",
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
        html_body: str | None = None,
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
        html_body: str | None = None,
    ) -> EmailDeliveryResult:
        _ = (to, subject, body, purpose, html_body)
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
        html_body: str | None = None,
    ) -> EmailDeliveryResult:
        _ = html_body
        # Body retained in-memory for local/dev tests only — never logged.
        self._sent.append(
            {"to": to, "subject": subject, "purpose": purpose, "body": body}
        )
        # Optional: TOKEN=... / OTP=... markers for local flows (not for API exposure).
        debug = None
        for line in body.splitlines():
            if line.startswith("TOKEN=") or line.startswith("OTP="):
                debug = line.split("=", 1)[1].strip()
                break
        return EmailDeliveryResult(
            ok=True,
            provider=self.provider_name(),
            detail=f"Console email to {to}: {subject}",
            debug_token=debug,
        )


class SmtpEmailAdapter:
    """Production SMTP adapter — STARTTLS or implicit TLS, plaintext + HTML multipart."""

    def __init__(
        self,
        *,
        host: str,
        port: int = 587,
        username: str = "",
        password: str = "",
        from_address: str = "",
        from_name: str = "DSP AI Indicator",
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: float = 20.0,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_address = from_address or username
        self._from_name = from_name
        self._use_tls = use_tls
        self._use_ssl = use_ssl
        self._timeout = timeout

    def provider_name(self) -> str:
        return "smtp"

    def is_available(self) -> bool:
        return bool(self._host and self._from_address)

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        purpose: str = "transactional",
        html_body: str | None = None,
    ) -> EmailDeliveryResult:
        if not self.is_available():
            return EmailDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail="SMTP host/from-address not configured.",
            )
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self._from_name} <{self._from_address}>"
        message["To"] = to
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")
        try:
            if self._use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self._host, self._port, timeout=self._timeout, context=context
                ) as client:
                    self._authenticate_and_send(client, message)
            else:
                with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
                    if self._use_tls:
                        client.starttls(context=ssl.create_default_context())
                    self._authenticate_and_send(client, message)
            return EmailDeliveryResult(
                ok=True,
                provider=self.provider_name(),
                detail=f"SMTP email queued to {to} ({purpose}).",
            )
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("SMTP send failed for purpose=%s: %s", purpose, exc)
            return EmailDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail=f"SMTP send failed: {exc}",
            )

    def _authenticate_and_send(self, client: smtplib.SMTP, message: EmailMessage) -> None:
        if self._username and self._password:
            client.login(self._username, self._password)
        client.send_message(message)


def build_email_provider(name: str | None = None) -> EmailProviderPort:
    """Env-driven email factory. Defaults to Console in non-production, Null in production."""
    preferred = (name or os.environ.get("DSP_EMAIL_PROVIDER") or "").strip().lower()
    env = (os.environ.get("DSP_ENVIRONMENT") or "development").strip().lower()

    smtp = SmtpEmailAdapter(
        host=os.environ.get("DSP_SMTP_HOST", ""),
        port=int(os.environ.get("DSP_SMTP_PORT", "587") or "587"),
        username=os.environ.get("DSP_SMTP_USERNAME", ""),
        password=os.environ.get("DSP_SMTP_PASSWORD", ""),
        from_address=os.environ.get("DSP_SMTP_FROM_ADDRESS", ""),
        from_name=os.environ.get("DSP_SMTP_FROM_NAME", "DSP AI Indicator"),
        use_tls=(os.environ.get("DSP_SMTP_USE_TLS", "true").strip().lower() not in {"0", "false", "no"}),
        use_ssl=(os.environ.get("DSP_SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes"}),
    )

    if preferred == "smtp":
        return smtp if smtp.is_available() else NullEmailAdapter()
    if preferred == "null":
        return NullEmailAdapter()
    if preferred == "console":
        return ConsoleEmailAdapter()

    if smtp.is_available():
        return smtp
    if env in {"production", "prod", "staging"}:
        return NullEmailAdapter()
    return ConsoleEmailAdapter()
