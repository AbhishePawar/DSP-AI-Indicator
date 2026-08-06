"""RC1 Milestone 11 — Super Admin Control Center (configuration OS)."""

from __future__ import annotations

from dsp_platform.control_center.defaults import DEFAULT_REGISTRY, MODULE_IDS
from dsp_platform.control_center.registry import (
    ConfigurationRegistry,
    get_configuration_registry,
    reset_configuration_registry_for_tests,
)
from dsp_platform.control_center.service import (
    CONTROL_CENTER_SCHEMA_VERSION,
    CONTROL_CENTER_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    control_center_schema,
    run_control_center,
)

__all__ = [
    "CONTROL_CENTER_SCHEMA_VERSION",
    "CONTROL_CENTER_SERVICE_VERSION",
    "DEFAULT_REGISTRY",
    "MODULE_IDS",
    "UNAVAILABLE_MESSAGE",
    "ConfigurationRegistry",
    "control_center_schema",
    "get_configuration_registry",
    "reset_configuration_registry_for_tests",
    "run_control_center",
]
