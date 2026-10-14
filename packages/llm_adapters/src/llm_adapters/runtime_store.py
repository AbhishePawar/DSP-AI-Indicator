"""Server-Side Runtime Provider & Credential Management Store.

Provides thread-safe in-memory credential storage, authenticated encryption at rest
(Fernet AES-128-CBC + HMAC-SHA256, format enc:v1:<token>), server-isolated persistence
(POSIX mode 0600) with optional PostgreSQL synchronization, atomic credential replacement
with connection validation, credential revocation, version rollback, sanitized health diagnostics,
and structured audit logging. Secrets are NEVER returned in public APIs, logs, or audit records.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import logging
import os
import stat
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from llm_adapters.connection_tester import test_provider_connection
from llm_adapters.provider_health import (
    ProviderDiagnostics,
    ProviderHealthStatus,
    classify_provider_error,
)

logger = logging.getLogger(__name__)

DEFAULT_STORE_PATH = os.environ.get(
    "DSP_RUNTIME_STORE_PATH", "/tmp/dsp_runtime_providers.json"
)

_ENC_PREFIX = "enc:v1:"


def _derive_fernet_key(passphrase: str) -> bytes:
    """Deterministically derive a 32-byte urlsafe-base64 Fernet key from a secret passphrase."""
    digest = hashlib.sha256(passphrase.strip().encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_active_encryption_key() -> bytes:
    """Retrieve or derive the encryption key for credential encryption at rest."""
    from cryptography.fernet import Fernet

    # 1. Master credential encryption key
    configured = (os.environ.get("DSP_CREDENTIAL_MASTER_KEY") or "").strip()
    if configured:
        try:
            Fernet(configured.encode("ascii"))
            return configured.encode("ascii")
        except Exception:
            return _derive_fernet_key(configured)

    # 2. MFA secret key fallback
    mfa_key = (os.environ.get("DSP_MFA_SECRET_KEY") or "").strip()
    if mfa_key:
        try:
            Fernet(mfa_key.encode("ascii"))
            return mfa_key.encode("ascii")
        except Exception:
            return _derive_fernet_key(mfa_key)

    # 3. JWT Secret or platform secret key derivation
    jwt_secret = (
        os.environ.get("DSP_AUTH_JWT_SECRET")
        or "dsp-production-secret-deterministic-key-fallback"
    ).strip()
    return _derive_fernet_key(jwt_secret)


def encrypt_at_rest(plaintext: str) -> str:
    """Encrypt plaintext string using Fernet authenticated encryption."""
    if not plaintext:
        return ""
    from cryptography.fernet import Fernet

    key = _get_active_encryption_key()
    token = Fernet(key).encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{_ENC_PREFIX}{token}"


def decrypt_at_rest(stored: str) -> str:
    """Decrypt stored ciphertext string using Fernet authenticated encryption."""
    if not stored:
        return ""
    if not stored.startswith(_ENC_PREFIX):
        # Unencrypted legacy record: return as is
        return stored
    from cryptography.fernet import Fernet, InvalidToken

    token = stored[len(_ENC_PREFIX) :].encode("ascii")
    key = _get_active_encryption_key()
    try:
        return Fernet(key).decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        logger.error("Failed to decrypt stored credential: key mismatch or ciphertext corrupted.")
        raise ValueError("Stored credential could not be decrypted.") from exc


def mask_secret(secret: str | None) -> str | None:
    """Generate safe masked string for administrator confirmation without leaking secret."""
    if not secret:
        return None
    s = secret.strip()
    if len(s) <= 8:
        return "***configured***"
    if s.startswith("sk-"):
        return f"{s[:7]}...{s[-4:]}"
    return f"{s[:4]}...{s[-4:]}"


class ValidationFailedError(Exception):
    """Raised when candidate credentials fail connection verification."""

    def __init__(self, message: str, diagnostics: ProviderDiagnostics | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics


class ProviderNotFoundError(KeyError):
    """Raised when requested provider is not in the registry."""
    pass


@dataclass
class ProviderConfig:
    """Non-sensitive representation of a provider's configuration and health."""

    provider_id: str
    display_name: str
    category: str  # "ai" | "market_data"
    is_active: bool = True
    selected_model: str = ""
    supported_models: list[str] = field(default_factory=list)
    supported_capabilities: list[str] = field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int = 2048
    base_url: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 2
    health_status: ProviderHealthStatus = ProviderHealthStatus.NOT_CONFIGURED
    last_test_timestamp: str | None = None
    last_test_latency_ms: float | None = None
    last_test_success: bool | None = None
    last_error_sanitized: str | None = None
    recommended_action: str | None = None
    last_successful_use: str | None = None
    has_credential: bool = False
    version: int = 1

    def to_public_dict(self, masked_credential: str | None = None) -> dict[str, Any]:
        """Convert to client-safe dictionary. NEVER reveals secrets."""
        d = asdict(self)
        d["health_status"] = self.health_status.value
        d["masked_credential"] = masked_credential
        d["available_models"] = self.supported_models
        d["requires_credential"] = True
        d["error_message"] = self.last_error_sanitized
        d["last_tested_at"] = self.last_test_timestamp
        d["last_latency_ms"] = self.last_test_latency_ms
        return d

    to_dict = to_public_dict


