"""WebAuthn / Passkey adapter tests using real captured FIDO2 ceremony fixtures.

The credential/assertion payloads below are the well-known public test
vectors distributed with Duo Labs' ``py_webauthn`` test suite (BSD-3-Clause,
https://github.com/duo-labs/py_webauthn) — genuine browser-produced
attestation/assertion objects, not hand-crafted mocks. Using them lets us
exercise the *real* CBOR/COSE parsing and signature-verification code paths
end-to-end without a physical authenticator.
"""

from __future__ import annotations

import time

import pytest

webauthn_lib = pytest.importorskip("webauthn", reason="optional 'webauthn' package not installed")

from auth.mfa_webauthn import WebAuthnAdapter, _b64url_decode  # noqa: E402
from persistence import (  # noqa: E402
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
)


class _FakeUser:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.email = f"{user_id}@example.com"
        self.username = user_id
        self.display_name = user_id


class _FakeUsers:
    def __init__(self) -> None:
        self._users: dict[str, _FakeUser] = {}

    def add(self, user_id: str) -> _FakeUser:
        user = _FakeUser(user_id)
        self._users[user_id] = user
        return user

    def get(self, user_id: str):
        return self._users.get(user_id)

    def get_by_username(self, username: str):
        return self._users.get(username)

    def list_users(self):
        return list(self._users.values())


def _persistence() -> PersistenceService:
    return PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))


_REG_CREDENTIAL = {
    "id": "9y1xA8Tmg1FEmT-c7_fvWZ_uoTuoih3OvR45_oAK-cwHWhAbXrl2q62iLVTjiyEZ7O7n-CROOY494k7Q3xrs_w",
    "rawId": "9y1xA8Tmg1FEmT-c7_fvWZ_uoTuoih3OvR45_oAK-cwHWhAbXrl2q62iLVTjiyEZ7O7n-CROOY494k7Q3xrs_w",
    "response": {
        "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjESZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NFAAAAFwAAAAAAAAAAAAAAAAAAAAAAQPctcQPE5oNRRJk_nO_371mf7qE7qIodzr0eOf6ACvnMB1oQG165dqutoi1U44shGezu5_gkTjmOPeJO0N8a7P-lAQIDJiABIVggSFbUJF-42Ug3pdM8rDRFu_N5oiVEysPDB6n66r_7dZAiWCDUVnB39FlGypL-qAoIO9xWHtJygo2jfDmHl-_eKFRLDA",
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiVHdON240V1R5R0tMYzRaWS1xR3NGcUtuSE00bmdscXN5VjBJQ0psTjJUTzlYaVJ5RnRya2FEd1V2c3FsLWdrTEpYUDZmbkYxTWxyWjUzTW00UjdDdnciLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjUwMDAiLCJjcm9zc09yaWdpbiI6ZmFsc2V9",
    },
    "type": "public-key",
    "clientExtensionResults": {},
    "transports": ["nfc", "usb"],
}
_REG_CHALLENGE_B64URL = (
    "TwN7n4WTyGKLc4ZY-qGsFqKnHM4nglqsyV0ICJlN2TO9XiRyFtrkaDwUvsql-gkLJXP6fnF1MlrZ53Mm4R7Cvw"
)

_AUTH_CREDENTIAL = {
    "id": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "rawId": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "response": {
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAATg",
        "clientDataJSON": "eyJjaGFsbGVuZ2UiOiJ4aTMwR1BHQUZZUnhWRHBZMXNNMTBEYUx6VlFHNjZudi1fN1JVYXpIMHZJMll2RzhMWWdERW52TjVmWlpOVnV2RUR1TWk5dGUzVkxxYjQyTjBma0xHQSIsImNsaWVudEV4dGVuc2lvbnMiOnt9LCJoYXNoQWxnb3JpdGhtIjoiU0hBLTI1NiIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTAwMCIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ",
        "signature": "MEUCIGisVZOBapCWbnJJvjelIzwpixxIwkjCCb5aCHafQu68AiEA88v-2pJNNApPFwAKFiNuf82-2hBxYW5kGwVweeoxCwo",
    },
    "type": "public-key",
    "clientExtensionResults": {},
}
_AUTH_CHALLENGE_B64URL = (
    "xi30GPGAFYRxVDpY1sM10DaLzVQG66nv-_7RUazH0vI2YvG8LYgDEnvN5fZZNVuvEDuMi9te3VLqb42N0fkLGA"
)
_AUTH_PUBLIC_KEY_B64URL = (
    "pQECAyYgASFYIIeDTe-gN8A-zQclHoRnGFWN8ehM1b7yAsa8I8KIvmplIlgg4nFGT5px8o6gpPZZhO01wdy9crDSA_Ngtkx0vGpvPHI"
)


