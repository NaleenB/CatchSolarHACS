"""pytest fixtures for Catch Solar HACS tests.

Tests that require the ``hass`` fixture rely on the
``pytest-homeassistant-custom-component`` package, which is the
standard test harness for Home Assistant custom integrations.

Install it before running the test suite:

    pip install pytest-homeassistant-custom-component

The CI workflow installs this package before running the suite. The HA-backed
tests intentionally fail fast when the harness is missing so CI cannot report
a false-green result with most integration tests skipped.
"""

from __future__ import annotations
