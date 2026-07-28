"""Password hashing and policy (PEP-001)."""

from __future__ import annotations

import hashlib
import hmac
import importlib
import secrets
from dataclasses import dataclass

from security_platform.security.exceptions import SecurityError

__all__ = [
    "PasswordPolicy",
    "ScryptPasswordHasher",
    "Argon2PasswordHasher",
    "build_password_hasher",
]


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Password strength rules."""

    min_length: int = 12
    require_upper: bool = True
    require_lower: bool = True
    require_digit: bool = True

    def validate(self, password: str) -> None:
        if password is None or not password.strip():
            raise SecurityError("password must not be empty")
        if len(password) < self.min_length:
            raise SecurityError(f"password must be at least {self.min_length} characters")
        if self.require_upper and not any(c.isupper() for c in password):
            raise SecurityError("password must include an uppercase letter")
        if self.require_lower and not any(c.islower() for c in password):
            raise SecurityError("password must include a lowercase letter")
        if self.require_digit and not any(c.isdigit() for c in password):
            raise SecurityError("password must include a digit")


class ScryptPasswordHasher:
    """Stdlib scrypt hasher — behavioural reference / CI default."""

    _PREFIX = "scrypt$"

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        return (
            f"{self._PREFIX}{salt.hex()}${digest.hex()}"
        )

    def verify(self, password: str, password_hash: str) -> bool:
        if not password_hash.startswith(self._PREFIX):
            return False
        try:
            _, salt_hex, digest_hex = password_hash.split("$", 2)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except ValueError:
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        return hmac.compare_digest(actual, expected)


class Argon2PasswordHasher:
    """Argon2id hasher — preferred when argon2-cffi is installed (lazy)."""

    def __init__(self) -> None:
        self._argon2 = importlib.import_module("argon2")
        self._ph = self._argon2.PasswordHasher()

    def hash(self, password: str) -> str:
        return f"argon2${self._ph.hash(password)}"

    def verify(self, password: str, password_hash: str) -> bool:
        if password_hash.startswith("argon2$"):
            material = password_hash[len("argon2$") :]
        elif password_hash.startswith("$argon2"):
            material = password_hash
        else:
            return False
        try:
            return bool(self._ph.verify(material, password))
        except Exception:
            return False


def build_password_hasher(*, prefer_argon2: bool = True) -> ScryptPasswordHasher | Argon2PasswordHasher:
    """Prefer Argon2 when available; else scrypt reference."""
    if prefer_argon2:
        try:
            return Argon2PasswordHasher()
        except ImportError:
            pass
    return ScryptPasswordHasher()
