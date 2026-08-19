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

extract_daily_energy = MODULE.extract_daily_energy
extract_live_event = MODULE.extract_live_event
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


def test_pick_primary_device_returns_none_without_controlling_load() -> None:
    devices = [{"id": 1, "controlling_load": 0}, {"id": 2, "controlling_load": 0}]
    assert pick_primary_device(devices) is None


def test_normalize_device_entry_rejects_invalid_state_and_ids() -> None:
    normalized = normalize_device_entry(
        {"loadState": "invalid", "online": None, "device": {"id": 0, "locationId": "bad"}}
    )
    assert normalized["id"] is None
    assert normalized["location_id"] is None
    assert normalized["load_state"] is None
    assert normalized["online"] is None


def test_parse_locations_ignores_invalid_result_shape() -> None:
    assert parse_locations({"result": "invalid"}) == []


def test_extract_daily_energy_converts_signed_wh_totals_to_positive_kwh() -> None:
    result = extract_daily_energy(
        {
            "success": True,
            "result": {
                "xAxis": ["13-08-2026"],
                "seriesList": [
                    {"name": "Solar", "totalWh": 12345.6, "dataWh": [12345.6]},
                    {"name": "Export", "totalWh": -2345.6, "dataWh": [-2345.6]},
                    {"name": "Import", "totalWh": 456.7, "dataWh": [456.7]},
                    {"name": "Ignored", "totalWh": 999, "dataWh": [999]},
                ],
            },
        }
    )

    assert result["series"] == {
        "solar_yield_energy": 12.346,
        "grid_export_energy": 2.346,
        "grid_import_energy": 0.457,
    }
    assert result["raw_total_wh"]["grid_export_energy"] == -2345.6
    assert result["x_axis"] == ["13-08-2026"]


def test_extract_live_event_discovers_site_actor_and_channel_values() -> None:
    result = extract_live_event(_load_fixture("live_event.json"))

    assert result["site_power"] == {
        "mains_power": -250.0,
        "solar_power": 4200.0,
        "house_power": 3950.0,
        "battery_power": 0.0,
    }
    assert result["limits"] == {"import_limit": 15000.0, "active_control": -5000.0}
    assert result["actors"][0]["class"] == "OTHER"
    assert result["actors"][0]["state"] == "ON"
    assert result["actors"][1]["soc"] == 73.0
    assert result["channels"] == [
        {
            "key": "LOAD:Hot Water",
            "name": "Hot Water",
            "type": "LOAD",
            "power": 3600.0,
        }
    ]
