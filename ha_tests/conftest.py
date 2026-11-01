"""Expose this checkout alongside the test harness's own custom components."""

from pathlib import Path

import custom_components

# The HA fixture adds its testing configuration to sys.path. Explicitly include
# our source directory even when that configuration supplies a regular package.
custom_components.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components"),
    *custom_components.__path__,
]

pytest_plugins = "pytest_homeassistant_custom_component"
