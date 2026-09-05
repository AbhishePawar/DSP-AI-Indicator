"""Generic listed-equity T1 evidence acquisition — not production authority.

Connectors normalize official JSON/text into DSP evidence objects.
Live NSE/BSE HTTP remains PENDING for promotion; recorded pages are
the unit-test path. Gemini is never called.
"""

from __future__ import annotations

from dsp_platform.share_count_acquisition.artifacts import public_json, write_artifact
from dsp_platform.share_count_acquisition.bse import acquire_bse_disclosures
from dsp_platform.share_count_acquisition.coverage import (
    CoverageRow,
    ShareCountCoverageIndex,
)
from dsp_platform.share_count_acquisition.http import JsonHttpPort, RecordedJsonHttp
from dsp_platform.share_count_acquisition.issuer import (
    IssuerEvidenceSource,
    extract_outstanding_observation,
)
from dsp_platform.share_count_acquisition.live_http import AllowlistedLiveJsonHttp
from dsp_platform.share_count_acquisition.models import (
    ExchangeAcquisitionRequest,
    ExchangeAcquisitionResult,
    ShareCountEvidenceClaim,
)
from dsp_platform.share_count_acquisition.nse import acquire_nse_disclosures
from dsp_platform.share_count_acquisition.operator import (
    acquire_listed_equity,
    acquire_universe,
    promote_candidate_file,
)
from dsp_platform.share_count_acquisition.pipeline import (
    attest_exchange_bundle,
    refresh_from_acquired_evidence,
)
from dsp_platform.share_count_acquisition.policy import iter_source_policy
from dsp_platform.share_count_acquisition.universe import get_listed_equity, iter_listed_equities

__all__ = [
    "AllowlistedLiveJsonHttp",
    "CoverageRow",
    "ExchangeAcquisitionRequest",
    "ExchangeAcquisitionResult",
    "IssuerEvidenceSource",
    "JsonHttpPort",
    "RecordedJsonHttp",
    "ShareCountCoverageIndex",
    "ShareCountEvidenceClaim",
    "acquire_bse_disclosures",
    "acquire_listed_equity",
    "acquire_nse_disclosures",
    "acquire_universe",
    "attest_exchange_bundle",
    "extract_outstanding_observation",
    "get_listed_equity",
    "iter_listed_equities",
    "iter_source_policy",
    "promote_candidate_file",
    "public_json",
    "refresh_from_acquired_evidence",
    "write_artifact",
]
