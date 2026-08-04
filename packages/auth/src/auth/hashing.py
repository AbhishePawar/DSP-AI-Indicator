"""Password hashing — Argon2id preferred; bcrypt / PBKDF2-SHA256 for verify + upgrade."""

from __future__ import annotations

import hashlib
import hmac
import importlib
import os
import secrets

__all__ = ["hash_password", "verify_password", "needs_rehash"]

_ITERATIONS = 120_000
_ALGO = "sha256"


def _argon2_available() -> bool:
    try:
        importlib.import_module("argon2")
        return True
    except ImportError:
        return False


def _bcrypt_available() -> bool:
    try:
        importlib.import_module("bcrypt")
        return True
    except ImportError:
        return False


def _preferred_scheme() -> str:
    mode = (os.environ.get("DSP_PASSWORD_HASHER") or "argon2id").strip().lower()
    if mode in {"pbkdf2", "pbkdf2-sha256"}:
        return "pbkdf2"
    if mode in {"bcrypt"}:
        return "bcrypt" if _bcrypt_available() else ("argon2id" if _argon2_available() else "pbkdf2")
    if mode in {"argon2", "argon2id"}:
        return "argon2id" if _argon2_available() else ("bcrypt" if _bcrypt_available() else "pbkdf2")
    return "argon2id" if _argon2_available() else ("bcrypt" if _bcrypt_available() else "pbkdf2")


def hash_password(password: str, *, salt: str | None = None) -> str:
    """Return salted hash — never store plaintext.

    Prefers ``argon2id$…`` (argon2-cffi) for enterprise policy.
    Fixed ``salt`` forces the PBKDF2 path (tests / determinism).
    """
    if not password:
        raise ValueError("password is required")
    if salt is not None:
        salt_hex = salt
        digest = hashlib.pbkdf2_hmac(
            _ALGO,
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            _ITERATIONS,
        ).hex()
        return f"pbkdf2${_ITERATIONS}${salt_hex}${digest}"

    scheme = _preferred_scheme()
    if scheme == "argon2id":
        argon2 = importlib.import_module("argon2")
        ph = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=2,
            hash_len=32,
            salt_len=16,
            type=argon2.Type.ID,
        )
        return f"argon2id${ph.hash(password)}"
    if scheme == "bcrypt":
        bcrypt = importlib.import_module("bcrypt")
        digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return f"bcrypt${digest.decode('utf-8')}"
    salt_hex = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        _ALGO,
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        _ITERATIONS,
    ).hex()
    return f"pbkdf2${_ITERATIONS}${salt_hex}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    if password_hash.startswith("argon2id$") or password_hash.startswith("argon2$"):
        try:
            argon2 = importlib.import_module("argon2")
        except ImportError:
            return False
        raw = password_hash.split("$", 1)[1]
        ph = argon2.PasswordHasher()
        try:
            return bool(ph.verify(raw, password))
        except Exception:  # noqa: BLE001
            return False
    if password_hash.startswith("bcrypt$"):
        try:
            bcrypt = importlib.import_module("bcrypt")
        except ImportError:
            return False
        raw = password_hash[len("bcrypt$") :].encode("utf-8")
        try:
            return bool(bcrypt.checkpw(password.encode("utf-8"), raw))
        except Exception:  # noqa: BLE001
            return False
    try:
        scheme, iters_s, salt_hex, digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2":
        return False
    try:
        iterations = int(iters_s)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        _ALGO,
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest)


def needs_rehash(password_hash: str) -> bool:
    """True when stored hash should be upgraded to the preferred scheme."""
    preferred = _preferred_scheme()
    if preferred == "argon2id":
        return not (
            password_hash.startswith("argon2id$") or password_hash.startswith("argon2$")
        )
    if preferred == "bcrypt":
        return not password_hash.startswith("bcrypt$")
    return not password_hash.startswith("pbkdf2$")