@dataclass
class AuditRecord:
    """Audit log entry for administrator configuration and credential actions."""

    timestamp: str
    author: str
    action: str  # "credential_replace", "credential_revoked", "config_update", "activate", "test", "rollback"
    provider_id: str
    version: int
    validation_result: str
    sanitized_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Default catalog covering AI and Market Data
DEFAULT_PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        provider_id="gemini",
        display_name="Google Gemini",
        category="ai",
        is_active=True,
        selected_model="gemini-2.0-flash",
        supported_models=[
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-3.1-flash-lite",
        ],
        supported_capabilities=["chat", "structured_output", "financial_extraction"],
    ),
    ProviderConfig(
        provider_id="openai",
        display_name="OpenAI",
        category="ai",
        is_active=True,
        selected_model="gpt-4.1-mini",
        supported_models=["gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o1-mini"],
        supported_capabilities=["chat", "structured_output", "financial_extraction"],
    ),
    ProviderConfig(
        provider_id="anthropic",
        display_name="Anthropic Claude",
        category="ai",
        is_active=True,
        selected_model="claude-3-5-sonnet-20241022",
        supported_models=[
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229",
        ],
        supported_capabilities=["chat", "structured_output", "reasoning"],
    ),
    ProviderConfig(
        provider_id="deepseek",
        display_name="DeepSeek",
        category="ai",
        is_active=True,
        selected_model="deepseek-chat",
        supported_models=["deepseek-chat", "deepseek-reasoner"],
        supported_capabilities=["chat", "reasoning"],
    ),
    ProviderConfig(
        provider_id="openrouter",
        display_name="OpenRouter",
        category="ai",
        is_active=True,
        selected_model="anthropic/claude-3.5-sonnet",
        supported_models=[
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3.3-70b-instruct",
        ],
        supported_capabilities=["chat", "multi_model"],
    ),
    ProviderConfig(
        provider_id="groq",
        display_name="Groq",
        category="ai",
        is_active=True,
        selected_model="llama-3.3-70b-versatile",
        supported_models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        supported_capabilities=["chat", "high_speed"],
    ),
    ProviderConfig(
        provider_id="mistral",
        display_name="Mistral AI",
        category="ai",
        is_active=True,
        selected_model="mistral-large-latest",
        supported_models=["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
        supported_capabilities=["chat", "structured_output"],
    ),
    ProviderConfig(
        provider_id="xai",
        display_name="xAI Grok",
        category="ai",
        is_active=True,
        selected_model="grok-beta",
        supported_models=["grok-beta", "grok-2-latest"],
        supported_capabilities=["chat", "realtime_knowledge"],
    ),
    ProviderConfig(
        provider_id="together",
        display_name="Together AI",
        category="ai",
        is_active=True,
        selected_model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        supported_models=[
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
        ],
        supported_capabilities=["chat"],
    ),
    ProviderConfig(
        provider_id="fireworks",
        display_name="Fireworks AI",
        category="ai",
        is_active=True,
        selected_model="accounts/fireworks/models/llama-v3p1-70b-instruct",
        supported_models=["accounts/fireworks/models/llama-v3p1-70b-instruct"],
        supported_capabilities=["chat"],
    ),
    ProviderConfig(
        provider_id="perplexity",
        display_name="Perplexity API",
        category="ai",
        is_active=True,
        selected_model="sonar",
        supported_models=["sonar", "sonar-pro", "sonar-reasoning"],
        supported_capabilities=["chat", "web_search"],
    ),
    ProviderConfig(
        provider_id="cohere",
        display_name="Cohere",
        category="ai",
        is_active=True,
        selected_model="command-r-plus",
        supported_models=["command-r-plus", "command-r"],
        supported_capabilities=["chat", "rag"],
    ),
    ProviderConfig(
        provider_id="ollama",
        display_name="Ollama (Self-Hosted)",
        category="ai",
        is_active=False,
        selected_model="llama3",
        supported_models=["llama3", "mistral", "qwen2.5"],
        base_url="http://localhost:11434",
        supported_capabilities=["chat", "offline"],
    ),
    ProviderConfig(
        provider_id="upstox",
        display_name="Upstox Market Data",
        category="market_data",
        is_active=True,
        selected_model="quotes-v3",
        supported_models=["quotes-v3", "live-feed-v3"],
        supported_capabilities=["market_quote", "instrument_resolution"],
    ),
]


