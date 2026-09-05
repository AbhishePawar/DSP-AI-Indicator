"""TOTP (RFC 6238) / HOTP (RFC 4226) MFA adapter — stdlib crypto, optional QR image.

Design notes
------------
- Secrets and codes are computed with stdlib ``hmac``/``hashlib`` only (same
  philosophy as :mod:`auth.jwt` and :mod:`auth.hashing`): no mandatory
  third-party TOTP dependency.
- QR code *image* rendering is optional (``qrcode`` package). When absent the
  ``otpauth://`` URI is still returned so any authenticator app can be
  provisioned by manual entry or by a client-side QR renderer.
- Recovery codes are salted + hashed (never stored in plaintext) exactly like
  :mod:`auth.otp` hashes SMS codes.
- Enrollment is two-phase: ``begin_enroll`` issues a *pending* secret that
  only becomes active once ``confirm_enroll`` validates a live code. This
  prevents a user from being locked into a secret they never actually
  provisioned in their authenticator app.
- Verified codes are tracked per-user (last accepted TOTP step) to reject
  immediate replay of an already-used code within the same time window.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse
from typing import Any

from auth.exceptions import AuthenticationError, ValidationError
from auth.mfa_pending import MfaPendingStore
from auth.secret_box import decrypt_secret, encrypt_secret, is_encrypted

__all__ = [
    "TotpAdapter",
    "build_otpauth_uri",
    "generate_recovery_codes",
    "generate_totp_secret",
    "qr_code_data_uri",
    "totp_at",
    "verify_totp",
]

_STEP_SECONDS = 30
_DIGITS = 6
_DRIFT_WINDOW = 1  # accept one step before/after for clock drift
_PENDING_TTL_SECONDS = 600  # 10 minutes to confirm enrollment
_RECOVERY_CODE_COUNT = 10
_ENTITY_PREFIX = "auth-mfa-totp-"


def generate_totp_secret(length: int = 20) -> str:
    """Return a base32 (RFC 4648) secret suitable for authenticator apps."""
    return base64.b32encode(secrets.token_bytes(length)).decode("ascii").rstrip("=")


def _b32_pad(value: str) -> str:
    return value + "=" * (-len(value) % 8)


def _hotp(secret_b32: str, counter: int, *, digits: int = _DIGITS) -> str:
    key = base64.b32decode(_b32_pad(secret_b32.strip().upper()), casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = (int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF) % (
        10**digits
    )
    return str(truncated).zfill(digits)


def totp_at(secret_b32: str, *, for_time: float | None = None, step: int = _STEP_SECONDS) -> str:
    """Return the current TOTP code for ``secret_b32`` (test/debug helper)."""
    t = for_time if for_time is not None else time.time()
    return _hotp(secret_b32, int(t // step))


def verify_totp(
    secret_b32: str,
    code: str,
    *,
    for_time: float | None = None,
    step: int = _STEP_SECONDS,
    window: int = _DRIFT_WINDOW,
) -> tuple[bool, int]:
    """Validate ``code`` against ``secret_b32``.

    Returns ``(matched, step_counter)``. ``step_counter`` is ``-1`` when the
    code did not match any step in the drift window; callers should persist
    the matched counter to reject replay of the same one-time code.
    """
    cleaned = (code or "").strip().replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) != _DIGITS:
        return False, -1
    t = for_time if for_time is not None else time.time()
    counter = int(t // step)
    for offset in range(-window, window + 1):
        candidate = _hotp(secret_b32, counter + offset, digits=_DIGITS)
        if hmac.compare_digest(candidate, cleaned):
            return True, counter + offset
    return False, -1


def build_otpauth_uri(secret_b32: str, *, issuer: str, account_name: str) -> str:
    label = urllib.parse.quote(f"{issuer}:{account_name}")
    query = urllib.parse.urlencode(
        {
            "secret": secret_b32,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": _DIGITS,
            "period": _STEP_SECONDS,
        }
    )
    return f"otpauth://totp/{label}?{query}"


def qr_code_data_uri(otpauth_uri: str) -> str | None:
    """Best-effort PNG QR data URI. ``None`` when the optional ``qrcode`` lib is absent."""
    try:
        import io

        import qrcode
    except ImportError:
        return None
    try:
        img = qrcode.make(otpauth_uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:  # noqa: BLE001 — QR rendering must never break enrollment
        return None


def generate_recovery_codes(n: int = _RECOVERY_CODE_COUNT) -> list[str]:
    codes = []
    for _ in range(n):
        raw = secrets.token_hex(5)  # 10 hex chars
        codes.append(f"{raw[:5]}-{raw[5:]}".upper())
    return codes


def _hash_secret_token(token: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.sha256(f"{salt}:{token.strip().lower()}".encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def _verify_secret_token(token: str, token_hash: str) -> bool:
    try:
        scheme, salt, digest = token_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "sha256":
        return False
    candidate = hashlib.sha256(f"{salt}:{token.strip().lower()}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(candidate, digest)


class TotpAdapter:
    """Production TOTP MFA method — persists via the shared metadata store.

    Implements :class:`auth.mfa.MfaMethodPort`. Storage uses the same
    generic ``persistence.put(kind="metadata", ...)`` pattern used
    throughout :mod:`auth.enterprise_platform` — no new persistence adapter
    is introduced.
    """

    def __init__(self, persistence: Any, *, issuer: str = "DSP AI Indicator") -> None:
        self._persistence = persistence
        self._issuer = issuer
        self._pending_store = MfaPendingStore(persistence)

    # -- MfaMethodPort ------------------------------------------------

    def method_name(self) -> str:
        return "totp"

    def is_available(self) -> bool:
        return True

    def is_enrolled(self, user_id: str) -> bool:
        record = self._load(user_id)
        return bool(record and record.get("enabled"))

    def begin_enroll(self, user_id: str, *, account_name: str | None = None) -> dict[str, Any]:
        secret = generate_totp_secret()
        self._pending_store.put_totp_pending(
            user_id, secret=secret, ttl_seconds=_PENDING_TTL_SECONDS
        )
        uri = build_otpauth_uri(secret, issuer=self._issuer, account_name=account_name or user_id)
        return {
            "method": "totp",
            "secret": secret,
            "otpauth_uri": uri,
            "qr_code": qr_code_data_uri(uri),
            "issuer": self._issuer,
            "digits": _DIGITS,
            "period": _STEP_SECONDS,
            "expires_in": _PENDING_TTL_SECONDS,
        }

    def confirm_enroll(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        code = str(payload.get("code") or "").strip()
        pending = self._pending_store.get_totp_pending(user_id)
        if pending is None:
            raise ValidationError("No pending TOTP enrollment. Start enrollment again.")
        matched, counter = verify_totp(pending.secret, code)
        if not matched:
            raise AuthenticationError("Invalid authenticator code.")
        consumed = self._pending_store.consume_totp_pending(user_id)
        if consumed is None:
            raise ValidationError("No pending TOTP enrollment. Start enrollment again.")
        recovery_codes = generate_recovery_codes()
        encrypted_secret = encrypt_secret(consumed.secret)
        record = {
            "auth_entity": "mfa_totp",
            "user_id": user_id,
            "secret": encrypted_secret,
            "secret_encrypted": is_encrypted(encrypted_secret),
            "enabled": True,
            "confirmed_at": time.time(),
            "last_used_counter": counter,
            "recovery_codes": [
                {"hash": _hash_secret_token(c), "used": False} for c in recovery_codes
            ],
            "recovery_codes_generated_at": time.time(),
        }
        self._save(user_id, record)
        return {"ok": True, "method": "totp", "recovery_codes": recovery_codes}

    def begin_challenge(self, user_id: str) -> dict[str, Any]:
        _ = user_id
        return {
            "method": "totp",
            "message": "Enter the 6-digit code from your authenticator app.",
        }

    def verify_challenge(self, user_id: str, payload: dict[str, Any]) -> bool:
        record = self._load(user_id)
        if record is None or not record.get("enabled"):
            return False
        recovery_code = str(payload.get("recovery_code") or "").strip()
        if recovery_code:
            return self._consume_recovery_code(user_id, record, recovery_code)
        code = str(payload.get("code") or "").strip()
        secret = decrypt_secret(str(record.get("secret") or ""))
        matched, counter = verify_totp(secret, code)
        if not matched:
            return False
        if counter == int(record.get("last_used_counter") or -1):
            return False  # replay of an already-consumed step
        record["last_used_counter"] = counter
        self._save(user_id, record)
        return True

    # -- Admin / self-service extensions (beyond the Protocol) --------

    def disable(self, user_id: str) -> None:
        self._persistence.delete("metadata", f"{_ENTITY_PREFIX}{user_id}")
        self._pending_store.delete_totp_pending(user_id)

    def recovery_codes_remaining(self, user_id: str) -> int:
        record = self._load(user_id)
        if not record:
            return 0
        return sum(1 for c in record.get("recovery_codes") or [] if not c.get("used"))

    def recovery_codes_status(self, user_id: str) -> dict[str, Any]:
        """Return recovery-code counts/metadata — never the codes themselves.

        Recovery codes are salted+hashed at rest (see :func:`_hash_secret_token`)
        so, by design, the plaintext values can only ever be surfaced once, at
        the moment they are generated (:meth:`confirm_enroll` /
        :meth:`regenerate_recovery_codes`).
        """
        record = self._load(user_id)
        if record is None or not record.get("enabled"):
            raise ValidationError("TOTP MFA is not enabled for this account.")
        codes = record.get("recovery_codes") or []
        return {
            "total": len(codes),
            "remaining": sum(1 for c in codes if not c.get("used")),
            "generated_at": record.get("recovery_codes_generated_at"),
        }

    def regenerate_recovery_codes(self, user_id: str) -> list[str]:
        """Invalidate all existing recovery codes and issue a fresh set."""
        record = self._load(user_id)
        if record is None or not record.get("enabled"):
            raise ValidationError("TOTP MFA is not enabled for this account.")
        codes = generate_recovery_codes()
        record["recovery_codes"] = [
            {"hash": _hash_secret_token(c), "used": False} for c in codes
        ]
        record["recovery_codes_generated_at"] = time.time()
        self._save(user_id, record)
        return codes

    # -- internal -------------------------------------------------------

    def _consume_recovery_code(
        self, user_id: str, record: dict[str, Any], recovery_code: str
    ) -> bool:
        codes = list(record.get("recovery_codes") or [])
        for entry in codes:
            if entry.get("used"):
                continue
            if _verify_secret_token(recovery_code, str(entry.get("hash") or "")):
                entry["used"] = True
                record["recovery_codes"] = codes
                self._save(user_id, record)
                return True
        return False

    def _load(self, user_id: str) -> dict[str, Any] | None:
        row = self._persistence.get("metadata", f"{_ENTITY_PREFIX}{user_id}")
        if row is None:
            return None
        return dict(row.get("payload") or {})

    def _save(self, user_id: str, record: dict[str, Any]) -> None:
        self._persistence.put(
            kind="metadata",
            entity_id=f"{_ENTITY_PREFIX}{user_id}",
            payload=record,
            refs={"auth_entity": "mfa_totp", "user_id": user_id},
            created_at=None,
            allow_update=True,
        )
