from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSING_PATH = ROOT / "custom_components" / "catchsolar" / "parsing.py"
SPEC = importlib.util.spec_from_file_location("catchsolar_parsing", PARSING_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

extract_latest_power_series = MODULE.extract_latest_power_series
normalize_device_entry = MODULE.normalize_device_entry
parse_locations = MODULE.parse_locations


def _load_fixture(name: str):
    return json.loads((Path(__file__).parent / "fixtures" / name).read_text())


def test_parse_locations() -> None:
    locations = parse_locations(_load_fixture("locations.json"))
    assert len(locations) == 1
    assert locations[0]["id"] == 1234


def test_normalize_device_entry() -> None:
    devices = _load_fixture("devices.json")
    normalized = normalize_device_entry(devices[0])
    assert normalized["id"] == 9001
    assert normalized["load_state"] == 1
    assert normalized["online"] == 1
    assert normalized["serial_number"] == "SERIAL-001"


def test_extract_latest_power_series() -> None:
    payload = _load_fixture("data24.json")
    result = extract_latest_power_series(payload)
    assert result["timestamp_ms"] == 1782646500000
    assert result["series"]["solar_power"] == 1200
    assert result["series"]["total_consumption_power"] == 900
    assert result["series"]["export_import_power"] == 300
    assert "undefined" not in result["series"]
