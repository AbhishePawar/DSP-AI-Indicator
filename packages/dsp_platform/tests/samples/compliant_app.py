"""Compliant application sample — imports only public surface."""

from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from dsp_platform import DSPPlatform, PlatformConfig

# Placeholder illustrating legal application imports only.
_ = (date, Instrument, AssetClass, DSPPlatform, PlatformConfig)
