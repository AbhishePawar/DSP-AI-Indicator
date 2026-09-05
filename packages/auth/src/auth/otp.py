"""Login OTP service — mobile SMS only, 6-digit, hashed, single-use.

Email numeric OTP has been removed; email sign-in is Google OAuth (and
password for provisioned accounts). Transactional email (reset, invite,
magic link) stays on :mod:`auth.email_delivery`.

Security policy:
- 6-digit cryptographically secure codes
- Store only salted SHA-256 hashes (never plaintext)
- 5-minute expiry, 30s resend cooldown, 5 attempts, hourly send caps
- IP-scoped verify-failure rate limiting when ``ip_hint`` is supplied
- Public responses never include the OTP
- Authoritative challenge/attempt/send-window state is A008-backed so Cloud
  Run instances share one store (Postgres in production)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

from auth.enterprise_models import OtpChallenge
from auth.exceptions import AuthenticationError, ValidationError
from auth.otp_challenges import OtpChallengeStore, default_otp_store
from auth.sms import SmsProviderPort, build_sms_provider

logger = logging.getLogger(__name__)

__all__ = [
    "OtpService",
    "OtpVerifyResult",
    "classify_otp_identifier",
    "normalize_india_mobile",
    "try_normalize_india_mobile",
]

_INDIA_MOBILE_RE = re.compile(r"^(?:\+91|91|0)?([6-9]\d{9})$")
_OTP_TTL = timedelta(minutes=5)
_RESEND_COOLDOWN = timedelta(seconds=30)
_MAX_ATTEMPTS = 5
_MAX_SENDS_PER_HOUR = 5
_MAX_VERIFY_FAILURES_IP = 20

_EMAIL_OTP_DISABLED = (
    "Email OTP is no longer supported. Sign in with Google or password, "
    "or use mobile OTP."
)


class OtpVerifyResult(NamedTuple):
    channel: str
    destination: str


def normalize_india_mobile(mobile: str) -> str:
    raw = (mobile or "").strip().replace(" ", "").replace("-", "")
    match = _INDIA_MOBILE_RE.match(raw)
    if not match:
        raise ValidationError(
            "Invalid India mobile number. Use +91 followed by a 10-digit number starting 6–9."
        )
    return f"+91{match.group(1)}"


def try_normalize_india_mobile(mobile: str) -> str | None:
    try:
        return normalize_india_mobile(mobile)
    except ValidationError:
        return None


def classify_otp_identifier(identifier: str) -> tuple[str, str]:
    """Return ``(channel, normalized_destination)`` for India mobile only.

    Email identifiers are rejected — numeric email OTP is disabled.
    """
    raw = (identifier or "").strip()
    if not raw:
        raise ValidationError("identifier is required")
    if "@" in raw:
        raise ValidationError(_EMAIL_OTP_DISABLED)
    return "mobile", normalize_india_mobile(raw)


def _hash_code(code: str, *, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def _verify_code(code: str, code_hash: str) -> bool:
    try:
        scheme, salt, digest = code_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "sha256":
        return False
    candidate = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(candidate, digest)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class OtpService:
    def __init__(
        self,
        sms: SmsProviderPort | None = None,
        email: Any = None,
        *,
        store: OtpChallengeStore | None = None,
    ) -> None:
        # ``email`` is accepted for call-site compatibility but ignored —
        # numeric email OTP has been removed.
        _ = email
        self._sms = sms or build_sms_provider()
        self._store = store if store is not None else default_otp_store()

    def sms_status(self) -> dict[str, Any]:
        return {
            "provider": self._sms.provider_name(),
            "available": self._sms.is_available(),
        }

    def request_otp(
        self,
        mobile: str,
        *,
        ip_hint: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        ts = now or datetime.now(tz=timezone.utc)
        normalized = normalize_india_mobile(mobile)
        challenge, code = self._create_challenge(
            channel="mobile",
            destination=normalized,
            ip_hint=ip_hint,
            ts=ts,
            deliver=True,
        )
        delivery = self._sms.send_otp(normalized, code, purpose="login")
        if not delivery.ok and self._sms.provider_name() != "dev":
            if not self._sms.is_available():
                raise AuthenticationError(
                    delivery.detail
                    or "SMS provider unavailable. OTP cannot be delivered."
                )

        public = challenge.to_public_dict()
        public["sms"] = delivery.to_dict()
        # Strip debug_code from public API unless Dev SMS adapter.
        if delivery.provider != "dev":
            public["sms"].pop("debug_code", None)
        return public

    def issue_undelivered_challenge(
        self,
        *,
        opaque_key: str,
        ip_hint: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Return a login-shaped OTP challenge without sending SMS.

        Used when the identifier does not resolve to a verified mobile so the
        public response cannot be used to enumerate accounts.
        """
        ts = now or datetime.now(tz=timezone.utc)
        digest = hashlib.sha256(f"otp-opaque:{opaque_key.strip().lower()}".encode("utf-8")).hexdigest()
        destination = f"opaque-{digest[:24]}"
        challenge, _code = self._create_challenge(
            channel="mobile",
            destination=destination,
            ip_hint=ip_hint,
            ts=ts,
            deliver=False,
        )
        public = challenge.to_public_dict()
        public.pop("mobile", None)
        public.pop("destination", None)
        public["sms"] = {
            "provider": self._sms.provider_name(),
            "ok": True,
        }
        return public

    def verify_otp(
        self,
        *,
        challenge_id: str,
        code: str,
        ip_hint: str | None = None,
        now: datetime | None = None,
    ) -> str:
        """Verify OTP; return destination (normalized mobile)."""
        return self.verify_otp_result(
            challenge_id=challenge_id, code=code, ip_hint=ip_hint, now=now
        ).destination

    def verify_otp_result(
        self,
        *,
        challenge_id: str,
        code: str,
        ip_hint: str | None = None,
        now: datetime | None = None,
    ) -> OtpVerifyResult:
        """Verify OTP; return channel + destination on success."""
        ts = now or datetime.now(tz=timezone.utc)
        now_iso = ts.isoformat()
        record = self._store.get_challenge(challenge_id, now=ts)
        if record is None:
            raise AuthenticationError("Invalid or expired OTP challenge.")
        challenge = record.challenge
        if challenge.channel != "mobile":
            raise AuthenticationError(
                "Email OTP is no longer supported. Sign in with Google or password."
            )
        if challenge.consumed:
            raise AuthenticationError("OTP already used.")
        expires = _parse_dt(challenge.expires_at)
        if expires is None or ts > expires:
            raise AuthenticationError("OTP expired.")
        if challenge.attempts >= _MAX_ATTEMPTS:
            self._record_ip_failure(ip_hint, ts)
            raise AuthenticationError("Too many invalid OTP attempts.")
        if not _verify_code((code or "").strip(), challenge.code_hash):
            updated = self._store.increment_attempts(
                challenge_id, now_iso=now_iso, max_attempts=_MAX_ATTEMPTS
            )
            self._record_ip_failure(ip_hint, ts)
            if updated is None:
                again = self._store.get_challenge(challenge_id, now=ts)
                if again is not None and again.challenge.consumed:
                    raise AuthenticationError("OTP already used.")
                if again is not None and again.challenge.attempts >= _MAX_ATTEMPTS:
                    raise AuthenticationError("Too many invalid OTP attempts.")
            raise AuthenticationError("Invalid OTP code.")
        consumed = self._store.consume_success(
            challenge_id, now_iso=now_iso, max_attempts=_MAX_ATTEMPTS
        )
        if consumed is None:
            again = self._store.get_challenge(challenge_id, now=ts)
            if again is not None and again.challenge.consumed:
                raise AuthenticationError("OTP already used.")
            if again is not None and again.challenge.attempts >= _MAX_ATTEMPTS:
                raise AuthenticationError("Too many invalid OTP attempts.")
            raise AuthenticationError("Invalid or expired OTP challenge.")
        return OtpVerifyResult(
            channel=consumed.challenge.channel,
            destination=consumed.challenge.resolved_destination(),
        )

    def _create_challenge(
        self,
        *,
        channel: str,
        destination: str,
        ip_hint: str | None,
        ts: datetime,
        deliver: bool,
    ) -> tuple[OtpChallenge, str]:
        hour_ago = ts - timedelta(hours=1)
        if ip_hint:
            failures = [
                t
                for t in (_parse_dt(raw) for raw in self._store.get_ip_failures(ip_hint))
                if t is not None and t >= hour_ago
            ]
            if len(failures) >= _MAX_VERIFY_FAILURES_IP:
                raise AuthenticationError("Too many failed attempts. Try again later.")

        dest_row = self._store.get_destination(destination)
        send_times: list[datetime] = []
        if dest_row:
            send_times = [
                t
                for t in (_parse_dt(raw) for raw in (dest_row.get("send_times") or []))
                if t is not None and t >= hour_ago
            ]
            if len(send_times) >= _MAX_SENDS_PER_HOUR:
                raise AuthenticationError("OTP rate limit exceeded. Try again later.")
            existing_id = str(dest_row.get("challenge_id") or "")
            if existing_id:
                existing = self._store.get_challenge(existing_id, now=ts)
                if existing and existing.challenge.resend_available_at:
                    resend_at = _parse_dt(existing.challenge.resend_available_at)
                    if (
                        resend_at is not None
                        and ts < resend_at
                        and not existing.challenge.consumed
                    ):
                        raise AuthenticationError(
                            f"Resend available after {existing.challenge.resend_available_at}."
                        )

        if deliver:
            code = f"{secrets.randbelow(1_000_000):06d}"
        else:
            # Unguessable stand-in so response shape matches without a usable OTP.
            code = secrets.token_hex(16)
        salt = secrets.token_hex(8)
        challenge_id = str(uuid.uuid4())
        expires = ts + _OTP_TTL
        resend_at = ts + _RESEND_COOLDOWN
        challenge = OtpChallenge(
            challenge_id=challenge_id,
            mobile=destination if channel == "mobile" else "",
            code_hash=_hash_code(code, salt=salt),
            expires_at=expires.isoformat(),
            created_at=ts.isoformat(),
            attempts=0,
            consumed=False,
            resend_available_at=resend_at.isoformat(),
            channel=channel,
            destination=destination,
        )
        self._store.put_challenge(challenge)
        send_iso = [t.isoformat() for t in send_times] + [ts.isoformat()]
        self._store.put_destination(
            destination,
            challenge_id=challenge_id,
            send_times=send_iso,
            resend_available_at=challenge.resend_available_at,
            created_at=challenge.created_at,
        )
        return challenge, code if deliver else ""

    def _record_ip_failure(self, ip_hint: str | None, ts: datetime) -> None:
        if not ip_hint:
            return
        cutoff = ts - timedelta(hours=2)
        previous = [
            raw
            for raw in self._store.get_ip_failures(ip_hint)
            if (parsed := _parse_dt(raw)) is not None and parsed >= cutoff
        ]
        previous.append(ts.isoformat())
        self._store.put_ip_failures(
            ip_hint, failures=previous, created_at=ts.isoformat()
        )
