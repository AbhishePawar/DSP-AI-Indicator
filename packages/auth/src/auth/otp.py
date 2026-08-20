"""Login OTP service — mobile SMS and email, 6-digit, hashed, single-use.

Security policy (shared across channels):
- 6-digit cryptographically secure codes
- Store only salted SHA-256 hashes (never plaintext)
- 5-minute expiry, 30s resend cooldown, 5 attempts, hourly send caps
- IP-scoped verify-failure rate limiting when ``ip_hint`` is supplied
- Public responses never include the OTP
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, NamedTuple

from auth.email_delivery import EmailProviderPort, build_email_provider
from auth.email_templates import render_email_otp_email
from auth.enterprise_models import OtpChallenge
from auth.exceptions import AuthenticationError, ValidationError
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
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_OTP_TTL = timedelta(minutes=5)
_RESEND_COOLDOWN = timedelta(seconds=30)
_MAX_ATTEMPTS = 5
_MAX_SENDS_PER_HOUR = 5
_MAX_VERIFY_FAILURES_IP = 20


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
    """Return ``(channel, normalized_destination)`` for email or India mobile."""
    raw = (identifier or "").strip()
    if not raw:
        raise ValidationError("identifier is required")
    if "@" in raw:
        mail = raw.lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("Invalid email address.")
        return "email", mail
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


class OtpService:
    def __init__(
        self,
        sms: SmsProviderPort | None = None,
        email: EmailProviderPort | None = None,
    ) -> None:
        self._sms = sms or build_sms_provider()
        self._email = email or build_email_provider()
        self._challenges: dict[str, OtpChallenge] = {}
        self._by_destination: dict[str, str] = {}
        self._send_log: list[tuple[str, datetime]] = []
        self._ip_failures: list[tuple[str, datetime]] = []
        self._lock = Lock()

    def sms_status(self) -> dict[str, Any]:
        return {
            "provider": self._sms.provider_name(),
            "available": self._sms.is_available(),
        }

    def email_status(self) -> dict[str, Any]:
        return {
            "provider": self._email.provider_name(),
            "available": self._email.is_available(),
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

    @staticmethod
    def _opaque_email_otp_public() -> dict[str, Any]:
        """Fixed public envelope — identical for known, unknown, and delivery failure."""
        return {
            "ok": True,
            "detail": "If an account exists, a one-time code was sent.",
        }

    def request_email_otp(
        self,
        email: str,
        *,
        ip_hint: str | None = None,
        now: datetime | None = None,
        deliver: bool = True,
    ) -> dict[str, Any]:
        """Create an email OTP challenge.

        When ``deliver`` is False (unknown / unverified address), a real
        challenge row is still created with an unguessable hash so timing and
        response shape stay uniform without sending mail or revealing existence.

        Public responses never encode delivery success, provider availability,
        or whether the address is registered (anti-enumeration).
        """
        ts = now or datetime.now(tz=timezone.utc)
        mail = (email or "").strip().lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("Invalid email address.")
        challenge, code = self._create_challenge(
            channel="email",
            destination=mail,
            ip_hint=ip_hint,
            ts=ts,
            deliver=deliver,
        )
        public = challenge.to_public_dict()
        public["email"] = self._opaque_email_otp_public()

        if not deliver:
            return public

        subject, text_body, html_body = render_email_otp_email(
            code=code, expires_minutes=int(_OTP_TTL.total_seconds() // 60)
        )
        try:
            delivery = self._email.send(
                to=mail,
                subject=subject,
                body=text_body,
                html_body=html_body,
                purpose="login_otp",
            )
        except Exception:  # noqa: BLE001 — never leak delivery faults on the public path
            # Do not log OTP, body, or recipient — purpose only.
            logger.warning("Email OTP delivery failed for purpose=login_otp")
            return public

        if not delivery.ok:
            # Generic operational signal only — no OTP, body, recipient, or API change.
            logger.warning(
                "Email OTP delivery unsuccessful for purpose=login_otp provider=%s",
                delivery.provider,
            )
        return public

    def verify_otp(
        self,
        *,
        challenge_id: str,
        code: str,
        ip_hint: str | None = None,
        now: datetime | None = None,
    ) -> str:
        """Verify OTP; return destination (normalized mobile or email)."""
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
        with self._lock:
            self._prune(ts)
            challenge = self._challenges.get(challenge_id)
            if challenge is None:
                raise AuthenticationError("Invalid or expired OTP challenge.")
            if challenge.consumed:
                raise AuthenticationError("OTP already used.")
            expires = datetime.fromisoformat(challenge.expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if ts > expires:
                raise AuthenticationError("OTP expired.")
            if challenge.attempts >= _MAX_ATTEMPTS:
                if ip_hint:
                    self._ip_failures.append((ip_hint, ts))
                raise AuthenticationError("Too many invalid OTP attempts.")
            if not _verify_code((code or "").strip(), challenge.code_hash):
                updated = replace(challenge, attempts=challenge.attempts + 1)
                self._challenges[challenge_id] = updated
                if ip_hint:
                    self._ip_failures.append((ip_hint, ts))
                raise AuthenticationError("Invalid OTP code.")
            self._challenges[challenge_id] = replace(
                challenge, consumed=True, attempts=challenge.attempts + 1
            )
            return OtpVerifyResult(
                channel=challenge.channel,
                destination=challenge.resolved_destination(),
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
        with self._lock:
            self._prune(ts)
            hour_ago = ts - timedelta(hours=1)
            sends = sum(1 for d, t in self._send_log if d == destination and t >= hour_ago)
            if sends >= _MAX_SENDS_PER_HOUR:
                raise AuthenticationError("OTP rate limit exceeded. Try again later.")
            if ip_hint:
                ip_fails = sum(1 for ip, t in self._ip_failures if ip == ip_hint and t >= hour_ago)
                if ip_fails >= _MAX_VERIFY_FAILURES_IP:
                    raise AuthenticationError("Too many failed attempts. Try again later.")

            existing_id = self._by_destination.get(destination)
            if existing_id:
                existing = self._challenges.get(existing_id)
                if existing and existing.resend_available_at:
                    resend_at = datetime.fromisoformat(existing.resend_available_at)
                    if resend_at.tzinfo is None:
                        resend_at = resend_at.replace(tzinfo=timezone.utc)
                    if ts < resend_at and not existing.consumed:
                        raise AuthenticationError(
                            f"Resend available after {existing.resend_available_at}."
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
            self._challenges[challenge_id] = challenge
            self._by_destination[destination] = challenge_id
            self._send_log.append((destination, ts))
            return challenge, code if deliver else ""

    def _prune(self, now: datetime) -> None:
        # Keep consumed challenges until well after expiry so reuse attempts
        # surface "OTP already used" instead of looking like a missing challenge.
        stale_ids = []
        for cid, ch in self._challenges.items():
            expires = datetime.fromisoformat(ch.expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if now > expires + timedelta(hours=1):
                stale_ids.append(cid)
        for cid in stale_ids:
            ch = self._challenges.pop(cid, None)
            if ch is None:
                continue
            dest = ch.resolved_destination()
            if self._by_destination.get(dest) == cid:
                self._by_destination.pop(dest, None)
        cutoff = now - timedelta(hours=2)
        self._send_log = [(d, t) for d, t in self._send_log if t >= cutoff]
        self._ip_failures = [(ip, t) for ip, t in self._ip_failures if t >= cutoff]
