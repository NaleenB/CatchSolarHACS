from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELPERS_PATH = ROOT / "custom_components" / "catchsolar" / "diagnostics_helpers.py"
SPEC = importlib.util.spec_from_file_location("catchsolar_diagnostics_helpers", HELPERS_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

redact_value = MODULE.redact_value


def test_redact_value_redacts_nested_credentials() -> None:
    value = {
        "username": "person@example.com",
        "password": "secret",
        "device": {"token": "abc", "serialNumber": "SERIAL-001"},
        "items": [{"accessToken": "xyz", "name": "item"}],
    }

    result = redact_value(value)

    assert result["username"] == "**REDACTED**"
    assert result["password"] == "**REDACTED**"
    assert result["device"]["token"] == "**REDACTED**"
    assert result["device"]["serialNumber"] == "SERIAL-001"
    assert result["items"][0]["accessToken"] == "**REDACTED**"
