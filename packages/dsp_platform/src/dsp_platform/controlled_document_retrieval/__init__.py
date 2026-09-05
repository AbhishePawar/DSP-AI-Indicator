"""Controlled HTTPS document retrieval behind PrimarySourceDocumentRetrievalPort.

Production protocol factories do not import this package. Test doubles live
in testing.py.
"""

from __future__ import annotations

from dsp_platform.controlled_document_retrieval.adapter import (
    ALLOWED_MEDIA_TYPES,
    MAX_DOCUMENT_BYTES,
    MAX_REDIRECTS,
    RETRIEVAL_TIMEOUT_SECONDS,
    ControlledHttpsDocumentRetrieval,
)
from dsp_platform.controlled_document_retrieval.policy import (
    SCREENER_WEB_HOSTS,
    TIER_1_WEB_HOSTS,
    source_tier_for_host,
)
from dsp_platform.controlled_document_retrieval.ssrf import (
    BLOCKED_HOSTNAMES,
    assert_public_https_locator,
    hosts_equivalent,
)

__all__ = [
    "ALLOWED_MEDIA_TYPES",
    "BLOCKED_HOSTNAMES",
    "ControlledHttpsDocumentRetrieval",
    "MAX_DOCUMENT_BYTES",
    "MAX_REDIRECTS",
    "RETRIEVAL_TIMEOUT_SECONDS",
    "SCREENER_WEB_HOSTS",
    "TIER_1_WEB_HOSTS",
    "assert_public_https_locator",
    "hosts_equivalent",
    "source_tier_for_host",
]
