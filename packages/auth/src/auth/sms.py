"""SMS provider abstraction for mobile OTP (Twilio / MSG91 / Firebase / Dev / Null)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "SmsDeliveryResult",
    "SmsProviderPort",
    "NullSmsAdapter",
    "DevSmsAdapter",
    "ConsoleSmsAdapter",
    "TwilioSmsAdapter",
    "Msg91SmsAdapter",
    "Fast2SmsAdapter",
    "FirebaseSmsAdapter",
    "build_sms_provider",
]


@dataclass(frozen=True, slots=True)
class SmsDeliveryResult:
    ok: bool
    provider: str
    message_id: str | None = None
    detail: str | None = None
    # Dev adapter may echo code for local testing only — never in production SMS.
    debug_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "provider": self.provider,
            "message_id": self.message_id,
            "detail": self.detail,
        }
        if self.debug_code is not None:
            out["debug_code"] = self.debug_code
        return out


@runtime_checkable
class SmsProviderPort(Protocol):
    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def send_otp(self, mobile: str, code: str, *, purpose: str = "login") -> SmsDeliveryResult: ...


class NullSmsAdapter:
    def provider_name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def send_otp(self, mobile: str, code: str, *, purpose: str = "login") -> SmsDeliveryResult:
        _ = (mobile, code, purpose)
        return SmsDeliveryResult(
            ok=False,
            provider=self.provider_name(),
            detail="SMS provider unavailable. Configure Twilio, MSG91, or Firebase credentials.",
        )


class DevSmsAdapter:
    """Local/dev adapter — does not send SMS; returns code in debug payload only."""

    def __init__(self) -> None:
        self._last: dict[str, str] = {}

    def provider_name(self) -> str:
        return "dev"

    def is_available(self) -> bool:
        return True

    def send_otp(self, mobile: str, code: str, *, purpose: str = "login") -> SmsDeliveryResult:
        self._last[mobile] = code
        return SmsDeliveryResult(
            ok=True,
            provider=self.provider_name(),
            message_id=f"dev-{purpose}-{mobile[-4:]}",
            detail="Dev SMS adapter: message not sent externally.",
            debug_code=code,
        )

    def last_code(self, mobile: str) -> str | None:
        return self._last.get(mobile)


ConsoleSmsAdapter = DevSmsAdapter


class TwilioSmsAdapter:
    def __init__(self, *, account_sid: str, auth_token: str, from_number: str) -> None:
        self._sid = account_sid
        self._token = auth_token
        self._from = from_number

    def provider_name(self) -> str:
        return "twilio"

    def is_available(self) -> bool:
        return bool(self._sid and self._token and self._from)

    def send_otp(self, mobile: str, code: str, *, purpose: str = "login") -> SmsDeliveryResult:
        if not self.is_available():
            return SmsDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail="Twilio credentials incomplete.",
            )
        try:
            import base64
            import json
            import urllib.parse
            import urllib.request

            body = (
                f"Body={urllib.parse.quote(f'DSP AI Indicator OTP: {code} ({purpose})')}&"
                f"From={urllib.parse.quote(self._from)}&"
                f"To={urllib.parse.quote(mobile)}"
            )

            url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
            req = urllib.request.Request(
                url,
                data=body.encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": "Basic "
                    + base64.b64encode(f"{self._sid}:{self._token}".encode()).decode(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
            return SmsDeliveryResult(
                ok=True,
                provider=self.provider_name(),
                message_id=str(payload.get("sid") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            return SmsDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail=f"Twilio send failed: {exc}",
            )


class Msg91SmsAdapter:
    def __init__(self, *, auth_key: str, sender_id: str = "DSPAI", template_id: str = "") -> None:
        self._key = auth_key
        self._sender = sender_id
        self._template = template_id

    def provider_name(self) -> str:
        return "msg91"

    def is_available(self) -> bool:
        return bool(self._key)

    def send_otp(self, mobile: str, code: str, *, purpose: str = "login") -> SmsDeliveryResult:
        if not self.is_available():
            return SmsDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail="MSG91 credentials incomplete.",
            )
        try:
            import json
            import urllib.request

            digits = "".join(ch for ch in mobile if ch.isdigit())
            payload = {
                "template_id": self._template or "otp",
                "sender": self._sender,
                "short_url": "0",
                "recipients": [{"mobiles": digits, "otp": code, "purpose": purpose}],
            }
            req = urllib.request.Request(
                "https://control.msg91.com/api/v5/flow/",
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers={
                    "authkey": self._key,
                    "Content-Type": "application/json",
                    "accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                body = json.loads(resp.read().decode("utf-8"))
            return SmsDeliveryResult(
                ok=True,
                provider=self.provider_name(),
                message_id=str(body.get("request_id") or body.get("type") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            return SmsDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail=f"MSG91 send failed: {exc}",
            )


class Fast2SmsAdapter:
    """Fast2SMS DLT/OTP route — popular India-focused transactional SMS provider."""

    def __init__(self, *, api_key: str, sender_id: str = "FSTSMS", route: str = "otp") -> None:
        self._api_key = api_key
        self._sender_id = sender_id
        self._route = route

    def provider_name(self) -> str:
        return "fast2sms"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def send_otp(self, mobile: str, code: str, *, purpose: str = "login") -> SmsDeliveryResult:
        if not self.is_available():
            return SmsDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail="Fast2SMS credentials incomplete.",
            )
        try:
            import json
            import urllib.parse
            import urllib.request

            digits = "".join(ch for ch in mobile if ch.isdigit())[-10:]
            params = {
                "authorization": self._api_key,
                "route": self._route,
                "variables_values": code,
                "numbers": digits,
            }
            if self._route == "dlt":
                params["sender_id"] = self._sender_id
            url = f"https://www.fast2sms.com/dev/bulkV2?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                method="GET",
                headers={"cache-control": "no-cache"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
            ok = bool(payload.get("return"))
            request_id = str(payload.get("request_id") or "")
            if not ok:
                message = "; ".join(str(m) for m in (payload.get("message") or [])) or "unknown error"
                return SmsDeliveryResult(
                    ok=False,
                    provider=self.provider_name(),
                    detail=f"Fast2SMS send failed: {message}",
                )
            return SmsDeliveryResult(ok=True, provider=self.provider_name(), message_id=request_id)
        except Exception as exc:  # noqa: BLE001
            return SmsDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail=f"Fast2SMS send failed: {exc}",
            )


class FirebaseSmsAdapter:
    """Firebase Identity Toolkit SMS — requires API key; honest when absent."""

    def __init__(self, *, api_key: str) -> None:
        self._api_key = api_key

    def provider_name(self) -> str:
        return "firebase"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def send_otp(self, mobile: str, code: str, *, purpose: str = "login") -> SmsDeliveryResult:
        _ = (mobile, code, purpose)
        if not self.is_available():
            return SmsDeliveryResult(
                ok=False,
                provider=self.provider_name(),
                detail="Firebase API key incomplete.",
            )
        # Firebase client SDK typically owns SMS OTP; server path needs App Check + reCAPTCHA.
        return SmsDeliveryResult(
            ok=False,
            provider=self.provider_name(),
            detail=(
                "Firebase SMS OTP requires client SDK / Identity Toolkit session. "
                "Use Twilio, MSG91, or Dev adapter for server-side OTP delivery."
            ),
        )


def build_sms_provider(name: str | None = None) -> SmsProviderPort:
    """Env-driven SMS factory. Defaults to Dev in non-production, Null in production."""
    preferred = (name or os.environ.get("DSP_SMS_PROVIDER") or "").strip().lower()
    env = (os.environ.get("DSP_ENVIRONMENT") or "development").strip().lower()

    twilio = TwilioSmsAdapter(
        account_sid=os.environ.get("DSP_TWILIO_ACCOUNT_SID", ""),
        auth_token=os.environ.get("DSP_TWILIO_AUTH_TOKEN", ""),
        from_number=os.environ.get("DSP_TWILIO_FROM_NUMBER", ""),
    )
    msg91 = Msg91SmsAdapter(
        auth_key=os.environ.get("DSP_MSG91_AUTH_KEY", ""),
        sender_id=os.environ.get("DSP_MSG91_SENDER_ID", "DSPAI"),
        template_id=os.environ.get("DSP_MSG91_TEMPLATE_ID", ""),
    )
    fast2sms = Fast2SmsAdapter(
        api_key=os.environ.get("DSP_FAST2SMS_API_KEY", ""),
        sender_id=os.environ.get("DSP_FAST2SMS_SENDER_ID", "FSTSMS"),
        route=os.environ.get("DSP_FAST2SMS_ROUTE", "otp"),
    )
    firebase = FirebaseSmsAdapter(api_key=os.environ.get("DSP_FIREBASE_API_KEY", ""))

    if preferred == "twilio":
        return twilio if twilio.is_available() else NullSmsAdapter()
    if preferred == "msg91":
        return msg91 if msg91.is_available() else NullSmsAdapter()
    if preferred == "fast2sms":
        return fast2sms if fast2sms.is_available() else NullSmsAdapter()
    if preferred == "firebase":
        return firebase if firebase.is_available() else NullSmsAdapter()
    if preferred == "null":
        return NullSmsAdapter()
    if preferred in {"dev", "console"}:
        return DevSmsAdapter()

    if twilio.is_available():
        return twilio
    if msg91.is_available():
        return msg91
    if fast2sms.is_available():
        return fast2sms
    if env in {"production", "prod", "staging"}:
        return NullSmsAdapter()
    return DevSmsAdapter()
