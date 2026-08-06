"""DSP API Platform — HTTP surface over ``dsp_platform`` (K1.1).

Contains no business logic. Routes validate HTTP schemas and delegate to
``DSPPlatform`` public methods only.
"""

from __future__ import annotations

from api_platform.api.app import app, create_app

__all__ = [
    "app",
    "create_app",
    "__version__",
]

__version__ = "0.3.0"
