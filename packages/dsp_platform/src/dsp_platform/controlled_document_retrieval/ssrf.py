"""SSRF-safe URL validation for AI-discovered document locators.

Does not fetch. Rejects private, loopback, link-local, metadata, and
non-HTTPS locators before any network call.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Sequence
from urllib.parse import urlparse

from dsp_platform.external_evidence import ExternalEvidenceValidationError
from dsp_platform.primary_source_retrieval import validate_document_locator

__all__ = [
    "ALLOWED_HTTPS_PORT",
    "BLOCKED_HOSTNAMES",
    "MAX_LOCATOR_CHARS",
    "assert_public_https_locator",
    "hosts_equivalent",
    "resolve_public_addresses",
]

ALLOWED_HTTPS_PORT = 443
MAX_LOCATOR_CHARS = 2048
BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "internal",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "metadata.internal",
        "169.254.169.254",
        "0.0.0.0",
        "::",
        "::1",
        "[::]",
        "[::1]",
    }
)
_BLOCKED_HOST_SUFFIXES = (
    ".internal",
    ".local",
    ".localhost",
    ".corp",
    ".lan",
    ".home",
    ".invalid",
)

AddrInfo = tuple[object, ...]
Resolver = Callable[..., Sequence[AddrInfo]]


def hosts_equivalent(left: str, right: str) -> bool:
    """True when hostnames refer to the same site, ignoring a www. prefix."""
    return _norm_host(left) == _norm_host(right)


def assert_public_https_locator(locator: str) -> str:
    """Return the validated HTTPS hostname. Does not fetch."""
    validate_document_locator(locator)
    if len(locator) > MAX_LOCATOR_CHARS:
        raise ExternalEvidenceValidationError(
            "document locator rejected: URL exceeds size limit"
        )
    _reject_control_characters(locator)
    parsed = urlparse(locator)
    if parsed.scheme != "https":
        raise ExternalEvidenceValidationError(
            "document locator rejected: only https URLs may be fetched"
        )
    if parsed.fragment:
        raise ExternalEvidenceValidationError(
            "document locator rejected: fragments are not allowed"
        )
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise ExternalEvidenceValidationError(
            "document locator rejected: missing host"
        )
    if host in BLOCKED_HOSTNAMES or _has_blocked_suffix(host):
        raise ExternalEvidenceValidationError(
            "document locator rejected: blocked hostname"
        )
    port = parsed.port
    if port is not None and port != ALLOWED_HTTPS_PORT:
        raise ExternalEvidenceValidationError(
            "document locator rejected: only HTTPS port 443 is allowed"
        )
    _reject_literal_blocked_ip(host)
    return host


def resolve_public_addresses(
    hostname: str,
    *,
    resolver: Resolver | None = None,
) -> tuple[str, ...]:
    """Resolve hostname and reject any non-public address."""
    host = hostname.strip().lower()
    if not host:
        raise ExternalEvidenceValidationError(
            "document locator rejected: missing host"
        )
    literal = _try_ip(host)
    if literal is not None:
        _reject_blocked_ip(literal)
        return (str(literal),)
    lookup = resolver or socket.getaddrinfo
    try:
        records = lookup(host, ALLOWED_HTTPS_PORT, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ExternalEvidenceValidationError(
            "document locator rejected: hostname could not be resolved"
        ) from exc
    addresses: list[str] = []
    seen: set[str] = set()
    for record in records:
        sockaddr = record[4] if len(record) > 4 else ()
        raw = sockaddr[0] if sockaddr else None
        if not isinstance(raw, str) or not raw:
            continue
        ip = _try_ip(raw)
        if ip is None:
            continue
        _reject_blocked_ip(ip)
        text = str(ip)
        if text not in seen:
            seen.add(text)
            addresses.append(text)
    if not addresses:
        raise ExternalEvidenceValidationError(
            "document locator rejected: no public addresses resolved"
        )
    return tuple(addresses)


def _reject_literal_blocked_ip(host: str) -> None:
    ip = _try_ip(host)
    if ip is not None:
        _reject_blocked_ip(ip)


def _reject_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if ip.version == 6 and ip.ipv4_mapped is not None:
        _reject_blocked_ip(ip.ipv4_mapped)
        return
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    ):
        raise ExternalEvidenceValidationError(
            "document locator rejected: private or non-public address"
        )


def _try_ip(raw: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        return None


def _reject_control_characters(locator: str) -> None:
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in locator):
        raise ExternalEvidenceValidationError(
            "document locator rejected: control characters are not allowed"
        )


def _has_blocked_suffix(host: str) -> bool:
    return any(
        host == suffix[1:] or host.endswith(suffix)
        for suffix in _BLOCKED_HOST_SUFFIXES
    )


def _norm_host(host: str) -> str:
    value = (host or "").strip().lower().rstrip(".")
    if value.startswith("www."):
        return value[4:]
    return value