class RuntimeProviderStore:
    """Thread-safe runtime provider registry and secret store with authenticated encryption at rest."""

    def __init__(self, store_path: str = DEFAULT_STORE_PATH):
        self._lock = threading.RLock()
        self._store_path = store_path
        self._providers: dict[str, ProviderConfig] = {}
        self._secrets: dict[str, str] = {}  # In-memory decrypted secret cache
        self._history: dict[str, list[dict[str, Any]]] = {}  # Version snapshots
        self._audit_log: list[AuditRecord] = []
        self._postgres_enabled: bool = False
        self._postgres_dsn: str | None = None
        self._postgres_pool: Any | None = None
        self._credential_revoked: set[str] = set()
        self._last_refresh_monotonic: float = 0.0
        self._refresh_interval_seconds: float = max(
            0.25, float(os.environ.get("DSP_RUNTIME_STORE_REFRESH_SECONDS", "1.0"))
        )

        self._check_persistence_backend()
        self._initialize_from_catalog_and_env()
        self._load_from_storage_if_present()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _check_persistence_backend(self) -> None:
        """Inspect environment for PostgreSQL persistence connectivity."""
        dsn = (
            os.environ.get("DSP_RUNTIME_STORE_DSN")
            or os.environ.get("DSP_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
        )
        production_mode = any(
            os.environ.get(name, "").strip().lower() in {"production", "prod"}
            for name in ("DSP_ENV", "APP_ENV", "ENVIRONMENT", "NODE_ENV", "ENV")
        )
        if not dsn or not dsn.strip():
            if production_mode:
                raise RuntimeError(
                    "Runtime provider store requires PostgreSQL in production; "
                    "configure DSP_RUNTIME_STORE_DSN or DSP_DATABASE_URL."
                )
            self._postgres_enabled = False
            return

        self._postgres_dsn = dsn.strip()
        try:
            from psycopg_pool import ConnectionPool

            self._postgres_pool = ConnectionPool(
                conninfo=self._postgres_dsn,
                min_size=1,
                max_size=max(2, int(os.environ.get("DSP_RUNTIME_STORE_POOL_MAX_SIZE", "8"))),
                timeout=3,
                kwargs={"connect_timeout": 3},
                open=True,
            )
            with self._postgres_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS dsp_runtime_providers (
                            provider_id TEXT PRIMARY KEY,
                            config_json TEXT NOT NULL,
                            encrypted_credential TEXT,
                            credential_revoked BOOLEAN NOT NULL DEFAULT FALSE,
                            version INT NOT NULL DEFAULT 1,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        ALTER TABLE dsp_runtime_providers
                            ADD COLUMN IF NOT EXISTS credential_revoked BOOLEAN NOT NULL DEFAULT FALSE;
                        CREATE TABLE IF NOT EXISTS dsp_runtime_provider_audits (
                            id BIGSERIAL PRIMARY KEY,
                            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            author TEXT NOT NULL,
                            action TEXT NOT NULL,
                            provider_id TEXT NOT NULL,
                            version INT NOT NULL,
                            validation_result TEXT NOT NULL,
                            sanitized_metadata JSONB NOT NULL
                        );
                        """
                    )
                conn.commit()
            self._postgres_enabled = True
            logger.info("PostgreSQL runtime provider persistence initialized and verified.")
        except Exception as exc:
            if self._postgres_pool is not None:
                try:
                    self._postgres_pool.close()
                except Exception:
                    pass
                self._postgres_pool = None
            if production_mode:
                raise RuntimeError(
                    "PostgreSQL runtime provider storage is required in production "
                    "and could not be initialized."
                ) from exc
            logger.warning(
                "PostgreSQL persistence unavailable; using local storage only outside production."
            )
            self._postgres_enabled = False

    def _initialize_from_catalog_and_env(self) -> None:
        """Seed default providers and link existing environment credentials."""
        for p in DEFAULT_PROVIDERS:
            copied = copy.deepcopy(p)
            self._providers[copied.provider_id] = copied
            self._history[copied.provider_id] = []

        env_mappings = {
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "DSP_AI_GEMINI_API_KEY"],
            "openai": [
                "OPENAI_API_KEY",
                "DSP_AI_OPENAI_API_KEY",
                "OPENAI_API_KEY_5",
            ],
            "anthropic": ["ANTHROPIC_API_KEY", "DSP_AI_ANTHROPIC_API_KEY"],
            "deepseek": ["DEEPSEEK_API_KEY", "DSP_AI_DEEPSEEK_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY"],
            "groq": ["GROQ_API_KEY"],
            "mistral": ["MISTRAL_API_KEY"],
            "xai": ["XAI_API_KEY"],
            "together": ["TOGETHER_API_KEY"],
            "fireworks": ["FIREWORKS_API_KEY"],
            "perplexity": ["PERPLEXITY_API_KEY"],
            "cohere": ["COHERE_API_KEY"],
            "upstox": [
                "UPSTOX_ACCESS_TOKEN",
                "UPSTOX_AUTH_TOKEN",
                "UPSTOX_TOKEN",
                "DSP_UPSTOX_ACCESS_TOKEN",
            ],
        }

        for provider_id, env_vars in env_mappings.items():
            if provider_id not in self._providers:
                continue
            for var_name in env_vars:
                val = os.environ.get(var_name)
                if val and val.strip():
                    self._secrets[provider_id] = val.strip()
                    self._providers[provider_id].has_credential = True
                    self._providers[provider_id].health_status = (
                        ProviderHealthStatus.CONFIGURED_UNTESTED
                    )
                    break

    def _load_from_storage_if_present(self) -> None:
        """Load persisted configuration from PostgreSQL or encrypted isolated server disk file."""
        if self._postgres_enabled and self._postgres_pool is not None:
            try:
                with self._postgres_pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT provider_id, config_json, encrypted_credential, version, "
                            "credential_revoked FROM dsp_runtime_providers"
                        )
                        rows = cur.fetchall()
                        with self._lock:
                            for pid, cfg_str, enc_cred, ver, credential_revoked in rows:
                                if pid in self._providers:
                                    prov = self._providers[pid]
                                    pdata = json.loads(cfg_str)
                                    prov.is_active = pdata.get("is_active", prov.is_active)
                                    prov.selected_model = pdata.get("selected_model", prov.selected_model)
                                    prov.temperature = pdata.get("temperature", prov.temperature)
                                    prov.max_tokens = pdata.get("max_tokens", prov.max_tokens)
                                    prov.base_url = pdata.get("base_url", prov.base_url)
                                    prov.timeout_seconds = pdata.get("timeout_seconds", prov.timeout_seconds)
                                    prov.max_retries = pdata.get("max_retries", prov.max_retries)
                                    prov.version = ver

                                if credential_revoked:
                                    self._credential_revoked.add(pid)
                                    self._secrets.pop(pid, None)
                                    if pid in self._providers:
                                        self._providers[pid].has_credential = False
                                        self._providers[pid].health_status = ProviderHealthStatus.NOT_CONFIGURED
                                elif enc_cred:
                                    self._credential_revoked.discard(pid)
                                    try:
                                        decrypted = decrypt_at_rest(enc_cred)
                                        if decrypted:
                                            self._secrets[pid] = decrypted
                                            if pid in self._providers:
                                                self._providers[pid].has_credential = True
                                    except Exception:
                                        logger.error("Failed to decrypt credentials for %s from db.", pid)

                        # Load audits
                        cur.execute("SELECT timestamp, author, action, provider_id, version, validation_result, sanitized_metadata FROM dsp_runtime_provider_audits ORDER BY timestamp ASC LIMIT 100")
                        audit_rows = cur.fetchall()
                        for tstamp, author, action, pid, ver, val_res, meta in audit_rows:
                            self._audit_log.append(
                                AuditRecord(
                                    timestamp=tstamp.isoformat() if hasattr(tstamp, "isoformat") else str(tstamp),
                                    author=author,
                                    action=action,
                                    provider_id=pid,
                                    version=ver,
                                    validation_result=val_res,
                                    sanitized_metadata=meta or {},
                                )
                            )
                return
            except Exception as exc:
                logger.error("Failed loading configuration from PostgreSQL: %s; trying disk", exc)

        # Local fallback is forbidden in production; PostgreSQL initialization/read failures
        # must not silently change the persistence backend.
        if any(os.environ.get(name, "").strip().lower() in {"production", "prod"}
               for name in ("DSP_ENV", "APP_ENV", "ENVIRONMENT", "NODE_ENV", "ENV")):
            raise RuntimeError("PostgreSQL provider store could not be loaded in production.")
        if not os.path.exists(self._store_path):
            return

        try:
            with open(self._store_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self._lock:
                for pid, pdata in data.get("providers", {}).items():
                    if pid in self._providers:
                        prov = self._providers[pid]
                        prov.is_active = pdata.get("is_active", prov.is_active)
                        prov.selected_model = pdata.get("selected_model", prov.selected_model)
                        prov.temperature = pdata.get("temperature", prov.temperature)
                        prov.max_tokens = pdata.get("max_tokens", prov.max_tokens)
                        prov.base_url = pdata.get("base_url", prov.base_url)
                        prov.timeout_seconds = pdata.get("timeout_seconds", prov.timeout_seconds)
                        prov.max_retries = pdata.get("max_retries", prov.max_retries)
                        prov.version = pdata.get("version", prov.version)

                # Load persisted secrets from encrypted store
                for pid, enc_sec in data.get("credentials", {}).items():
                    if enc_sec and isinstance(enc_sec, str):
                        try:
                            decrypted = decrypt_at_rest(enc_sec)
                            if decrypted:
                                self._secrets[pid] = decrypted
                                if pid in self._providers:
                                    self._providers[pid].has_credential = True
                        except Exception as exc:
                            logger.error("Failed to decrypt stored credential for %s: %s", pid, exc)

                # Apply durable revocation tombstones after environment/disk secrets are loaded.
                for pid in data.get("revoked_credentials", []):
                    self._credential_revoked.add(pid)
                    self._secrets.pop(pid, None)
                    if pid in self._providers:
                        self._providers[pid].has_credential = False
                        self._providers[pid].health_status = ProviderHealthStatus.NOT_CONFIGURED

                # Load audit log
                for a in data.get("audit_log", []):
                    self._audit_log.append(AuditRecord(**a))

                # Load version history
                self._history.update(data.get("history", {}))
        except Exception as e:
            logger.error("Failed to load runtime store from disk: %s", e)

    def _save_to_storage(self, provider_id: str | None = None) -> None:
        """Persist state. PostgreSQL writes are provider-targeted to prevent stale-catalog overwrites."""
        target_ids = [provider_id.lower()] if provider_id else list(self._providers)
        encrypted_credentials = {
            pid: encrypt_at_rest(self._secrets[pid])
            for pid in target_ids
            if self._secrets.get(pid)
        }
        # Local development storage is a complete snapshot, unlike targeted DB writes.
        all_encrypted_credentials = {
            pid: encrypt_at_rest(secret)
            for pid, secret in self._secrets.items()
            if secret and pid not in self._credential_revoked
        }

        if self._postgres_enabled and self._postgres_pool is not None:
            try:
                with self._postgres_pool.connection() as conn:
                    with conn.cursor() as cur:
                        for pid in target_ids:
                            prov = self._providers.get(pid)
                            if prov is None:
                                continue
                            cfg_json = json.dumps(prov.to_public_dict())
                            enc_cred = encrypted_credentials.get(pid)
                            cur.execute(
                                """
                                INSERT INTO dsp_runtime_providers
                                    (provider_id, config_json, encrypted_credential, credential_revoked, version, updated_at)
                                VALUES (%s, %s, %s, %s, %s, NOW())
                                ON CONFLICT (provider_id) DO UPDATE SET
                                    config_json = EXCLUDED.config_json,
                                    encrypted_credential = EXCLUDED.encrypted_credential,
                                    credential_revoked = EXCLUDED.credential_revoked,
                                    version = EXCLUDED.version,
                                    updated_at = NOW();
                                """,
                                (
                                    pid, cfg_json, enc_cred,
                                    pid in self._credential_revoked, prov.version,
                                ),
                            )
            except Exception as exc:
                logger.error("Failed writing provider state to PostgreSQL.")
                if any(os.environ.get(name, "").strip().lower() in {"production", "prod"}
                       for name in ("DSP_ENV", "APP_ENV", "ENVIRONMENT", "NODE_ENV", "ENV")):
                    raise RuntimeError("Required PostgreSQL provider-store write failed.") from exc

        # Local file is only a single-instance development fallback, never a production fallback.
        if any(os.environ.get(name, "").strip().lower() in {"production", "prod"}
               for name in ("DSP_ENV", "APP_ENV", "ENVIRONMENT", "NODE_ENV", "ENV")):
            return
        try:
            providers_data = {}
            for pid, prov in self._providers.items():
                providers_data[pid] = prov.to_public_dict(mask_secret(self._secrets.get(pid)))

            data = {
                "providers": providers_data,
                "credentials": all_encrypted_credentials,
                "revoked_credentials": sorted(self._credential_revoked),
                "history": self._history,
                "audit_log": [a.to_dict() for a in self._audit_log[-100:]],
                "updated_at": self._now_iso(),
            }

            temp_path = f"{self._store_path}.tmp.{os.getpid()}"
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            fd = os.open(temp_path, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, self._store_path)
        except Exception as e:
            logger.error("Failed to save runtime store to encrypted disk file: %s", e)

    _save_to_disk = _save_to_storage

    # -----------------------------------------------------------------------
    # Public Safe Inspection
    # -----------------------------------------------------------------------

    def _refresh_from_storage_if_stale(self, *, force: bool = False) -> None:
        """Refresh shared PostgreSQL state periodically so workers observe other workers' updates."""
        if not self._postgres_enabled or self._postgres_pool is None:
            return
        now = time.monotonic()
        if not force and now - self._last_refresh_monotonic < self._refresh_interval_seconds:
            return
        with self._lock:
            now = time.monotonic()
            if not force and now - self._last_refresh_monotonic < self._refresh_interval_seconds:
                return
            try:
                with self._postgres_pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT provider_id, config_json, encrypted_credential, version, "
                            "credential_revoked FROM dsp_runtime_providers"
                        )
                        rows = cur.fetchall()
                        cur.execute(
                            "SELECT timestamp, author, action, provider_id, version, "
                            "validation_result, sanitized_metadata FROM dsp_runtime_provider_audits "
                            "ORDER BY timestamp DESC LIMIT 100"
                        )
                        audit_rows = cur.fetchall()
                self._audit_log = [
                    AuditRecord(
                        timestamp=tstamp.isoformat() if hasattr(tstamp, "isoformat") else str(tstamp),
                        author=author, action=action, provider_id=pid, version=ver,
                        validation_result=result, sanitized_metadata=metadata or {},
                    )
                    for tstamp, author, action, pid, ver, result, metadata in reversed(audit_rows)
                ]
                for pid, cfg_json, enc_cred, version, revoked in rows:
                    if pid not in self._providers:
                        continue
                    data = json.loads(cfg_json)
                    prov = self._providers[pid]
                    prov.is_active = data.get("is_active", prov.is_active)
                    prov.selected_model = data.get("selected_model", prov.selected_model)
                    prov.temperature = data.get("temperature", prov.temperature)
                    prov.max_tokens = data.get("max_tokens", prov.max_tokens)
                    prov.base_url = data.get("base_url", prov.base_url)
                    prov.timeout_seconds = data.get("timeout_seconds", prov.timeout_seconds)
                    prov.max_retries = data.get("max_retries", prov.max_retries)
                    prov.version = version
                    if revoked:
                        self._credential_revoked.add(pid)
                        self._secrets.pop(pid, None)
                        prov.has_credential = False
                        prov.health_status = ProviderHealthStatus.NOT_CONFIGURED
                    elif enc_cred:
                        secret = decrypt_at_rest(enc_cred)
                        self._credential_revoked.discard(pid)
                        self._secrets[pid] = secret
                        prov.has_credential = True
                self._last_refresh_monotonic = now
            except Exception as exc:
                logger.error("Runtime provider PostgreSQL refresh failed.")
                if any(os.environ.get(name, "").strip().lower() in {"production", "prod"}
                       for name in ("DSP_ENV", "APP_ENV", "ENVIRONMENT", "NODE_ENV", "ENV")):
                    raise RuntimeError("Required PostgreSQL provider-store refresh failed.") from exc

    def get_provider(self, provider_id: str) -> dict[str, Any] | None:
        self._refresh_from_storage_if_stale()
        with self._lock:
            pid = provider_id.lower()
            p = self._providers.get(pid)
            if not p:
                return None
            masked = mask_secret(self._secrets.get(pid))
            return p.to_public_dict(masked)

    def get_provider_config(self, provider_id: str) -> ProviderConfig | None:
        self._refresh_from_storage_if_stale()
        with self._lock:
            p = self._providers.get(provider_id.lower())
            return copy.deepcopy(p) if p else None

    def list_providers(self, category: str | None = None) -> list[dict[str, Any]]:
        self._refresh_from_storage_if_stale()
        with self._lock:
            result = []
            for p in self._providers.values():
                if category is None or p.category == category:
                    masked = mask_secret(self._secrets.get(p.provider_id))
                    result.append(p.to_public_dict(masked))
            return sorted(result, key=lambda x: (x["category"] != "ai", x["provider_id"]))

    def get_credential(self, provider_id: str) -> str | None:
        """Internal retrieval of active decrypted credential for execution."""
        self._refresh_from_storage_if_stale()
        with self._lock:
            return self._secrets.get(provider_id.lower())

    # -----------------------------------------------------------------------
    # Credential Replacement, Validation & Revocation
    # -----------------------------------------------------------------------

    def replace_credential(
        self,
        provider_id: str,
        new_secret: str,
        *,
        author: str = "administrator",
        validate: bool = True,
        model: str | None = None,
    ) -> ProviderConfig:
        """Atomically replace credential with optional validation.

        If validation fails, the previous working credential is preserved.
        """
        clean_secret = new_secret.strip()
        if not clean_secret:
            raise ValueError("Secret credential cannot be empty.")

        pid = provider_id.lower()
        with self._lock:
            prov = self._providers.get(pid)
            if not prov:
                raise KeyError(f"Provider '{provider_id}' is not registered.")

            prev_snapshot = prov.to_public_dict(mask_secret(self._secrets.get(pid)))
            self._history.setdefault(pid, []).append(prev_snapshot)

            # Validation step
            if validate:
                test_model = model or prov.selected_model
                success, latency_ms, error_msg = test_provider_connection(
                    pid,
                    clean_secret,
                    model=test_model,
                    base_url=prov.base_url,
                    timeout=prov.timeout_seconds,
                )
                if not success:
                    diag = classify_provider_error(error_msg, provider_id=pid)
                    # Preserve existing credential!
                    prov.last_test_timestamp = self._now_iso()
                    prov.last_test_latency_ms = latency_ms
                    prov.last_test_success = False
                    prov.last_error_sanitized = diag.sanitized_reason
                    prov.recommended_action = diag.recommended_action

                    self._record_audit(
                        author=author,
                        action="credential_replace_failed",
                        provider_id=pid,
                        version=prov.version,
                        validation_result="FAILED",
                        metadata={"error": diag.sanitized_reason},
                    )
                    raise ValidationFailedError(
                        f"Validation failed for {prov.display_name}: {diag.sanitized_reason}",
                        diagnostics=diag,
                    )

            # Store validated secret
            self._secrets[pid] = clean_secret
            self._credential_revoked.discard(pid)
            prov.has_credential = True
            prov.version += 1
            if validate:
                prov.health_status = ProviderHealthStatus.HEALTHY
                prov.last_test_timestamp = self._now_iso()
                prov.last_test_success = True
                prov.last_error_sanitized = None
                prov.recommended_action = None
            else:
                prov.health_status = ProviderHealthStatus.CONFIGURED_UNTESTED

            self._record_audit(
                author=author,
                action="credential_replace",
                provider_id=pid,
                version=prov.version,
                validation_result="VALIDATED" if validate else "SKIPPED",
                metadata={"status": prov.health_status.value},
            )
            self._save_to_storage(pid)
            return copy.deepcopy(prov)

    def revoke_credential(
        self,
        provider_id: str,
        *,
        author: str = "administrator",
    ) -> ProviderConfig:
        """Revoke / delete stored credential for a provider."""
        pid = provider_id.lower()
        with self._lock:
            prov = self._providers.get(pid)
            if not prov:
                raise KeyError(f"Provider '{provider_id}' is not registered.")

            prev_snapshot = prov.to_public_dict(mask_secret(self._secrets.get(pid)))
            self._history.setdefault(pid, []).append(prev_snapshot)

            # Keep a durable tombstone so environment variables cannot reactivate this key.
            self._secrets.pop(pid, None)
            self._credential_revoked.add(pid)
            prov.has_credential = False
            prov.health_status = ProviderHealthStatus.NOT_CONFIGURED
            prov.last_test_timestamp = None
            prov.last_test_latency_ms = None
            prov.last_test_success = None
            prov.last_error_sanitized = None
            prov.recommended_action = None
            prov.version += 1

            self._record_audit(
                author=author,
                action="credential_revoked",
                provider_id=pid,
                version=prov.version,
                validation_result="REVOKED",
                metadata={"reason": "administrator_revocation"},
            )
            self._save_to_storage()
            return copy.deepcopy(prov)

    # -----------------------------------------------------------------------
    # Non-Secret Configuration Mutation
    # -----------------------------------------------------------------------

    def update_config(
        self,
        provider_id: str,
        *,
        author: str = "administrator",
        selected_model: str | None = None,
        is_active: bool | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ProviderConfig:
        """Update provider configuration parameters."""
        pid = provider_id.lower()
        with self._lock:
            prov = self._providers.get(pid)
            if not prov:
                raise KeyError(f"Provider '{provider_id}' is not registered.")

            prev_snapshot = prov.to_public_dict(mask_secret(self._secrets.get(pid)))
            self._history.setdefault(pid, []).append(prev_snapshot)

            changed: dict[str, Any] = {}
            if selected_model is not None:
                prov.selected_model = selected_model
                changed["selected_model"] = selected_model
            if is_active is not None:
                prov.is_active = is_active
                changed["is_active"] = is_active
            if base_url is not None:
                low = base_url.lower()
                if "169.254.169.254" in low or "metadata.google.internal" in low:
                    raise ValueError("Target URL is blocked by SSRF protection policy.")
                prov.base_url = base_url
                changed["base_url"] = base_url
            if timeout_seconds is not None:
                prov.timeout_seconds = max(1.0, min(300.0, float(timeout_seconds)))
                changed["timeout_seconds"] = prov.timeout_seconds
            if temperature is not None:
                prov.temperature = max(0.0, min(2.0, float(temperature)))
                changed["temperature"] = prov.temperature
            if max_tokens is not None:
                prov.max_tokens = max(100, min(32768, int(max_tokens)))
                changed["max_tokens"] = prov.max_tokens

            prov.version += 1
            self._record_audit(
                author=author,
                action="config_update",
                provider_id=pid,
                version=prov.version,
                validation_result="OK",
                metadata=changed,
            )
            self._save_to_storage()
            return copy.deepcopy(prov)

    # -----------------------------------------------------------------------
    # Connection Testing
    # -----------------------------------------------------------------------

    def test_connection(
        self,
        provider_id: str,
        candidate_secret: str | None = None,
        candidate_model: str | None = None,
    ) -> dict[str, Any]:
        """Test connection using currently active or supplied candidate credentials."""
        pid = provider_id.lower()
        with self._lock:
            prov = self._providers.get(pid)
            if not prov:
                raise ProviderNotFoundError(f"Provider '{provider_id}' is not registered.")
            secret = candidate_secret if candidate_secret is not None else self._secrets.get(pid)

        if not secret:
            return {
                "ok": False,
                "latency_ms": 0.0,
                "status": ProviderHealthStatus.NOT_CONFIGURED.value,
                "sanitized_error": "No credential configured.",
                "recommended_action": f"Save an API key for {prov.display_name}.",
            }

        target_model = candidate_model if candidate_model is not None else prov.selected_model
        success, latency_ms, error_msg = test_provider_connection(
            pid,
            secret,
            model=target_model,
            base_url=prov.base_url,
            timeout=prov.timeout_seconds,
        )

        diag = classify_provider_error(error_msg, provider_id=pid) if not success else None

        if candidate_secret is None:
            with self._lock:
                prov.last_test_timestamp = self._now_iso()
                prov.last_test_latency_ms = latency_ms
                prov.last_test_success = success
                if success:
                    prov.health_status = ProviderHealthStatus.HEALTHY
                    prov.last_error_sanitized = None
                    prov.recommended_action = None
                else:
                    prov.health_status = diag.status if diag else ProviderHealthStatus.CONFIG_ERROR
                    prov.last_error_sanitized = diag.sanitized_reason if diag else None
                    prov.recommended_action = diag.recommended_action if diag else None

            self._save_to_storage()
            status_val = prov.health_status.value
            err_sanitized = prov.last_error_sanitized
            rec_act = prov.recommended_action
            tstamp = prov.last_test_timestamp
        else:
            status_val = (
                ProviderHealthStatus.HEALTHY.value
                if success
                else (diag.status.value if diag else ProviderHealthStatus.CONFIG_ERROR.value)
            )
            err_sanitized = diag.sanitized_reason if diag else None
            rec_act = diag.recommended_action if diag else None
            tstamp = self._now_iso()

        return {
            "ok": success,
            "latency_ms": round(latency_ms, 2),
            "status": status_val,
            "sanitized_error": err_sanitized,
            "recommended_action": rec_act,
            "timestamp": tstamp,
        }

    def record_successful_use(self, provider_id: str) -> None:
        """Record timestamp of successful live request."""
        pid = provider_id.lower()
        with self._lock:
            prov = self._providers.get(pid)
            if prov:
                prov.last_successful_use = self._now_iso()
                prov.health_status = ProviderHealthStatus.HEALTHY

    # -----------------------------------------------------------------------
    # Rollback & Audit
    # -----------------------------------------------------------------------

    def update_model(
        self, provider_id: str, model: str, *, author: str = "administrator"
    ) -> ProviderConfig:
        return self.update_config(provider_id, selected_model=model, author=author)

    def set_active_status(
        self, provider_id: str, is_active: bool, *, author: str = "administrator"
    ) -> ProviderConfig:
        return self.update_config(provider_id, is_active=is_active, author=author)

    def rollback(
        self, provider_id: str, target_version: int | None = None, *, author: str = "administrator"
    ) -> ProviderConfig:
        """Rollback configuration to a previous version."""
        pid = provider_id.lower()
        with self._lock:
            prov = self._providers.get(pid)
            if not prov:
                raise KeyError(f"Provider '{provider_id}' is not registered.")

            snapshots = self._history.get(pid, [])
            if target_version is None:
                if not snapshots:
                    raise ValueError(f"No history available to rollback provider '{provider_id}'.")
                match = snapshots[-1]
                target_version = match.get("version", 1)
            else:
                match = next((s for s in snapshots if s.get("version") == target_version), None)
                if not match:
                    raise ValueError(
                        f"Version {target_version} not found in history for {provider_id}."
                    )

            prov.selected_model = match.get("selected_model", prov.selected_model)
            prov.is_active = match.get("is_active", prov.is_active)
            prov.base_url = match.get("base_url", prov.base_url)
            prov.timeout_seconds = match.get("timeout_seconds", prov.timeout_seconds)
            prov.temperature = match.get("temperature", prov.temperature)
            prov.max_tokens = match.get("max_tokens", prov.max_tokens)
            prov.version += 1

            self._record_audit(
                author=author,
                action="rollback",
                provider_id=pid,
                version=prov.version,
                validation_result="OK",
                metadata={"target_version": target_version},
            )
            self._save_to_storage()
            return copy.deepcopy(prov)

    def _record_audit(
        self,
        *,
        author: str,
        action: str,
        provider_id: str,
        version: int,
        validation_result: str,
        metadata: dict[str, Any],
    ) -> None:
        rec = AuditRecord(
            timestamp=self._now_iso(),
            author=author,
            action=action,
            provider_id=provider_id,
            version=version,
            validation_result=validation_result,
            sanitized_metadata=metadata,
        )
        self._audit_log.append(rec)
        if self._postgres_enabled and self._postgres_pool is not None:
            try:
                with self._postgres_pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO dsp_runtime_provider_audits
                            (author, action, provider_id, version, validation_result, sanitized_metadata)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                author,
                                action,
                                provider_id,
                                version,
                                validation_result,
                                json.dumps(metadata),
                            ),
                        )
                    conn.commit()
            except Exception as exc:
                logger.error("Failed recording audit log to PostgreSQL: %s", exc)

    def get_audit_log(
        self, provider_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        self._refresh_from_storage_if_stale()
        with self._lock:
            logs = self._audit_log
            if provider_id:
                logs = [l for l in logs if l.provider_id == provider_id.lower()]
            return [l.to_dict() for l in reversed(logs[-limit:])]


# Singleton instance
_GLOBAL_STORE: RuntimeProviderStore | None = None
_STORE_LOCK = threading.Lock()


def get_runtime_store() -> RuntimeProviderStore:
    """Access singleton runtime store."""
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        with _STORE_LOCK:
            if _GLOBAL_STORE is None:
                _GLOBAL_STORE = RuntimeProviderStore()
    return _GLOBAL_STORE
