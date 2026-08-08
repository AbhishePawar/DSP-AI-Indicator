"""Mobile OTP service — India numbers, 6-digit, 5min expiry, resend 30s, rate limits."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from auth.enterprise_models import OtpChallenge
from auth.exceptions import AuthenticationError, ValidationError
from auth.sms import SmsProviderPort, build_sms_provider

__all__ = ["OtpService", "normalize_india_mobile"]

_INDIA_MOBILE_RE = re.compile(r"^(?:\+91|91|0)?([6-9]\d{9})$")
_OTP_TTL = timedelta(minutes=5)
_RESEND_COOLDOWN = timedelta(seconds=30)
_MAX_ATTEMPTS = 5
_MAX_SENDS_PER_HOUR = 5
_MAX_VERIFY_FAILURES_IP = 20


def normalize_india_mobile(mobile: str) -> str:
    raw = (mobile or "").strip().replace(" ", "").replace("-", "")
    match = _INDIA_MOBILE_RE.match(raw)
    if not match:
        raise ValidationError(
            "Invalid India mobile number. Use +91 followed by a 10-digit number starting 6–9."
        )
    return f"+91{match.group(1)}"


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
    def __init__(self, sms: SmsProviderPort | None = None) -> None:
        self._sms = sms or build_sms_provider()
        self._challenges: dict[str, OtpChallenge] = {}
        self._by_mobile: dict[str, str] = {}
        self._send_log: list[tuple[str, datetime]] = []
        self._ip_failures: list[tuple[str, datetime]] = []
        self._lock = Lock()

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
        with self._lock:
            self._prune(ts)
            hour_ago = ts - timedelta(hours=1)
            sends = sum(1 for m, t in self._send_log if m == normalized and t >= hour_ago)
            if sends >= _MAX_SENDS_PER_HOUR:
                raise AuthenticationError("OTP rate limit exceeded. Try again later.")
            if ip_hint:
                ip_fails = sum(1 for ip, t in self._ip_failures if ip == ip_hint and t >= hour_ago)
                if ip_fails >= _MAX_VERIFY_FAILURES_IP:
                    raise AuthenticationError("Too many failed attempts. Try again later.")

            existing_id = self._by_mobile.get(normalized)
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

            code = f"{secrets.randbelow(1_000_000):06d}"
            salt = secrets.token_hex(8)
            challenge_id = str(uuid.uuid4())
            expires = ts + _OTP_TTL
            resend_at = ts + _RESEND_COOLDOWN
            challenge = OtpChallenge(
                challenge_id=challenge_id,
                mobile=normalized,
                code_hash=_hash_code(code, salt=salt),
                expires_at=expires.isoformat(),
                created_at=ts.isoformat(),
                attempts=0,
                consumed=False,
                resend_available_at=resend_at.isoformat(),
            )
            self._challenges[challenge_id] = challenge
            self._by_mobile[normalized] = challenge_id
            self._send_log.append((normalized, ts))

        delivery = self._sms.send_otp(normalized, code, purpose="login")
        if not delivery.ok and self._sms.provider_name() != "dev":
            # Keep challenge for Dev; for Null/failed vendors surface honest error.
            if not self._sms.is_available():
                raise AuthenticationError(
                    delivery.detail
                    or "SMS provider unavailable. OTP cannot be delivered."
                )

        public = challenge.to_public_dict()
        public["sms"] = delivery.to_dict()
        # Strip debug_code from public API in production-shaped responses unless Dev.
        if delivery.provider != "dev":
            public["sms"].pop("debug_code", None)
        return public

    def verify_otp(
        self,
        *,
        challenge_id: str,
        code: str,
        ip_hint: str | None = None,
        now: datetime | None = None,
    ) -> str:
        """Verify OTP; return normalized mobile on success."""
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
            self._challenges[challenge_id] = replace(challenge, consumed=True, attempts=challenge.attempts + 1)
            return challenge.mobile

    def _prune(self, now: datetime) -> None:
        stale_ids = []
        for cid, ch in self._challenges.items():
            expires = datetime.fromisoformat(ch.expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if now > expires + timedelta(hours=1) or ch.consumed:
                stale_ids.append(cid)
        for cid in stale_ids:
            ch = self._challenges.pop(cid, None)
            if ch and self._by_mobile.get(ch.mobile) == cid:
                self._by_mobile.pop(ch.mobile, None)
        cutoff = now - timedelta(hours=2)
        self._send_log = [(m, t) for m, t in self._send_log if t >= cutoff]
        self._ip_failures = [(ip, t) for ip, t in self._ip_failures if t >= cutoff]
