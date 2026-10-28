"""SSRF defense, destination validation, and secure document retrieval."""

from __future__ import annotations

import hashlib
import ipaddress
import socket
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlparse

from dsp_platform.research_retrieval.models import FetchedDocument, utc_now_iso

__all__ = [
    "DnsResolutionError",
    "DnsResolver",
    "SafeHttpFetcher",
    "UrlSafetyError",
    "UrlSafetyPolicy",
    "is_safe_ip_address",
    "validate_url_safety",
]


class UrlSafetyError(ValueError):
    """Raised when a URL violates safety, scheme, or destination policies."""


class DnsResolutionError(UrlSafetyError):
    """Raised when DNS resolution fails or resolves to an unsafe address."""


@dataclass(frozen=True, slots=True)
class UrlSafetyPolicy:
    """Configurable boundaries for outbound network retrieval."""

    allowed_schemes: frozenset[str] = frozenset({"https"})
    allowed_ports: frozenset[int] = frozenset({443})
    max_redirects: int = 3
    timeout_seconds: float = 10.0
    max_body_bytes: int = 5_000_000  # 5 MB
    allowed_content_types: frozenset[str] = frozenset(
        {
            "text/html",
            "text/plain",
            "application/pdf",
            "application/json",
            "application/xml",
            "text/xml",
        }
    )


# Explicit cloud metadata and forbidden hostnames
FORBIDDEN_HOSTNAMES = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata",
        "instance-data",
        "localhost",
        "local",
        "loopback",
    }
)


def is_safe_ip_address(ip_str: str) -> tuple[bool, str]:
    """Validate that an IP string does not belong to private/loopback/metadata ranges."""
    try:
        ip = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False, "invalid_ip_format"

    # Normalize IPv4-mapped IPv6 (::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    if ip.is_loopback:
        return False, "loopback_blocked"
    if ip.is_private:
        return False, "private_network_blocked"
    if ip.is_link_local:
        return False, "link_local_blocked"
    if ip.is_multicast:
        return False, "multicast_blocked"
    if ip.is_unspecified:
        return False, "unspecified_address_blocked"
    if ip.is_reserved:
        return False, "reserved_address_blocked"

    if isinstance(ip, ipaddress.IPv4Address):
        # AWS / GCP / Azure metadata
        if ip == ipaddress.IPv4Address("169.254.169.254"):
            return False, "cloud_metadata_blocked"
        # Alibaba Cloud metadata
        if ip == ipaddress.IPv4Address("100.100.100.200"):
            return False, "cloud_metadata_blocked"
        # Carrier-grade NAT (RFC 6598)
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False, "cgnat_blocked"
        # Benchmark network (RFC 2544)
        if ip in ipaddress.IPv4Network("198.18.0.0/15"):
            return False, "benchmark_network_blocked"
        # IANA Special purpose (RFC 5736)
        if ip in ipaddress.IPv4Network("192.0.0.0/24"):
            return False, "iana_special_blocked"
        # Future use / Class E
        if ip in ipaddress.IPv4Network("240.0.0.0/4"):
            return False, "future_reserved_blocked"

    if isinstance(ip, ipaddress.IPv6Address):
        # Unique local address (fc00::/7)
        if ip in ipaddress.IPv6Network("fc00::/7"):
            return False, "unique_local_blocked"
        # Discard prefix (100::/64)
        if ip in ipaddress.IPv6Network("100::/64"):
            return False, "discard_prefix_blocked"
        # Documentation prefix (2001:db8::/32)
        if ip in ipaddress.IPv6Network("2001:db8::/32"):
            return False, "documentation_prefix_blocked"

    return True, "safe"


