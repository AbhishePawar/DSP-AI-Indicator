"""WebAuthn / FIDO2 passkey adapter — registration + authentication ceremonies.

Uses the optional ``webauthn`` (Duo Labs ``py_webauthn``) package — a narrow,
widely-used FIDO2 *protocol* library (COSE key parsing, CBOR attestation
decoding, signature verification). It is **not** an authentication framework
(it has no notion of users, sessions, or routing) and is used here purely as
a cryptographic-primitives helper inside DSP's own Ports & Adapters
architecture, in exactly the same spirit as ``argon2-cffi`` is used as a
hashing primitive inside :mod:`auth.hashing`. When the package is not
installed, :class:`NullWebAuthnAdapter` (see :mod:`auth.mfa`) is used
instead and the feature reports itself as unavailable — the platform never
hard-fails on a missing optional dependency.

Two independent ceremonies are supported end-to-end:

* **Registration** — an *authenticated* user (bearer token) adds a
  passkey/security key to their account (resident/discoverable key,
  ``ResidentKeyRequirement.REQUIRED``). Multiple credentials per user are
  supported.
* **Authentication** — a discoverable ("usernameless") login: the browser's
  own credential picker supplies the credential, and the server resolves the
  account from the credential ID / ``userHandle`` in the assertion. An
  optional ``identifier`` narrows ``allow_credentials`` when supplied.

Challenges are single-use and time-boxed (matches the OAuth PKCE ``state``
pattern already used in :mod:`auth.oauth_providers`), which provides replay
protection independent of the library's own challenge check.
"""

from __future__ import annotations

import base64
import os
import secrets
import time
from threading import Lock
from typing import Any

from auth.exceptions import AuthenticationError, ValidationError

__all__ = ["WebAuthnAdapter", "webauthn_library_available"]

_CHALLENGE_TTL_SECONDS = 300
_CRED_PREFIX = "auth-webauthn-creds-"
_INDEX_PREFIX = "auth-webauthn-cred-index-"


def webauthn_library_available() -> bool:
    try:
        import webauthn  # noqa: F401
    except ImportError:
        return False
    return True


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


