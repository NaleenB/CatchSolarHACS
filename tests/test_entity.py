from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("homeassistant")

from custom_components.catchsolar.binary_sensor import CatchSolarLoadStateBinarySensor
from custom_components.catchsolar.entity import CatchSolarCoordinatorEntity
from custom_components.catchsolar.sensor import CatchSolarPowerSensor


def _build_coordinator() -> SimpleNamespace:
    return SimpleNamespace(
        data={
            "location": {"id": 8382, "name": "Catch Solar 8382"},
            "primary_device_id": 3649,
            "last_polled_at": "2026-06-29T00:30:21+00:00",
            "power": {
                "timestamp_ms": 1782685500000,
                "series": {
                    "solar_power": -2797.16,
                    "total_consumption_power": None,
                    "export_import_power": -41.12,
                },
                "latest_non_null_series": {
                    "solar_power": -2797.16,
                    "total_consumption_power": 0,
                    "export_import_power": -41.12,
                },
            },
            "devices": [
                {
                    "id": 3649,
                    "device_name": "Water Heater",
                    "device_type": "SR",
                    "serial_number": "ABC123",
                    "load_state": 1,
                    "online": 1,
                    "impl_class": "Relay",
                }
            ],
        },
        config={},
    )


def test_coordinator_entity_exposes_catchsolar_device_without_shadowing_core_properties() -> None:
    entity = CatchSolarCoordinatorEntity(_build_coordinator(), 3649)

    assert entity.catchsolar_device == {
        "id": 3649,
        "device_name": "Water Heater",
        "device_type": "SR",
        "serial_number": "ABC123",
        "load_state": 1,
        "online": 1,
        "impl_class": "Relay",
    }
    assert not hasattr(type(entity), "device_entry")


def test_load_state_binary_sensor_reads_primary_device_state() -> None:
    entity = CatchSolarLoadStateBinarySensor(_build_coordinator(), 3649)

    assert entity.is_on is True
    assert entity.extra_state_attributes["raw_load_state"] == 1


def test_power_sensor_exposes_raw_bucket_metadata() -> None:
    entity = CatchSolarPowerSensor(_build_coordinator(), "total_consumption_power", "Monocle Total Consumption Power")

    assert entity.native_value is None
    assert entity.extra_state_attributes["series_key"] == "total_consumption_power"
    assert entity.extra_state_attributes["series_resolution_seconds"] == 300
    assert entity.extra_state_attributes["latest_non_null_value"] == 0
    assert entity.extra_state_attributes["timestamp_local"] == "2026-06-29T08:25:00+10:00"
    assert entity.extra_state_attributes["last_polled_at"] == "2026-06-29T00:30:21+00:00"
