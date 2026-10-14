"""Centralized Provider Connection Testing Service.

Performs lightweight, safe connectivity tests against upstream APIs without
logging credentials or leaking secrets into error messages.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from llm_adapters.provider_health import (
    classify_provider_error,
)

logger = logging.getLogger(__name__)

# SSRF Blocklist for custom / local endpoints
_SSRF_BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.azure.internal",
    "100.100.100.200",  # Alibaba Cloud IMDS
}


def _validate_safe_url(url: str, allow_local: bool = True) -> str:
    """Ensure URL is http/https and not pointing to cloud metadata endpoints."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid URL scheme: must be http or https.")
    hostname = (parsed.hostname or "").lower()
    if hostname in _SSRF_BLOCKED_HOSTS:
        raise ValueError("Connection to cloud metadata service is prohibited by SSRF policy.")
    if not allow_local and hostname in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Connection to localhost is prohibited in this mode.")
    return url


def test_provider_connection(
    provider_id: str,
    credential: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 8.0,
) -> tuple[bool, float, str | None]:
    """Test connection to upstream provider.

    Returns:
        (success, latency_ms, error_message)
    """
    secret = (credential or "").strip()
    if not secret:
        return False, 0.0, "Missing credential or access token."

    start_time = time.monotonic()
    pid = provider_id.lower()

    try:
        if pid == "gemini":
            # Gemini models list probe
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={urllib.parse.quote(secret)}"
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "dsp-ai-indicator/1.0"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                body = resp.read()
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "openai":
            # OpenAI models list probe
            url = "https://api.openai.com/v1/models"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "anthropic":
            # Anthropic test probe (ping with 1 token)
            url = "https://api.anthropic.com/v1/messages"
            test_model = model or "claude-3-haiku-20240307"
            payload = json.dumps({
                "model": test_model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "x-api-key": secret,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "deepseek":
            url = "https://api.deepseek.com/models"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "openrouter":
            # OpenRouter key auth probe
            url = "https://openrouter.ai/api/v1/auth/key"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "groq":
            url = "https://api.groq.com/openai/v1/models"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "mistral":
            url = "https://api.mistral.ai/v1/models"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "xai":
            url = "https://api.x.ai/v1/models"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid in ("together", "fireworks", "cohere", "perplexity"):
            endpoints = {
                "together": "https://api.together.xyz/v1/models",
                "fireworks": "https://api.fireworks.ai/inference/v1/models",
                "cohere": "https://api.cohere.com/v2/models",
                "perplexity": "https://api.perplexity.ai/chat/completions",
            }
            target_url = endpoints[pid]
            if pid == "perplexity":
                payload = json.dumps({
                    "model": model or "sonar",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                }).encode("utf-8")
                req = urllib.request.Request(
                    target_url,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {secret}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    method="POST",
                )
            else:
                req = urllib.request.Request(
                    target_url,
                    headers={
                        "Authorization": f"Bearer {secret}",
                        "Accept": "application/json",
                    },
                    method="GET",
                )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "ollama":
            endpoint = _validate_safe_url(base_url or "http://localhost:11434")
            url = f"{endpoint.rstrip('/')}/api/tags"
            req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        elif pid == "upstox":
            # Upstox profile or market-quote probe
            url = "https://api.upstox.com/v3/user/profile"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Accept": "application/json",
                    "User-Agent": "dsp-ai-indicator/1.0",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                latency_ms = (time.monotonic() - start_time) * 1000.0
                if 200 <= status < 300:
                    return True, latency_ms, None
                return False, latency_ms, f"HTTP {status}"

        else:
            # Generic endpoint check if base_url is provided
            if base_url:
                endpoint = _validate_safe_url(base_url)
                req = urllib.request.Request(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {secret}",
                        "Accept": "application/json",
                    },
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status = resp.status
                    latency_ms = (time.monotonic() - start_time) * 1000.0
                    return 200 <= status < 300, latency_ms, None
            return False, 0.0, f"Unsupported provider: {provider_id}"

    except urllib.error.HTTPError as exc:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        # Parse error message safely without leaking auth
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            err_body = exc.reason
        diag = classify_provider_error(err_body, status_code=exc.code, provider_id=pid)
        return False, latency_ms, diag.sanitized_reason
    except urllib.error.URLError as exc:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        diag = classify_provider_error(str(exc.reason), provider_id=pid)
        return False, latency_ms, diag.sanitized_reason
    except Exception as exc:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        diag = classify_provider_error(str(exc), provider_id=pid)
        return False, latency_ms, diag.sanitized_reason


test_connection = test_provider_connection