class WebAuthnAdapter:
    """Production FIDO2/WebAuthn adapter — persists via the shared metadata store."""

    def __init__(
        self,
        persistence: Any,
        users: Any,
        *,
        rp_id: str | None = None,
        rp_name: str | None = None,
        origin: str | None = None,
    ) -> None:
        self._persistence = persistence
        self._users = users
        self._rp_id = rp_id or os.environ.get("DSP_WEBAUTHN_RP_ID", "localhost")
        self._rp_name = rp_name or os.environ.get("DSP_WEBAUTHN_RP_NAME", "DSP AI Indicator")
        self._origin = origin or os.environ.get(
            "DSP_WEBAUTHN_ORIGIN", "http://localhost:3000"
        )
        self._pending: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def is_available(self) -> bool:
        return webauthn_library_available()

    # -- registration (authenticated: add a passkey to my account) -----

    def begin_registration(self, user_id: str) -> dict[str, Any]:
        if not self.is_available():
            raise NotImplementedError(
                "WebAuthn library not installed. Install the 'auth[passkey]' extra."
            )
        from webauthn import generate_registration_options, options_to_json
        from webauthn.helpers.cose import COSEAlgorithmIdentifier
        from webauthn.helpers.structs import (
            AttestationConveyancePreference,
            AuthenticatorSelectionCriteria,
            PublicKeyCredentialDescriptor,
            ResidentKeyRequirement,
            UserVerificationRequirement,
        )

        user = self._users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        existing = self._load_credentials(user_id)
        options = generate_registration_options(
            rp_id=self._rp_id,
            rp_name=self._rp_name,
            user_id=user_id.encode("utf-8"),
            user_name=user.email or user.username,
            user_display_name=user.display_name or user.username,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=_b64url_decode(c["credential_id"]))
                for c in existing
            ],
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
        )
        state = secrets.token_urlsafe(24)
        with self._lock:
            self._prune()
            self._pending[state] = {
                "kind": "registration",
                "user_id": user_id,
                "challenge": options.challenge,
                "created_at": time.time(),
            }
        payload: dict[str, Any] = _json(options_to_json(options))
        payload["state"] = state
        return payload

    def complete_registration(self, user_id: str, credential: dict[str, Any]) -> dict[str, Any]:
        if not self.is_available():
            raise NotImplementedError("WebAuthn library not installed.")
        from webauthn import verify_registration_response

        state = str(credential.get("state") or "")
        response = credential.get("credential") or credential.get("response") or credential
        with self._lock:
            pending = self._pending.pop(state, None)
        if pending is None or pending.get("kind") != "registration" or pending.get("user_id") != user_id:
            raise AuthenticationError("Invalid or expired registration challenge.")
        if time.time() - float(pending.get("created_at") or 0) > _CHALLENGE_TTL_SECONDS:
            raise AuthenticationError("Registration challenge expired.")
        try:
            verification = verify_registration_response(
                credential=response,
                expected_challenge=pending["challenge"],
                expected_rp_id=self._rp_id,
                expected_origin=self._origin,
                require_user_verification=False,
            )
        except Exception as exc:  # noqa: BLE001 — library raises its own exception hierarchy
            raise AuthenticationError(f"Passkey registration failed: {exc}") from exc

        cred_id_b64 = _b64url_encode(verification.credential_id)
        record = {
            "credential_id": cred_id_b64,
            "public_key": _b64url_encode(verification.credential_public_key),
            "sign_count": int(verification.sign_count),
            "device_type": str(getattr(verification, "credential_device_type", "") or ""),
            "backed_up": bool(getattr(verification, "credential_backed_up", False)),
            "transports": list((response.get("response") or {}).get("transports") or []),
            "label": str(credential.get("label") or "Passkey"),
            "created_at": time.time(),
        }
        creds = self._load_credentials(user_id)
        creds.append(record)
        self._save_credentials(user_id, creds)
        self._persistence.put(
            kind="metadata",
            entity_id=f"{_INDEX_PREFIX}{cred_id_b64}",
            payload={"auth_entity": "webauthn_cred_index", "user_id": user_id, "credential_id": cred_id_b64},
            refs={"auth_entity": "webauthn_cred_index"},
            created_at=None,
            allow_update=True,
        )
        return {
            "ok": True,
            "credential_id": cred_id_b64,
            "device_type": record["device_type"],
            "backed_up": record["backed_up"],
        }

    # -- authentication (discoverable / usernameless login) -------------

    def begin_discoverable_authentication(self, identifier: str | None = None) -> dict[str, Any]:
        if not self.is_available():
            raise NotImplementedError("WebAuthn library not installed.")
        from webauthn import generate_authentication_options, options_to_json
        from webauthn.helpers.structs import (
            PublicKeyCredentialDescriptor,
            UserVerificationRequirement,
        )

        allow: list[Any] = []
        if identifier:
            user = self._users.get_by_username(identifier) if "@" not in identifier else None
            if user is None:
                for candidate in self._users.list_users():
                    if candidate.email.casefold() == identifier.strip().casefold():
                        user = candidate
                        break
            if user is not None:
                allow = [
                    PublicKeyCredentialDescriptor(id=_b64url_decode(c["credential_id"]))
                    for c in self._load_credentials(user.user_id)
                ]
        options = generate_authentication_options(
            rp_id=self._rp_id,
            allow_credentials=allow or None,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        state = secrets.token_urlsafe(24)
        with self._lock:
            self._prune()
            self._pending[state] = {
                "kind": "authentication",
                "challenge": options.challenge,
                "created_at": time.time(),
            }
        payload: dict[str, Any] = _json(options_to_json(options))
        payload["state"] = state
        return payload

    def begin_authentication(self, user_id: str) -> dict[str, Any]:
        """MFA step-up variant: scoped to a single already-authenticated user."""
        user = self._users.get(user_id)
        identifier = user.email if user else None
        return self.begin_discoverable_authentication(identifier)

    def complete_discoverable_authentication(self, assertion: dict[str, Any]) -> dict[str, Any]:
        """Verify assertion and resolve the account — returns ``{user_id, ...}``."""
        if not self.is_available():
            raise NotImplementedError("WebAuthn library not installed.")
        from webauthn import verify_authentication_response

        state = str(assertion.get("state") or "")
        response = assertion.get("credential") or assertion.get("response") or assertion
        with self._lock:
            pending = self._pending.pop(state, None)
        if pending is None or pending.get("kind") != "authentication":
            raise AuthenticationError("Invalid or expired authentication challenge.")
        if time.time() - float(pending.get("created_at") or 0) > _CHALLENGE_TTL_SECONDS:
            raise AuthenticationError("Authentication challenge expired.")

        raw_id = response.get("rawId") or response.get("id")
        if not raw_id:
            raise AuthenticationError("Malformed passkey assertion.")
        # Browsers/authenticator libraries encode credential ids as base64url
        # already (WebAuthn spec §5.8.3) — the same convention used when the
        # credential was stored in `complete_registration`.
        cred_id_b64 = str(raw_id).rstrip("=")
        index_row = self._persistence.get("metadata", f"{_INDEX_PREFIX}{cred_id_b64}")
        if index_row is None:
            raise AuthenticationError("Unknown passkey credential.")
        user_id = str((index_row.get("payload") or {}).get("user_id") or "")
        creds = self._load_credentials(user_id)
        record = next((c for c in creds if c["credential_id"] == cred_id_b64), None)
        if record is None:
            raise AuthenticationError("Unknown passkey credential.")
        try:
            verification = verify_authentication_response(
                credential=response,
                expected_challenge=pending["challenge"],
                expected_rp_id=self._rp_id,
                expected_origin=self._origin,
                credential_public_key=_b64url_decode(record["public_key"]),
                credential_current_sign_count=int(record["sign_count"]),
                require_user_verification=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationError(f"Passkey verification failed: {exc}") from exc

        record["sign_count"] = int(verification.new_sign_count)
        record["last_used_at"] = time.time()
        self._save_credentials(user_id, creds)
        return {"user_id": user_id, "credential_id": cred_id_b64}

    def complete_authentication(self, user_id: str, assertion: dict[str, Any]) -> bool:
        """MFA step-up variant matching :class:`auth.mfa.WebAuthnPort`."""
        try:
            result = self.complete_discoverable_authentication(assertion)
        except AuthenticationError:
            return False
        return result.get("user_id") == user_id

    # -- introspection ---------------------------------------------------

    def list_credentials(self, user_id: str) -> list[dict[str, Any]]:
        return [
            {k: v for k, v in c.items() if k != "public_key"} for c in self._load_credentials(user_id)
        ]

    def remove_credential(self, user_id: str, credential_id: str) -> bool:
        creds = self._load_credentials(user_id)
        remaining = [c for c in creds if c["credential_id"] != credential_id]
        if len(remaining) == len(creds):
            return False
        self._save_credentials(user_id, remaining)
        self._persistence.delete("metadata", f"{_INDEX_PREFIX}{credential_id}")
        return True

    # -- internal ---------------------------------------------------------

    def _prune(self) -> None:
        now = time.time()
        stale = [
            k for k, v in self._pending.items() if now - float(v.get("created_at") or 0) > _CHALLENGE_TTL_SECONDS
        ]
        for k in stale:
            self._pending.pop(k, None)

    def _load_credentials(self, user_id: str) -> list[dict[str, Any]]:
        row = self._persistence.get("metadata", f"{_CRED_PREFIX}{user_id}")
        if row is None:
            return []
        return list((row.get("payload") or {}).get("credentials") or [])

    def _save_credentials(self, user_id: str, credentials: list[dict[str, Any]]) -> None:
        self._persistence.put(
            kind="metadata",
            entity_id=f"{_CRED_PREFIX}{user_id}",
            payload={"auth_entity": "webauthn_creds", "user_id": user_id, "credentials": credentials},
            refs={"auth_entity": "webauthn_creds", "user_id": user_id},
            created_at=None,
            allow_update=True,
        )


def _json(text: str) -> dict[str, Any]:
    import json

    return dict(json.loads(text))
