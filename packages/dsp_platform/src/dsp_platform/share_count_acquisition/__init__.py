"""Generic listed-equity T1 evidence acquisition — not production authority.

Connectors normalize official JSON/text into DSP evidence objects.
Live NSE/BSE HTTP remains PENDING for promotion; recorded pages are
the unit-test path. Gemini is never called.
"""

from __future__ import annotations

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
from dsp_platform.share_count_acquisition.models import (
    ExchangeAcquisitionRequest,
    ExchangeAcquisitionResult,
    ShareCountEvidenceClaim,
)
from dsp_platform.share_count_acquisition.nse import acquire_nse_disclosures
from dsp_platform.share_count_acquisition.pipeline import (
    attest_exchange_bundle,
    refresh_from_acquired_evidence,
)

__all__ = [
    "CoverageRow",
    "ExchangeAcquisitionRequest",
    "ExchangeAcquisitionResult",
    "IssuerEvidenceSource",
    "JsonHttpPort",
    "RecordedJsonHttp",
    "ShareCountCoverageIndex",
    "ShareCountEvidenceClaim",
    "acquire_bse_disclosures",
    "acquire_nse_disclosures",
    "attest_exchange_bundle",
    "extract_outstanding_observation",
    "refresh_from_acquired_evidence",
]
