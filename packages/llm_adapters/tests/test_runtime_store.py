import json
import os
from unittest.mock import patch
import pytest

from llm_adapters.runtime_store import (
    RuntimeProviderStore,
    ValidationFailedError,
    encrypt_at_rest,
    decrypt_at_rest,
    mask_secret,
)


def test_encryption_at_rest():
    secret = "sk-super-secret-key-1234567890"
    encrypted = encrypt_at_rest(secret)
    assert encrypted.startswith("enc:v1:")
    assert secret not in encrypted
    decrypted = decrypt_at_rest(encrypted)
    assert decrypted == secret


def test_mask_secret():
    assert mask_secret("short") == "***configured***"
    masked = mask_secret("sk-1234567890abcdef")
    assert masked.startswith("sk-1")
    assert masked.endswith("cdef")
    assert "234567890ab" not in masked
    assert mask_secret(None) is None


def test_store_replace_and_revoke_credential(tmp_path):
    store_file = str(tmp_path / "test_store.json")
    store = RuntimeProviderStore(store_path=store_file)
    
    # Initially not configured
    gemini = store.get_provider("gemini")
    assert gemini is not None
    assert gemini["has_credential"] is False
    assert gemini["masked_credential"] is None

    # Replace credential without validation
    updated = store.replace_credential(
        "gemini",
        new_secret="test-gemini-key-999999",
        author="admin_test",
        validate=False,
        model="gemini-2.5-pro",
    )
    assert updated.has_credential is True
    assert updated.version == 2

    # Check persisted file on disk is encrypted
    with open(store_file, "r") as f:
        disk_content = f.read()
    assert "test-gemini-key-999999" not in disk_content
    assert "enc:v1:" in disk_content

    # Reload store from disk (restart simulation)
    new_store = RuntimeProviderStore(store_path=store_file)
    reloaded = new_store.get_provider("gemini")
    assert reloaded["has_credential"] is True
    assert reloaded["masked_credential"] is not None
    assert "9999" in reloaded["masked_credential"]
    assert new_store.get_credential("gemini") == "test-gemini-key-999999"

    # Revoke credential
    revoked = new_store.revoke_credential("gemini", author="admin_test")
    assert revoked.has_credential is False
    assert revoked.health_status.value == "not_configured"
    assert new_store.get_credential("gemini") is None

    # Audit trail records action without secret
    audits = new_store.get_audit_log("gemini")
    assert len(audits) >= 2
    for log in audits:
        log_str = json.dumps(log)
        assert "test-gemini-key-999999" not in log_str


def test_revoked_environment_credential_stays_revoked_after_restart(tmp_path):
    store_file = str(tmp_path / "revocation_store.json")
    with patch.dict(os.environ, {"OPENAI_API_KEY": "environment-key-that-must-stay-revoked"}):
        first = RuntimeProviderStore(store_path=store_file)
        assert first.get_credential("openai") == "environment-key-that-must-stay-revoked"

        first.revoke_credential("openai", author="admin_test")
        assert first.get_credential("openai") is None

        # Simulate a process restart while the original environment variable remains set.
        restarted = RuntimeProviderStore(store_path=store_file)
        assert restarted.get_credential("openai") is None
        assert restarted.get_provider("openai")["has_credential"] is False


def test_failed_candidate_preserves_existing_credential(tmp_path):
    store_file = str(tmp_path / "test_store.json")
    store = RuntimeProviderStore(store_path=store_file)
    store.replace_credential(
        "openai",
        new_secret="good-openai-key-111111",
        author="admin_test",
        validate=False,
    )
    assert store.get_credential("openai") == "good-openai-key-111111"
    assert store.get_provider("openai")["version"] == 2

    # Now attempt replacement with candidate that fails validation
    with patch.object(store, "test_connection", return_value={"ok": False, "status": "auth_failure", "latency_ms": 50, "sanitized_error": "Invalid API Key"}):
        with pytest.raises(ValidationFailedError):
            store.replace_credential(
                "openai",
                new_secret="bad-openai-key-222222",
                author="admin_test",
                validate=True,
            )

    # Existing key must be preserved!
    assert store.get_credential("openai") == "good-openai-key-111111"
    assert store.get_provider("openai")["version"] == 2

def test_production_store_requires_explicit_encryption_master_key(tmp_path):
    store_file = str(tmp_path / "production_store.json")
    with patch.dict(
        os.environ,
        {
            "DSP_ENV": "production",
            "DATABASE_URL": "",
            "DSP_DATABASE_URL": "",
            "DSP_RUNTIME_STORE_DSN": "",
            "DSP_CREDENTIAL_MASTER_KEY": "",
            "DSP_MFA_SECRET_KEY": "",
            "DSP_AUTH_JWT_SECRET": "jwt-secret-must-not-be-used-for-credential-encryption",
        },
        clear=False,
    ):
        with pytest.raises(RuntimeError, match="DSP_CREDENTIAL_MASTER_KEY"):
            RuntimeProviderStore(store_path=store_file)

