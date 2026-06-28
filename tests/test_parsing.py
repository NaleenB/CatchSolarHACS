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
pick_primary_device = MODULE.pick_primary_device


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
    assert normalized["impl_class"] == "solar-relay/SolarRelay"


def test_pick_primary_device_prefers_controlling_load() -> None:
    devices = [
        {"id": 1, "controlling_load": 0},
        {"id": 2, "controlling_load": 1},
    ]
    assert pick_primary_device(devices) == {"id": 2, "controlling_load": 1}


def test_pick_primary_device_falls_back_to_first_device() -> None:
    devices = [{"id": 1, "controlling_load": 0}, {"id": 2, "controlling_load": 0}]
    assert pick_primary_device(devices) == {"id": 1, "controlling_load": 0}


def test_parse_locations_ignores_invalid_result_shape() -> None:
    assert parse_locations({"result": "invalid"}) == []


def test_extract_latest_power_series() -> None:
    payload = _load_fixture("data24.json")
    result = extract_latest_power_series(payload)
    assert result["timestamp_ms"] == 1782646500000
    assert result["series"]["solar_power"] == 1200
    assert result["series"]["total_consumption_power"] == 900
    assert result["series"]["export_import_power"] == 300
    assert result["latest_non_null_series"]["solar_power"] == 1200
    assert "undefined" not in result["series"]


def test_extract_latest_power_series_keeps_latest_value_and_tracks_non_null_fallback() -> None:
    payload = {
        "result": {
            "xAxis": [1, 2, 3],
            "seriesList": [
                {"name": "Solar", "data": [1000, None, None]},
                {"name": "Total Consumption", "data": [None, 800, None]},
            ],
        }
    }
    result = extract_latest_power_series(payload)
    assert result["timestamp_ms"] == 3
    assert result["series"]["solar_power"] is None
    assert result["series"]["total_consumption_power"] is None
    assert result["latest_non_null_series"]["solar_power"] == 1000
    assert result["latest_non_null_series"]["total_consumption_power"] == 800