def test_registration_completes_with_real_attestation() -> None:
    persistence = _persistence()
    users = _FakeUsers()
    users.add("user-1")
    adapter = WebAuthnAdapter(
        persistence, users, rp_id="localhost", rp_name="Test RP", origin="http://localhost:5000"
    )
    state = "reg-state-1"
    adapter.seed_pending(state, {  # noqa: SLF001 — seeding a deterministic ceremony for the test
        "kind": "registration",
        "user_id": "user-1",
        "challenge": _b64url_decode(_REG_CHALLENGE_B64URL),
        "created_at": time.time(),
    })
    result = adapter.complete_registration("user-1", {"state": state, "credential": _REG_CREDENTIAL})
    assert result["ok"] is True
    assert result["credential_id"] == _REG_CREDENTIAL["id"]
    creds = adapter.list_credentials("user-1")
    assert len(creds) == 1
    assert creds[0]["sign_count"] == 23


def test_registration_rejects_wrong_state() -> None:
    persistence = _persistence()
    users = _FakeUsers()
    users.add("user-1")
    adapter = WebAuthnAdapter(persistence, users, rp_id="localhost", origin="http://localhost:5000")
    with pytest.raises(Exception):
        adapter.complete_registration("user-1", {"state": "does-not-exist", "credential": _REG_CREDENTIAL})


def test_discoverable_authentication_completes_and_rotates_sign_count() -> None:
    persistence = _persistence()
    users = _FakeUsers()
    users.add("user-2")
    adapter = WebAuthnAdapter(
        persistence, users, rp_id="localhost", rp_name="Test RP", origin="http://localhost:5000"
    )
    cred_id = _AUTH_CREDENTIAL["id"]
    adapter._save_credentials(  # noqa: SLF001
        "user-2",
        [
            {
                "credential_id": cred_id,
                "public_key": _AUTH_PUBLIC_KEY_B64URL,
                "sign_count": 77,
                "device_type": "single_device",
                "backed_up": False,
                "transports": [],
                "label": "Test key",
                "created_at": time.time(),
            }
        ],
    )
    persistence.put(
        kind="metadata",
        entity_id=f"auth-webauthn-cred-index-{cred_id}",
        payload={"auth_entity": "webauthn_cred_index", "user_id": "user-2", "credential_id": cred_id},
        refs={"auth_entity": "webauthn_cred_index"},
        created_at=None,
        allow_update=True,
    )
    state = "auth-state-1"
    adapter.seed_pending(state, {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    })
    resolved = adapter.complete_discoverable_authentication(
        {"state": state, "credential": _AUTH_CREDENTIAL}
    )
    assert resolved["user_id"] == "user-2"
    assert resolved["credential_id"] == cred_id
    creds = adapter.list_credentials("user-2")
    assert creds[0]["sign_count"] == 78  # rotated per verification.new_sign_count


def test_unknown_credential_is_rejected() -> None:
    persistence = _persistence()
    users = _FakeUsers()
    adapter = WebAuthnAdapter(persistence, users, rp_id="localhost", origin="http://localhost:5000")
    state = "auth-state-2"
    adapter.seed_pending(state, {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    })
    with pytest.raises(Exception):
        adapter.complete_discoverable_authentication({"state": state, "credential": _AUTH_CREDENTIAL})


def test_begin_registration_and_discoverable_authentication_shapes() -> None:
    persistence = _persistence()
    users = _FakeUsers()
    users.add("user-3")
    adapter = WebAuthnAdapter(persistence, users, rp_id="localhost", origin="http://localhost:5000")
    reg_options = adapter.begin_registration("user-3")
    assert reg_options["state"]
    assert reg_options["rp"]["id"] == "localhost"
    assert reg_options["authenticatorSelection"]["residentKey"] == "required"

    auth_options = adapter.begin_discoverable_authentication(None)
    assert auth_options["state"]
    assert auth_options["rpId"] == "localhost"