def validate_url_safety(url: str, policy: UrlSafetyPolicy | None = None) -> None:
    """Validate URL scheme, authority, credentials, and port."""
    pol = policy or UrlSafetyPolicy()
    if not url or not isinstance(url, str):
        raise UrlSafetyError("URL must be a non-empty string")

    if any(ch in url for ch in "\r\n\t\0"):
        raise UrlSafetyError("URL contains illegal control characters")

    stripped = url.strip()

    try:
        parsed = urlparse(stripped)
    except Exception as exc:
        raise UrlSafetyError(f"Malformed URL: {exc}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in pol.allowed_schemes:
        raise UrlSafetyError(f"Prohibited URL scheme '{scheme}'; only {sorted(pol.allowed_schemes)} allowed")

    if parsed.username or parsed.password:
        raise UrlSafetyError("Embedded user credentials in URLs are prohibited")

    host = parsed.hostname
    if not host:
        raise UrlSafetyError("URL must include a valid hostname")

    host_lower = host.lower()
    if host_lower in FORBIDDEN_HOSTNAMES or host_lower.endswith(".internal"):
        raise UrlSafetyError(f"Hostname '{host}' is prohibited as an internal/metadata address")

    port = parsed.port
    if port is not None and port not in pol.allowed_ports:
        raise UrlSafetyError(f"Port {port} is not in allowed secure ports {sorted(pol.allowed_ports)}")

    # If host is an IP literal, validate it directly
    is_ip = False
    try:
        ipaddress.ip_address(host_lower)
        is_ip = True
    except ValueError:
        pass

    if is_ip:
        safe, reason = is_safe_ip_address(host_lower)
        if not safe:
            raise UrlSafetyError(f"Destination IP '{host_lower}' blocked: {reason}")
    else:
        # Check alternative IPv4 representations (integer, octal, hex, short-form)
        try:
            raw_ip = socket.inet_aton(host_lower)
            canonical_ip = socket.inet_ntoa(raw_ip)
            safe, reason = is_safe_ip_address(canonical_ip)
            if not safe:
                raise UrlSafetyError(
                    f"Destination alternate IP '{host_lower}' ({canonical_ip}) blocked: {reason}"
                )
        except UrlSafetyError:
            raise
        except OSError:
            pass


class DnsResolver(Protocol):
    """Protocol for resolving hostnames to IP addresses."""

    def resolve(self, hostname: str) -> tuple[str, ...]:
        ...


class SystemDnsResolver:
    """Default DNS resolver using standard library getaddrinfo."""

    def resolve(self, hostname: str) -> tuple[str, ...]:
        try:
            results = socket.getaddrinfo(hostname, 443, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
            ips = {res[4][0] for res in results}
            if not ips:
                raise DnsResolutionError(f"No IP addresses resolved for hostname '{hostname}'")
            return tuple(sorted(ips))
        except socket.gaierror as exc:
            raise DnsResolutionError(f"DNS resolution failed for '{hostname}': {exc}") from exc


class SafeHttpFetcher(Protocol):
    """Protocol for secure document fetching."""

    def fetch(self, url: str) -> FetchedDocument:
        ...


class DefaultSafeHttpFetcher:
    """SSRF-hardened document fetcher with DNS-rebinding protection and redirect interception."""

    def __init__(
        self,
        policy: UrlSafetyPolicy | None = None,
        dns_resolver: DnsResolver | None = None,
        socket_connector: Callable[[str, int, float], socket.socket] | None = None,
    ) -> None:
        self.policy = policy or UrlSafetyPolicy()
        self.dns_resolver = dns_resolver or SystemDnsResolver()
        self._socket_connector = socket_connector or socket.create_connection

    def _validate_and_resolve_destination(self, url: str) -> tuple[str, str]:
        """Validate URL safety and resolve host to a validated safe IP."""
        validate_url_safety(url, self.policy)
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Resolve all IPs and ensure every single one is safe (fail-closed)
        resolved_ips = self.dns_resolver.resolve(hostname)
        for ip_addr in resolved_ips:
            safe, reason = is_safe_ip_address(ip_addr)
            if not safe:
                raise DnsResolutionError(
                    f"DNS resolution for '{hostname}' returned unsafe address '{ip_addr}': {reason}"
                )

        # Pin the first resolved safe IP to prevent DNS rebinding TOCTOU
        return hostname, resolved_ips[0]

    def fetch(self, url: str) -> FetchedDocument:
        """Fetch document following redirects manually with safety re-checks at each hop."""
        current_url = url
        redirect_chain: list[str] = []
        hops = 0

        while True:
            hostname, target_ip = self._validate_and_resolve_destination(current_url)
            parsed = urlparse(current_url)
            port = parsed.port or 443
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"

            # Prepare TLS context with strict certificate and SNI validation
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = True
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED

            raw_resp = self._execute_request(
                target_ip=target_ip,
                hostname=hostname,
                port=port,
                path=path,
                ssl_ctx=ssl_ctx,
            )

            status_code, headers, body_bytes = raw_resp

            # Handle Redirects
            if status_code in {301, 302, 303, 307, 308}:
                hops += 1
                if hops > self.policy.max_redirects:
                    raise UrlSafetyError(f"Exceeded max redirects ({self.policy.max_redirects})")

                location = headers.get("location")
                if not location:
                    raise UrlSafetyError(f"Redirect status {status_code} missing Location header")

                next_url = urljoin(current_url, location)
                redirect_chain.append(current_url)

                # Check for redirect loops
                if next_url in redirect_chain:
                    raise UrlSafetyError(f"Redirect loop detected targeting '{next_url}'")

                # Verify new scheme is HTTPS (prevent downgrade to HTTP)
                if not next_url.lower().startswith("https://"):
                    raise UrlSafetyError(f"Prohibited protocol downgrade in redirect to '{next_url}'")

                current_url = next_url
                continue

            # Non-redirect response
            content_type = headers.get("content-type", "application/octet-stream").split(";")[0].strip().lower()
            if self.policy.allowed_content_types and content_type not in self.policy.allowed_content_types:
                raise UrlSafetyError(
                    f"Prohibited content-type '{content_type}'; allowed: {sorted(self.policy.allowed_content_types)}"
                )

            text_content = body_bytes.decode("utf-8", errors="replace")
            content_hash = hashlib.sha256(body_bytes).hexdigest()

            return FetchedDocument(
                url=url,
                final_url=current_url,
                status_code=status_code,
                content_type=content_type,
                text_content=text_content,
                content_hash=content_hash,
                fetched_at=utc_now_iso(),
                redirect_chain=tuple(redirect_chain),
                headers=headers,
            )

    def _execute_request(
        self,
        target_ip: str,
        hostname: str,
        port: int,
        path: str,
        ssl_ctx: ssl.SSLContext,
    ) -> tuple[int, dict[str, str], bytes]:
        """Perform raw HTTPS request connected directly to pinned target IP with SNI hostname."""
        # Connecting to the pinned IP prevents DNS rebinding
        plain_sock = self._socket_connector(target_ip, port, self.policy.timeout_seconds)
        plain_sock.settimeout(self.policy.timeout_seconds)
        try:
            tls_sock = ssl_ctx.wrap_socket(plain_sock, server_hostname=hostname)
        except Exception:
            plain_sock.close()
            raise

        try:
            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {hostname}\r\n"
                f"User-Agent: DSP-AI-Indicator/1.0 (ResearchEvidenceFetcher)\r\n"
                f"Accept: {','.join(self.policy.allowed_content_types)}\r\n"
                f"Connection: close\r\n\r\n"
            )
            tls_sock.sendall(req.encode("utf-8"))

            response_data = bytearray()
            while True:
                chunk = tls_sock.recv(16384)
                if not chunk:
                    break
                response_data.extend(chunk)
                if len(response_data) > self.policy.max_body_bytes:
                    raise UrlSafetyError(f"Response exceeded maximum size of {self.policy.max_body_bytes} bytes")
        finally:
            tls_sock.close()

        # Parse HTTP response
        header_end = response_data.find(b"\r\n\r\n")
        if header_end == -1:
            raise UrlSafetyError("Malformed HTTP response: headers terminator not found")

        header_bytes = response_data[:header_end]
        body_bytes = bytes(response_data[header_end + 4 :])

        header_lines = header_bytes.decode("iso-8859-1", errors="replace").split("\r\n")
        if not header_lines:
            raise UrlSafetyError("Empty HTTP response headers")

        status_line = header_lines[0].split()
        if len(status_line) < 2:
            raise UrlSafetyError(f"Malformed HTTP status line: {header_lines[0]}")

        try:
            status_code = int(status_line[1])
        except ValueError as exc:
            raise UrlSafetyError(f"Invalid HTTP status code: {status_line[1]}") from exc

        headers: dict[str, str] = {}
        for line in header_lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        return status_code, headers, body_bytes
