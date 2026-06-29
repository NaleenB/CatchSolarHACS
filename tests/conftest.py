"""pytest fixtures for Catch Solar HACS tests.

Tests that require the ``hass`` fixture rely on the
``pytest-homeassistant-custom-component`` package, which is the
standard test harness for Home Assistant custom integrations.

Install it before running the test suite:

    pip install pytest-homeassistant-custom-component

If the package is not installed, individual tests import-guard with
``pytest.importorskip("homeassistant")`` and will be skipped rather
than failing the suite.
"""

from __future__ import annotations
